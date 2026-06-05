"""
Portfolio & Risk Management System
Advanced position sizing, risk controls, and portfolio optimization
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class RiskLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DEGEN = "degen"

@dataclass
class Position:
    symbol: str
    entry_price: float
    current_price: float
    quantity: float
    side: str  # long/short
    entry_time: datetime
    stop_loss: float = 0
    take_profit_1: float = 0
    take_profit_2: float = 0
    take_profit_3: float = 0
    trailing_stop: float = 0
    trailing_distance: float = 0
    
    @property
    def value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def pnl(self) -> float:
        if self.side == 'long':
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity
    
    @property
    def pnl_pct(self) -> float:
        if self.entry_price > 0:
            return (self.current_price - self.entry_price) / self.entry_price * 100 if self.side == 'long' else (self.entry_price - self.current_price) / self.entry_price * 100
        return 0
    
    @property
    def should_exit(self) -> tuple:
        """Check if position should be exited (signal, reason)"""
        if self.side == 'long':
            if self.stop_loss > 0 and self.current_price <= self.stop_loss:
                return True, 'stop_loss'
            if self.take_profit_1 > 0 and self.current_price >= self.take_profit_1:
                return True, 'take_profit_1'
            if self.take_profit_2 > 0 and self.current_price >= self.take_profit_2:
                return True, 'take_profit_2'
            if self.take_profit_3 > 0 and self.current_price >= self.take_profit_3:
                return True, 'take_profit_3'
            if self.trailing_stop > 0 and self.current_price <= self.trailing_stop:
                return True, 'trailing_stop'
        else:
            if self.stop_loss > 0 and self.current_price >= self.stop_loss:
                return True, 'stop_loss'
            if self.take_profit_1 > 0 and self.current_price <= self.take_profit_1:
                return True, 'take_profit_1'
            if self.trailing_stop > 0 and self.current_price >= self.trailing_stop:
                return True, 'trailing_stop'
        
        return False, ''
    
    def update_trailing_stop(self):
        """Update trailing stop if price moves favorably"""
        if self.trailing_distance <= 0:
            return
        
        if self.side == 'long':
            new_stop = self.current_price * (1 - self.trailing_distance)
            if new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
        else:
            new_stop = self.current_price * (1 + self.trailing_distance)
            if new_stop < self.trailing_stop or self.trailing_stop == 0:
                self.trailing_stop = new_stop

@dataclass
class Portfolio:
    total_equity: float = 0
    available_cash: float = 0
    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[Dict] = field(default_factory=list)
    
    @property
    def total_pnl(self) -> float:
        return sum(p.pnl for p in self.positions.values()) + sum(t.get('pnl', 0) for t in self.closed_trades)
    
    @property
    def total_exposure(self) -> float:
        return sum(p.value for p in self.positions.values())
    
    @property
    def margin_used_pct(self) -> float:
        return (self.total_exposure / self.total_equity * 100) if self.total_equity > 0 else 0
    
    @property
    def position_count(self) -> int:
        return len(self.positions)

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, risk_level: RiskLevel = RiskLevel.MODERATE):
        self.risk_level = risk_level
        self.portfolio = Portfolio()
        
        # Risk parameters based on level
        self.risk_params = self._set_risk_params()
        
        # Tracking
        self.daily_pnl: List[float] = []
        self.peak_equity = 0
        self.current_drawdown = 0
        self.max_drawdown = 0
        
        # Limits
        self.daily_loss_limit = 0
        self.max_positions = 0
        self.max_position_size_pct = 0
        
    def _set_risk_params(self) -> Dict:
        """Set risk parameters based on risk level"""
        params = {
            RiskLevel.CONSERVATIVE: {
                'max_position_size_pct': 5,  # 5% per position
                'max_positions': 10,
                'stop_loss_pct': 3,
                'take_profit_1_pct': 6,
                'take_profit_2_pct': 10,
                'take_profit_3_pct': 15,
                'trailing_stop_pct': 0,
                'daily_loss_limit_pct': 2,
                'leverage_max': 1,
                'correlation_limit': 0.7
            },
            RiskLevel.MODERATE: {
                'max_position_size_pct': 10,
                'max_positions': 15,
                'stop_loss_pct': 5,
                'take_profit_1_pct': 15,
                'take_profit_2_pct': 30,
                'take_profit_3_pct': 50,
                'trailing_stop_pct': 10,
                'daily_loss_limit_pct': 5,
                'leverage_max': 3,
                'correlation_limit': 0.8
            },
            RiskLevel.AGGRESSIVE: {
                'max_position_size_pct': 20,
                'max_positions': 20,
                'stop_loss_pct': 8,
                'take_profit_1_pct': 25,
                'take_profit_2_pct': 50,
                'take_profit_3_pct': 100,
                'trailing_stop_pct': 15,
                'daily_loss_limit_pct': 10,
                'leverage_max': 5,
                'correlation_limit': 0.9
            },
            RiskLevel.DEGEN: {
                'max_position_size_pct': 50,
                'max_positions': 30,
                'stop_loss_pct': 15,
                'take_profit_1_pct': 50,
                'take_profit_2_pct': 100,
                'take_profit_3_pct': 200,
                'trailing_stop_pct': 20,
                'daily_loss_limit_pct': 25,
                'leverage_max': 10,
                'correlation_limit': 1.0
            }
        }
        
        return params.get(self.risk_level, params[RiskLevel.MODERATE])
    
    def calculate_position_size(self, 
                                symbol: str, 
                                entry_price: float, 
                                stop_loss: float,
                                portfolio_value: float,
                                confidence: float = 50) -> Dict:
        """Calculate optimal position size using Kelly Criterion + risk limits"""
        
        # Basic risk limit
        max_risk_amount = portfolio_value * (self.risk_params['max_position_size_pct'] / 100)
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share <= 0:
            return {'size': 0, 'reason': 'Invalid stop loss'}
        
        # Kelly fraction (simplified)
        win_rate = 0.55  # Assume 55% win rate
        avg_win = self.risk_params['take_profit_1_pct'] / 100
        avg_loss = self.risk_params['stop_loss_pct'] / 100
        
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win if avg_win > 0 else 0
        kelly = max(0, min(kelly, 0.25))  # Cap at 25% Kelly
        
        # Adjust by confidence
        confidence_multiplier = confidence / 100
        
        # Position value
        position_value = portfolio_value * kelly * confidence_multiplier
        position_value = min(position_value, max_risk_amount)
        
        # Number of shares/tokens
        quantity = position_value / entry_price
        
        # Risk amount
        risk_amount = quantity * risk_per_share
        risk_pct = (risk_amount / portfolio_value * 100) if portfolio_value > 0 else 0
        
        return {
            'quantity': quantity,
            'position_value': position_value,
            'risk_amount': risk_amount,
            'risk_pct': risk_pct,
            'kelly_fraction': kelly,
            'confidence_multiplier': confidence_multiplier,
            'reason': f"Kelly: {kelly:.2%}, Confidence: {confidence}%, Max risk: {self.risk_params['max_position_size_pct']}%"
        }
    
    def set_stop_levels(self, entry_price: float, side: str) -> Dict:
        """Calculate stop loss and take profit levels"""
        if side == 'long':
            stop_loss = entry_price * (1 - self.risk_params['stop_loss_pct'] / 100)
            tp1 = entry_price * (1 + self.risk_params['take_profit_1_pct'] / 100)
            tp2 = entry_price * (1 + self.risk_params['take_profit_2_pct'] / 100)
            tp3 = entry_price * (1 + self.risk_params['take_profit_3_pct'] / 100)
        else:
            stop_loss = entry_price * (1 + self.risk_params['stop_loss_pct'] / 100)
            tp1 = entry_price * (1 - self.risk_params['take_profit_1_pct'] / 100)
            tp2 = entry_price * (1 - self.risk_params['take_profit_2_pct'] / 100)
            tp3 = entry_price * (1 - self.risk_params['take_profit_3_pct'] / 100)
        
        trailing = self.risk_params['trailing_stop_pct'] / 100 if self.risk_params['trailing_stop_pct'] > 0 else 0
        
        return {
            'stop_loss': stop_loss,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'take_profit_3': tp3,
            'trailing_distance': trailing
        }
    
    def check_portfolio_limits(self, new_position_value: float) -> tuple:
        """Check if new position violates portfolio limits"""
        
        # Check max positions
        if self.portfolio.position_count >= self.risk_params['max_positions']:
            return False, f"Max positions reached ({self.risk_params['max_positions']})"
        
        # Check position size
        max_size = self.portfolio.total_equity * (self.risk_params['max_position_size_pct'] / 100)
        if new_position_value > max_size:
            return False, f"Position size ${new_position_value:,.2f} exceeds max ${max_size:,.2f}"
        
        # Check daily loss limit
        daily_loss = sum(self.daily_pnl)
        max_daily_loss = -self.portfolio.total_equity * (self.risk_params['daily_loss_limit_pct'] / 100)
        if daily_loss <= max_daily_loss:
            return False, f"Daily loss limit reached ({daily_loss:,.2f})"
        
        # Check drawdown
        if self.current_drawdown >= 20:  # 20% max drawdown
            return False, f"Max drawdown reached ({self.current_drawdown:.1f}%)"
        
        return True, "Position allowed"
    
    def update_portfolio(self, position: Position):
        """Add/update position in portfolio"""
        self.portfolio.positions[position.symbol] = position
        self._update_drawdown()
    
    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict:
        """Close a position and record P&L"""
        if symbol not in self.portfolio.positions:
            return {'error': 'Position not found'}
        
        position = self.portfolio.positions[symbol]
        position.current_price = exit_price
        
        pnl = position.pnl
        pnl_pct = position.pnl_pct
        
        trade_record = {
            'symbol': symbol,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'side': position.side,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'exit_reason': reason,
            'duration_hours': (datetime.now() - position.entry_time).total_seconds() / 3600
        }
        
        self.portfolio.closed_trades.append(trade_record)
        self.daily_pnl.append(pnl)
        
        del self.portfolio.positions[symbol]
        
        return trade_record
    
    def _update_drawdown(self):
        """Update drawdown calculations"""
        current_equity = self.portfolio.total_equity + self.portfolio.total_pnl
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    def get_portfolio_stats(self) -> Dict:
        """Get comprehensive portfolio statistics"""
        if not self.portfolio.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': self.max_drawdown,
                'current_drawdown': self.current_drawdown
            }
        
        trades = self.portfolio.closed_trades
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        total_profit = sum(t['pnl'] for t in wins)
        total_loss = abs(sum(t['pnl'] for t in losses))
        
        pnls = [t['pnl'] for t in trades]
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_pnl': np.mean(pnls),
            'avg_win': np.mean([t['pnl'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl'] for t in losses]) if losses else 0,
            'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
            'sharpe_ratio': np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0,
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'avg_trade_duration': np.mean([t['duration_hours'] for t in trades]),
            'best_trade': max(pnls),
            'worst_trade': min(pnls)
        }
    
    def get_position_risk_report(self, symbol: str) -> Dict:
        """Get risk report for a specific position"""
        if symbol not in self.portfolio.positions:
            return {'error': 'Position not found'}
        
        position = self.portfolio.positions[symbol]
        
        # Distance to stop
        if position.side == 'long':
            stop_distance = ((position.current_price - position.stop_loss) / position.current_price * 100) if position.current_price > 0 else 0
        else:
            stop_distance = ((position.stop_loss - position.current_price) / position.current_price * 100) if position.current_price > 0 else 0
        
        # Risk/Reward
        risk = abs(position.entry_price - position.stop_loss)
        reward_1 = abs(position.take_profit_1 - position.entry_price)
        rr_ratio = reward_1 / risk if risk > 0 else 0
        
        return {
            'symbol': symbol,
            'position_value': position.value,
            'unrealized_pnl': position.pnl,
            'unrealized_pnl_pct': position.pnl_pct,
            'stop_distance_pct': stop_distance,
            'risk_reward_ratio': rr_ratio,
            'time_in_trade_hours': (datetime.now() - position.entry_time).total_seconds() / 3600,
            'should_exit': position.should_exit
        }
    
    def set_risk_level(self, level: RiskLevel):
        """Change risk level dynamically"""
        self.risk_level = level
        self.risk_params = self._set_risk_params()
    
    def get_daily_summary(self) -> Dict:
        """Get daily trading summary"""
        today_trades = [t for t in self.portfolio.closed_trades 
                       if t['exit_time'].date() == datetime.now().date()]
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trades_today': len(today_trades),
            'pnl_today': sum(t['pnl'] for t in today_trades),
            'win_rate_today': len([t for t in today_trades if t['pnl'] > 0]) / len(today_trades) * 100 if today_trades else 0,
            'open_positions': len(self.portfolio.positions),
            'exposure_pct': self.portfolio.margin_used_pct,
            'available_buying_power': self.portfolio.available_cash,
            'current_drawdown': self.current_drawdown
        }


class PortfolioOptimizer:
    """Portfolio optimization using Modern Portfolio Theory"""
    
    def __init__(self):
        self.returns_data: Dict[str, List[float]] = {}  # symbol -> returns
        
    def add_returns(self, symbol: str, returns: List[float]):
        """Add historical returns for a symbol"""
        self.returns_data[symbol] = returns
    
    def optimize(self, target_return: Optional[float] = None) -> Dict:
        """Optimize portfolio weights"""
        if len(self.returns_data) < 2:
            return {'error': 'Need at least 2 assets'}
        
        symbols = list(self.returns_data.keys())
        returns_matrix = np.array([self.returns_data[s] for s in symbols])
        
        # Expected returns
        expected_returns = np.mean(returns_matrix, axis=1)
        
        # Covariance matrix
        cov_matrix = np.cov(returns_matrix)
        
        # Number of assets
        n = len(symbols)
        
        # Optimize for maximum Sharpe ratio
        def neg_sharpe(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -(portfolio_return / portfolio_volatility) if portfolio_volatility > 0 else 0
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 0.5) for _ in range(n)]  # Max 50% in any asset
        
        # Initial guess
        x0 = np.array([1/n] * n)
        
        from scipy.optimize import minimize
        result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        optimal_weights = result.x
        
        portfolio_return = np.dot(optimal_weights, expected_returns)
        portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
        sharpe = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return {
            'weights': {symbols[i]: optimal_weights[i] for i in range(n)},
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_volatility,
            'sharpe_ratio': sharpe,
            'symbols': symbols
        }


# Usage example
if __name__ == "__main__":
    # Initialize risk manager
    risk = RiskManager(RiskLevel.MODERATE)
    
    # Set portfolio value
    risk.portfolio.total_equity = 100000
    risk.portfolio.available_cash = 100000
    
    # Calculate position size
    sizing = risk.calculate_position_size(
        symbol="SOL",
        entry_price=150.0,
        stop_loss=142.5,  # 5% stop
        portfolio_value=100000,
        confidence=75
    )
    
    print(f"Position sizing: {sizing}")
    
    # Set stop levels
    stops = risk.set_stop_levels(150.0, 'long')
    print(f"Stop levels: {stops}")
    
    # Create position
    position = Position(
        symbol="SOL",
        entry_price=150.0,
        current_price=150.0,
        quantity=sizing['quantity'],
        side='long',
        entry_time=datetime.now(),
        stop_loss=stops['stop_loss'],
        take_profit_1=stops['take_profit_1'],
        take_profit_2=stops['take_profit_2'],
        take_profit_3=stops['take_profit_3'],
        trailing_distance=stops['trailing_distance']
    )
    
    risk.update_portfolio(position)
    
    # Check portfolio stats
    stats = risk.get_portfolio_stats()
    print(f"Portfolio stats: {stats}")
