#!/usr/bin/env python3
"""🔍 Event-Driven Validator — consumes TokenDiscoveredEvent, publishes TokensValidatedEvent."""
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from core import (
    get_logger, get_settings,
    ValidatorStateManager,
    get_event_bus, EventType, SwarmEvent,
    TokenDiscoveredEvent, TokensValidatedEvent, TokenValidation,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("validator")


class EventDrivenValidator:
    """Validator that consumes scanner events and publishes validation events."""
    
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
    
    async def _validate_token(self, token: Dict[str, Any]) -> TokenValidation:
        """Validate a single token."""
        symbol = token.get("symbol", "UNKNOWN")
        price = token.get("price", 0)
        volume = token.get("volume_24h", 0)
        liquidity = token.get("liquidity", 0)
        change_24h = token.get("price_change_24h", 0)
        change_1h = token.get("price_change_1h", 0)
        change_5m = token.get("price_change_5m", 0)
        buy_ratio = token.get("buy_ratio", 0)
        
        checks = []
        passed = 0
        total = 8
        
        # Check 1: Liquidity
        liq_ok = liquidity >= 50000
        checks.append({"name": "liquidity_minimum", "passed": liq_ok, "value": liquidity, "threshold": 50000, "message": f"${liquidity:,.0f} vs ${50000:,.0f}"})
        if liq_ok: passed += 1
        
        # Check 2: Volume
        vol_ok = volume >= 10000
        checks.append({"name": "volume_minimum", "passed": vol_ok, "value": volume, "threshold": 10000, "message": f"${volume:,.0f} vs ${10000:,.0f}"})
        if vol_ok: passed += 1
        
        # Check 3: 24h momentum
        mom24_ok = change_24h >= 0
        checks.append({"name": "momentum_24h", "passed": mom24_ok, "value": change_24h, "threshold": 0, "message": f"{change_24h:+.1f}%"})
        if mom24_ok: passed += 1
        
        # Check 4: 1h momentum
        mom1_ok = change_1h >= -5
        checks.append({"name": "momentum_1h", "passed": mom1_ok, "value": change_1h, "threshold": -5, "message": f"{change_1h:+.1f}%"})
        if mom1_ok: passed += 1
        
        # Check 5: 5m momentum
        mom5_ok = change_5m >= -2
        checks.append({"name": "momentum_5m", "passed": mom5_ok, "value": change_5m, "threshold": -2, "message": f"{change_5m:+.1f}%"})
        if mom5_ok: passed += 1
        
        # Check 6: Buy pressure
        buy_ok = buy_ratio >= 0.8
        checks.append({"name": "buy_pressure", "passed": buy_ok, "value": buy_ratio, "threshold": 0.8, "message": f"{buy_ratio:.2f}x"})
        if buy_ok: passed += 1
        
        # Check 7: Volume/Liquidity ratio
        vol_liq_ratio = volume / liquidity if liquidity > 0 else 0
        vol_liq_ok = vol_liq_ratio >= 0.1
        checks.append({"name": "volume_liquidity_ratio", "passed": vol_liq_ok, "value": vol_liq_ratio, "threshold": 0.1, "message": f"{vol_liq_ratio:.2f}"})
        if vol_liq_ok: passed += 1
        
        # Check 8: Minimum momentum
        min_mom_ok = change_24h >= 5 or change_1h >= 2
        checks.append({"name": "minimum_momentum", "passed": min_mom_ok, "value": max(change_24h, change_1h), "threshold": 2, "message": f"24h={change_24h:+.1f}%, 1h={change_1h:+.1f}%"})
        if min_mom_ok: passed += 1
        
        # Calculate pass rate
        pass_rate = passed / total if total > 0 else 0
        
        # Determine tier
        if pass_rate >= 0.875 and buy_ratio >= 1.2:
            tier = "TIER_1"
            confidence = 90.0 + (pass_rate - 0.875) * 80
        elif pass_rate >= 0.625:
            tier = "TIER_2"
            confidence = 70.0 + (pass_rate - 0.625) * 80
        elif pass_rate >= 0.375:
            tier = "TIER_3"
            confidence = 50.0 + (pass_rate - 0.375) * 53.3
        else:
            tier = "REJECT"
            confidence = pass_rate * 133.3
        
        is_approved = tier in ("TIER_1", "TIER_2")
        
        # Rejection reason
        rejection_reason = ""
        if not is_approved:
            failed = [c["name"] for c in checks if not c["passed"]]
            rejection_reason = f"Failed checks: {', '.join(failed)} (pass rate {pass_rate:.0%})"
        
        return TokenValidation(
            scanner_output_id=token.get("id", 0),
            symbol=symbol,
            is_approved=is_approved,
            tier=tier,
            confidence=round(confidence, 1),
            pass_rate=pass_rate,
            total_checks=total,
            passed_checks=passed,
            checks=checks,
            rejection_reason=rejection_reason,
            buy_sell_ratio=buy_ratio,
        )
    
    async def handle_tokens_discovered(self, event: SwarmEvent):
        """Handle tokens discovered event."""
        try:
            logger.info(f"=== VALIDATION CYCLE | batch={event.correlation_id} ===")
            
            # Parse event
            data = event.data
            tokens = data.get("tokens", [])
            
            logger.info(f"Validating {len(tokens)} tokens...")
            
            # Validate each token
            validated = []
            for token in tokens:
                try:
                    result = await self._validate_token(token)
                    validated.append(result)
                    
                    status = "✅ APPROVED" if result.is_approved else "❌ REJECTED"
                    logger.info(f"  {result.symbol}: {status} (tier={result.tier}, conf={result.confidence}, pass={result.passed_checks}/{result.total_checks})")
                    
                except Exception as e:
                    logger.error(f"Validation failed for {token.get('symbol', '?')}: {e}")
                    continue
            
            # Count approvals
            approved = [v for v in validated if v.is_approved]
            logger.info(f"Validation complete: {len(approved)}/{len(validated)} approved")
            
            if approved:
                # Publish validation event
                validation_event = TokensValidatedEvent(
                    validated_tokens=validated,
                    batch_id=event.correlation_id,
                )
                
                msg_id = await self.bus.publish_simple(
                    event_type=EventType.TOKENS_VALIDATED,
                    data=validation_event.model_dump(),
                    source="validator",
                    correlation_id=event.correlation_id,
                )
                logger.info(f"Published TOKENS_VALIDATED: {msg_id} ({len(approved)} approved)")
            
            set_agent_healthy("validator")
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
            set_agent_down("validator")
    
    async def run(self):
        """Main loop — subscribe to events."""
        logger.info("═══════════════════════════════════════")
        logger.info("🔍 EVENT-DRIVEN VALIDATOR STARTED")
        logger.info("Consumes: TOKENS_DISCOVERED")
        logger.info("Publishes: TOKENS_VALIDATED")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to scanner events
        self.consumer_task = await self.bus.subscribe(
            event_type=EventType.TOKENS_DISCOVERED,
            consumer_name="validator_main",
            handler=self.handle_tokens_discovered,
        )
        
        logger.info("Waiting for scanner events...")
        
        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Validator stopped")


async def main():
    """Entry point."""
    async with EventDrivenValidator() as validator:
        await validator.run()


if __name__ == "__main__":
    asyncio.run(main())
