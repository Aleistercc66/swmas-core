#!/usr/bin/env python3
"""
⚡ AGENT V2: AUTO EXECUTOR — Atomic execution with manual confirmation
Replaces auto_executor.py. Event-driven, database-backed, circuit breaker protected.
"""
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from core import (
    settings, get_logger, init_db,
    RiskStateManager, PositionStateManager, PortfolioManager,
    RiskAssessment, Position, PositionStatus, TradeTier,
    emit_position_opened,
    timed, count_exceptions, set_agent_healthy, set_agent_down,
    POSITIONS_OPENED, ERRORS_TOTAL,
)

logger = get_logger("executor")

class AsyncExecutor:
    """Production-grade execution engine with manual confirmation."""
    
    def __init__(self):
        self.running = False
        self.cycle_counter = 0
        self.pending_confirmations: Dict[int, Dict] = {}  # position_id -> signal data
    
    async def check_circuit_breakers(self) -> bool:
        """Check if trading is allowed. Returns True if OK to trade."""
        portfolio = await PortfolioManager.get_summary()
        
        # Daily loss circuit breaker
        daily_loss = abs(portfolio.get("daily_pnl", 0))
        if daily_loss >= settings.trading.circuit_breaker_daily_loss_pct / 100 * portfolio["starting_balance"]:
            logger.warning(f"CIRCUIT BREAKER: Daily loss ${daily_loss:.2f} exceeds limit")
            return False
        
        # Consecutive losses
        # (Would need to track this in portfolio state)
        
        # Max daily trades
        if portfolio.get("daily_trades", 0) >= settings.trading.max_daily_trades:
            logger.warning(f"Max daily trades reached: {portfolio['daily_trades']}")
            return False
        
        return True
    
    async def execute_trade(self, risk: RiskAssessment, confirmed: bool = False) -> Optional[Position]:
        """
        Execute a trade from risk assessment.
        If not confirmed and TIER_1, queue for manual confirmation.
        """
        # Check circuit breakers
        if not await self.check_circuit_breakers():
            return None
        
        # For TIER_1, require manual confirmation
        if risk.tier == TradeTier.TIER_1.value and not confirmed:
            logger.info(f"TIER_1 trade queued for confirmation: {risk.symbol}")
            self.pending_confirmations[risk.id] = {
                "risk": risk,
                "queued_at": datetime.now(timezone.utc).isoformat(),
            }
            return None
        
        # For TIER_2/3 or confirmed TIER_1, execute
        try:
            # Calculate position size
            portfolio = await PortfolioManager.get_summary()
            balance = portfolio["balance"]
            size_usd = balance * (risk.position_size_pct / 100)
            
            if size_usd < 1:
                logger.warning(f"Position size too small: ${size_usd:.2f}")
                return None
            
            # Calculate quantity
            entry_price = risk.metadata.get("entry_price", 0)
            if entry_price <= 0:
                logger.error(f"Invalid entry price for {risk.symbol}")
                return None
            
            quantity = size_usd / entry_price
            
            # Slippage estimate (0.5% for paper trading)
            slippage_cost = size_usd * 0.005
            entry_fee = size_usd * 0.001  # 0.1% fee
            
            # Create position
            position = Position(
                symbol=risk.symbol,
                token_address=risk.metadata.get("token_address", ""),
                chain="solana",
                tier=risk.tier,
                entry_price=entry_price,
                current_price=entry_price,
                position_size_usd=size_usd,
                quantity=quantity,
                stop_price=risk.stop_price,
                tp1_price=risk.tp1_price,
                tp2_price=risk.tp2_price,
                tp3_price=risk.tp3_price,
                entry_fee=entry_fee,
                slippage_cost=slippage_cost,
                status=PositionStatus.OPEN.value,
                entry_at=datetime.now(timezone.utc),
                highest_price=entry_price,
                risk_assessment_id=risk.id,
                metadata={
                    "composite_score": risk.composite_score,
                    "atr": risk.atr_proxy,
                    "risk_reward": risk.risk_reward_ratio,
                },
            )
            
            # Atomic open
            opened = await PositionStateManager.open_position(position)
            
            # Metrics
            POSITIONS_OPENED.labels(symbol=opened.symbol, tier=opened.tier).inc()
            
            # Event
            await emit_position_opened(
                symbol=opened.symbol,
                size_usd=opened.position_size_usd,
                position_id=opened.id,
            )
            
            logger.info(
                f"Position opened: #{opened.id} {opened.symbol} "
                f"@ ${opened.entry_price:.8f} "
                f"size=${opened.position_size_usd:.2f} "
                f"stop={opened.stop_price:.8f}"
            )
            
            return opened
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            ERRORS_TOTAL.labels(agent="executor", type="execution").inc()
            return None
    
    async def run_execution_cycle(self):
        """Fetch active risk assessments and execute."""
        self.cycle_counter += 1
        
        try:
            # Get active risk assessments
            active = await RiskStateManager.get_active_signals(min_score=50)
            
            if not active:
                return
            
            logger.info(f"Execution cycle: {len(active)} active signals")
            
            for risk in active:
                try:
                    # Check if already in position
                    existing = await PositionStateManager.get_position_by_symbol(risk.symbol)
                    if existing:
                        logger.info(f"Already in position: {risk.symbol}")
                        continue
                    
                    # Execute
                    result = await self.execute_trade(risk, confirmed=False)
                    
                    if result:
                        logger.info(f"Executed: {risk.symbol} → Position #{result.id}")
                    elif risk.tier == TradeTier.TIER_1.value:
                        logger.info(f"TIER_1 queued: {risk.symbol} (awaiting confirmation)")
                    
                except Exception as e:
                    logger.error(f"Execution failed for {risk.symbol}: {e}")
                    continue
            
            set_agent_healthy("executor")
            
        except Exception as e:
            logger.error(f"Execution cycle failed: {e}")
            set_agent_down("executor")
    
    async def confirm_pending(self, risk_id: int) -> Optional[Position]:
        """Manual confirmation handler — called by Telegram bot."""
        if risk_id not in self.pending_confirmations:
            return None
        
        data = self.pending_confirmations.pop(risk_id)
        risk = data["risk"]
        
        logger.info(f"Manual confirmation received for {risk.symbol}")
        
        return await self.execute_trade(risk, confirmed=True)
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("⚡ ASYNC EXECUTOR V2 STARTED")
        logger.info("Manual confirm for TIER_1 | Circuit breakers")
        logger.info("═══════════════════════════════════════")
        
        # Init DB
        await init_db()
        
        self.running = True
        
        while self.running:
            try:
                await self.run_execution_cycle()
                await asyncio.sleep(20)  # 20s between execution checks
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Executor loop error: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        self.running = False

async def main():
    executor = AsyncExecutor()
    await executor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Executor stopped")
