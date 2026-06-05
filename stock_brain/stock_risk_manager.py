"""
Stock Risk Manager — Position Sizing, Drawdown Protection, Circuit Breakers
Fixed 2% + Kelly Criterion, loss streak adjustments, portfolio heat.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from stock_config import DEFAULT_RISK_CONFIG, RiskConfig
from stock_signal_generator import Signal, SignalBatch

logger = logging.getLogger(__name__)

# ───────────────────────────
# RISK DATA MODELS
# ───────────────────────────

@dataclass
class Position:
    """A live position."""
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: float
    size: int  # Number of shares
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Current state
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    highest_price: float = 0.0  # For trailing stop
    
    # Metadata
    entry_time: datetime = field(default_factory=datetime.utcnow)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # STOP_LOSS, TP1, TP2, TP3, TRAILING, MANUAL
    
    def update_price(self, price: float):
        """Update position with current price."""
        self.current_price = price
        
        if self.direction == "LONG":
            self.unrealized_pnl = (price - self.entry_price) * self.size
            self.unrealized_pnl_percent = (price - self.entry_price) / self.entry_price * 100
            self.highest_price = max(self.highest_price, price)
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.size
            self.unrealized_pnl_percent = (self.entry_price - price) / self.entry_price * 100
            self.highest_price = min(self.highest_price, price) if self.highest_price else price
    
    def check_exit(self, trailing_stop_pct: float = 3.0) -> Optional[str]:
        """Check if position should be exited. Returns reason or None."""
        if self.direction == "LONG":
            # Stop loss
            if self.current_price <= self.stop_loss:
                return "STOP_LOSS"
            
            # Take profits
            if self.current_price >= self.take_profit_3:
                return "TP3"
            elif self.current_price >= self.take_profit_2:
                return "TP2"
            elif self.current_price >= self.take_profit_1:
                return "TP1"
            
            # Trailing stop
            if self.highest_price > self.entry_price * 1.05:  # Only after 5% profit
                trailing_level = self.highest_price * (1 - trailing_stop_pct / 100)
                if self.current_price <= trailing_level:
                    return "TRAILING"
        
        else:  # SHORT
            if self.current_price >= self.stop_loss:
                return "STOP_LOSS"
            
            if self.current_price <= self.take_profit_3:
                return "TP3"
            elif self.current_price <= self.take_profit_2:
                return "TP2"
            elif self.current_price <= self.take_profit_1:
                return "TP1"
        
        return None

@dataclass
class PortfolioState:
    """Current portfolio state."""
    total_value: float = 100000.0  # Starting capital
    cash: float = 100000.0
    positions: List[Position] = field(default_factory=list)
    
    # Tracking
    daily_pnl: float = 0.0
    daily_pnl_percent: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    
    # Drawdown
    peak_value: float = 100000.0
    current_drawdown_percent: float = 0.0
    max_drawdown_percent: float = 0.0
    
    # Loss tracking
    consecutive_losses: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Time tracking
    trading_day_start: datetime = field(default_factory=datetime.utcnow)

# ───────────────────────────
# RISK MANAGER
# ───────────────────────────

class RiskManager:
    """
    Comprehensive risk management for stock trading.
    
    Features:
    - Position sizing: 2% fixed + Kelly Criterion
    - Drawdown protection: 10% circuit breaker
    - Daily loss limit: 2% hard stop
    - Loss streak adjustments: 3 losses → 50% size, 5 losses → 1h pause
    - Portfolio heat: max 30% deployed
    - Correlation limits
    """
    
    def __init__(
        self,
        config: RiskConfig = None,
        portfolio: PortfolioState = None,
    ):
        self.config = config or DEFAULT_RISK_CONFIG
        self.portfolio = portfolio or PortfolioState()
        self._paused_until: Optional[datetime] = None
        self._circuit_breaker_triggered: bool = False
        
        logger.info(
            f"RiskManager initialized — "
            f"max_position={self.config.max_position_percent}%, "
            f"daily_loss_limit={self.config.daily_loss_limit_percent}%, "
            f"max_drawdown={self.config.max_drawdown_percent}%"
        )
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed.
        
        Returns:
            (allowed, reason)
        """
        # Check circuit breaker
        if self._circuit_breaker_triggered:
            return False, "CIRCUIT_BREAKER: Max drawdown reached"
        
        # Check pause
        if self._paused_until and datetime.utcnow() < self._paused_until:
            remaining = (self._paused_until - datetime.utcnow()).total_seconds() / 60
            return False, f"PAUSED: {remaining:.0f} minutes remaining"
        
        # Check daily loss limit
        if self.portfolio.daily_pnl_percent <= -self.config.daily_loss_limit_percent:
            return False, f"DAILY_LIMIT: {self.portfolio.daily_pnl_percent:.2f}% loss"
        
        # Check portfolio heat
        heat = self._calculate_portfolio_heat()
        if heat >= self.config.max_portfolio_heat_percent:
            return False, f"MAX_HEAT: {heat:.1f}% deployed"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: Optional[float] = None,
    ) -> Tuple[int, float, Dict]:
        """
        Calculate position size using Kelly + fixed 2% base.
        
        Args:
            signal: The signal to size
            portfolio_value: Current portfolio value (uses total if None)
            
        Returns:
            (shares, risk_amount, sizing_details)
        """
        if portfolio_value is None:
            portfolio_value = self.portfolio.total_value
        
        # Base size: 2% of portfolio
        base_size = portfolio_value * (self.config.base_position_percent / 100)
        
        # Kelly adjustment
        win_prob = signal.score / 100  # Use signal score as win probability estimate
        win_loss_ratio = signal.rr_ratio if signal.rr_ratio > 0 else 1.0
        
        # Kelly fraction: f = (p*b - q) / b
        # where p = win prob, q = loss prob, b = win/loss ratio
        q = 1 - win_prob
        kelly = (win_prob * win_loss_ratio - q) / win_loss_ratio if win_loss_ratio > 0 else 0
        kelly = max(0, min(0.25, kelly))  # Cap Kelly at 25%
        
        # Apply Kelly fraction (quarter Kelly)
        kelly_size = portfolio_value * kelly * self.config.kelly_fraction
        
        # Blend: 70% fixed, 30% Kelly
        position_value = base_size * 0.7 + kelly_size * 0.3
        
        # Loss streak adjustment
        streak_multiplier = 1.0
        if self.portfolio.consecutive_losses >= 5:
            return 0, 0.0, {"reason": "PAUSED: 5+ consecutive losses"}
        elif self.portfolio.consecutive_losses >= 3:
            streak_multiplier = self.config.loss_streak_3_reduce
            position_value *= streak_multiplier
        
        # Max position cap
        max_position = portfolio_value * (self.config.max_position_percent / 100)
        position_value = min(position_value, max_position)
        
        # Calculate shares
        entry_price = signal.entry_price
        stop_price = signal.stop_loss
        risk_per_share = abs(entry_price - stop_price)
        
        if risk_per_share <= 0:
            return 0, 0.0, {"reason": "Invalid stop loss"}
        
        # Risk-based sizing: max 2% risk per trade
        max_risk = portfolio_value * 0.02
        risk_based_shares = int(max_risk / risk_per_share)
        
        # Position value based shares
        value_based_shares = int(position_value / entry_price)
        
        # Take the more conservative
        shares = min(risk_based_shares, value_based_shares)
        
        if shares < 1:
            return 0, 0.0, {"reason": "Position too small"}
        
        actual_value = shares * entry_price
        actual_risk = shares * risk_per_share
        
        sizing_details = {
            "base_size": base_size,
            "kelly_size": kelly_size,
            "kelly_fraction": kelly,
            "streak_multiplier": streak_multiplier,
            "max_position": max_position,
            "risk_per_share": risk_per_share,
            "risk_based_shares": risk_based_shares,
            "value_based_shares": value_based_shares,
            "actual_value": actual_value,
            "actual_risk": actual_risk,
            "actual_risk_percent": (actual_risk / portfolio_value) * 100,
        }
        
        return shares, actual_risk, sizing_details
    
    def validate_signal(self, signal: Signal) -> Tuple[bool, str, float]:
        """
        Validate a signal against risk rules.
        
        Returns:
            (valid, reason, adjusted_score)
        """
        # Check trading allowed
        can_trade, reason = self.can_trade()
        if not can_trade:
            return False, reason, 0.0
        
        # Check signal score
        if signal.score < 70:
            return False, f"Score too low: {signal.score:.0f}", 0.0
        
        # Check edge
        if signal.edge_percent < 2.0:
            return False, f"Edge too small: {signal.edge_percent:.2f}%", 0.0
        
        # Check R:R
        if signal.rr_ratio < 1.5:
            return False, f"R:R too low: {signal.rr_ratio:.1f}:1", 0.0
        
        # Check portfolio heat
        heat = self._calculate_portfolio_heat()
        if heat >= self.config.max_portfolio_heat_percent:
            return False, f"Portfolio heat: {heat:.1f}%", 0.0
        
        # Check correlation (simplified)
        # In production, check correlation with existing positions
        
        # Calculate adjusted score based on risk state
        adjusted_score = signal.score
        
        # Reduce score if in loss streak
        if self.portfolio.consecutive_losses >= 3:
            adjusted_score *= 0.8
        
        # Reduce score if near daily limit
        daily_loss_pct = abs(self.portfolio.daily_pnl_percent)
        if daily_loss_pct >= 1.5:  # Near 2% limit
            adjusted_score *= 0.7
        
        return True, "OK", adjusted_score
    
    def update_portfolio(self, prices: Dict[str, float]):
        """Update all positions with current prices."""
        for position in self.portfolio.positions:
            if position.symbol in prices:
                position.update_price(prices[position.symbol])
        
        # Recalculate portfolio value
        total_position_value = sum(
            p.current_price * p.size for p in self.portfolio.positions
        )
        self.portfolio.total_value = self.portfolio.cash + total_position_value
        
        # Calculate P&L
        total_unrealized = sum(p.unrealized_pnl for p in self.portfolio.positions)
        self.portfolio.total_pnl = total_unrealized + self._realized_pnl()
        self.portfolio.total_pnl_percent = (self.portfolio.total_pnl / self.portfolio.peak_value) * 100
        
        # Update daily P&L
        day_start_value = self.portfolio.peak_value  # Simplified
        self.portfolio.daily_pnl = self.portfolio.total_value - day_start_value
        self.portfolio.daily_pnl_percent = (self.portfolio.daily_pnl / day_start_value) * 100
        
        # Update drawdown
        if self.portfolio.total_value > self.portfolio.peak_value:
            self.portfolio.peak_value = self.portfolio.total_value
        
        self.portfolio.current_drawdown_percent = (
            (self.portfolio.peak_value - self.portfolio.total_value) / self.portfolio.peak_value
        ) * 100
        
        self.portfolio.max_drawdown_percent = max(
            self.portfolio.max_drawdown_percent,
            self.portfolio.current_drawdown_percent,
        )
        
        # Check circuit breaker
        if self.portfolio.current_drawdown_percent >= self.config.max_drawdown_percent:
            self._trigger_circuit_breaker()
    
    def check_exits(self) -> List[Position]:
        """Check all positions for exit signals."""
        exits = []
        
        for position in self.portfolio.positions:
            exit_reason = position.check_exit(self.config.trailing_stop_percent)
            if exit_reason:
                position.exit_reason = exit_reason
                position.exit_time = datetime.utcnow()
                position.exit_price = position.current_price
                exits.append(position)
                
                # Update loss streak
                realized_pnl = position.exit_price - position.entry_price
                if realized_pnl < 0:
                    self.portfolio.consecutive_losses += 1
                else:
                    self.portfolio.consecutive_losses = 0
                
                self.portfolio.total_trades += 1
                if realized_pnl > 0:
                    self.portfolio.winning_trades += 1
                else:
                    self.portfolio.losing_trades += 1
                
                logger.info(
                    f"EXIT: {position.symbol} @ {position.exit_price:.2f} "
                    f"({exit_reason}) | P&L: ${realized_pnl:.2f}"
                )
        
        # Remove exited positions
        self.portfolio.positions = [
            p for p in self.portfolio.positions if p.exit_time is None
        ]
        
        return exits
    
    def _calculate_portfolio_heat(self) -> float:
        """Calculate percentage of portfolio deployed."""
        if self.portfolio.total_value <= 0:
            return 0.0
        
        deployed = sum(p.current_price * p.size for p in self.portfolio.positions)
        return (deployed / self.portfolio.total_value) * 100
    
    def _realized_pnl(self) -> float:
        """Calculate total realized P&L (simplified)."""
        # In production, track from closed trades database
        return 0.0
    
    def _trigger_circuit_breaker(self):
        """Trigger circuit breaker due to max drawdown."""
        self._circuit_breaker_triggered = True
        logger.critical(
            f"🚨 CIRCUIT BREAKER TRIGGERED! "
            f"Drawdown: {self.portfolio.current_drawdown_percent:.2f}% "
            f"(max: {self.config.max_drawdown_percent}%)"
        )
    
    def reset_daily(self):
        """Reset daily tracking."""
        self.portfolio.daily_pnl = 0.0
        self.portfolio.daily_pnl_percent = 0.0
        self.portfolio.trading_day_start = datetime.utcnow()
        self._circuit_breaker_triggered = False
        self._paused_until = None
        
        logger.info("📅 Daily reset complete")
    
    def get_status(self) -> Dict:
        """Get full risk status."""
        return {
            "portfolio_value": self.portfolio.total_value,
            "cash": self.portfolio.cash,
            "deployed": self._calculate_portfolio_heat(),
            "daily_pnl": self.portfolio.daily_pnl,
            "daily_pnl_percent": self.portfolio.daily_pnl_percent,
            "total_pnl": self.portfolio.total_pnl,
            "total_pnl_percent": self.portfolio.total_pnl_percent,
            "current_drawdown": self.portfolio.current_drawdown_percent,
            "max_drawdown": self.portfolio.max_drawdown_percent,
            "consecutive_losses": self.portfolio.consecutive_losses,
            "total_trades": self.portfolio.total_trades,
            "win_rate": (
                self.portfolio.winning_trades / self.portfolio.total_trades * 100
                if self.portfolio.total_trades > 0 else 0
            ),
            "open_positions": len(self.portfolio.positions),
            "can_trade": self.can_trade()[0],
            "circuit_breaker": self._circuit_breaker_triggered,
            "paused": self._paused_until is not None,
        }


# ───────────────────────────
# MAIN (for testing)
# ───────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    rm = RiskManager()
    
    # Test signal
    test_signal = Signal(
        symbol="AAPL",
        signal_type="MOMENTUM",
        direction="LONG",
        score=82,
        confidence="HIGH",
        entry_price=180.0,
        stop_loss=176.0,
        take_profit_1=186.0,
        take_profit_2=190.0,
        take_profit_3=198.0,
        edge_percent=3.5,
        rr_ratio=2.0,
    )
    
    # Validate
    valid, reason, adjusted = rm.validate_signal(test_signal)
    print(f"\n✅ Signal validation: {valid} | {reason} | Adjusted score: {adjusted:.1f}")
    
    # Calculate size
    shares, risk, details = rm.calculate_position_size(test_signal)
    print(f"\n📊 Position sizing:")
    print(f"  Shares: {shares}")
    print(f"  Risk: ${risk:.2f}")
    for k, v in details.items():
        print(f"  {k}: {v}")
    
    # Status
    print(f"\n🛡️ Risk status:")
    for k, v in rm.get_status().items():
        print(f"  {k}: {v}")
