#!/usr/bin/env python3
"""🧠 Master Orchestrator — Brain of the trading swarm."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from core import (
    get_logger, get_settings,
    get_event_bus, EventType, SwarmEvent,
    RiskAssessedEvent, TradeDecision, PortfolioState,
    set_agent_healthy, set_agent_down, set_agent_degraded,
)

logger = get_logger("master")


class MasterOrchestrator:
    """Central brain: receives risk signals, makes decisions, manages portfolio."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bus = None
        self.running = False
        self.circuit_breaker = False
        self.circuit_reason = ""
        self.consumer_task = None
        self.heartbeat_task = None
        
        # Portfolio state (in-memory + DB)
        self.portfolio = PortfolioState(
            balance_usd=self.settings.portfolio_size_usd,
        )
        
        # Safety limits
        self.MAX_DAILY_TRADES = 8
        self.MAX_DRAWDOWN_PCT = 15.0
        self.MAX_POSITIONS = self.settings.max_positions
        self.MIN_CONFIDENCE = 60.0
        self.MIN_RISK_REWARD = 1.5
        self.PORTFOLIO_HEAT_LIMIT = 50.0  # Max % of portfolio at risk
    
    async def __aenter__(self):
        self.bus = await get_event_bus()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.bus:
            await self.bus.disconnect()
    
    # ── Portfolio Management ──
    
    def _calculate_portfolio_heat(self) -> float:
        """Calculate % of portfolio currently at risk."""
        if not self.portfolio.open_positions:
            return 0.0
        
        total_risk = sum(
            pos.get("position_size_usd", 0) * (pos.get("stop_distance_pct", 10) / 100)
            for pos in self.portfolio.open_positions
        )
        return (total_risk / self.portfolio.balance_usd) * 100 if self.portfolio.balance_usd > 0 else 0.0
    
    def _update_win_rate(self):
        """Recalculate win rate."""
        total = self.portfolio.winning_trades + self.portfolio.losing_trades
        if total > 0:
            self.portfolio.win_rate = (self.portfolio.winning_trades / total) * 100
    
    def _reset_daily_stats(self):
        """Reset daily stats if it's a new day."""
        now = datetime.utcnow()
        last = self.portfolio.last_updated
        if last and last.date() != now.date():
            logger.info("New day — resetting daily stats")
            self.portfolio.daily_trades = 0
            self.portfolio.daily_pnl = 0.0
            self.circuit_breaker = False
            self.circuit_reason = ""
    
    # ── Circuit Breakers ──
    
    def _check_circuit_breakers(self) -> tuple[bool, str]:
        """Check if trading should be halted."""
        # Check drawdown
        if self.portfolio.current_drawdown > self.MAX_DRAWDOWN_PCT:
            return True, f"Drawdown limit: {self.portfolio.current_drawdown:.1f}% > {self.MAX_DRAWDOWN_PCT}%"
        
        # Check daily trades
        if self.portfolio.daily_trades >= self.MAX_DAILY_TRADES:
            return True, f"Daily trade limit: {self.portfolio.daily_trades}/{self.MAX_DAILY_TRADES}"
        
        # Check portfolio heat
        heat = self._calculate_portfolio_heat()
        if heat > self.PORTFOLIO_HEAT_LIMIT:
            return True, f"Portfolio heat: {heat:.1f}% > {self.PORTFOLIO_HEAT_LIMIT}%"
        
        # Check max positions
        if len(self.portfolio.open_positions) >= self.MAX_POSITIONS:
            return True, f"Max positions: {len(self.portfolio.open_positions)}/{self.MAX_POSITIONS}"
        
        return False, ""
    
    # ── Trade Evaluation ──
    
    def _evaluate_signal(self, signal: Dict[str, Any]) -> TradeDecision:
        """Evaluate a single risk signal and return trading decision."""
        symbol = signal.get("symbol", "UNKNOWN")
        composite = signal.get("composite_score", 0)
        rr = signal.get("risk_reward_ratio", 0)
        tier = signal.get("tier", "TIER_3")
        entry = signal.get("entry_price", 0)
        stop = signal.get("stop_loss_price", 0)
        tps = [signal.get("take_profit_1", 0), signal.get("take_profit_2", 0), signal.get("take_profit_3", 0)]
        is_executable = signal.get("is_executable", False)
        
        # Check circuit breakers
        if self.circuit_breaker:
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason=f"Circuit breaker active: {self.circuit_reason}",
                confidence=composite,
            )
        
        tripped, reason = self._check_circuit_breakers()
        if tripped:
            self.circuit_breaker = True
            self.circuit_reason = reason
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason=f"Circuit breaker: {reason}",
                confidence=composite,
            )
        
        # Check minimum confidence
        if composite < self.MIN_CONFIDENCE:
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason=f"Confidence too low: {composite:.1f} < {self.MIN_CONFIDENCE}",
                confidence=composite,
            )
        
        # Check minimum risk/reward
        if rr < self.MIN_RISK_REWARD:
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason=f"Risk/Reward too low: {rr:.1f} < {self.MIN_RISK_REWARD}",
                confidence=composite,
            )
        
        # Check if not executable
        if not is_executable:
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason="Signal not executable (score or RR below threshold)",
                confidence=composite,
            )
        
        # Calculate position size (Kelly-like)
        risk_per_trade = self.settings.risk_per_trade_pct / 100
        position_size = self.portfolio.balance_usd * risk_per_trade
        
        # Limit by available balance
        available = self.portfolio.balance_usd - sum(
            pos.get("position_size_usd", 0) for pos in self.portfolio.open_positions
        )
        position_size = min(position_size, available * 0.95)
        
        if position_size < 10:  # Minimum $10 trade
            return TradeDecision(
                symbol=symbol,
                decision="REJECT",
                reason=f"Position size too small: ${position_size:.2f}",
                confidence=composite,
            )
        
        # APPROVED!
        portfolio_heat = self._calculate_portfolio_heat()
        
        return TradeDecision(
            symbol=symbol,
            decision="APPROVE",
            tier=tier,
            position_size_usd=round(position_size, 2),
            entry_price=round(entry, 8),
            stop_loss=round(stop, 8),
            take_profits=[round(tp, 8) for tp in tps if tp > 0],
            confidence=round(composite, 1),
            risk_reward=round(rr, 2),
            portfolio_heat_pct=round(portfolio_heat, 1),
            reason="All checks passed",
        )
    
    # ── Event Handlers ──
    
    async def handle_risk_assessed(self, event: SwarmEvent):
        """Handle RISK_ASSESSED events."""
        try:
            logger.info(f"=== MASTER CYCLE | batch={event.correlation_id} ===")
            self._reset_daily_stats()
            
            data = event.data
            signals = data.get("signals", [])
            
            logger.info(f"Evaluating {len(signals)} signals...")
            
            decisions = []
            for signal in signals:
                try:
                    decision = self._evaluate_signal(signal)
                    decisions.append(decision)
                    
                    status = "🟢 APPROVED" if decision.decision == "APPROVE" else "🔴 REJECTED"
                    logger.info(
                        f"  {decision.symbol}: {status} | "
                        f"conf={decision.confidence:.1f} RR={decision.risk_reward:.1f} "
                        f"size=${decision.position_size_usd:.2f} | {decision.reason}"
                    )
                    
                except Exception as e:
                    logger.error(f"Evaluation failed for signal: {e}")
                    continue
            
            # Count approvals
            approved = [d for d in decisions if d.decision == "APPROVE"]
            logger.info(f"Decisions: {len(approved)}/{len(decisions)} approved")
            
            # Publish decisions
            for decision in decisions:
                event_type = (
                    EventType.POSITION_OPENED if decision.decision == "APPROVE"
                    else EventType.ALERT
                )
                
                msg_id = await self.bus.publish_simple(
                    event_type=event_type,
                    data=decision.model_dump(),
                    source="master",
                    correlation_id=event.correlation_id,
                )
                
                if decision.decision == "APPROVE":
                    # Update portfolio
                    self.portfolio.open_positions.append(decision.model_dump())
                    self.portfolio.daily_trades += 1
                    self.portfolio.total_trades += 1
                    self.portfolio.last_trade_time = datetime.utcnow()
                
                logger.info(f"Published {event_type.value}: {msg_id}")
            
            set_agent_healthy("master")
            
        except Exception as e:
            logger.error(f"Master handler error: {e}")
            set_agent_down("master")
    
    async def handle_position_closed(self, event: SwarmEvent):
        """Handle position close events (from executor)."""
        data = event.data
        symbol = data.get("symbol", "UNKNOWN")
        pnl_pct = data.get("pnl_pct", 0)
        
        logger.info(f"Position closed: {symbol} PnL={pnl_pct:+.2f}%")
        
        # Update portfolio
        self.portfolio.daily_pnl += pnl_pct
        
        if pnl_pct > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
        
        # Remove from open positions
        self.portfolio.open_positions = [
            p for p in self.portfolio.open_positions
            if p.get("symbol") != symbol
        ]
        
        # Update drawdown
        self.portfolio.current_drawdown = max(0, -self.portfolio.daily_pnl)
        self._update_win_rate()
        
        # Check if circuit breaker should be reset
        if self.circuit_breaker and self.portfolio.current_drawdown < self.MAX_DRAWDOWN_PCT:
            self.circuit_breaker = False
            self.circuit_reason = ""
            logger.info("Circuit breaker reset — drawdown recovered")
    
    async def _heartbeat(self):
        """Send periodic heartbeat with portfolio status."""
        while self.running:
            try:
                await asyncio.sleep(60)
                
                health_status = "healthy"
                if self.circuit_breaker:
                    health_status = "degraded"
                
                from core.events import HeartbeatEvent
                
                heartbeat = HeartbeatEvent(
                    agent="master",
                    status=health_status,
                    uptime_seconds=0,  # Could track actual uptime
                    last_action=f"Portfolio: {len(self.portfolio.open_positions)} open, "
                               f"daily={self.portfolio.daily_trades}, "
                               f"dd={self.portfolio.current_drawdown:.1f}%",
                )
                
                await self.bus.publish_simple(
                    event_type=EventType.HEARTBEAT,
                    data=heartbeat.model_dump(),
                    source="master",
                )
                
                logger.debug(
                    f"💓 Heartbeat | positions={len(self.portfolio.open_positions)} "
                    f"daily={self.portfolio.daily_trades} "
                    f"dd={self.portfolio.current_drawdown:.1f}% "
                    f"winrate={self.portfolio.win_rate:.1f}%"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    # ── Main Loop ──
    
    async def run(self):
        """Run master orchestrator."""
        logger.info("═══════════════════════════════════════")
        logger.info("🧠 MASTER ORCHESTRATOR STARTED")
        logger.info("═══════════════════════════════════════")
        logger.info(f"  Balance: ${self.portfolio.balance_usd:,.2f}")
        logger.info(f"  Max positions: {self.MAX_POSITIONS}")
        logger.info(f"  Max daily trades: {self.MAX_DAILY_TRADES}")
        logger.info(f"  Max drawdown: {self.MAX_DRAWDOWN_PCT}%")
        logger.info(f"  Min confidence: {self.MIN_CONFIDENCE}")
        logger.info(f"  Min R/R: {self.MIN_RISK_REWARD}")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to risk events
        self.consumer_task = await self.bus.subscribe(
            event_type=EventType.RISK_ASSESSED,
            consumer_name="master_main",
            handler=self.handle_risk_assessed,
        )
        
        # Subscribe to position close events
        self.close_consumer = await self.bus.subscribe(
            event_type=EventType.POSITION_CLOSED,
            consumer_name="master_positions",
            handler=self.handle_position_closed,
        )
        
        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self._heartbeat())
        
        logger.info("Waiting for risk assessment events...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Master stopped")


async def main():
    """Entry point."""
    async with MasterOrchestrator() as master:
        await master.run()


if __name__ == "__main__":
    asyncio.run(main())
