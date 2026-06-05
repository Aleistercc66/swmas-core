#!/usr/bin/env python3
"""
Risk Manager - Position sizing, stop losses, portfolio protection
Διαχειρίζεται risk για consistent 15-30% ημερήσιες αποδόσεις.
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from statistics import mean


@dataclass
class RiskProfile:
    """Risk profile για τον trader."""
    max_portfolio_risk_per_trade: float = 2.0  # % of portfolio
    max_daily_drawdown: float = 10.0  # Stop trading if down >10%
    max_positions_open: int = 3      # Max 3 positions
    max_concentration_per_token: float = 20.0  # % in one token
    
    # Daily targets
    daily_profit_target: float = 15.0  # Stop when +15%
    daily_loss_limit: float = -5.0   # Stop when -5%
    
    # Per trade
    default_stop_loss: float = -15.0  # TIGHTER: was -10%, now -15% (will be overridden by setup)
    min_risk_reward: float = 2.0  # Need at least 2:1
    
    # Time limits
    max_hold_time_hours: float = 6.0
    overnight_holding: bool = False
    
    # SOL fee reserve
    sol_fee_reserve: float = 0.1  # Reserve 0.1 SOL for fees
    
    # Batch control
    max_batch_trades: int = 4
    min_batch_wins_for_continue: int = 2  # Halt if <2 wins after 4 trades


class RiskManager:
    """
    Risk management για Solana trading.
    Προστατεύει από μεγάλα drawdowns και εξασφαλίζει discipline.
    """
    
    def __init__(self, storage_path: str = "solana_risk.json"):
        self.storage_path = storage_path
        self.profile = RiskProfile()
        
        # Daily tracking
        self.daily_pnl_pct: float = 0.0
        self.daily_trades: int = 0
        self.daily_wins: int = 0
        self.daily_losses: int = 0
        
        # Session tracking
        self.session_start_time: float = time.time()
        self.session_trades: int = 0
        self.session_pnl: float = 0.0
        
        # Consecutive tracking
        self.consecutive_losses: int = 0
        self.consecutive_wins: int = 0
        
        # Circuit breakers
        self.trading_halted: bool = False
        self.halt_reason: str = ""
        self.halt_until: float = 0
        
        # Historical
        self.trade_history: List[Dict] = []
        self.daily_stats: Dict[str, Dict] = {}
        
        self.load_risk_data()
    
    def load_risk_data(self):
        """Φόρτωση risk data."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.daily_stats = data.get("daily_stats", {})
                self.trade_history = data.get("trade_history", [])
                print(f"📊 Loaded risk data: {len(self.trade_history)} trades")
        except FileNotFoundError:
            print("📊 New risk manager")
    
    def save_risk_data(self):
        """Αποθήκευση risk data."""
        data = {
            "daily_stats": self.daily_stats,
            "trade_history": self.trade_history[-100:],  # Keep last 100
            "current_daily_pnl": self.daily_pnl_pct,
            "saved_at": time.time(),
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def can_trade(self) -> tuple[bool, str]:
        """Check αν μπορούμε να trade."""
        
        if self.trading_halted:
            if time.time() < self.halt_until:
                return False, f"Trading halted: {self.halt_reason} until {time.strftime('%H:%M', time.localtime(self.halt_until))}"
            else:
                self.trading_halted = False
                self.halt_reason = ""
        
        # Check daily loss limit
        if self.daily_pnl_pct <= self.profile.daily_loss_limit:
            self._halt_trading("Daily loss limit reached", 86400)  # Halt for 24h
            return False, f"Daily loss limit reached: {self.daily_pnl_pct:.1f}%"
        
        # Check max daily drawdown
        if self.daily_pnl_pct <= -self.profile.max_daily_drawdown:
            self._halt_trading("Max drawdown reached", 3600)  # Halt for 1h
            return False, f"Max drawdown reached: {self.daily_pnl_pct:.1f}%"
        
        # Check consecutive losses
        if self.consecutive_losses >= 3:
            self._halt_trading("3 consecutive losses", 1800)  # Halt for 30min
            return False, "3 consecutive losses - taking a break"
        
        # Check daily profit target (optional - can keep trading)
        if self.daily_pnl_pct >= self.profile.daily_profit_target:
            return True, f"Daily target reached ({self.daily_pnl_pct:.1f}%) - consider stopping"
        
        return True, "OK"
    
    def _halt_trading(self, reason: str, duration_seconds: float):
        """Halt trading for specified duration."""
        self.trading_halted = True
        self.halt_reason = reason
        self.halt_until = time.time() + duration_seconds
        print(f"🚫 TRADING HALTED: {reason} for {duration_seconds/60:.0f} minutes")
    
    def validate_setup(self, setup: Any, portfolio_value: float,
                      current_positions: int) -> tuple[bool, str, float]:
        """Validate αν ένα setup περνάει τα risk criteria."""
        
        # Check max positions
        if current_positions >= self.profile.max_positions_open:
            return False, "Max positions reached", 0.0
        
        # Check risk/reward
        risk_reward = getattr(setup, 'risk_reward', 0)
        if risk_reward < self.profile.min_risk_reward:
            return False, f"Risk/Reward too low: {risk_reward:.1f} (min {self.profile.min_risk_reward})", 0.0
        
        # Calculate position size
        target_return = getattr(setup, 'target_return', 0)
        stop_loss = getattr(setup, 'stop_loss', -10)
        
        # Risk-based sizing
        risk_per_trade = self.profile.max_portfolio_risk_per_trade / 100
        position_size = portfolio_value * risk_per_trade
        
        # Adjust for setup quality
        opportunity_score = getattr(setup, 'opportunity_score', 50)
        if opportunity_score > 80:
            position_size *= 1.5  # Increase for high confidence
        elif opportunity_score < 60:
            position_size *= 0.7  # Decrease for low confidence
        
        # Cap at concentration limit
        max_position = portfolio_value * (self.profile.max_concentration_per_token / 100)
        position_size = min(position_size, max_position)
        
        # Ensure minimum
        min_position = portfolio_value * 0.01  # 1% minimum
        position_size = max(position_size, min_position)
        
        return True, "OK", position_size
    
    def record_trade(self, token: str, entry_price: float, exit_price: float,
                    position_size: float, reason: str):
        """Record trade result για tracking."""
        
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        pnl_usd = position_size * (pnl_pct / 100)
        
        # Update tracking
        self.daily_pnl_pct += pnl_pct * (position_size / 100000)  # Approximate portfolio impact
        self.daily_trades += 1
        self.session_trades += 1
        
        if pnl_pct > 0:
            self.daily_wins += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.daily_losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Record
        trade = {
            "token": token,
            "entry": entry_price,
            "exit": exit_price,
            "pnl_pct": pnl_pct,
            "pnl_usd": pnl_usd,
            "reason": reason,
            "time": time.time(),
        }
        self.trade_history.append(trade)
        
        # Log
        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"{emoji} Trade: {token} | PnL: {pnl_pct:+.1f}% | ${pnl_usd:+.2f}")
        
        # Save
        self.save_risk_data()
        
        # Check if we should halt after this trade
        can_trade, msg = self.can_trade()
        if not can_trade:
            print(f"🚫 {msg}")
    
    def get_daily_stats(self) -> Dict:
        """Get today's trading stats."""
        return {
            "daily_pnl_pct": self.daily_pnl_pct,
            "trades": self.daily_trades,
            "wins": self.daily_wins,
            "losses": self.daily_losses,
            "win_rate": self.daily_wins / self.daily_trades if self.daily_trades > 0 else 0,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "can_trade": self.can_trade()[0],
            "halt_reason": self.halt_reason if self.trading_halted else None,
        }
    
    def reset_daily_stats(self):
        """Reset daily stats (call at start of new day)."""
        # Save yesterday's stats
        yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        self.daily_stats[yesterday] = {
            "pnl_pct": self.daily_pnl_pct,
            "trades": self.daily_trades,
            "wins": self.daily_wins,
            "losses": self.daily_losses,
        }
        
        # Reset
        self.daily_pnl_pct = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        print("📅 Daily stats reset")
        self.save_risk_data()
    
    def get_risk_report(self) -> Dict:
        """Generate risk management report."""
        
        if not self.trade_history:
            return {"message": "No trades yet"}
        
        recent = self.trade_history[-30:]  # Last 30 trades
        wins = [t for t in recent if t["pnl_pct"] > 0]
        losses = [t for t in recent if t["pnl_pct"] <= 0]
        
        return {
            "summary": {
                "total_trades": len(self.trade_history),
                "recent_trades": len(recent),
                "win_rate": len(wins) / len(recent) if recent else 0,
                "avg_win": mean([t["pnl_pct"] for t in wins]) if wins else 0,
                "avg_loss": mean([t["pnl_pct"] for t in losses]) if losses else 0,
                "max_win": max([t["pnl_pct"] for t in wins]) if wins else 0,
                "max_loss": min([t["pnl_pct"] for t in losses]) if losses else 0,
            },
            "daily": self.get_daily_stats(),
            "risk_profile": {
                "max_risk_per_trade": self.profile.max_portfolio_risk_per_trade,
                "max_daily_drawdown": self.profile.max_daily_drawdown,
                "max_positions": self.profile.max_positions_open,
                "daily_profit_target": self.profile.daily_profit_target,
                "daily_loss_limit": self.profile.daily_loss_limit,
            },
            "circuit_breakers": {
                "trading_halted": self.trading_halted,
                "halt_reason": self.halt_reason,
                "halt_until": time.strftime("%H:%M", time.localtime(self.halt_until)) if self.halt_until > 0 else None,
            },
        }


if __name__ == "__main__":
    rm = RiskManager()
    
    # Check if we can trade
    can_trade, msg = rm.can_trade()
    print(f"Can trade: {can_trade} | {msg}")
    
    # Show risk profile
    print(f"\n📋 Risk Profile:")
    print(f"  Max risk per trade: {rm.profile.max_portfolio_risk_per_trade}%")
    print(f"  Max daily drawdown: {rm.profile.max_daily_drawdown}%")
    print(f"  Max positions: {rm.profile.max_positions_open}")
    print(f"  Daily profit target: {rm.profile.daily_profit_target}%")
    print(f"  Daily loss limit: {rm.profile.daily_loss_limit}%")
    
    rm.save_risk_data()
    print("\n✅ Risk data saved!")
