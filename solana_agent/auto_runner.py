#!/usr/bin/env python3
"""
Solana Profit Agent - AUTO-RUNNER (Production)
Τρέχει αυτόματα 24/7 με real data, real prices, Telegram alerts.
Χρήση: python auto_runner.py
"""

import asyncio
import aiohttp
import json
import time
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Import all modules
from learning_engine import SolanaKnowledgeBase
from historian import SolanaHistorian
from opportunity_scanner import OpportunityScanner, TradeSetup
from strategy_engine import StrategyEngine
from execution_layer import ExecutionEngine
from risk_manager import RiskManager
from telegram_alerts import TelegramAlerter, AlertConfig
from pumpfun_tracker import PumpFunTracker
from token_safety import TokenSafetyAnalyzer
from mev_protection import MEVProtection, MEVConfig
from websocket_sniper import WebSocketSniper, SnipeSignal
from jupiter_client import JupiterClient, JupiterSwapConfig
from training_engine import SuperiorTrainingEngine


class SolanaAutoRunner:
    """
    Production auto-runner για Solana Profit Agent.
    Τρέχει 24/7, χρησιμοποιεί πραγματικά data, στέλνει Telegram alerts.
    """
    
    def __init__(self):
        print("🔥🔥🔥 SOLANA AUTO-RUNNER INITIALIZING 🔥🔥🔥")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Configuration
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Check config
        if not self.telegram_token or not self.telegram_chat_id:
            print("❌ ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables!")
            print("   export TELEGRAM_BOT_TOKEN='your_token'")
            print("   export TELEGRAM_CHAT_ID='your_chat_id'")
            sys.exit(1)
        
        # Initialize all systems
        self.kb = SolanaKnowledgeBase()
        self.historian = SolanaHistorian()
        self.scanner = OpportunityScanner(self.kb, self.historian)
        self.strategy_engine = StrategyEngine()
        self.execution = ExecutionEngine()  # No wallet = alerts only mode
        self.risk = RiskManager()
        
        self.pump_tracker = PumpFunTracker()
        self.safety = TokenSafetyAnalyzer()
        self.mev = MEVProtection(MEVConfig())
        self.jupiter = JupiterClient(JupiterSwapConfig())
        self.trainer = SuperiorTrainingEngine(self.kb, self.historian, self.strategy_engine, self.risk)
        
        # Telegram alerter
        alert_config = AlertConfig(
            bot_token=self.telegram_token,
            chat_id=self.telegram_chat_id,
        )
        self.alerter = TelegramAlerter(alert_config)
        
        # WebSocket sniper
        self.ws_sniper = WebSocketSniper()
        self.ws_sniper.on_new_token = self._handle_ws_new_token
        self.ws_sniper.on_trade = self._handle_ws_trade
        
        # State
        self.running = False
        self.start_time = time.time()
        self.cycle_count = 0
        self.active_alerts: Dict[str, Dict] = {}  # token -> alert info
        
        # Intervals (seconds)
        self.scan_interval = 180      # 3 minutes
        self.price_check_interval = 60  # 1 minute
        self.training_interval = 21600  # 6 hours
        
        # Load previous state
        self._load_state()
        
        print("✅ ALL SYSTEMS OPERATIONAL")
        print(f"   Telegram: {self.telegram_chat_id}")
        print(f"   Scan interval: {self.scan_interval}s")
        print(f"   Price check: {self.price_check_interval}s")
        print("="*70)
    
    async def start(self):
        """Start the auto-runner."""
        self.running = True
        
        # Send startup notification
        await self._send_startup_message()
        
        # Start all background tasks
        tasks = [
            asyncio.create_task(self._scanning_loop()),
            asyncio.create_task(self._price_monitor_loop()),
            asyncio.create_task(self._training_loop()),
            asyncio.create_task(self._ws_sniper_loop()),
            asyncio.create_task(self._status_report_loop()),
        ]
        
        print("\n🚀 AUTO-RUNNER STARTED - Monitoring Solana 24/7")
        print("   Waiting for opportunities...\n")
        
        await asyncio.gather(*tasks)
    
    async def _scanning_loop(self):
        """Main scanning loop - every 3 minutes."""
        while self.running:
            try:
                await self._run_scan_cycle()
                self.cycle_count += 1
            except Exception as e:
                print(f"❌ Scan error: {e}")
                await self._send_error_alert(f"Scan error: {e}")
            
            await asyncio.sleep(self.scan_interval)
    
    async def _run_scan_cycle(self):
        """One scan cycle with real data."""
        cycle_start = time.time()
        
        async with aiohttp.ClientSession() as session:
            # 1. Fetch real data from DexScreener
            print(f"\n🔍 CYCLE #{self.cycle_count} | {datetime.now().strftime('%H:%M:%S')}")
            
            trending = await self._fetch_trending_tokens(session)
            print(f"   📊 Fetched {len(trending)} trending tokens")
            
            # 2. Analyze each token
            opportunities = []
            for token in trending[:20]:  # Top 20
                try:
                    opp = await self._analyze_token(session, token)
                    if opp and opp.opportunity_score >= 60:
                        opportunities.append(opp)
                except Exception as e:
                    print(f"   ⚠️ Error analyzing {token.get('symbol', '?')}: {e}")
            
            # 3. Sort by score
            opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
            
            # 4. Send alerts for high-confidence opportunities
            for opp in opportunities[:3]:  # Top 3
                if opp.opportunity_score >= 70:
                    await self._send_buy_alert(session, opp)
            
            # 5. Check Pump.fun graduations
            await self._check_pump_fun_graduations(session)
            
            cycle_time = time.time() - cycle_start
            print(f"   ✅ Cycle complete in {cycle_time:.1f}s | {len(opportunities)} opportunities")
    
    async def _analyze_token(self, session: aiohttp.ClientSession, token: Dict) -> Optional[TradeSetup]:
        """Analyze single token for opportunity."""
        
        address = token.get("baseToken", {}).get("address", "")
        symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
        
        # Get detailed data
        price = float(token.get("priceUsd", 0))
        volume_24h = token.get("volume", {}).get("h24", 0)
        liquidity = token.get("liquidity", {}).get("usd", 0)
        
        # Price changes
        changes = token.get("priceChange", {})
        h1 = changes.get("h1", 0)
        h6 = changes.get("h6", 0)
        h24 = changes.get("h24", 0)
        
        # Safety check
        safety = self.safety.quick_safety_check({
            "liquidity": liquidity,
            "volume_24h": volume_24h,
            "changes": changes,
        })
        
        if not safety.get("is_safe", False):
            return None
        
        # Calculate opportunity score
        score = 0
        
        # Momentum (weight: 30%)
        momentum_score = min(100, max(0, (h1 + h6 * 0.5) * 2))
        score += momentum_score * 0.30
        
        # Volume (weight: 25%)
        if volume_24h > 50000:
            vol_score = 100
        elif volume_24h > 10000:
            vol_score = 70
        elif volume_24h > 5000:
            vol_score = 50
        else:
            vol_score = 20
        score += vol_score * 0.25
        
        # Liquidity (weight: 20%)
        if liquidity > 100000:
            liq_score = 100
        elif liquidity > 50000:
            liq_score = 80
        elif liquidity > 20000:
            liq_score = 60
        else:
            liq_score = 30
        score += liq_score * 0.20
        
        # Historical pattern (weight: 15%)
        hist_score = self.historian.assess_historical_setup(token)
        score += hist_score * 0.15
        
        # Risk (weight: 10%) - higher = safer = better score
        risk_score = max(0, 100 - safety.get("score", 50))
        score += risk_score * 0.10
        
        final_score = min(100, score)
        
        if final_score < 60:
            return None
        
        # Determine strategy and targets
        if h1 > 15 and volume_24h > 30000:
            strategy = "early_momentum"
            target = 25
            stop = -15
        elif h24 > 30 and h1 < -5:
            strategy = "pullback"
            target = 20
            stop = -15
        elif volume_24h > 50000:
            strategy = "volume_breakout"
            target = 30
            stop = -15
        else:
            strategy = "early_momentum"
            target = 15
            stop = -15
        
        # Risk/Reward
        rr = target / abs(stop)
        
        return TradeSetup(
            token_address=address,
            symbol=symbol,
            entry_price=price,
            target_return=target,
            tp1=target * 0.4,
            tp2=target * 0.7,
            tp3=target,
            stop_loss=stop,
            risk_reward=rr,
            opportunity_score=final_score,
            catalyst=strategy,
            urgency="critical" if final_score >= 85 else "high" if final_score >= 75 else "normal",
        )
    
    async def _price_monitor_loop(self):
        """Monitor prices for exit triggers."""
        while self.running:
            try:
                await self._check_exit_conditions()
            except Exception as e:
                print(f"❌ Price monitor error: {e}")
            
            await asyncio.sleep(self.price_check_interval)
    
    async def _check_exit_conditions(self):
        """Check if any active positions hit targets or stops."""
        
        if not self.active_alerts:
            return
        
        async with aiohttp.ClientSession() as session:
            for token_address, alert_info in list(self.active_alerts.items()):
                try:
                    # Get current price
                    current_price = await self._get_current_price(session, token_address)
                    if not current_price:
                        continue
                    
                    entry_price = alert_info["entry_price"]
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    # Check targets
                    tp1 = alert_info.get("tp1")
                    tp2 = alert_info.get("tp2")
                    tp3 = alert_info.get("tp3")
                    stop = alert_info.get("stop_loss")
                    symbol = alert_info["symbol"]
                    
                    # Exit checks
                    exited = False
                    exit_reason = ""
                    
                    if tp3 and pnl_pct >= tp3:
                        exited = True
                        exit_reason = f"🎯 TP3 HIT! +{pnl_pct:.1f}%"
                    elif tp2 and pnl_pct >= tp2:
                        # Send TP2 alert (partial exit)
                        await self._send_tp_alert(session, symbol, token_address, current_price, pnl_pct, "TP2", tp3)
                    elif tp1 and pnl_pct >= tp1:
                        # Send TP1 alert (partial exit)
                        await self._send_tp_alert(session, symbol, token_address, current_price, pnl_pct, "TP1", tp2)
                    elif stop and pnl_pct <= stop:
                        exited = True
                        exit_reason = f"🛑 STOP LOSS HIT: {pnl_pct:.1f}%"
                    
                    if exited:
                        await self._send_sell_alert(session, symbol, token_address, current_price, pnl_pct, exit_reason)
                        del self.active_alerts[token_address]
                        
                except Exception as e:
                    print(f"   ⚠️ Error checking {token_address}: {e}")
    
    async def _training_loop(self):
        """Run training every 6 hours."""
        while self.running:
            try:
                print("\n🎓 Starting training cycle...")
                async with aiohttp.ClientSession() as session:
                    results = await self.trainer.run_full_training(session)
                    
                    # Apply improvements
                    for result in results:
                        if result.model_updates:
                            if result.module == "opportunity_model" and result.model_updates.get("weights"):
                                print(f"   🎯 Updated opportunity weights")
                            elif result.module == "risk_calibration":
                                stop = result.model_updates.get("optimal_stop")
                                if stop:
                                    print(f"   🛡️ Updated stop loss to {stop:.1f}%")
                
                    await self._send_training_alert(results)
                    
            except Exception as e:
                print(f"❌ Training error: {e}")
            
            await asyncio.sleep(self.training_interval)
    
    async def _ws_sniper_loop(self):
        """WebSocket sniper for real-time launches."""
        try:
            await self.ws_sniper.start_monitoring()
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await asyncio.sleep(60)
            # Retry
            asyncio.create_task(self._ws_sniper_loop())
    
    async def _status_report_loop(self):
        """Send periodic status reports."""
        while self.running:
            await asyncio.sleep(3600)  # Every hour
            
            try:
                uptime = time.time() - self.start_time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                
                report = (
                    f"📊 STATUS REPORT\n"
                    f"Uptime: {hours}h {minutes}m\n"
                    f"Cycles: {self.cycle_count}\n"
                    f"Active alerts: {len(self.active_alerts)}\n"
                    f"Scanner: {self.ws_sniper.get_stats() if hasattr(self.ws_sniper, 'get_stats') else 'N/A'}"
                )
                
                await self._send_message(report)
                
            except Exception as e:
                print(f"❌ Status report error: {e}")
    
    # Alert methods
    
    async def _send_buy_alert(self, session: aiohttp.ClientSession, opp: TradeSetup):
        """Send BUY alert with exact instructions."""
        
        # Jupiter swap link
        jupiter_link = f"https://jup.ag/swap/SOL-{opp.token_address}"
        
        message = (
            f"🔥🔥🔥 BUY ALERT 🔥🔥🔥\n\n"
            f"🪙 Token: {opp.symbol}\n"
            f"📍 Address: {opp.token_address}\n"
            f"💰 Entry Price: ${opp.entry_price:.6f}\n\n"
            f"🎯 TARGETS:\n"
            f"   TP1 (+{opp.tp1:.1f}%) | TP2 (+{opp.tp2:.1f}%) | TP3 (+{opp.tp3:.1f}%)\n"
            f"🛑 Stop Loss: {opp.stop_loss:.1f}%\n"
            f"📊 Risk/Reward: {opp.risk_reward:.1f}x\n"
            f"💎 Score: {opp.opportunity_score:.0f}/100\n"
            f"⚡ Urgency: {opp.urgency.upper()}\n"
            f"📈 Strategy: {opp.catalyst}\n\n"
            f"🚀 JUPITER SWAP:\n"
            f"{jupiter_link}\n\n"
            f"⏰ Detected: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await self._send_message(message)
        
        # Track active alert
        self.active_alerts[opp.token_address] = {
            "symbol": opp.symbol,
            "entry_price": opp.entry_price,
            "tp1": opp.tp1,
            "tp2": opp.tp2,
            "tp3": opp.tp3,
            "stop_loss": opp.stop_loss,
            "alert_time": time.time(),
        }
        
        print(f"   🚨 BUY ALERT SENT: {opp.symbol} | Score: {opp.opportunity_score}")
    
    async def _send_tp_alert(self, session, symbol: str, address: str, 
                             price: float, pnl: float, tp_level: str, next_tp: float):
        """Send take profit partial exit alert."""
        
        message = (
            f"🎯 {tp_level} HIT: {symbol}\n\n"
            f"💰 Current Price: ${price:.6f}\n"
            f"📈 PnL: +{pnl:.1f}%\n\n"
            f"✅ Sell 30-50% here\n"
            f"🚀 Next target: +{next_tp:.1f}%\n\n"
            f"📍 {address[:20]}..."
        )
        
        await self._send_message(message)
    
    async def _send_sell_alert(self, session, symbol: str, address: str,
                              price: float, pnl: float, reason: str):
        """Send SELL alert."""
        
        jupiter_link = f"https://jup.ag/swap/{address}-SOL"
        
        emoji = "🟢" if pnl > 0 else "🔴"
        
        message = (
            f"{emoji} SELL ALERT: {symbol}\n\n"
            f"{reason}\n\n"
            f"💰 Exit Price: ${price:.6f}\n"
            f"📊 PnL: {pnl:+.1f}%\n\n"
            f"💸 JUPITER SELL:\n"
            f"{jupiter_link}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await self._send_message(message)
        print(f"   🚨 SELL ALERT SENT: {symbol} | PnL: {pnl:+.1f}%")
    
    async def _send_training_alert(self, results: list):
        """Send training results summary."""
        
        total_improvement = sum(r.improvement_pct for r in results)
        
        message = (
            f"🎓 TRAINING COMPLETE\n\n"
            f"📊 Total Improvement: +{total_improvement:.1f}%\n"
            f"🔄 Modules trained: {len(results)}\n\n"
            f"Top improvements:\n"
        )
        
        for r in sorted(results, key=lambda x: x.improvement_pct, reverse=True)[:3]:
            message += f"   {r.module}: +{r.improvement_pct:.1f}%\n"
        
        await self._send_message(message)
    
    async def _send_startup_message(self):
        """Send startup notification."""
        message = (
            f"🔥 SOLANA PROFIT AGENT STARTED 🔥\n\n"
            f"🤖 Auto-runner active\n"
            f"⏰ Scanning every {self.scan_interval}s\n"
            f"📊 Price checks every {self.price_check_interval}s\n"
            f"🎓 Training every {self.training_interval//3600}h\n\n"
            f"Waiting for opportunities..."
        )
        await self._send_message(message)
    
    async def _send_error_alert(self, error: str):
        """Send error notification."""
        message = f"⚠️ ERROR: {error}\n\nAgent will retry automatically."
        await self._send_message(message)
    
    async def _send_message(self, text: str):
        """Send Telegram message."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                }
                
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        print(f"   📤 Telegram sent")
                    else:
                        print(f"   ❌ Telegram failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Telegram error: {e}")
    
    # Data fetching
    
    async def _fetch_trending_tokens(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch trending tokens από DexScreener."""
        
        try:
            # Solana trending
            async with session.get(
                "https://api.dexscreener.com/latest/dex/search?q=solana",
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    
                    # Filter for Solana pairs with good activity
                    solana_pairs = [
                        p for p in pairs
                        if p.get("chainId") == "solana"
                        and p.get("liquidity", {}).get("usd", 0) >= 20000
                        and p.get("volume", {}).get("h24", 0) > 25000
                    ]
                    
                    # Sort by volume * momentum
                    def score(p):
                        vol = p.get("volume", {}).get("h24", 0)
                        change = p.get("priceChange", {}).get("h1", 0)
                        return vol * (1 + change / 100)
                    
                    return sorted(solana_pairs, key=score, reverse=True)[:50]
                    
        except Exception as e:
            print(f"❌ DexScreener error: {e}")
        
        return []
    
    async def _get_current_price(self, session: aiohttp.ClientSession, 
                                  token_address: str) -> Optional[float]:
        """Get real-time price από Jupiter."""
        
        try:
            prices = await self.jupiter.get_token_prices(session, [token_address])
            if prices and token_address in prices:
                return float(prices[token_address].get("price", 0))
        except Exception:
            pass
        
        # Fallback to DexScreener
        try:
            async with session.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        return float(pairs[0].get("priceUsd", 0))
        except Exception:
            pass
        
        return None
    
    async def _check_pump_fun_graduations(self, session: aiohttp.ClientSession):
        """Check Pump.fun for graduation opportunities."""
        
        # Fetch recent Pump.fun tokens
        try:
            # Use internal knowledge base or API
            grad_opps = self.pump_tracker.get_pre_graduation_setups()
            
            for opp in grad_opps[:3]:
                if opp['progress'] >= 85:
                    message = (
                        f"🎓 GRADUATION ALERT: {opp['symbol']}\n\n"
                        f"📈 Progress: {opp['progress']:.1f}%\n"
                        f"💰 Market Cap: ${opp['market_cap']:,.0f}\n"
                        f"👥 Holders: {opp['holders']}\n\n"
                        f"⚡ High probability of graduation pump!\n"
                        f"🚀 Entry before $13K cap!"
                    )
                    await self._send_message(message)
                    
        except Exception as e:
            print(f"⚠️ Pump.fun check error: {e}")
    
    async def _handle_ws_new_token(self, signal: SnipeSignal):
        """Handle new token from WebSocket."""
        print(f"🚀 WS: {signal.symbol} detected")
    
    async def _handle_ws_trade(self, signal: SnipeSignal):
        """Handle snipe signal."""
        if signal.snipe_score >= 75:
            message = (
                f"⚡ SNIPE ALERT: {signal.symbol}\n\n"
                f"🆕 New launch detected!\n"
                f"💎 Snipe Score: {signal.snipe_score:.0f}/100\n"
                f"👥 Early Buyers: {signal.initial_buyers}\n"
                f"💰 Early Volume: {signal.initial_volume:.2f} SOL\n\n"
                f"🚀 ACT FAST!"
            )
            await self._send_message(message)
    
    # Persistence
    
    def _load_state(self):
        """Load previous state."""
        try:
            with open("auto_runner_state.json", 'r') as f:
                state = json.load(f)
                self.active_alerts = state.get("active_alerts", {})
                self.cycle_count = state.get("cycle_count", 0)
                print(f"   📂 Loaded {len(self.active_alerts)} active alerts")
        except FileNotFoundError:
            pass
    
    def _save_state(self):
        """Save current state."""
        state = {
            "active_alerts": self.active_alerts,
            "cycle_count": self.cycle_count,
            "last_save": time.time(),
        }
        with open("auto_runner_state.json", 'w') as f:
            json.dump(state, f, default=str)
    
    def stop(self):
        """Graceful shutdown."""
        print("\n🛑 Stopping auto-runner...")
        self.running = False
        self._save_state()
        
        # Send stop notification
        asyncio.create_task(self._send_message(
            f"🛑 Solana Agent Stopped\n"
            f"Uptime: {int((time.time() - self.start_time) / 3600)}h\n"
            f"Cycles: {self.cycle_count}"
        ))
        
        print("👋 Auto-runner stopped. State saved.")


def signal_handler(runner: SolanaAutoRunner):
    def handler(signum, frame):
        runner.stop()
        sys.exit(0)
    return handler


async def main():
    """Entry point."""
    runner = SolanaAutoRunner()
    
    signal.signal(signal.SIGINT, signal_handler(runner))
    signal.signal(signal.SIGTERM, signal_handler(runner))
    
    try:
        await runner.start()
    except Exception as e:
        print(f"❌ Fatal: {e}")
        runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
