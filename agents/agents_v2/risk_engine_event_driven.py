#!/usr/bin/env python3
"""⚠️ Event-Driven Risk Engine — consumes TokensValidatedEvent, publishes RiskAssessedEvent."""
import asyncio
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from core import (
    get_logger, get_settings,
    RiskStateManager,
    get_event_bus, EventType, SwarmEvent,
    TokensValidatedEvent, RiskSignal, RiskAssessedEvent,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("risk_engine")


class EventDrivenRiskEngine:
    """Risk engine that consumes validation events and publishes risk events."""
    
    def __init__(self):
        self.running = False
        self.bus = None
        self.settings = get_settings()
        self.consumer_task = None
    
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
    
    def _calculate_atr(self, token: Dict[str, Any]) -> float:
        """Calculate ATR proxy from price changes."""
        changes = [
            abs(token.get("price_change_24h", 0)),
            abs(token.get("price_change_6h", 0)),
            abs(token.get("price_change_1h", 0)),
            abs(token.get("price_change_5m", 0)),
        ]
        valid = [c for c in changes if c > 0]
        return sum(valid) / len(valid) * 0.5 if valid else 2.0
    
    async def _assess_risk(self, token: Dict[str, Any]) -> Optional[RiskSignal]:
        """Assess risk for a single validated token."""
        symbol = token.get("symbol", "UNKNOWN")
        price = token.get("price", 0)
        
        if price <= 0:
            logger.warning(f"Invalid price for {symbol}: {price}")
            return None
        
        # ATR proxy
        atr = self._calculate_atr(token)
        
        # Stop loss (2x ATR)
        stop_multiplier = 2.0
        stop_distance = atr * stop_multiplier
        stop_price = max(price * 0.5, price - stop_distance)
        stop_distance_pct = (price - stop_price) / price * 100 if price > 0 else 0
        
        # Take profits
        tp1 = price * 1.5
        tp2 = price * 2.0
        tp3 = price * 3.0
        
        # Risk/reward
        risk = price - stop_price
        reward_tp1 = tp1 - price
        rr_ratio = reward_tp1 / risk if risk > 0 else 0
        
        # Position size
        portfolio = self.settings.portfolio_size_usd
        risk_pct = self.settings.risk_per_trade_pct
        position_size_pct = risk_pct / max(stop_distance_pct, 1.0) * 100
        position_size_pct = min(position_size_pct, 10.0)
        position_size_usd = portfolio * position_size_pct / 100
        
        # Composite score (0-100)
        momentum_score = min(abs(token.get("price_change_24h", 0)) * 2, 30)
        liquidity_score = min(token.get("liquidity", 0) / 10000, 20)
        volume_score = min(token.get("volume_24h", 0) / 5000, 20)
        pass_rate = token.get("pass_rate", 0) * 20
        buy_score = min(token.get("buy_sell_ratio", 0) * 10, 10)
        
        composite = momentum_score + liquidity_score + volume_score + pass_rate + buy_score
        composite = min(composite, 100)
        
        # Determine if executable
        is_executable = composite >= 60 and rr_ratio >= 1.5
        
        # Volatility regime
        if atr > 10:
            vol_regime = "HIGH"
        elif atr > 5:
            vol_regime = "MEDIUM"
        else:
            vol_regime = "LOW"
        
        return RiskSignal(
            validator_output_id=token.get("scanner_output_id", 0),
            symbol=symbol,
            tier=token.get("tier", "TIER_3"),
            entry_price=round(price, 8),
            stop_loss_price=round(stop_price, 8),
            take_profit_1=round(tp1, 8),
            take_profit_2=round(tp2, 8),
            take_profit_3=round(tp3, 8),
            stop_distance_pct=round(stop_distance_pct, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            position_size_pct=round(position_size_pct, 2),
            composite_score=round(composite, 1),
            atr_proxy=round(atr, 2),
            volatility_regime=vol_regime,
            is_active=True,
            is_executable=is_executable,
        )
    
    async def handle_validated_tokens(self, event: SwarmEvent):
        """Handle tokens validated event."""
        try:
            logger.info(f"=== RISK CYCLE | batch={event.correlation_id} ===")
            
            # Parse event
            data = event.data
            tokens = data.get("validated_tokens", [])
            
            logger.info(f"Assessing risk for {len(tokens)} validated tokens...")
            
            # Assess each approved token
            signals = []
            for token_data in tokens:
                try:
                    # Only assess approved tokens
                    if not token_data.get("is_approved", False):
                        continue
                    
                    signal = await self._assess_risk(token_data)
                    if signal:
                        signals.append(signal)
                        
                        status = "✅ EXECUTABLE" if signal.is_executable else "⚠️ LOW SCORE"
                        logger.info(
                            f"  {signal.symbol}: {status} "
                            f"score={signal.composite_score:.1f} "
                            f"stop={signal.stop_distance_pct:.1f}% "
                            f"RR={signal.risk_reward_ratio:.1f} "
                            f"size={signal.position_size_pct:.1f}%"
                        )
                        
                except Exception as e:
                    logger.error(f"Risk assessment failed for {token_data.get('symbol', '?')}: {e}")
                    continue
            
            logger.info(f"Risk assessment complete: {len(signals)} active signals")
            
            if signals:
                # Publish risk event
                risk_event = RiskAssessedEvent(
                    signals=signals,
                    batch_id=event.correlation_id,
                )
                
                msg_id = await self.bus.publish_simple(
                    event_type=EventType.RISK_ASSESSED,
                    data=risk_event.model_dump(),
                    source="risk_engine",
                    correlation_id=event.correlation_id,
                )
                logger.info(f"Published RISK_ASSESSED: {msg_id} ({len(signals)} signals)")
            
            set_agent_healthy("risk_engine")
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
            set_agent_down("risk_engine")
    
    async def run(self):
        """Main loop — subscribe to validation events."""
        logger.info("═══════════════════════════════════════")
        logger.info("⚠️ EVENT-DRIVEN RISK ENGINE STARTED")
        logger.info("Consumes: TOKENS_VALIDATED")
        logger.info("Publishes: RISK_ASSESSED")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to validation events
        self.consumer_task = await self.bus.subscribe(
            event_type=EventType.TOKENS_VALIDATED,
            consumer_name="risk_engine_main",
            handler=self.handle_validated_tokens,
        )
        
        logger.info("Waiting for validation events...")
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Risk engine stopped")


async def main():
    """Entry point."""
    async with EventDrivenRiskEngine() as risk_engine:
        await risk_engine.run()


if __name__ == "__main__":
    asyncio.run(main())