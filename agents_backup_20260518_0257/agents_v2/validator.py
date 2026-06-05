#!/usr/bin/env python3
"""
🔒 AGENT V2: VALIDATOR — Event-driven quality gate
Replaces v2_validator.py. Strict typing, atomic decisions, event emission.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from core import (
    settings, get_logger,
    ScannerStateManager, ValidatorStateManager,
    ValidationCheck,
    emit_validated,
    timed, count_exceptions, set_agent_healthy, set_agent_down,
    VALIDATOR_CHECKS, VALIDATE_LATENCY, ERRORS_TOTAL,
)
from core.models import TradeTier

logger = get_logger("validator")

class AsyncValidator:
    """Production-grade validation engine."""
    
    def __init__(self):
        self.running = False
        self.cycle_counter = 0
    
    def run_checks(self, scanner_output) -> (List[ValidationCheck], bool, str, float, str):
        """
        Run all validation checks on a scanner output.
        Returns: (checks, is_approved, tier, confidence, rejection_reason)
        """
        checks = []
        p = scanner_output
        
        # 1. Liquidity check
        liq_check = ValidationCheck(
            name="liquidity",
            passed=p.liquidity >= 30000,
            value=p.liquidity,
            threshold=30000,
            message=f"Liquidity ${p.liquidity:,.0f} {'✅' if p.liquidity >= 30000 else '❌'} (min $30K)",
        )
        checks.append(liq_check)
        
        # 2. Volume check
        vol_check = ValidationCheck(
            name="volume",
            passed=p.volume_24h >= 10000,
            value=p.volume_24h,
            threshold=10000,
            message=f"24h Volume ${p.volume_24h:,.0f} {'✅' if p.volume_24h >= 10000 else '❌'} (min $10K)",
        )
        checks.append(vol_check)
        
        # 3. 24h momentum (not too low, not too high)
        chg24 = p.change_24h
        momentum_ok = 5 <= chg24 <= 200
        mom_check = ValidationCheck(
            name="momentum_24h",
            passed=momentum_ok,
            value=chg24,
            threshold=5,
            message=f"24h Change {chg24:+.1f}% {'✅' if momentum_ok else '❌'} (5-200%)",
        )
        checks.append(mom_check)
        
        # 4. 1h momentum (not dumping while 24h high)
        chg1 = p.change_1h
        dumping = chg24 > 50 and chg1 < -5
        h1_check = ValidationCheck(
            name="momentum_1h",
            passed=not dumping,
            value=chg1,
            threshold=-5,
            message=f"1h Change {chg1:+.1f}% {'✅' if not dumping else '❌ DUMPING'}",
        )
        checks.append(h1_check)
        
        # 5. Buy pressure
        buys = p.buys_24h
        sells = p.sells_24h
        if sells > 0:
            ratio = buys / sells
        elif buys > 0:
            ratio = 999
        else:
            ratio = 0
        
        buy_ok = ratio >= 1.0
        buy_check = ValidationCheck(
            name="buy_pressure",
            passed=buy_ok,
            value=ratio,
            threshold=1.0,
            message=f"Buy/Sell {ratio:.1f}x {'✅' if buy_ok else '❌'} (min 1.0)",
        )
        checks.append(buy_check)
        
        # 6. Not parabolic (adaptive threshold)
        if p.liquidity < 100000:
            parabolic_threshold = 300
        elif p.liquidity < 500000:
            parabolic_threshold = 200
        else:
            parabolic_threshold = 150
        
        not_parabolic = chg24 < parabolic_threshold
        parabolic_check = ValidationCheck(
            name="not_parabolic",
            passed=not_parabolic,
            value=chg24,
            threshold=parabolic_threshold,
            message=f"Parabolic check {chg24:.1f}% < {parabolic_threshold}% {'✅' if not_parabolic else '❌'}",
        )
        checks.append(parabolic_check)
        
        # 7. Volume/Liquidity ratio (hotness)
        vol_liq = p.volume_24h / p.liquidity if p.liquidity > 0 else 0
        hot_check = ValidationCheck(
            name="volume_liquidity_ratio",
            passed=vol_liq >= 0.5,
            value=vol_liq,
            threshold=0.5,
            message=f"Vol/Liq {vol_liq:.2f}x {'✅' if vol_liq >= 0.5 else '❌'}",
        )
        checks.append(hot_check)
        
        # 8. Minimum momentum (at least some movement)
        min_mom_check = ValidationCheck(
            name="minimum_momentum",
            passed=abs(p.change_5m) >= 0.5 or abs(p.change_1h) >= 2.0,
            value=max(abs(p.change_5m), abs(p.change_1h)),
            threshold=0.5,
            message=f"Min momentum 5m={p.change_5m:.1f}% 1h={p.change_1h:.1f}% {'✅' if abs(p.change_5m) >= 0.5 or abs(p.change_1h) >= 2.0 else '❌'}",
        )
        checks.append(min_mom_check)
        
        # Calculate results
        total = len(checks)
        passed = sum(1 for c in checks if c.passed)
        pass_rate = passed / total
        
        # Tier assignment
        if pass_rate >= 0.875 and p.change_24h <= 150 and ratio >= 2.0:
            tier = TradeTier.TIER_1.value
            confidence = min(95, 70 + (pass_rate * 100 * 0.25) + (ratio * 5))
        elif pass_rate >= 0.625 and p.change_24h <= 200:
            tier = TradeTier.TIER_2.value
            confidence = min(85, 55 + (pass_rate * 100 * 0.2) + (ratio * 3))
        elif pass_rate >= 0.5:
            tier = TradeTier.TIER_3.value
            confidence = min(70, 40 + (pass_rate * 100 * 0.15))
        else:
            tier = TradeTier.REJECT.value
            confidence = max(0, pass_rate * 100)
        
        is_approved = tier in (TradeTier.TIER_1.value, TradeTier.TIER_2.value)
        
        # Rejection reason
        if not is_approved:
            failed = [c.name for c in checks if not c.passed]
            rejection_reason = f"Failed checks: {', '.join(failed)} (pass rate {pass_rate:.0%})"
        else:
            rejection_reason = ""
        
        return checks, is_approved, tier, confidence, rejection_reason
    
    @timed(VALIDATE_LATENCY)
    @count_exceptions(ERRORS_TOTAL, "validator", "processing")
    async def run_validation_cycle(self):
        """Fetch latest scanner outputs and validate them."""
        self.cycle_counter += 1
        logger.info(f"=== VALIDATION CYCLE #{self.cycle_counter} ===")
        
        try:
            # Get recent unscanned outputs
            recent = await ScannerStateManager.get_latest(batch_size=50)
            
            if not recent:
                logger.info("No scanner outputs to validate")
                return
            
            logger.info(f"Validating {len(recent)} scanner outputs...")
            
            validated_count = 0
            approved_count = 0
            
            for scanner_output in recent:
                try:
                    # Skip if already validated
                    # (In production, add a flag to scanner_output or check validator_outputs table)
                    
                    # Run checks
                    checks, is_approved, tier, confidence, rejection_reason = self.run_checks(scanner_output)
                    
                    # Persist
                    validator_output = await ValidatorStateManager.create(
                        scanner_output_id=scanner_output.id,
                        symbol=scanner_output.symbol,
                        checks=checks,
                        is_approved=is_approved,
                        tier=tier,
                        confidence=confidence,
                        rejection_reason=rejection_reason,
                        buy_sell_ratio=scanner_output.buy_ratio,
                    )
                    
                    # Metrics
                    VALIDATOR_CHECKS.labels(result="pass" if is_approved else "reject").inc()
                    
                    # Event
                    await emit_validated(
                        symbol=scanner_output.symbol,
                        approved=is_approved,
                        tier=tier,
                        confidence=confidence,
                        batch_id=scanner_output.scan_batch_id,
                    )
                    
                    validated_count += 1
                    if is_approved:
                        approved_count += 1
                    
                    logger.info(
                        f"  {scanner_output.symbol}: {tier} (conf={confidence:.1f}, "
                        f"pass={sum(1 for c in checks if c.passed)}/{len(checks)})"
                    )
                    
                except Exception as e:
                    logger.error(f"Validation failed for {scanner_output.symbol}: {e}")
                    continue
            
            logger.info(f"Validation complete: {approved_count}/{validated_count} approved")
            set_agent_healthy("validator")
            
        except Exception as e:
            logger.error(f"Validation cycle failed: {e}")
            set_agent_down("validator")
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("🔒 ASYNC VALIDATOR V2 STARTED")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        while self.running:
            try:
                await self.run_validation_cycle()
                await asyncio.sleep(30)  # 30s between validations
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Validator loop error: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        self.running = False

async def main():
    validator = AsyncValidator()
    await validator.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Validator stopped")
