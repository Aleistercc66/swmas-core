#!/usr/bin/env python3
"""
Real-Time WebSocket Sniper - Sub-second Opportunity Detection
Χρησιμοποιεί WebSockets για real-time data από Pump.fun και Solana.
"""

import asyncio
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️ websockets module not available - WebSocket sniper disabled")
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SnipeSignal:
    """Signal για snipe."""
    token_address: str
    symbol: str
    
    # Launch data
    launch_timestamp: float = 0.0
    market_cap_at_launch: float = 0.0
    
    # Early metrics (first 10-30 seconds)
    initial_buyers: int = 0
    initial_volume: float = 0.0
    initial_price: float = 0.0
    
    # Scores
    snipe_score: float = 0.0  # 0-100
    urgency: str = "normal"  # critical/high/normal
    
    # Safety
    safety_check_passed: bool = False
    
    # Metadata
    detected_at: float = field(default_factory=time.time)
    source: str = "websocket"  # websocket/pump_portal/blockchain


class WebSocketSniper:
    """
    Real-time sniper που χρησιμοποιεί WebSockets.
    
    Υποστηρίζει:
    - PumpPortal WebSocket (Pump.fun launches)
    - Solana logsSubscribe (on-chain events)
    - Blocknative / Helius (premium RPC)
    """
    
    def __init__(self):
        self.pump_portal_ws = "wss://pumpportal.fun/api/data"
        self.solana_ws = "wss://api.mainnet-beta.solana.com"
        
        # Callbacks
        self.on_new_token: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_graduation: Optional[Callable] = None
        
        # Tracking
        self.recent_launches: Dict[str, SnipeSignal] = {}
        self.monitored_tokens: set = set()
        
        # Config
        self.evaluation_window_seconds = 10  # First 10 seconds
        self.min_snipe_score = 70
        
        # Stats
        self.tokens_detected: int = 0
        self.signals_generated: int = 0
        self.websocket_errors: int = 0
    
    async def connect_pump_portal(self):
        """Connect to PumpPortal WebSocket."""
        if not WEBSOCKETS_AVAILABLE:
            print("⚠️ WebSocket sniper disabled (websockets module missing)")
            await asyncio.sleep(3600)  # Sleep long, retry later
            return
        
        try:
            async with websockets.connect(self.pump_portal_ws) as ws:
                print("🔌 Connected to PumpPortal WebSocket")
                
                # Subscribe to new token launches
                subscribe_msg = {
                    "method": "subscribeNewToken",
                }
                await ws.send(json.dumps(subscribe_msg))
                
                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(message)
                        
                        await self._handle_pump_message(data)
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep alive
                        await ws.send(json.dumps({"method": "ping"}))
                    except Exception as e:
                        # Rate-limit error logging to prevent log flooding
                        self.websocket_errors += 1
                        if self.websocket_errors <= 5 or self.websocket_errors % 100 == 0:
                            print(f"⚠️ WebSocket message error: {e} (total: {self.websocket_errors})")
                        await asyncio.sleep(1)
                        
        except Exception as e:
            if self.websocket_errors <= 5 or self.websocket_errors % 20 == 0:
                print(f"❌ PumpPortal WebSocket error: {e} (total errors: {self.websocket_errors})")
            self.websocket_errors += 1
            # Exponential backoff: max 60s
            backoff = min(5 * (2 ** min(self.websocket_errors // 10, 6)), 60)
            await asyncio.sleep(backoff)
            # Retry connection
            await self.connect_pump_portal()
    
    async def _handle_pump_message(self, data: Dict):
        """Handle PumpPortal message."""
        msg_type = data.get("type", "")
        
        if msg_type == "newToken":
            # New token launched!
            token_address = data.get("mint", "")
            symbol = data.get("symbol", "UNKNOWN")
            
            self.tokens_detected += 1
            print(f"\n🚀 NEW TOKEN: {symbol} | {token_address[:20]}...")
            
            # Create signal
            signal = SnipeSignal(
                token_address=token_address,
                symbol=symbol,
                launch_timestamp=time.time(),
                initial_price=data.get("initialPrice", 0),
                source="pump_portal",
            )
            
            self.recent_launches[token_address] = signal
            
            # Start evaluation window
            asyncio.create_task(self._evaluate_token(signal))
            
            # Notify callback
            if self.on_new_token:
                asyncio.create_task(self.on_new_token(signal))
        
        elif msg_type == "trade":
            # Trade event
            token_address = data.get("mint", "")
            if token_address in self.recent_launches:
                signal = self.recent_launches[token_address]
                
                # Update metrics
                signal.initial_volume += data.get("solAmount", 0)
                signal.initial_buyers += 1
        
        elif msg_type == "graduation":
            # Token graduated!
            token_address = data.get("mint", "")
            print(f"🎓 TOKEN GRADUATED: {token_address[:20]}...")
            
            if self.on_graduation:
                asyncio.create_task(self.on_graduation(token_address))
    
    async def _evaluate_token(self, signal: SnipeSignal):
        """Evaluate token during first 10-30 seconds."""
        
        # Wait for evaluation window
        await asyncio.sleep(self.evaluation_window_seconds)
        
        # Calculate snipe score
        score = self._calculate_snipe_score(signal)
        signal.snipe_score = score
        
        if score >= self.min_snipe_score:
            signal.urgency = "critical" if score >= 90 else "high"
            self.signals_generated += 1
            
            print(f"🎯 SNIPE SIGNAL: {signal.symbol}")
            print(f"   Score: {score:.0f}/100 | Urgency: {signal.urgency}")
            print(f"   Buyers: {signal.initial_buyers} | Volume: {signal.initial_volume:.2f} SOL")
            
            # Notify
            if self.on_trade:
                asyncio.create_task(self.on_trade(signal))
        else:
            print(f"   ℹ️ {signal.symbol} score too low: {score:.0f}")
    
    def _calculate_snipe_score(self, signal: SnipeSignal) -> float:
        """Calculate snipe score for new token."""
        score = 0.0
        
        # Volume in first 10 seconds (most important)
        if signal.initial_volume >= 50:  # 50+ SOL in 10s
            score += 40
        elif signal.initial_volume >= 20:
            score += 30
        elif signal.initial_volume >= 10:
            score += 20
        elif signal.initial_volume >= 5:
            score += 10
        
        # Number of buyers
        if signal.initial_buyers >= 50:
            score += 25
        elif signal.initial_buyers >= 20:
            score += 20
        elif signal.initial_buyers >= 10:
            score += 15
        elif signal.initial_buyers >= 5:
            score += 10
        
        # Price action
        if signal.initial_price > 0:
            # Check if price already moving up
            pass  # Would need price history
        
        # Symbol/name analysis
        symbol_lower = signal.symbol.lower()
        if any(kw in symbol_lower for kw in ["pepe", "doge", "shib", "bonk", "wif"]):
            score += 10  # Known meme themes
        
        # Time factor (earlier = better)
        age_seconds = time.time() - signal.launch_timestamp
        if age_seconds < 5:
            score += 15
        elif age_seconds < 10:
            score += 10
        elif age_seconds < 20:
            score += 5
        
        return min(100, score)
    
    async def start_monitoring(self):
        """Start all WebSocket connections."""
        print("🎯 WebSocket Sniper starting...")
        
        # Run PumpPortal connection
        await self.connect_pump_portal()
    
    def get_stats(self) -> Dict:
        """Get sniper statistics."""
        return {
            "tokens_detected": self.tokens_detected,
            "signals_generated": self.signals_generated,
            "websocket_errors": self.websocket_errors,
            "recent_launches": len(self.recent_launches),
            "monitored_tokens": len(self.monitored_tokens),
        }


if __name__ == "__main__":
    sniper = WebSocketSniper()
    
    # Set up callbacks
    async def on_new(signal):
        print(f"New callback: {signal.symbol}")
    
    async def on_trade(signal):
        print(f"Trade callback: {signal.symbol} score={signal.snipe_score}")
    
    sniper.on_new_token = on_new
    sniper.on_trade = on_trade
    
    print("🎯 WebSocket Sniper initialized")
    print(f"   Evaluation window: {sniper.evaluation_window_seconds}s")
    print(f"   Min snipe score: {sniper.min_snipe_score}")
