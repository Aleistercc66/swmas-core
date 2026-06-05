#!/usr/bin/env python3
"""
Strategy Engine - Στρατηγικές απόφασης για trades
Μαθαίνει από επιτυχίες/αποτυχίες και προσαρμόζεται.
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from statistics import mean, median


@dataclass
class Strategy:
    """Trading strategy με performance tracking."""
    name: str
    description: str
    conditions: Dict[str, Any]  # Τι πρέπει να ισχύει
    entry_rules: List[str]
    exit_rules: List[str]
    risk_rules: List[str]
    
    # Performance
    total_trades: int = 0
    winning_trades: int = 0
    total_return: float = 0.0
    avg_return: float = 0.0
    max_return: float = 0.0
    max_drawdown: float = 0.0
    
    # Scoring
    confidence: float = 0.5  # 0-1, based on historical performance
    last_used: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    def update(self, won: bool, return_pct: float):
        self.total_trades += 1
        if won:
            self.winning_trades += 1
        
        self.total_return += return_pct
        self.avg_return = self.total_return / self.total_trades
        
        if return_pct > self.max_return:
            self.max_return = return_pct
        if return_pct < self.max_drawdown:
            self.max_drawdown = return_pct
        
        # Update confidence based on track record
        if self.total_trades >= 10:
            self.confidence = self.win_rate() * min(1.0, self.avg_return / 50)
        
        self.last_used = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "entry_rules": self.entry_rules,
            "exit_rules": self.exit_rules,
            "risk_rules": self.risk_rules,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "total_return": self.total_return,
            "avg_return": self.avg_return,
            "max_return": self.max_return,
            "max_drawdown": self.max_drawdown,
            "confidence": self.confidence,
            "last_used": self.last_used,
            "created_at": self.created_at,
        }


class StrategyEngine:
    """
    Engine που διαχειρίζεται στρατηγικές και επιλέγει την καλύτερη.
    """
    
    def __init__(self, storage_path: str = "solana_strategies.json"):
        self.storage_path = storage_path
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategy: Optional[str] = None
        self.market_regime: str = "unknown"  # bull/bear/sideways/volatile
        self.last_regime_change: float = 0
        
        self._init_default_strategies()
        self.load_strategies()
    
    def _init_default_strategies(self):
        """Αρχικοποίηση default στρατηγικών."""
        
        # Strategy 1: Early Momentum Catch
        self.strategies["early_momentum"] = Strategy(
            name="early_momentum",
            description="Catch momentum early (5-15% move) and ride to 15-30%",
            conditions={
                "m5_change_min": 3,
                "h1_change_min": 8,
                "h1_change_max": 30,  # Not too extended
                "volume_ratio_min": 2,
                "liquidity_min": 10000,
            },
            entry_rules=[
                "Enter immediately if m5 > 5% and h1 > 10%",
                "Use 50% position at market, 50% on any dip",
            ],
            exit_rules=[
                "TP1 at +15% (50% of position)",
                "TP2 at +25% (30% of position)",
                "TP3 at +35% (20% of position, trailing stop)",
                "Auto exit after 4h if no TP hit",
            ],
            risk_rules=[
                "Stop loss at -8%",
                "Max position: 5% of portfolio",
                "Never hold overnight without trailing stop",
            ],
        )
        
        # Strategy 2: Pullback Entry
        self.strategies["pullback_entry"] = Strategy(
            name="pullback_entry",
            description="Wait for pullback after initial pump, then enter",
            conditions={
                "h1_change_min": 20,  # Already pumped
                "h1_change_max": 100,
                "pullback_min": 5,  # At least 5% pullback
                "pullback_max": 20,  # But not more than 20%
                "volume_ratio_min": 3,
            },
            entry_rules=[
                "Wait for 5-15% pullback from local high",
                "Enter when momentum resumes (m5 turns positive)",
            ],
            exit_rules=[
                "TP1 at +12% (50% of position)",
                "TP2 at +20% (30% of position)",
                "TP3 at +30% (20% of position)",
            ],
            risk_rules=[
                "Stop loss at -10%",
                "Max position: 7% of portfolio",
                "Exit if pullback exceeds 25%",
            ],
        )
        
        # Strategy 3: Volume Breakout
        self.strategies["volume_breakout"] = Strategy(
            name="volume_breakout",
            description="Enter when volume spikes >3x average with price moving",
            conditions={
                "volume_spike_min": 3,
                "m5_change_min": 2,
                "h1_change_min": 5,
                "liquidity_min": 15000,
            },
            entry_rules=[
                "Enter when volume >3x 24h average AND price up >3% in 5m",
                "Confirm with second volume spike within 15m",
            ],
            exit_rules=[
                "TP1 at +20% (40% of position)",
                "TP2 at +30% (35% of position)",
                "TP3 at +50% (25% of position)",
            ],
            risk_rules=[
                "Stop loss at -12%",
                "Max position: 8% of portfolio",
                "Exit if volume drops below average within 1h",
            ],
        )
        
        # Strategy 4: New Launch Snipe
        self.strategies["launch_snipe"] = Strategy(
            name="launch_snipe",
            description="Buy new launches within first 30 minutes",
            conditions={
                "age_max_minutes": 30,
                "launch_platform": ["pump_fun", "raydium"],
                "initial_liquidity_min": 5000,
                "m5_change_min": 10,
            },
            entry_rules=[
                "Buy within 5 minutes of launch if m5 > 20%",
                "Scale in: 30% at 2min, 40% at 5min, 30% at 10min",
            ],
            exit_rules=[
                "TP1 at +50% (50% of position) — quick profit",
                "TP2 at +100% (30% of position)",
                "Let 20% run with trailing stop",
                "Auto exit 50% at 2h mark",
            ],
            risk_rules=[
                "Stop loss at -20% (high risk strategy)",
                "Max position: 3% of portfolio",
                "NEVER hold new launches >6h without taking profit",
                "If volume drops 50% from peak, exit immediately",
            ],
        )
        
        # Strategy 5: Dip Buy Recovery
        self.strategies["dip_recovery"] = Strategy(
            name="dip_recovery",
            description="Buy oversold tokens with high probability of bounce",
            conditions={
                "h24_change_min": -50,  # Down big
                "h24_change_max": -15,
                "h1_change_min": -5,  # But stabilizing
                "volume_ratio_min": 1.5,
                "liquidity_min": 20000,
            },
            entry_rules=[
                "Wait for 1h candle to turn green after dump",
                "Enter on first positive 5m candle",
            ],
            exit_rules=[
                "TP1 at +10% (60% of position)",
                "TP2 at +20% (40% of position)",
            ],
            risk_rules=[
                "Stop loss at -8% (below recent low)",
                "Max position: 4% of portfolio",
                "Exit if new low is made",
            ],
        )
    
    def load_strategies(self):
        """Φόρτωση στρατηγικών από disk."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for name, strat_data in data.get("strategies", {}).items():
                    if name in self.strategies:
                        # Update existing with saved performance
                        s = self.strategies[name]
                        s.total_trades = strat_data.get("total_trades", 0)
                        s.winning_trades = strat_data.get("winning_trades", 0)
                        s.total_return = strat_data.get("total_return", 0)
                        s.avg_return = strat_data.get("avg_return", 0)
                        s.max_return = strat_data.get("max_return", 0)
                        s.max_drawdown = strat_data.get("max_drawdown", 0)
                        s.confidence = strat_data.get("confidence", 0.5)
                
                self.market_regime = data.get("market_regime", "unknown")
                print(f"📋 Loaded {len(self.strategies)} strategies")
        except FileNotFoundError:
            print("📋 Using default strategies")
    
    def save_strategies(self):
        """Αποθήκευση στρατηγικών."""
        data = {
            "strategies": {
                name: strat.to_dict()
                for name, strat in self.strategies.items()
            },
            "market_regime": self.market_regime,
            "active_strategy": self.active_strategy,
            "saved_at": time.time(),
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def select_strategy(self, token_data: Dict, market_conditions: Dict) -> Optional[str]:
        """Επιλογή καλύτερης στρατηγικής για το setup."""
        
        scores = {}
        
        for name, strategy in self.strategies.items():
            score = self._score_strategy_for_setup(strategy, token_data, market_conditions)
            scores[name] = score
        
        if not scores:
            return None
        
        # Select best
        best = max(scores, key=scores.get)
        
        if scores[best] < 30:  # Minimum threshold
            return None
        
        self.active_strategy = best
        return best
    
    def _score_strategy_for_setup(self, strategy: Strategy, token_data: Dict, 
                                   market_conditions: Dict) -> float:
        """Score πόσο κατάλληλη είναι μια στρατηγική."""
        score = 0.0
        conditions = strategy.conditions
        
        # Check conditions match
        if "m5_change_min" in conditions:
            m5 = token_data.get("changes", {}).get("m5", 0)
            if m5 >= conditions["m5_change_min"]:
                score += 20
        
        if "h1_change_min" in conditions:
            h1 = token_data.get("changes", {}).get("h1", 0)
            if h1 >= conditions["h1_change_min"]:
                score += 20
            if "h1_change_max" in conditions and h1 <= conditions["h1_change_max"]:
                score += 10
        
        if "volume_ratio_min" in conditions:
            vol = token_data.get("volume_24h", 0)
            liq = token_data.get("liquidity", 1)
            ratio = vol / liq if liq > 0 else 0
            if ratio >= conditions["volume_ratio_min"]:
                score += 20
        
        if "liquidity_min" in conditions:
            if token_data.get("liquidity", 0) >= conditions["liquidity_min"]:
                score += 15
        
        # Historical confidence bonus
        score += strategy.confidence * 25
        
        # Win rate bonus (if enough data)
        if strategy.total_trades >= 5:
            score += strategy.win_rate() * 10
        
        return score
    
    def get_strategy(self, name: str) -> Optional[Strategy]:
        """Get strategy by name."""
        return self.strategies.get(name)
    
    def record_trade_result(self, strategy_name: str, success: bool, return_pct: float):
        """Record result for learning."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update(success, return_pct)
            self.save_strategies()
            
            print(f"📊 Strategy '{strategy_name}' updated: {self.strategies[strategy_name].win_rate():.1%} win rate ({self.strategies[strategy_name].total_trades} trades)")
    
    def get_best_performing_strategy(self) -> Optional[Strategy]:
        """Get strategy with best historical performance."""
        if not self.strategies:
            return None
        
        # Filter strategies with enough data
        experienced = [s for s in self.strategies.values() if s.total_trades >= 5]
        
        if not experienced:
            return max(self.strategies.values(), key=lambda s: s.confidence)
        
        return max(experienced, key=lambda s: s.avg_return * s.win_rate())
    
    def adapt_to_market_regime(self, sol_price_change_24h: float, 
                                volatility: float):
        """Adapt strategies based on market regime."""
        
        new_regime = self._detect_regime(sol_price_change_24h, volatility)
        
        if new_regime != self.market_regime:
            print(f"🔄 Market regime changed: {self.market_regime} -> {new_regime}")
            self.market_regime = new_regime
            self.last_regime_change = time.time()
            
            # Adjust strategies based on regime
            self._adjust_for_regime(new_regime)
    
    def _detect_regime(self, sol_change: float, volatility: float) -> str:
        """Detect market regime."""
        if sol_change > 10 and volatility > 0.5:
            return "volatile_bull"
        elif sol_change > 5:
            return "bull"
        elif sol_change < -10 and volatility > 0.5:
            return "volatile_bear"
        elif sol_change < -5:
            return "bear"
        elif volatility > 0.8:
            return "volatile"
        else:
            return "sideways"
    
    def _adjust_for_regime(self, regime: str):
        """Adjust strategy parameters for market regime."""
        
        if regime in ["bull", "volatile_bull"]:
            # More aggressive in bull
            for s in self.strategies.values():
                if "max_position" in str(s.risk_rules):
                    # Increase position sizes (handled in execution)
                    pass
        
        elif regime in ["bear", "volatile_bear"]:
            # More conservative, focus on dip recovery
            pass
        
        elif regime == "volatile":
            # Tighter stops, quicker profits
            pass
        
        self.save_strategies()
    
    def generate_strategy_report(self) -> Dict:
        """Generate strategy performance report."""
        return {
            "strategies": [
                {
                    "name": s.name,
                    "description": s.description,
                    "total_trades": s.total_trades,
                    "win_rate": s.win_rate(),
                    "avg_return": s.avg_return,
                    "max_return": s.max_return,
                    "max_drawdown": s.max_drawdown,
                    "confidence": s.confidence,
                }
                for s in self.strategies.values()
            ],
            "best_strategy": self.get_best_performing_strategy().name if self.get_best_performing_strategy() else None,
            "market_regime": self.market_regime,
            "active_strategy": self.active_strategy,
        }


if __name__ == "__main__":
    engine = StrategyEngine()
    
    # Show strategies
    print("\n📋 Available Strategies:")
    for name, strat in engine.strategies.items():
        print(f"\n{name}:")
        print(f"  {strat.description}")
        print(f"  Win rate: {strat.win_rate():.1%} ({strat.total_trades} trades)")
        print(f"  Avg return: {strat.avg_return:.1f}%")
        print(f"  Confidence: {strat.confidence:.2f}")
    
    engine.save_strategies()
    print("\n✅ Strategies saved!")
