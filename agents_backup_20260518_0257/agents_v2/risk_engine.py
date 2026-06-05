#!/usr/bin/env python3
"""
📈 AGENT V2: DYNAMIC RISK ENGINE — ATR-based, volatility-adjusted
Replaces v2_dynamic_risk.py. Atomic calculations, event-driven, database-backed.
"""
import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from core import (
    settings, get_logger,
    ValidatorStateManager, RiskStateManager,
    RiskAssessment, TradeTier,
    emit_risk_assessed,
    timed, count_exceptions, set_agent_healthy, set_agent_down,
    RISK_ASSESSMENTS, RISK_LATENCY, ERRORS_TOTAL,
)

logger = get_logger("risk_engine")

class AsyncRiskEngine:
    """Production-grade dynamic risk engine."""
    
    def __init__(self):
        self.running = False
        self.cycle_counter = 0
    
    def calculate_atr_proxy(self, price: float, chg24: float, chg6: float, chg1: float, chg5m: float) -> float:
        """Calculate ATR proxy from available timeframe data."""
        swings = [abs(chg24), abs(chg6), abs(chg1) * 24, abs(chg5m) * 288]
        hour_equiv = [s / 24 for s in swings]
        volatility = max(hour_equiv) if hour_equiv else 0.01
        return max(volatility, 0.01)
    
    def calculate_stop_loss(self, entry_price: float, atr: float, multiplier: float) -> float:
        """ATR-based stop loss."""
        return entry_price * (1 - (atr * multiplier / 100))
    
    def calculate_take_profits(self, entry_price: float, atr: float) -> Dict[str, float]:
        """Dynamic take profit levels based on volatility."""
        return {
            "TP1": entry_price * (1 + atr * 1.5 / 100),
            "TP2": entry_price * (1 + atr * 3.0 / 100),
            "TP3": entry_price * (1 + atr * 6.0 / 100),
        }
    
    def assess_risk(self, validator_output, scanner_output) -> RiskAssessment:
        """
        Full risk assessment from validated signal.
        Returns RiskAssessment model with all fields populated.
        """
        p = scanner_output
        v = validator_output
        
        # ATR proxy
        atr = self.calculate_atr_proxy(p.price, p.change_24h, p.change_6h, p.change_1h, p.change_5m)
        
        # Position sizing based on volatility
        vol_normalized = min(atr / 50.0, 1.0)  # 0-1 scale
        if vol_normalized > 0.8:
            size_multiplier = 0.5  # High vol = smaller size
        elif vol_normalized > 0.5:
            size_multiplier = 0.75
        else:
            size_multiplier = 1.0
        
        position_size_pct = settings.trading.position_size_pct * size_multiplier
        
        # Stop distance based on ATR
        if atr < 5:
            stop_multiplier = 2.0
        elif atr < 15:
            stop_multiplier = 1.5
        elif atr < 30:
            stop_multiplier = 1.0
        else:
            stop_multiplier = 0.75
        
        stop_distance_pct = atr * stop_multiplier
        stop_price = self.calculate_stop_loss(p.price, atr, stop_multiplier)
        
        # Take profits
        tps = self.calculate_take_profits(p.price, atr)
        
        # Risk/reward ratio
        risk = p.price - stop_price
        reward_tp1 = tps["TP1"] - p.price
        reward_tp2 = tps["TP2"] - p.price
        reward_tp3 = tps["TP3"] - p.price
        
        rr_tp1 = reward_tp1 / risk if risk > 0 else 0
        rr_tp2 = reward_tp2 / risk if risk > 0 else 0
        rr_tp3 = reward_tp3 / risk if risk > 0 else 0
        
        # Composite score (0-100)
        momentum_component = min(p.change_24h / 200 * 30, 30) if p.change_24h > 0 else 0
        vol_liq_component = min(p.vol_liq_ratio / 5 * 20, 20)
        pass_rate_component = v.pass_rate * 25
        buy_pressure_component = min(v.buy_sell_ratio / 5 * 15, 15) if v.buy_sell_ratio else 0
        rr_component = min(rr_tp1 * 5, 10)
        
        composite_score = (
            momentum_component + 
            vol_liq_component + 
            pass_rate_component + 
            buy_pressure_component + 
            rr_component
        )
        composite_score = min(100, max(0, composite_score))
        
        # Volatility risk level
        if atr > 50:
            vol_risk = "EXTREME"
        elif atr > 30:
            vol_risk = "HIGH"
        elif atr > 15:
            vol_risk = "MODERATE"
        else:
            vol_risk = "LOW"
        
        # Time to live for signal
        if v.tier == TradeTier.TIER_1.value:
            ttl_minutes = 15
        elif v.tier == TradeTier.TIER_2.value:
            ttl_minutes = 30
        else:
            ttl_minutes = 60
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        
        return RiskAssessment(
            validator_output_id=v.id,
            symbol=p.symbol,
            entry_price=round(p.price, 8),
            tier=v.tier,
            confidence=v.confidence,
            composite_score=round(composite_score, 2),
            position_size_pct=round(position_size_pct, 2),
            stop_loss_price=round(stop_price, 8),
            stop_distance_pct=round(stop_distance_pct, 2),
            take_profit_1=round(tps["TP1"], 8),
            take_profit_2=round(tps["TP2"], 8),
            take_profit_3=round(tps["TP3"], 8),
            risk_reward_ratio=round(rr_tp1, 2),
            atr_proxy=round(atr, 2),
            volatility_regime=vol_risk,
            is_active=True,
            expires_at=expires_at,
        )
    
    @timed(RISK_LATENCY)
    @count_exceptions(ERRORS_TOTAL, "risk_engine", "processing")
    async def run_risk_cycle(self):
        """Fetch approved validations and calculate risk assessments."""
        self.cycle_counter += 1
        logger.info(f"=== RISK CYCLE #{self.cycle_counter} ===")
        
        try:
            # Get recently approved validations
            approved = await ValidatorStateManager.get_approved(since_minutes=30)
            
            if not approved:
                logger.info("No approved signals to assess")
                return
            
            logger.info(f"Assessing risk for {len(approved)} signals...")
            
            assessed_count = 0
            
            for validation in approved:
                try:
                    # Get the scanner output
                    from core.database import AtomicTransaction
                    from sqlalchemy import select
                    from core.models import ScannerOutput
                    
                    async with AtomicTransaction() as session:
                        result = await session.execute(
                            select(ScannerOutput).where(ScannerOutput.id == validation.scanner_output_id)
                        )
                        scanner_output = result.scalar_one_or_none()
                    
                    if scanner_output is None:
                        logger.warning(f"Scanner output {validation.scanner_output_id} not found")
                        continue
                    
                    # Assess risk
                    assessment = self.assess_risk(validation, scanner_output)
                    
                    # Persist
                    saved = await RiskStateManager.create(assessment)
                    
                    # Metrics
                    RISK_ASSESSMENTS.labels(tier=assessment.tier).inc()
                    
                    # Event
                    await emit_risk_assessed(
                        symbol=assessment.symbol,
                        score=assessment.composite_score,
                        tier=assessment.tier,
                        batch_id=scanner_output.scan_batch_id,
                    )
                    
                    assessed_count += 1
                    
                    logger.info(
                        f"  {assessment.symbol}: score={assessment.composite_score:.1f} "
                        f"stop={assessment.stop_distance_pct:.1f}% "
                        f"size={assessment.position_size_pct:.1f}% "
                        f"RR={assessment.risk_reward_ratio:.1f}"
                    )
                    
                except Exception as e:
                    logger.error(f"Risk assessment failed for {validation.symbol}: {e}")
                    continue
            
            logger.info(f"Risk assessment complete: {assessed_count} signals")
            set_agent_healthy("risk_engine")
            
        except Exception as e:
            logger.error(f"Risk cycle failed: {e}")
            set_agent_down("risk_engine")
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("📈 ASYNC RISK ENGINE V2 STARTED")
        logger.info("ATR-based stops | Dynamic sizing | Atomic")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        while self.running:
            try:
                await self.run_risk_cycle()
                await asyncio.sleep(45)  # 45s between risk cycles
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Risk loop error: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        self.running = False

async def main():
    engine = AsyncRiskEngine()
    await engine.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Risk engine stopped")
