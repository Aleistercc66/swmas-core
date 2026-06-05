#!/usr/bin/env python3
"""
📦 STATE MANAGER — Atomic, versioned, observable state operations
Replaces all raw JSON file reads/writes.
"""
import json
from typing import Optional, List, Dict, Any, Type, TypeVar
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from core.database import AtomicTransaction, get_session_maker
from core.models import (
    ScannerOutput, ValidatorOutput, RiskAssessment, Position,
    PortfolioState, TradeLog, Alert, AgentHealth, EventLog,
    ScannerOutputCreate, TradeTier, PositionStatus, AgentHealthStatus,
)
from core.redis_client import (
    cache_set, cache_get, cache_delete, publish_event,
    acquire_lock, release_lock,
)
from core.logging_config import get_logger

logger = get_logger("state_manager")

T = TypeVar("T")

# ───────────────────────────────────────────────
# Scanner Operations
# ───────────────────────────────────────────────

class ScannerStateManager:
    """All scanner output CRUD with caching + events."""
    
    CACHE_PREFIX = "scanner"
    
    @staticmethod
    async def create(data: ScannerOutputCreate) -> ScannerOutput:
        async with AtomicTransaction() as session:
            obj = ScannerOutput(**data.model_dump())
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            
            # Cache
            await cache_set(f"scanner:{obj.id}", obj.model_dump(), ttl_seconds=60)
            
            # Event
            await publish_event("scanner:output", {
                "event_type": "token_discovered",
                "agent_name": "scanner",
                "correlation_id": obj.scan_batch_id,
                "payload": obj.model_dump(),
            })
            
            logger.info(f"Scanner output created: {obj.symbol} (id={obj.id})")
            return obj
    
    @staticmethod
    async def get_latest(batch_size: int = 50) -> List[ScannerOutput]:
        """Get latest scanner outputs with cache fallback."""
        cache_key = f"scanner:latest:{batch_size}"
        cached = await cache_get(cache_key)
        if cached:
            return [ScannerOutput(**item) for item in cached]
        
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(ScannerOutput)
                .order_by(desc(ScannerOutput.created_at))
                .limit(batch_size)
            )
            items = result.scalars().all()
            
            # Cache for 10 seconds
            await cache_set(cache_key, [item.model_dump() for item in items], ttl_seconds=10)
            
            return list(items)
    
    @staticmethod
    async def get_by_symbol(symbol: str, limit: int = 10) -> List[ScannerOutput]:
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(ScannerOutput)
                .where(ScannerOutput.symbol == symbol)
                .order_by(desc(ScannerOutput.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())

# ───────────────────────────────────────────────
# Validator Operations
# ───────────────────────────────────────────────

class ValidatorStateManager:
    """Validation results with atomic tier assignment."""
    
    @staticmethod
    async def create(
        scanner_output_id: int,
        symbol: str,
        checks: list,
        is_approved: bool,
        tier: str,
        confidence: float,
        rejection_reason: str = "",
        buy_sell_ratio: float = 0.0,
    ) -> ValidatorOutput:
        async with AtomicTransaction() as session:
            obj = ValidatorOutput(
                scanner_output_id=scanner_output_id,
                symbol=symbol,
                checks=checks,
                pass_rate=len([c for c in checks if c.passed]) / len(checks) if checks else 0,
                total_checks=len(checks),
                passed_checks=len([c for c in checks if c.passed]),
                is_approved=is_approved,
                tier=tier,
                confidence=confidence,
                buy_sell_ratio=buy_sell_ratio,
                rejection_reason=rejection_reason,
            )
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            
            await publish_event("validator:output", {
                "event_type": "validated",
                "agent_name": "validator",
                "payload": {"symbol": symbol, "approved": is_approved, "tier": tier},
            })
            
            logger.info(f"Validated: {symbol} → {tier} (conf={confidence:.1f})")
            return obj
    
    @staticmethod
    async def get_approved(since_minutes: int = 60) -> List[ValidatorOutput]:
        async with AtomicTransaction() as session:
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
            
            result = await session.execute(
                select(ValidatorOutput)
                .where(ValidatorOutput.is_approved == True)
                .where(ValidatorOutput.created_at >= cutoff)
                .order_by(desc(ValidatorOutput.confidence))
            )
            return list(result.scalars().all())

# ───────────────────────────────────────────────
# Risk Assessment Operations
# ───────────────────────────────────────────────

class RiskStateManager:
    """Dynamic risk levels — atomic score calculations."""
    
    @staticmethod
    async def create(assessment: RiskAssessment) -> RiskAssessment:
        async with AtomicTransaction() as session:
            session.add(assessment)
            await session.commit()
            await session.refresh(assessment)
            
            await publish_event("risk:assessment", {
                "event_type": "risk_assessed",
                "agent_name": "risk_engine",
                "payload": {
                    "symbol": assessment.symbol,
                    "tier": assessment.tier,
                    "score": assessment.composite_score,
                },
            })
            
            logger.info(
                f"Risk assessed: {assessment.symbol} "
                f"score={assessment.composite_score:.1f} "
                f"stop={assessment.stop_distance_pct:.1f}%"
            )
            return assessment
    
    @staticmethod
    async def get_active_signals(min_score: float = 50) -> List[RiskAssessment]:
        """Get active, non-expired signals above score threshold."""
        async with AtomicTransaction() as session:
            now = datetime.now(timezone.utc)
            result = await session.execute(
                select(RiskAssessment)
                .where(RiskAssessment.is_active == True)
                .where(RiskAssessment.composite_score >= min_score)
                .where(
                    (RiskAssessment.expires_at == None) | (RiskAssessment.expires_at > now)
                )
                .order_by(desc(RiskAssessment.composite_score))
            )
            return list(result.scalars().all())

# ───────────────────────────────────────────────
# Position Operations — CRITICAL: Atomic with locking
# ───────────────────────────────────────────────

class PositionStateManager:
    """
    Position CRUD with distributed locking.
    Solves the race condition that corrupted paper trading.
    """
    
    LOCK_TIMEOUT = 10  # seconds
    
    @staticmethod
    async def open_position(position: Position) -> Position:
        """Atomic position open with portfolio update."""
        lock_name = f"portfolio:lock"
        
        if not await acquire_lock(lock_name, PositionStateManager.LOCK_TIMEOUT):
            logger.warning("Redis lock unavailable — proceeding without distributed lock (dev mode)")
            # Proceed without lock for development/testing
        
        try:
            async with AtomicTransaction() as session:
                # 1. Add position
                session.add(position)
                await session.flush()
                
                # 2. Update portfolio atomically
                portfolio_result = await session.execute(
                    select(PortfolioState).where(PortfolioState.id == 1)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if portfolio is None:
                    portfolio = PortfolioState(id=1)
                    session.add(portfolio)
                
                # Deduct position size + fees from balance
                total_cost = position.position_size_usd + position.entry_fee + position.slippage_cost
                portfolio.balance -= total_cost
                portfolio.total_fees += position.entry_fee
                portfolio.total_slippage += position.slippage_cost
                portfolio.daily_trades += 1
                portfolio.version += 1
                portfolio.updated_at = datetime.now(timezone.utc)
                
                # 3. Log the trade
                trade_log = TradeLog(
                    position_id=position.id,
                    symbol=position.symbol,
                    action="OPEN",
                    price=position.entry_price,
                    quantity=position.quantity,
                    value_usd=position.position_size_usd,
                    fee=position.entry_fee,
                    slippage=position.slippage_cost,
                    balance_before=portfolio.balance + total_cost,
                    balance_after=portfolio.balance,
                )
                session.add(trade_log)
                
                await session.commit()
                await session.refresh(position)
                
                # Invalidate cache
                await cache_delete("portfolio:current")
                
                await publish_event("positions:updates", {
                    "event_type": "position_opened",
                    "agent_name": "executor",
                    "payload": {"symbol": position.symbol, "size": position.position_size_usd},
                })
                
                logger.info(
                    f"Position opened: {position.symbol} @ ${position.entry_price:.8f} "
                    f"size=${position.position_size_usd:.2f}"
                )
                return position
        finally:
            await release_lock(lock_name)
    
    @staticmethod
    async def close_position(
        position_id: int,
        exit_price: float,
        close_reason: str,
        exit_fee: float = 0.0,
    ) -> Position:
        """Atomic position close with PnL calculation and portfolio update."""
        lock_name = f"portfolio:lock"
        
        if not await acquire_lock(lock_name, PositionStateManager.LOCK_TIMEOUT):
            logger.warning("Redis lock unavailable — proceeding without distributed lock (dev mode)")
            # Proceed without lock for development/testing
        
        try:
            async with AtomicTransaction() as session:
                # 1. Fetch position
                result = await session.execute(
                    select(Position).where(Position.id == position_id)
                )
                position = result.scalar_one_or_none()
                
                if position is None:
                    raise ValueError(f"Position {position_id} not found")
                
                if position.status != PositionStatus.OPEN.value:
                    raise ValueError(f"Position {position_id} is not open")
                
                # 2. Calculate PnL
                price_change = (exit_price - position.entry_price) / position.entry_price
                gross_pnl = position.position_size_usd * price_change
                net_pnl = gross_pnl - exit_fee
                
                realized_pct = price_change * 100
                
                # 3. Update position
                position.status = PositionStatus.CLOSED.value
                position.closed_at = datetime.now(timezone.utc)
                position.exit_price = exit_price
                position.realized_pnl_usd = net_pnl
                position.realized_pnl_pct = realized_pct
                position.exit_fee = exit_fee
                position.close_reason = close_reason
                position.version += 1
                
                # 4. Update portfolio
                portfolio_result = await session.execute(
                    select(PortfolioState).where(PortfolioState.id == 1)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if portfolio is None:
                    portfolio = PortfolioState(id=1)
                    session.add(portfolio)
                
                # Return position value + PnL - exit fee
                return_value = position.position_size_usd + net_pnl - exit_fee
                portfolio.balance += return_value
                portfolio.total_fees += exit_fee
                portfolio.total_trades += 1
                portfolio.total_pnl += net_pnl
                portfolio.daily_pnl += net_pnl
                
                if net_pnl > 0:
                    portfolio.wins += 1
                    portfolio.avg_win = (
                        (portfolio.avg_win * (portfolio.wins - 1)) + net_pnl
                    ) / portfolio.wins if portfolio.wins > 0 else net_pnl
                    portfolio.consecutive_losses = 0
                else:
                    portfolio.losses += 1
                    portfolio.avg_loss = (
                        (portfolio.avg_loss * (portfolio.losses - 1)) + abs(net_pnl)
                    ) / portfolio.losses if portfolio.losses > 0 else abs(net_pnl)
                    portfolio.consecutive_losses += 1
                
                # Recalculate derived metrics
                total = portfolio.wins + portfolio.losses
                portfolio.win_rate = (portfolio.wins / total * 100) if total > 0 else 0.0
                
                gross_profit = portfolio.wins * portfolio.avg_win
                gross_loss = portfolio.losses * portfolio.avg_loss
                portfolio.profit_factor = (
                    gross_profit / gross_loss if gross_loss > 0 else float('inf')
                ) if gross_profit > 0 else 0.0
                
                portfolio.version += 1
                portfolio.updated_at = datetime.now(timezone.utc)
                
                # 5. Log trade
                trade_log = TradeLog(
                    position_id=position.id,
                    symbol=position.symbol,
                    action="CLOSE",
                    price=exit_price,
                    quantity=position.quantity,
                    value_usd=return_value,
                    fee=exit_fee,
                    pnl_before=0,
                    pnl_after=net_pnl,
                    balance_before=portfolio.balance - return_value,
                    balance_after=portfolio.balance,
                    metadata={"close_reason": close_reason, "realized_pct": realized_pct},
                )
                session.add(trade_log)
                
                await session.commit()
                await session.refresh(position)
                
                # Invalidate cache
                await cache_delete("portfolio:current")
                
                await publish_event("positions:updates", {
                    "event_type": "position_closed",
                    "agent_name": "position_monitor",
                    "payload": {
                        "symbol": position.symbol,
                        "pnl": net_pnl,
                        "reason": close_reason,
                    },
                })
                
                logger.info(
                    f"Position closed: {position.symbol} "
                    f"PnL=${net_pnl:+.2f} ({realized_pct:+.2f}%) "
                    f"reason={close_reason}"
                )
                return position
        finally:
            await release_lock(lock_name)
    
    @staticmethod
    async def update_position_price(position_id: int, current_price: float) -> Position:
        """Update current price without portfolio lock (read-only on position)."""
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(Position).where(Position.id == position_id)
            )
            position = result.scalar_one_or_none()
            
            if position and position.status == PositionStatus.OPEN.value:
                position.current_price = current_price
                price_change = (current_price - position.entry_price) / position.entry_price
                position.current_pnl_usd = position.position_size_usd * price_change
                position.current_pnl_pct = price_change * 100
                
                if current_price > position.highest_price:
                    position.highest_price = current_price
                
                await session.commit()
                await session.refresh(position)
            
            return position
    
    @staticmethod
    async def get_open_positions() -> List[Position]:
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(Position)
                .where(Position.status == PositionStatus.OPEN.value)
                .order_by(desc(Position.entry_at))
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_position_by_symbol(symbol: str) -> Optional[Position]:
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(Position)
                .where(Position.symbol == symbol)
                .where(Position.status == PositionStatus.OPEN.value)
                .order_by(desc(Position.entry_at))
                .limit(1)
            )
            return result.scalar_one_or_none()

# ───────────────────────────────────────────────
# Portfolio Singleton
# ───────────────────────────────────────────────

class PortfolioManager:
    """Atomic portfolio state management."""
    
    @staticmethod
    async def get_or_create() -> PortfolioState:
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(PortfolioState).where(PortfolioState.id == 1)
            )
            portfolio = result.scalar_one_or_none()
            
            if portfolio is None:
                portfolio = PortfolioState(id=1)
                session.add(portfolio)
                await session.commit()
                await session.refresh(portfolio)
            
            return portfolio
    
    @staticmethod
    async def get_summary() -> Dict[str, Any]:
        """Get full portfolio summary (with caching)."""
        cached = await cache_get("portfolio:current")
        if cached:
            return cached
        
        async with AtomicTransaction() as session:
            portfolio = await PortfolioManager.get_or_create()
            positions_result = await session.execute(
                select(Position).where(Position.status == PositionStatus.OPEN.value)
            )
            open_positions = positions_result.scalars().all()
            
            summary = {
                "balance": portfolio.balance,
                "starting_balance": portfolio.starting_balance,
                "return_pct": portfolio.return_pct,
                "open_positions_count": len(open_positions),
                "open_positions": [
                    {
                        "symbol": p.symbol,
                        "entry_price": p.entry_price,
                        "current_price": p.current_price,
                        "pnl_usd": p.current_pnl_usd,
                        "pnl_pct": p.current_pnl_pct,
                        "size_usd": p.position_size_usd,
                    }
                    for p in open_positions
                ],
                "total_trades": portfolio.total_trades,
                "wins": portfolio.wins,
                "losses": portfolio.losses,
                "win_rate": portfolio.win_rate,
                "total_pnl": portfolio.total_pnl,
                "profit_factor": portfolio.profit_factor,
                "max_drawdown_pct": portfolio.max_drawdown_pct,
                "daily_pnl": portfolio.daily_pnl,
                "daily_trades": portfolio.daily_trades,
                "circuit_breaker_active": portfolio.circuit_breaker_active,
                "kill_switch_active": portfolio.kill_switch_active,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            await cache_set("portfolio:current", summary, ttl_seconds=5)
            return summary

# ───────────────────────────────────────────────
# Event Log (Audit Trail)
# ───────────────────────────────────────────────

class EventLogManager:
    """Immutable event stream — the system journal."""
    
    @staticmethod
    async def log(
        event_type: str,
        event_name: str,
        agent_name: str,
        correlation_id: str,
        payload: Dict[str, Any],
    ) -> EventLog:
        async with AtomicTransaction() as session:
            event = EventLog(
                event_type=event_type,
                event_name=event_name,
                agent_name=agent_name,
                correlation_id=correlation_id,
                payload=payload,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event
    
    @staticmethod
    async def get_recent(limit: int = 100) -> List[EventLog]:
        async with AtomicTransaction() as session:
            result = await session.execute(
                select(EventLog)
                .order_by(desc(EventLog.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
