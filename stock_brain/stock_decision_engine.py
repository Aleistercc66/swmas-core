"""
Stock Decision Engine — Signal Scoring + Trade Approval
Score > 70, edge > 2%, R:R > 1:2, portfolio heat < 30%
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

from stock_config import DEFAULT_DECISION_CONFIG, DecisionConfig
from stock_signal_generator import Signal, SignalBatch
from stock_risk_manager import RiskManager, PortfolioState

logger = logging.getLogger(__name__)

# ───────────────────────────
# DECISION DATA MODELS
# ───────────────────────────

@dataclass
class TradeDecision:
    """A final trade decision."""
    symbol: str
    action: str  # BUY, SELL, HOLD
    direction: str  # LONG, SHORT
    
    # Size
    shares: int
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Risk
    risk_amount: float
    risk_percent: float
    position_size_percent: float
    
    # Signal
    signal_score: float
    adjusted_score: float
    edge_percent: float
    rr_ratio: float
    signal_type: str
    
    # Confidence
    confidence: str  # HIGH, MEDIUM, LOW
    decision_reason: str
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    portfolio_heat_before: float = 0.0
    portfolio_heat_after: float = 0.0

@dataclass
class DecisionBatch:
    """Batch of trade decisions."""
    timestamp: datetime
    decisions: List[TradeDecision] = field(default_factory=list)
    rejected_signals: List[Tuple[Signal, str]] = field(default_factory=list)
    
    # Stats
    total_signals: int = 0
    approved: int = 0
    rejected: int = 0
    total_risk: float = 0.0
    total_heat_after: float = 0.0

# ───────────────────────────
# DECISION ENGINE
# ───────────────────────────

class DecisionEngine:
    """
    Trade decision engine for US stock trading.
    
    Approval criteria:
    - Signal score > 70
    - Edge > 2%
    - R:R > 1:2
    - Portfolio heat < 30%
    - Risk manager validates
    - No correlation conflicts
    """
    
    def __init__(
        self,
        config: DecisionConfig = None,
        risk_manager: RiskManager = None,
    ):
        self.config = config or DEFAULT_DECISION_CONFIG
        self.risk_manager = risk_manager or RiskManager()
        
        logger.info(
            f"DecisionEngine initialized — "
            f"min_score={self.config.min_signal_score}, "
            f"min_edge={self.config.min_edge_percent}%, "
            f"min_rr={self.config.min_rr_ratio}:1"
        )
    
    def process_signals(self, signal_batch: SignalBatch) -> DecisionBatch:
        """
        Process a batch of signals into trade decisions.
        
        Args:
            signal_batch: Signals from SignalGenerator
            
        Returns:
            DecisionBatch with approved and rejected trades
        """
        logger.info(f"🧠 Processing {signal_batch.total_signals} signals...")
        
        decisions: List[TradeDecision] = []
        rejected: List[Tuple[Signal, str]] = []
        
        for signal in signal_batch.signals:
            try:
                decision = self._evaluate_signal(signal)
                
                if decision:
                    decisions.append(decision)
                else:
                    rejected.append((signal, "Failed evaluation"))
                    
            except Exception as e:
                logger.warning(f"Error evaluating {signal.symbol}: {e}")
                rejected.append((signal, str(e)))
        
        # Sort by adjusted score (best first)
        decisions.sort(key=lambda x: x.adjusted_score, reverse=True)
        
        # Limit to max positions
        max_positions = self.risk_manager.config.max_positions
        if len(decisions) > max_positions:
            for d in decisions[max_positions:]:
                rejected.append((
                    self._signal_from_decision(d), "Max positions reached"
                ))
            decisions = decisions[:max_positions]
        
        batch = DecisionBatch(
            timestamp=datetime.utcnow(),
            decisions=decisions,
            rejected_signals=rejected,
            total_signals=signal_batch.total_signals,
            approved=len(decisions),
            rejected=len(rejected),
            total_risk=sum(d.risk_amount for d in decisions),
            total_heat_after=decisions[-1].portfolio_heat_after if decisions else 0,
        )
        
        logger.info(
            f"✅ Decisions: {batch.approved} approved, {batch.rejected} rejected | "
            f"Total risk: ${batch.total_risk:.2f}"
        )
        
        return batch
    
    def _evaluate_signal(self, signal: Signal) -> Optional[TradeDecision]:
        """
        Evaluate a single signal and create trade decision if approved.
        
        Returns:
            TradeDecision or None if rejected
        """
        # Step 1: Risk manager validation
        valid, reason, adjusted_score = self.risk_manager.validate_signal(signal)
        if not valid:
            logger.info(f"REJECTED {signal.symbol}: {reason}")
            return None
        
        # Step 2: Score threshold
        if adjusted_score < self.config.min_signal_score:
            logger.info(f"REJECTED {signal.symbol}: Score {adjusted_score:.0f} < {self.config.min_signal_score}")
            return None
        
        # Step 3: Edge threshold
        if signal.edge_percent < self.config.min_edge_percent:
            logger.info(f"REJECTED {signal.symbol}: Edge {signal.edge_percent:.2f}% < {self.config.min_edge_percent}%")
            return None
        
        # Step 4: R:R threshold
        if signal.rr_ratio < self.config.min_rr_ratio:
            logger.info(f"REJECTED {signal.symbol}: R:R {signal.rr_ratio:.1f} < {self.config.min_rr_ratio}")
            return None
        
        # Step 5: Calculate position size
        shares, risk_amount, sizing_details = self.risk_manager.calculate_position_size(signal)
        
        if shares <= 0:
            logger.info(f"REJECTED {signal.symbol}: Position size too small")
            return None
        
        # Step 6: Check portfolio heat after this trade
        heat_before = self.risk_manager._calculate_portfolio_heat()
        position_value = shares * signal.entry_price
        portfolio_value = self.risk_manager.portfolio.total_value
        heat_after = heat_before + (position_value / portfolio_value * 100)
        
        if heat_after > self.config.max_portfolio_heat:
            logger.info(f"REJECTED {signal.symbol}: Heat would be {heat_after:.1f}% > {self.config.max_portfolio_heat}%")
            return None
        
        # Step 7: Determine confidence
        if adjusted_score >= self.config.confidence_tiers["HIGH"]:
            confidence = "HIGH"
        elif adjusted_score >= self.config.confidence_tiers["MEDIUM"]:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Step 8: Determine action
        action = "BUY" if signal.direction == "LONG" else "SELL"
        
        # Step 9: Build decision reason
        reasons = [
            f"Score: {adjusted_score:.0f}",
            f"Edge: {signal.edge_percent:.1f}%",
            f"R:R: {signal.rr_ratio:.1f}:1",
            f"Type: {signal.signal_type}",
            f"Risk: ${risk_amount:.2f}",
        ]
        decision_reason = " | ".join(reasons)
        
        # Build decision
        decision = TradeDecision(
            symbol=signal.symbol,
            action=action,
            direction=signal.direction,
            shares=shares,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
            take_profit_3=signal.take_profit_3,
            risk_amount=risk_amount,
            risk_percent=(risk_amount / portfolio_value) * 100,
            position_size_percent=(position_value / portfolio_value) * 100,
            signal_score=signal.score,
            adjusted_score=adjusted_score,
            edge_percent=signal.edge_percent,
            rr_ratio=signal.rr_ratio,
            signal_type=signal.signal_type,
            confidence=confidence,
            decision_reason=decision_reason,
            portfolio_heat_before=heat_before,
            portfolio_heat_after=heat_after,
        )
        
        logger.info(
            f"APPROVED {signal.symbol}: {action} {shares} shares @ ${signal.entry_price:.2f} | "
            f"Score: {adjusted_score:.0f} | R:R {signal.rr_ratio:.1f}:1 | "
            f"Risk: ${risk_amount:.2f} ({decision.risk_percent:.2f}%)"
        )
        
        return decision
    
    def _signal_from_decision(self, decision: TradeDecision) -> Signal:
        """Recreate a Signal from a TradeDecision (for rejected tracking)."""
        return Signal(
            symbol=decision.symbol,
            signal_type=decision.signal_type,
            direction=decision.direction,
            score=decision.signal_score,
            confidence="LOW",
            entry_price=decision.entry_price,
            stop_loss=decision.stop_loss,
            take_profit_1=decision.take_profit_1,
            take_profit_2=decision.take_profit_2,
            take_profit_3=decision.take_profit_3,
            edge_percent=decision.edge_percent,
            rr_ratio=decision.rr_ratio,
        )
    
    def get_decision_summary(self, batch: DecisionBatch) -> str:
        """Get human-readable summary of decisions."""
        lines = [
            f"🎯 DECISION BATCH — {batch.timestamp.strftime('%H:%M:%S')}",
            f"Signals: {batch.total_signals} | Approved: {batch.approved} | Rejected: {batch.rejected}",
            f"Total Risk: ${batch.total_risk:.2f} | Heat After: {batch.total_heat_after:.1f}%",
            "",
            "🔥 APPROVED TRADES:",
        ]
        
        for i, d in enumerate(batch.decisions[:5], 1):
            emoji = "🟢" if d.direction == "LONG" else "🔴"
            lines.append(
                f"{i}. {emoji} {d.symbol} | {d.action} {d.shares} @ ${d.entry_price:.2f} | "
                f"Score: {d.adjusted_score:.0f} | R:R {d.rr_ratio:.1f}:1 | "
                f"Risk: ${d.risk_amount:.2f} ({d.risk_percent:.2f}%) | "
                f"Heat: {d.portfolio_heat_after:.1f}%"
            )
        
        if batch.rejected_signals:
            lines.append("")
            lines.append("❌ REJECTED:")
            for signal, reason in batch.rejected_signals[:5]:
                lines.append(f"  {signal.symbol}: {reason}")
        
        return "\n".join(lines)
    
    def get_top_opportunity(self, batch: DecisionBatch) -> Optional[TradeDecision]:
        """Get the highest-scored opportunity."""
        if not batch.decisions:
            return None
        return max(batch.decisions, key=lambda x: x.adjusted_score)
    
    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "risk_status": self.risk_manager.get_status(),
            "decision_config": {
                "min_signal_score": self.config.min_signal_score,
                "min_edge_percent": self.config.min_edge_percent,
                "min_rr_ratio": self.config.min_rr_ratio,
                "max_portfolio_heat": self.config.max_portfolio_heat,
            },
            "can_trade": self.risk_manager.can_trade()[0],
        }


# ───────────────────────────
# MAIN (for testing)
# ───────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create test signals
    test_signals = [
        Signal(symbol="AAPL", signal_type="MOMENTUM", direction="LONG", score=82, confidence="HIGH",
               entry_price=180.0, stop_loss=176.0, take_profit_1=186.0, take_profit_2=190.0, take_profit_3=198.0,
               edge_percent=3.5, rr_ratio=2.0),
        Signal(symbol="TSLA", signal_type="MEAN_REVERSION", direction="LONG", score=75, confidence="MEDIUM",
               entry_price=240.0, stop_loss=228.0, take_profit_1=247.0, take_profit_2=255.0, take_profit_3=270.0,
               edge_percent=2.5, rr_ratio=1.8),
        Signal(symbol="NVDA", signal_type="BREAKOUT", direction="LONG", score=88, confidence="HIGH",
               entry_price=890.0, stop_loss=863.0, take_profit_1=920.0, take_profit_2=950.0, take_profit_3=1000.0,
               edge_percent=4.2, rr_ratio=2.5),
    ]
    
    test_batch = SignalBatch(
        timestamp=datetime.utcnow(),
        signals=test_signals,
        total_signals=3,
        long_signals=3,
        short_signals=0,
        high_confidence=2,
        avg_score=81.7,
    )
    
    engine = DecisionEngine()
    decisions = engine.process_signals(test_batch)
    
    print(engine.get_decision_summary(decisions))
    
    print(f"\n📊 Risk report:")
    for k, v in engine.get_risk_report().items():
        print(f"  {k}: {v}")
