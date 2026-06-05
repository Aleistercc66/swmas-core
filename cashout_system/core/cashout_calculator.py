#!/usr/bin/env python3
"""
CashOut Calculator - Advanced EV tracking and price drift simulation
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cashout_calculator")


@dataclass
class CashOutAnalysis:
    match_id: str
    home_team: str
    away_team: str
    current_score: str
    original_odds: float
    current_odds: float
    stake: float
    original_expected_value: float
    current_expected_value: float
    cash_out_value: float
    cash_out_ev: float
    cash_out_roi: float
    price_drift: float
    price_drift_pct: float
    recommendation: str
    confidence: float
    optimal_cash_out: bool
    last_updated: str


class CashOutCalculator:
    """Advanced cash-out calculator with EV tracking"""
    
    def __init__(self):
        self.history: Dict[str, List[Dict]] = {}  # Price history per match
        self.analysis_cache: Dict[str, CashOutAnalysis] = {}
        
    def calculate_cash_out(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        current_score: str,
        original_odds: float,
        current_odds: float,
        stake: float,
        cash_out_value: float = 0.0,
        market_probabilities: Dict[str, float] = None
    ) -> CashOutAnalysis:
        """Calculate cash-out analysis with EV tracking"""
        
        # Calculate original expected value
        original_ev = (original_odds * stake) - stake
        
        # Calculate current expected value
        current_ev = (current_odds * stake) - stake
        
        # Calculate cash-out EV
        if cash_out_value > 0:
            cash_out_ev = cash_out_value - stake
            cash_out_roi = (cash_out_value / stake - 1) * 100
        else:
            cash_out_ev = 0
            cash_out_roi = 0
        
        # Calculate price drift
        price_drift = current_odds - original_odds
        price_drift_pct = ((current_odds - original_odds) / original_odds * 100) if original_odds > 0 else 0
        
        # Determine recommendation
        if market_probabilities:
            recommendation = self._get_recommendation_with_prob(
                original_ev, current_ev, cash_out_ev, cash_out_roi, 
                price_drift_pct, market_probabilities
            )
        else:
            recommendation = self._get_simple_recommendation(
                cash_out_roi, price_drift_pct
            )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            price_drift_pct, cash_out_roi, len(self.history.get(match_id, []))
        )
        
        # Determine if cash-out is optimal
        optimal_cash_out = cash_out_roi > 20 and price_drift_pct < -10
        
        analysis = CashOutAnalysis(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            current_score=current_score,
            original_odds=original_odds,
            current_odds=current_odds,
            stake=stake,
            original_expected_value=original_ev,
            current_expected_value=current_ev,
            cash_out_value=cash_out_value,
            cash_out_ev=cash_out_ev,
            cash_out_roi=cash_out_roi,
            price_drift=price_drift,
            price_drift_pct=price_drift_pct,
            recommendation=recommendation,
            confidence=confidence,
            optimal_cash_out=optimal_cash_out,
            last_updated=datetime.now().isoformat()
        )
        
        # Store in cache
        self.analysis_cache[match_id] = analysis
        
        # Add to history
        if match_id not in self.history:
            self.history[match_id] = []
        self.history[match_id].append({
            "timestamp": datetime.now().isoformat(),
            "odds": current_odds,
            "cash_out_value": cash_out_value
        })
        
        return analysis
    
    def _get_simple_recommendation(self, cash_out_roi: float, price_drift_pct: float) -> str:
        """Simple recommendation based on ROI and drift"""
        if cash_out_roi > 50:
            return "🟢 STRONG CASH-OUT - High profit available!"
        elif cash_out_roi > 20:
            return "🟢 GOOD CASH-OUT - Solid profit available"
        elif cash_out_roi > 0 and price_drift_pct < -15:
            return "🟡 CONSIDER CASH-OUT - Price drifting against you"
        elif cash_out_roi < -20:
            return "🔴 HOLD - Don't cash out at loss"
        elif price_drift_pct > 20:
            return "🟢 HOLD - Price moving in your favor"
        else:
            return "🟡 MONITOR - Watch and wait"
    
    def _get_recommendation_with_prob(
        self, original_ev: float, current_ev: float, cash_out_ev: float,
        cash_out_roi: float, price_drift_pct: float, probabilities: Dict[str, float]
    ) -> str:
        """Advanced recommendation with market probabilities"""
        
        home_win_prob = probabilities.get("home_win", 0.33)
        draw_prob = probabilities.get("draw", 0.33)
        away_win_prob = probabilities.get("away_win", 0.33)
        
        # Calculate implied probability from odds
        total_prob = (1/self.analysis_cache.get("current_odds", 2.0)) if hasattr(self, 'analysis_cache') else 0.5
        
        if cash_out_roi > 50:
            return "🟢 STRONG CASH-OUT - Lock in massive profit!"
        elif cash_out_roi > 30 and price_drift_pct < -10:
            return "🟢 CASH-OUT RECOMMENDED - Price drift + solid profit"
        elif cash_out_roi > 0 and home_win_prob < 0.3:
            return "🟡 CONSIDER CASH-OUT - Probability against you"
        elif cash_out_roi < -10:
            return "🔴 HOLD - Wait for better opportunity"
        else:
            return "🟡 MONITOR - Collect more data"
    
    def _calculate_confidence(self, drift_pct: float, roi: float, history_len: int) -> float:
        """Calculate confidence score 0-100"""
        confidence = 50.0
        
        # More history = more confidence
        confidence += min(history_len * 2, 20)
        
        # High drift = less confidence (volatility)
        confidence -= min(abs(drift_pct) / 2, 15)
        
        # High ROI = more confidence
        if roi > 0:
            confidence += min(roi / 2, 25)
        else:
            confidence -= min(abs(roi), 15)
        
        return max(0, min(100, confidence))
    
    def simulate_price_drift(
        self, match_id: str, current_odds: float, 
        time_horizon_minutes: int = 90, volatility: float = 0.1
    ) -> List[float]:
        """Simulate price drift over time using Monte Carlo"""
        
        # Number of simulations
        n_sims = 100
        n_steps = time_horizon_minutes
        
        # Store simulations
        simulations = []
        
        for _ in range(n_sims):
            prices = [current_odds]
            for _ in range(n_steps):
                # Random walk with drift
                drift = np.random.normal(0, volatility)
                new_price = prices[-1] * (1 + drift)
                prices.append(max(new_price, 1.01))  # Min odds 1.01
            simulations.append(prices)
        
        # Calculate percentiles
        final_prices = [sim[-1] for sim in simulations]
        
        return {
            "current": current_odds,
            "median": np.median(final_prices),
            "mean": np.mean(final_prices),
            "p10": np.percentile(final_prices, 10),
            "p90": np.percentile(final_prices, 90),
            "prob_increase": sum(1 for p in final_prices if p > current_odds) / n_sims,
            "prob_decrease": sum(1 for p in final_prices if p < current_odds) / n_sims,
        }
    
    def get_price_trend(self, match_id: str) -> Dict:
        """Analyze price trend from history"""
        history = self.history.get(match_id, [])
        
        if len(history) < 2:
            return {"trend": "insufficient_data", "slope": 0}
        
        # Calculate trend
        odds_list = [h["odds"] for h in history]
        x = np.arange(len(odds_list))
        slope = np.polyfit(x, odds_list, 1)[0]
        
        if slope > 0.01:
            trend = "increasing"
        elif slope < -0.01:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": slope,
            "data_points": len(history),
            "min_odds": min(odds_list),
            "max_odds": max(odds_list),
            "avg_odds": np.mean(odds_list)
        }
    
    def format_analysis(self, analysis: CashOutAnalysis) -> str:
        """Format analysis for display"""
        return f"""
💰 **CASH-OUT ANALYSIS** 💰

⚽ {analysis.home_team} vs {analysis.away_team}
📊 Score: {analysis.current_score}

📈 **ODDS TRACKING**
Original: {analysis.original_odds:.2f}
Current: {analysis.current_odds:.2f}
Drift: {analysis.price_drift:+.2f} ({analysis.price_drift_pct:+.1f}%)

💵 **STAKE & VALUE**
Stake: €{analysis.stake:.2f}
Cash-Out Value: €{analysis.cash_out_value:.2f}
Cash-Out ROI: {analysis.cash_out_roi:+.1f}%

🎯 **EV ANALYSIS**
Original EV: €{analysis.original_expected_value:.2f}
Current EV: €{analysis.current_expected_value:.2f}
Cash-Out EV: €{analysis.cash_out_ev:.2f}

📋 **RECOMMENDATION**
{analysis.recommendation}

🎯 Confidence: {analysis.confidence:.0f}%
⏰ Updated: {analysis.last_updated}
"""
    
    def save_analysis(self, match_id: str, filepath: str = None):
        """Save analysis to file"""
        filepath = filepath or f"/root/.openclaw/workspace/cashout_system/data/analysis_{match_id}.json"
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        analysis = self.analysis_cache.get(match_id)
        if analysis:
            with open(filepath, 'w') as f:
                json.dump(asdict(analysis), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved analysis to {filepath}")


# Example usage
if __name__ == "__main__":
    calc = CashOutCalculator()
    
    analysis = calc.calculate_cash_out(
        match_id="12345",
        home_team="Olympiacos",
        away_team="PAOK",
        current_score="2-1",
        original_odds=2.50,
        current_odds=1.80,
        stake=100.0,
        cash_out_value=135.0
    )
    
    print(calc.format_analysis(analysis))
    
    # Simulate price drift
    drift_sim = calc.simulate_price_drift("12345", 1.80, 90)
    print(f"\n📊 Price Drift Simulation:")
    print(f"Median: {drift_sim['median']:.2f}")
    print(f"P10: {drift_sim['p10']:.2f}")
    print(f"P90: {drift_sim['p90']:.2f}")
    print(f"Prob Increase: {drift_sim['prob_increase']:.1%}")