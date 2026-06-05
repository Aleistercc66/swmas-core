import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Open trading position"""
    mint: str
    entry_price: float
    entry_time: float
    size: float  # SOL amount
    direction: str  # 'LONG' or 'SHORT'
    
    # Risk parameters
    stop_loss: float
    trailing_stop: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # State
    peak_price: float = 0.0
    status: str = 'OPEN'
    exit_price: float = 0.0
    exit_time: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Partial exits
    exited_1: bool = False
    exited_2: bool = False
    exited_3: bool = False
    remaining_size: float = 0.0

@dataclass
class RiskProfile:
    """User risk profile"""
    max_position_pct: float = 0.05  # 5% of bankroll per trade
    max_daily_risk_pct: float = 0.10  # 10% daily risk
    max_total_exposure: float = 0.30  # 30% total exposure
    
    stop_loss_pct: float = 0.15  # 15% hard stop
    trailing_stop_pct: float = 0.10  # 10% trailing
    time_stop_seconds: float = 3600  # 1 hour max hold
    
    kelly_fraction: float = 0.5  # Half-Kelly
    
    profit_tiers: List[Dict] = None
    
    def __post_init__(self):
        if self.profit_tiers is None:
            self.profit_tiers = [
                {'pct': 0.50, 'size': 0.25},   # +50% → sell 25%
                {'pct': 1.00, 'size': 0.35},   # +100% → sell 35% (total 60%)
                {'pct': 2.00, 'size': 0.25},   # +200% → sell 25% (total 85%)
                {'pct': 4.00, 'size': 0.15},   # +400% → sell 15% (total 100%)
            ]


class RiskManager:
    """
    Comprehensive risk management system.
    
    Features:
    - Kelly Criterion position sizing
    - Multi-layer stop loss (hard, trailing, time)
    - Tiered profit taking
    - Daily risk tracking
    - Exposure monitoring
    """
    
    def __init__(self, profile: RiskProfile, initial_bankroll: float = 10.0):
        self.profile = profile
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.daily_pnl = 0.0
        self.daily_risk_used = 0.0
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Position] = []
        self.last_reset_day = datetime.now().day
        
    def calculate_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        signal_confidence: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Kelly = (p*b - q) / b
        Where: p = win rate, q = 1-p, b = avg_win/avg_loss
        
        Returns position size in SOL.
        """
        # Kelly calculation
        b = avg_win / avg_loss if avg_loss > 0 else 1.0
        kelly = (win_rate * b - (1 - win_rate)) / b
        
        # Apply Half-Kelly for safety
        half_kelly = kelly * self.profile.kelly_fraction
        
        # Confidence adjustment (reduce size if confidence < 80)
        confidence_adjustment = min(1.0, signal_confidence / 80)
        
        # Calculate position
        position = self.current_bankroll * half_kelly * confidence_adjustment
        
        # Apply caps
        max_position = self.current_bankroll * self.profile.max_position_pct
        position = min(position, max_position)
        
        # Check daily risk limit
        remaining_risk = (self.current_bankroll * self.profile.max_daily_risk_pct) - self.daily_risk_used
        if remaining_risk <= 0:
            logger.warning("Daily risk limit reached")
            return 0.0
            
        position = min(position, remaining_risk)
        
        # Minimum viable trade
        if position < 0.001:  # 0.001 SOL minimum
            return 0.0
            
        return position
        
    def check_entry_permission(self, mint: str) -> Tuple[bool, str]:
        """
        Check if entry is allowed based on risk rules.
        
        Returns (allowed, reason).
        """
        # Reset daily counters if new day
        if datetime.now().day != self.last_reset_day:
            self.daily_pnl = 0.0
            self.daily_risk_used = 0.0
            self.last_reset_day = datetime.now().day
            
        # Check if already in position
        if mint in self.positions and self.positions[mint].status == 'OPEN':
            return False, "Already in position"
            
        # Check total exposure
        total_exposure = sum(p.size for p in self.positions.values() if p.status == 'OPEN')
        exposure_pct = total_exposure / self.current_bankroll
        if exposure_pct >= self.profile.max_total_exposure:
            return False, f"Max exposure reached: {exposure_pct:.1%}"
            
        # Check daily risk
        if self.daily_risk_used >= self.current_bankroll * self.profile.max_daily_risk_pct:
            return False, "Daily risk limit reached"
            
        return True, "OK"
        
    def open_position(self, mint: str, price: float, size: float, direction: str = 'LONG') -> Position:
        """Open a new position with risk parameters"""
        position = Position(
            mint=mint,
            entry_price=price,
            entry_time=datetime.now().timestamp(),
            size=size,
            direction=direction,
            stop_loss=price * (1 - self.profile.stop_loss_pct) if direction == 'LONG' else price * (1 + self.profile.stop_loss_pct),
            trailing_stop=self.profile.trailing_stop_pct,
            take_profit_1=price * 1.50 if direction == 'LONG' else price * 0.70,
            take_profit_2=price * 2.00 if direction == 'LONG' else price * 0.50,
            take_profit_3=price * 3.00 if direction == 'LONG' else price * 0.30,
            peak_price=price,
            remaining_size=size
        )
        
        self.positions[mint] = position
        self.daily_risk_used += size
        
        logger.info(f"Position opened: {mint} | ${price:.6f} | {size:.4f} SOL | {direction}")
        return position
        
    async def monitor_position(self, mint: str, get_price_func) -> Optional[Dict]:
        """
        Monitor a position and trigger exits if needed.
        
        Returns exit signal if triggered, None otherwise.
        """
        position = self.positions.get(mint)
        if not position or position.status != 'OPEN':
            return None
            
        current_price = await get_price_func(mint)
        if current_price is None:
            return None
            
        # Update peak price
        if position.direction == 'LONG':
            if current_price > position.peak_price:
                position.peak_price = current_price
        else:
            if current_price < position.peak_price:
                position.peak_price = current_price
                
        # Calculate P&L
        if position.direction == 'LONG':
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - current_price) / position.entry_price
            
        position.pnl = position.size * pnl_pct
        position.pnl_pct = pnl_pct
        
        # Check hard stop loss
        if position.direction == 'LONG' and current_price <= position.stop_loss:
            return self._create_exit_signal(position, 'HARD_STOP', current_price)
        elif position.direction == 'SHORT' and current_price >= position.stop_loss:
            return self._create_exit_signal(position, 'HARD_STOP', current_price)
            
        # Check trailing stop
        if position.direction == 'LONG':
            trail_price = position.peak_price * (1 - position.trailing_stop)
            if current_price <= trail_price and current_price > position.entry_price:
                return self._create_exit_signal(position, 'TRAILING_STOP', current_price)
        else:
            trail_price = position.peak_price * (1 + position.trailing_stop)
            if current_price >= trail_price and current_price < position.entry_price:
                return self._create_exit_signal(position, 'TRAILING_STOP', current_price)
                
        # Check time stop
        hold_time = datetime.now().timestamp() - position.entry_time
        if hold_time >= self.profile.time_stop_seconds:
            return self._create_exit_signal(position, 'TIME_STOP', current_price)
            
        # Check profit taking tiers
        for tier in self.profile.profit_tiers:
            if pnl_pct >= tier['pct']:
                if not position.exited_1 and tier['pct'] == 0.50:
                    position.exited_1 = True
                    return self._create_profit_signal(position, tier, current_price)
                elif not position.exited_2 and tier['pct'] == 1.00:
                    position.exited_2 = True
                    return self._create_profit_signal(position, tier, current_price)
                elif not position.exited_3 and tier['pct'] == 2.00:
                    position.exited_3 = True
                    return self._create_profit_signal(position, tier, current_price)
                    
        return None
        
    def _create_exit_signal(self, position: Position, reason: str, price: float) -> Dict:
        """Create exit signal"""
        position.status = 'CLOSED'
        position.exit_price = price
        position.exit_time = datetime.now().timestamp()
        
        # Calculate final P&L
        if position.direction == 'LONG':
            position.pnl = position.size * (price - position.entry_price) / position.entry_price
        else:
            position.pnl = position.size * (position.entry_price - price) / position.entry_price
            
        position.pnl_pct = position.pnl / position.size
        
        # Update bankroll
        self.current_bankroll += position.pnl
        self.daily_pnl += position.pnl
        self.trade_history.append(position)
        
        logger.info(f"Position closed: {position.mint} | {reason} | PnL: {position.pnl:.4f} SOL ({position.pnl_pct:.1%})")
        
        return {
            'action': 'EXIT',
            'mint': position.mint,
            'reason': reason,
            'price': price,
            'pnl': position.pnl,
            'pnl_pct': position.pnl_pct
        }
        
    def _create_profit_signal(self, position: Position, tier: Dict, price: float) -> Dict:
        """Create partial exit signal for profit taking"""
        exit_size = position.size * tier['size']
        
        if position.direction == 'LONG':
            pnl = exit_size * (price - position.entry_price) / position.entry_price
        else:
            pnl = exit_size * (position.entry_price - price) / position.entry_price
            
        position.remaining_size -= exit_size
        
        return {
            'action': 'PARTIAL_EXIT',
            'mint': position.mint,
            'reason': f'TAKE_PROFIT_{int(tier["pct"] * 100)}%',
            'price': price,
            'exit_size': exit_size,
            'remaining_size': position.remaining_size,
            'pnl': pnl
        }
        
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'total_pnl': 0.0,
                'bankroll': self.current_bankroll
            }
            
        wins = sum(1 for p in self.trade_history if p.pnl > 0)
        total = len(self.trade_history)
        
        return {
            'total_trades': total,
            'win_rate': wins / total if total > 0 else 0.0,
            'avg_pnl': sum(p.pnl for p in self.trade_history) / total,
            'total_pnl': sum(p.pnl for p in self.trade_history),
            'bankroll': self.current_bankroll,
            'daily_pnl': self.daily_pnl,
            'open_positions': len([p for p in self.positions.values() if p.status == 'OPEN'])
        }


# ─── QUICK TEST ───
def test_risk_manager():
    """Test the risk manager"""
    profile = RiskProfile()
    manager = RiskManager(profile, initial_bankroll=10.0)
    
    # Test position sizing
    size = manager.calculate_position_size(
        win_rate=0.45,
        avg_win=0.35,
        avg_loss=0.15,
        signal_confidence=75.0
    )
    print(f"Position size: {size:.4f} SOL")
    
    # Test entry
    allowed, reason = manager.check_entry_permission("TEST_TOKEN")
    print(f"Entry allowed: {allowed} | {reason}")
    
    if allowed:
        position = manager.open_position("TEST_TOKEN", 0.001, size, 'LONG')
        print(f"Position opened: {position}")
        
    # Test stats
    stats = manager.get_stats()
    print(f"Stats: {stats}")
    
    return manager


if __name__ == "__main__":
    test_risk_manager()
