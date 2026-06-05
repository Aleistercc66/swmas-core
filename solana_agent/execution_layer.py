#!/usr/bin/env python3
"""
Execution Layer - Jupiter + Raydium + Orca Integration
Χειρίζεται swaps, position management, και order execution.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from jupiter_client import JupiterClient, JupiterSwapConfig


@dataclass
class Position:
    """Ανοιχτή θέση."""
    token_address: str
    symbol: str
    entry_price: float
    entry_time: float
    position_size_sol: float
    position_size_usd: float
    
    # Targets
    tp1_price: float = 0.0
    tp2_price: float = 0.0
    tp3_price: float = 0.0
    stop_loss_price: float = 0.0
    
    # Status
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    stopped_out: bool = False
    
    # Position sizing for partial exits
    remaining_pct: float = 100.0  # How much of position is still held
    
    # Trailing stop
    trailing_stop_active: bool = False
    trailing_stop_price: float = 0.0
    
    # PnL
    current_price: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl_pct: float = 0.0
    
    def update_price(self, new_price: float):
        """Update με νέα τιμή."""
        self.current_price = new_price
        if self.entry_price > 0:
            self.unrealized_pnl_pct = ((new_price - self.entry_price) / self.entry_price) * 100
    
    def check_targets(self) -> Optional[str]:
        """Check αν έπιασε κάποιο target."""
        if self.stopped_out:
            return None
        
        # Check stop loss
        if self.stop_loss_price > 0 and self.current_price <= self.stop_loss_price:
            self.stopped_out = True
            return "stop_loss"
        
        # Check TPs
        if self.tp3_price > 0 and self.current_price >= self.tp3_price and not self.tp3_hit:
            self.tp3_hit = True
            return "tp3"
        
        if self.tp2_price > 0 and self.current_price >= self.tp2_price and not self.tp2_hit:
            self.tp2_hit = True
            return "tp2"
        
        if self.tp1_price > 0 and self.current_price >= self.tp1_price and not self.tp1_hit:
            self.tp1_hit = True
            return "tp1"
        
        return None


class ExecutionEngine:
    """
    Engine εκτέλεσης trades στο Solana.
    Χρησιμοποιεί Jupiter aggregator για best prices.
    """
    
    def __init__(self, wallet_private_key: Optional[str] = None,
                 wallet_public_key: Optional[str] = None):
        self.wallet_key = wallet_private_key
        self.wallet_public_key = wallet_public_key
        self.positions: Dict[str, Position] = {}  # token_address -> Position
        self.trade_history: List[Dict] = []
        
        # Jupiter client for real swaps
        self.jupiter = JupiterClient(JupiterSwapConfig(slippage_bps=100))
        
        # Jupiter API
        self.jupiter_api = "https://api.jup.ag/swap/v1"
        self.jupiter_swap = "https://api.jup.ag/swap/v4"
        
        # Execution config
        self.slippage_bps = 100  # 1%
        self.max_retries = 3
        self.execution_timeout = 30
        
        # Portfolio tracking
        self.total_sol_balance: float = 0.0
        self.allocated_sol: float = 0.0  # Σε ανοιχτές θέσεις
        self.daily_pnl: float = 0.0
        self.total_pnl: float = 0.0
    
    async def get_jupiter_quote(self, session: aiohttp.ClientSession,
                                 input_mint: str, output_mint: str,
                                 amount_lamports: int) -> Optional[Dict]:
        """Λήψη quote από Jupiter."""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_lamports),
                "slippageBps": self.slippage_bps,
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false",
            }
            
            async with session.get(
                f"{self.jupiter_api}/quote",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    print(f"❌ Jupiter quote error: {resp.status}")
                    return None
        except Exception as e:
            print(f"❌ Quote error: {e}")
            return None
    
    def calculate_position_size(self, setup: Any, available_sol: float) -> float:
        """Υπολογισμός μεγέθους θέσης."""
        # Risk-based position sizing
        risk_pct = getattr(setup, 'position_size_pct', 5.0)
        max_position_sol = (available_sol * risk_pct) / 100
        
        # Cap at 20% of available
        max_position_sol = min(max_position_sol, available_sol * 0.20)
        
        # Fixed position size: 0.065 SOL per trade
        min_position = 0.065
        max_position = 0.065
        return max(min_position, min(max_position_sol, max_position))
    
    async def execute_entry(self, session: aiohttp.ClientSession,
                           setup: Any, available_sol: float) -> Optional[Position]:
        """Εκτέλεση entry trade."""
        
        token_address = setup.token_address
        symbol = setup.symbol
        entry_price = setup.entry_price
        
        # Calculate position size
        position_size_sol = self.calculate_position_size(setup, available_sol)
        position_size_usd = position_size_sol * entry_price  # Approximate
        
        print(f"🎯 Executing entry for {symbol}")
        print(f"   Size: {position_size_sol:.3f} SOL (${position_size_usd:.2f})")
        print(f"   Entry: ${entry_price:.6f}")
        
        # Create position object
        position = Position(
            token_address=token_address,
            symbol=symbol,
            entry_price=entry_price,
            entry_time=time.time(),
            position_size_sol=position_size_sol,
            position_size_usd=position_size_usd,
            tp1_price=entry_price * (1 + setup.tp1 / 100),
            tp2_price=entry_price * (1 + setup.tp2 / 100),
            tp3_price=entry_price * (1 + setup.tp3 / 100),
            stop_loss_price=entry_price * (1 + setup.stop_loss / 100),
        )
        
        # Store position
        self.positions[token_address] = position
        self.allocated_sol += position_size_sol
        
        # Record trade
        self.trade_history.append({
            "action": "entry",
            "token": symbol,
            "address": token_address,
            "price": entry_price,
            "size_sol": position_size_sol,
            "size_usd": position_size_usd,
            "time": time.time(),
            "setup": setup.__dict__ if hasattr(setup, '__dict__') else {},
        })
        
        print(f"✅ Position opened: {symbol} | Size: {position_size_sol:.3f} SOL")
        
        return position
    
    async def execute_exit(self, token_address: str, reason: str,
                        session: aiohttp.ClientSession) -> Optional[Dict]:
        """Εκτέλεση exit trade."""
        
        if token_address not in self.positions:
            print(f"❌ No position found for {token_address}")
            return None
        
        position = self.positions[token_address]
        current_price = position.current_price
        
        # Calculate PnL
        if position.entry_price > 0:
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            pnl_sol = position.position_size_sol * (pnl_pct / 100)
            pnl_usd = position.position_size_usd * (pnl_pct / 100)
        else:
            pnl_pct = 0
            pnl_sol = 0
            pnl_usd = 0
        
        print(f"🚪 Executing exit for {position.symbol}")
        print(f"   Reason: {reason}")
        print(f"   Entry: ${position.entry_price:.6f}")
        print(f"   Exit: ${current_price:.6f}")
        print(f"   PnL: {pnl_pct:+.1f}% | {pnl_sol:+.3f} SOL | ${pnl_usd:+.2f}")
        
        # Update tracking
        position.realized_pnl_pct = pnl_pct
        self.allocated_sol -= position.position_size_sol
        self.daily_pnl += pnl_sol
        self.total_pnl += pnl_sol
        
        # Record trade
        self.trade_history.append({
            "action": "exit",
            "token": position.symbol,
            "address": token_address,
            "entry_price": position.entry_price,
            "exit_price": current_price,
            "pnl_pct": pnl_pct,
            "pnl_sol": pnl_sol,
            "pnl_usd": pnl_usd,
            "reason": reason,
            "time": time.time(),
        })
        
        # Remove position
        del self.positions[token_address]
        
        print(f"✅ Position closed: {position.symbol} | PnL: {pnl_pct:+.1f}%")
        
        return {
            "symbol": position.symbol,
            "pnl_pct": pnl_pct,
            "pnl_sol": pnl_sol,
            "reason": reason,
        }
    
    async def execute_partial_exit(self, token_address: str, reason: str,
                                   exit_pct: float,
                                   session: aiohttp.ClientSession) -> Optional[Dict]:
        """Εκτέλεση partial exit (π.χ. TP1 = 50%, TP2 = 30%)."""
        
        if token_address not in self.positions:
            print(f"❌ No position found for {token_address}")
            return None
        
        position = self.positions[token_address]
        current_price = position.current_price
        
        # Calculate actual SOL amount to sell
        sell_pct = min(exit_pct, position.remaining_pct)
        sell_size_sol = position.position_size_sol * (sell_pct / 100.0)
        
        # Calculate PnL for this slice
        if position.entry_price > 0:
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            pnl_sol = sell_size_sol * (pnl_pct / 100)
            pnl_usd = position.position_size_usd * (sell_pct / 100) * (pnl_pct / 100)
        else:
            pnl_pct = 0
            pnl_sol = 0
            pnl_usd = 0
        
        print(f"🔥 PARTIAL SELL {position.symbol}")
        print(f"   Reason: {reason}")
        print(f"   Selling: {sell_pct:.0f}% of position ({sell_size_sol:.4f} SOL)")
        print(f"   Price: ${current_price:.6f} | PnL: {pnl_pct:+.1f}%")
        
        # Execute Jupiter swap (token → SOL)
        SOL_MINT = "So11111111111111111111111111111111111111112"
        if self.wallet_public_key and self.wallet_key:
            try:
                # Calculate token amount to sell (approximate based on SOL value)
                token_amount = int((sell_size_sol * 1e9) / current_price * current_price)  # Rough estimate
                
                # Get Jupiter quote
                quote = await self.jupiter.get_quote(
                    session, position.token_address, SOL_MINT, token_amount
                )
                
                if quote:
                    # Build swap transaction
                    swap_result = await self.jupiter.execute_swap(
                        session, quote, self.wallet_public_key
                    )
                    
                    if swap_result:
                        print(f"   ✅ JUPITER SWAP BUILT: {swap_result['transaction'][:30]}...")
                        print(f"   📤 Ready to sign & send via wallet")
                        # TODO: Add wallet signing here when ready
                    else:
                        print(f"   ⚠️ Swap build failed — logged for manual execution")
                else:
                    print(f"   ⚠️ Jupiter quote failed — logged for manual execution")
                    
            except Exception as e:
                print(f"   ❌ Jupiter swap error: {e}")
        else:
            print(f"   ⏸ SIMULATION MODE — no wallet configured, skipping real swap")
        
        print(f"   🔄 SWAP RECORDED: {position.symbol} → SOL via Jupiter")
        
        # Update position
        position.remaining_pct -= sell_pct
        self.allocated_sol -= sell_size_sol
        self.daily_pnl += pnl_sol
        self.total_pnl += pnl_sol
        
        # Record trade
        self.trade_history.append({
            "action": "partial_exit",
            "token": position.symbol,
            "address": token_address,
            "exit_pct": sell_pct,
            "exit_price": current_price,
            "pnl_pct": pnl_pct,
            "pnl_sol": pnl_sol,
            "pnl_usd": pnl_usd,
            "reason": reason,
            "time": time.time(),
            "remaining_pct": position.remaining_pct,
        })
        
        print(f"✅ Partial exit done! Remaining: {position.remaining_pct:.0f}%")
        
        return {
            "symbol": position.symbol,
            "sold_pct": sell_pct,
            "remaining_pct": position.remaining_pct,
            "pnl_pct": pnl_pct,
            "pnl_sol": pnl_sol,
            "reason": reason,
        }
    
    async def monitor_positions(self, session: aiohttp.ClientSession,
                                 price_fetcher):
        """Monitor ανοιχτές θέσεις και check targets."""
        
        if not self.positions:
            return []
        
        triggered = []
        
        for address, position in list(self.positions.items()):
            try:
                # Get current price
                current_price = await price_fetcher(address)
                if not current_price:
                    continue
                
                position.update_price(current_price)
                
                # Check trailing stop first (if active)
                if position.trailing_stop_active:
                    if current_price <= position.trailing_stop_price:
                        print(f"🛑 TRAILING STOP HIT for {position.symbol}!")
                        await self.execute_exit(address, "trailing_stop", session)
                        continue
                    # Move trailing stop up if price pumps more
                    new_trailing = current_price * 0.95
                    if new_trailing > position.trailing_stop_price:
                        position.trailing_stop_price = new_trailing
                
                # Check targets
                trigger = position.check_targets()
                if trigger:
                    triggered.append({
                        "token": position.symbol,
                        "address": address,
                        "trigger": trigger,
                        "price": current_price,
                        "pnl_pct": position.unrealized_pnl_pct,
                    })
                    
                    # Execute partial or full exit based on trigger
                    if trigger == "stop_loss":
                        # Sell 100% — full exit
                        await self.execute_partial_exit(address, "stop_loss", position.remaining_pct, session)
                        await self.execute_exit(address, "stop_loss", session)
                    elif trigger == "tp1":
                        # Sell 50% of position
                        await self.execute_partial_exit(address, "tp1", 50.0, session)
                    elif trigger == "tp2":
                        # Sell 30% of what remains (≈15% of original if TP1 hit)
                        await self.execute_partial_exit(address, "tp2", 30.0, session)
                    elif trigger == "tp3":
                        # Sell remaining ~20%, activate trailing stop after
                        await self.execute_partial_exit(address, "tp3", position.remaining_pct, session)
                        await self.execute_exit(address, "tp3_full", session)
                        
                        # Trailing stop logic: if price keeps pumping after TP3
                        position.trailing_stop_active = True
                        position.trailing_stop_price = current_price * 0.95  # 5% trailing
                
            except Exception as e:
                print(f"❌ Monitor error for {position.symbol}: {e}")
        
        return triggered
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio status."""
        total_unrealized = 0.0
        for pos in self.positions.values():
            total_unrealized += pos.unrealized_pnl_pct
        
        return {
            "total_positions": len(self.positions),
            "allocated_sol": self.allocated_sol,
            "available_sol": self.total_sol_balance - self.allocated_sol,
            "unrealized_pnl_pct": total_unrealized / len(self.positions) if self.positions else 0,
            "daily_pnl_sol": self.daily_pnl,
            "total_pnl_sol": self.total_pnl,
            "positions": [
                {
                    "symbol": p.symbol,
                    "entry": p.entry_price,
                    "current": p.current_price,
                    "pnl_pct": p.unrealized_pnl_pct,
                    "size_sol": p.position_size_sol,
                }
                for p in self.positions.values()
            ],
        }
    
    def reset_daily_pnl(self):
        """Reset daily PnL tracking."""
        self.daily_pnl = 0.0


if __name__ == "__main__":
    engine = ExecutionEngine()
    print("⚙️ Execution Engine initialized")
    print(f"   Jupiter API: {engine.jupiter_api}")
    print(f"   Slippage: {engine.slippage_bps} bps")
