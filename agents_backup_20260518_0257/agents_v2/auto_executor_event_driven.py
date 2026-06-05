#!/usr/bin/env python3
"""🚀 Auto Executor — Event-driven trade execution with safety toggle."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core import (
    get_logger, get_settings,
    get_event_bus, EventType, SwarmEvent,
    TradeDecision, PositionOpenedEvent,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("auto_executor")


class AutoExecutor:
    """Auto-executes approved trades or waits for manual confirmation."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bus = None
        self.running = False
        self.auto_mode = False  # Safety: starts OFF
        self.paper_mode = True  # Default: paper trading
        self.consumer_task = None
        self.executed_trades: Dict[str, Dict[str, Any]] = {}
    
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
        if self.bus:
            await self.bus.disconnect()
    
    def _generate_trade_id(self, symbol: str) -> str:
        """Generate unique trade ID."""
        return f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{symbol}_{uuid.uuid4().hex[:6]}"
    
    async def _execute_paper_trade(self, decision: TradeDecision) -> Dict[str, Any]:
        """Simulate a paper trade execution."""
        trade_id = self._generate_trade_id(decision.symbol)
        
        execution = {
            "trade_id": trade_id,
            "symbol": decision.symbol,
            "entry_price": decision.entry_price,
            "position_size_usd": decision.position_size_usd,
            "stop_loss": decision.stop_loss,
            "take_profits": decision.take_profits,
            "tier": decision.tier,
            "confidence": decision.confidence,
            "risk_reward": decision.risk_reward,
            "executed_at": datetime.utcnow().isoformat(),
            "mode": "paper",
            "status": "OPEN",
        }
        
        self.executed_trades[trade_id] = execution
        
        logger.info(
            f"🚀 PAPER TRADE: {decision.symbol} | "
            f"Entry: ${decision.entry_price:.8f} | "
            f"Size: ${decision.position_size_usd:.2f} | "
            f"SL: ${decision.stop_loss:.8f}"
        )
        
        return execution
    
    async def _execute_real_trade(self, decision: TradeDecision) -> Optional[Dict[str, Any]]:
        """Execute a real trade (placeholder for exchange integration)."""
        # TODO: Integrate with exchange APIs (Jupiter, Binance, etc.)
        logger.warning("Real trade execution not yet implemented — using paper mode")
        return await self._execute_paper_trade(decision)
    
    async def handle_trade_decision(self, event: SwarmEvent):
        """Handle trade approval events from master."""
        try:
            data = event.data
            decision = data.get("decision", "REJECT")
            symbol = data.get("symbol", "UNKNOWN")
            
            if decision != "APPROVE":
                logger.info(f"🟡 Trade rejected for {symbol}: {data.get('reason', 'Unknown')}")
                return
            
            # Check auto mode
            if not self.auto_mode:
                logger.info(
                    f"🟡 MANUAL CONFIRM NEEDED: {symbol} | "
                    f"Auto mode is OFF. Use toggle_auto_mode() to enable."
                )
                
                # Publish alert for manual review
                await self.bus.publish_simple(
                    event_type=EventType.ALERT,
                    data={
                        "alert_type": "MANUAL_CONFIRM",
                        "symbol": symbol,
                        "message": f"Trade approved but auto mode is OFF",
                        "data": data,
                    },
                    source="auto_executor",
                )
                return
            
            # Build TradeDecision
            trade = TradeDecision(
                symbol=symbol,
                decision="APPROVE",
                tier=data.get("tier", "TIER_2"),
                position_size_usd=data.get("position_size_usd", 0),
                entry_price=data.get("entry_price", 0),
                stop_loss=data.get("stop_loss", 0),
                take_profits=data.get("take_profits", []),
                confidence=data.get("confidence", 0),
                risk_reward=data.get("risk_reward", 0),
                reason=data.get("reason", ""),
            )
            
            # Execute
            if self.paper_mode:
                execution = await self._execute_paper_trade(trade)
            else:
                execution = await self._execute_real_trade(trade)
            
            if execution:
                # Publish position opened event
                opened = PositionOpenedEvent(
                    trade_id=execution["trade_id"],
                    symbol=trade.symbol,
                    entry_price=trade.entry_price,
                    position_size_usd=trade.position_size_usd,
                    stop_loss=trade.stop_loss,
                    take_profits=trade.take_profits,
                    tier=trade.tier,
                    confidence=trade.confidence,
                )
                
                await self.bus.publish_simple(
                    event_type=EventType.POSITION_OPENED,
                    data=opened.model_dump(),
                    source="auto_executor",
                    correlation_id=event.correlation_id,
                )
                
                logger.info(f"✅ Position published: {execution['trade_id']}")
            
            set_agent_healthy("auto_executor")
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            set_agent_down("auto_executor")
    
    def toggle_auto_mode(self, enabled: bool = None) -> bool:
        """Toggle auto execution mode."""
        if enabled is None:
            self.auto_mode = not self.auto_mode
        else:
            self.auto_mode = enabled
        
        status = "ON" if self.auto_mode else "OFF"
        logger.info(f"🔄 Auto mode: {status}")
        return self.auto_mode
    
    def toggle_paper_mode(self, enabled: bool = None) -> bool:
        """Toggle paper trading mode."""
        if enabled is None:
            self.paper_mode = not self.paper_mode
        else:
            self.paper_mode = enabled
        
        status = "PAPER" if self.paper_mode else "REAL"
        logger.info(f"🔄 Trading mode: {status}")
        return self.paper_mode
    
    async def run(self):
        """Run auto executor."""
        logger.info("═══════════════════════════════════════")
        logger.info("🚀 AUTO EXECUTOR STARTED")
        logger.info(f"  Auto mode: {'ON' if self.auto_mode else 'OFF'}")
        logger.info(f"  Paper mode: {'ON' if self.paper_mode else 'OFF'}")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to position opened events (from master)
        self.consumer_task = await self.bus.subscribe(
            event_type=EventType.POSITION_OPENED,
            consumer_name="auto_executor",
            handler=self.handle_trade_decision,
        )
        
        logger.info("Waiting for trade decisions...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Auto executor stopped")


async def main():
    async with AutoExecutor() as executor:
        await executor.run()


if __name__ == "__main__":
    asyncio.run(main())
