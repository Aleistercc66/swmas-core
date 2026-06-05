#!/usr/bin/env python3
"""
🎯 DYNAMIC RISK ENGINE
ATR-based stops, volatility-adjusted position sizing.
NOT fixed percentages. Technical invalidation.
"""
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def calculate_atr_proxy(price, chg24, chg6, chg1):
    """Calculate ATR proxy from available timeframe data"""
    # Use max swing across timeframes as volatility estimate
    swings = [abs(chg24), abs(chg6), abs(chg1) * 24]
    # Normalize to hourly equivalent
    hourly_vol = max(abs(chg1), abs(chg6) / 6, abs(chg24) / 24)
    return hourly_vol

def calculate_dynamic_levels(pair_data, regime_data=None):
    """Calculate entry/stop/TP based on volatility and structure"""
    
    symbol = pair_data.get("symbol", "???")
    price = pair_data.get("price", 0)
    chg24 = pair_data.get("change_24h", 0)
    chg6 = pair_data.get("change_6h", 0)
    chg1 = pair_data.get("change_1h", 0)
    liq = pair_data.get("liquidity", 0)
    vol = pair_data.get("volume_24h", 0)
    vol_ratio = vol / liq if liq > 0 else 0
    
    # ATR proxy (hourly volatility %)
    atr = calculate_atr_proxy(price, chg24, chg6, chg1)
    
    # Regime multiplier
    regime_mult = 1.0
    if regime_data:
        regime = regime_data.get("overall", "UNKNOWN")
        if regime == "HIGH_VOLATILITY":
            regime_mult = 1.5
        elif regime == "PANIC":
            regime_mult = 2.0
        elif regime == "EUPHORIC":
            regime_mult = 1.3
        elif regime == "RANGING":
            regime_mult = 0.8
    
    # Liquidity adjustment (tighter stops in low liquidity)
    liq_mult = 1.0
    if liq < 50000:
        liq_mult = 1.3
    elif liq > 200000:
        liq_mult = 0.8
    
    # Dynamic stop distance (ATR-based)
    # Stop = 2.5-4 ATR below entry depending on conditions
    # Use ATR properly - not just hourly, but actual swing potential
    
    # Calculate true volatility range (max swing across timeframes)
    true_volatility = max(abs(chg24), abs(chg6), abs(chg1))
    
    # ATR multiplier: more for microcaps, less for established coins
    base_multiplier = 2.5
    if liq < 100000:
        base_multiplier = 3.5  # More room for microcaps
    elif liq > 500000:
        base_multiplier = 2.0  # Tighter for established
    
    atr_multiplier = base_multiplier * regime_mult * liq_mult
    stop_distance_pct = true_volatility * atr_multiplier
    
    # Minimum stop: 10% for microcaps, 7% for mid, 5% for large
    # NEVER less than 10% for low liquidity (<50K) — too much slippage risk
    if liq < 50000:
        min_stop = 12.0
    elif liq < 100000:
        min_stop = 10.0
    elif liq < 500000:
        min_stop = 8.0
    else:
        min_stop = 5.0
    
    stop_distance_pct = max(stop_distance_pct, min_stop)
    
    # Maximum stop: 35% for extreme volatility, 25% normal max
    max_stop = 35.0 if regime_data and regime_data.get("overall") in ["PANIC", "HIGH_VOLATILITY"] else 25.0
    stop_distance_pct = min(stop_distance_pct, max_stop)
    
    # Entry zone
    entry = price * (1 - 0.02)  # 2% discount from current
    
    # Stop loss — technical invalidation
    stop = entry * (1 - stop_distance_pct / 100)
    
    # Take profits based on risk:reward
    # Minimum R:R = 1:2
    # TP1 = 2x risk
    # TP2 = 3x risk
    # TP3 = 4x risk
    risk = entry - stop
    
    tp1 = entry + (risk * 2)
    tp2 = entry + (risk * 3)
    tp3 = entry + (risk * 4)
    
    # Calculate actual R:R
    rr = round((tp1 - entry) / (entry - stop), 1) if risk > 0 else 0
    
    # Position sizing based on volatility
    if stop_distance_pct > 25:
        position_pct = 1  # High volatility = tiny position
    elif stop_distance_pct > 15:
        position_pct = 2
    elif stop_distance_pct > 10:
        position_pct = 3
    else:
        position_pct = 5  # Low volatility = standard position
    
    # Regime adjustments
    regime = "UNKNOWN"
    if regime_data:
        regime = regime_data.get("overall", "UNKNOWN")
        if regime in ["PANIC", "EUPHORIC", "HIGH_VOLATILITY"]:
            position_pct = max(position_pct - 2, 1)
        elif regime == "BEARISH_TREND":
            position_pct = 1
    
    # Risk level based on stop distance
    if stop_distance_pct > 20:
        risk_level = "HIGH"
    elif stop_distance_pct > 12:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Lower confidence threshold to show more signals
    confidence = 50
    
    # Base score
    if rr >= 3:
        confidence += 15
    elif rr >= 2:
        confidence += 10
    elif rr >= 1.5:
        confidence += 5
    
    # Volatility penalty (high ATR = less predictable)
    if atr > 5:
        confidence -= 15
    elif atr > 2:
        confidence -= 5
    elif atr < 1:
        confidence += 5  # Low volatility bonus
    
    # Liquidity bonus
    if liq > 100000:
        confidence += 10
    elif liq > 50000:
        confidence += 5
    elif liq < 30000:
        confidence -= 10
    
    # Volume confirmation
    if vol_ratio > 2:
        confidence += 5
    elif vol_ratio < 0.5:
        confidence -= 5
    
    # Momentum alignment
    if chg1 > 0 and chg6 > 0:
        confidence += 5
    elif chg1 < 0 and chg24 > 20:
        confidence -= 10
    
    # In ranging market, still allow trades but reduce confidence
    if regime == "RANGING":
        confidence -= 5  # Small penalty, not a block
    elif regime == "PANIC":
        confidence -= 20
    elif regime == "EUPHORIC":
        confidence -= 15
    elif regime == "HIGH_VOLATILITY":
        confidence -= 10
    elif regime == "BEARISH_TREND":
        confidence -= 15
    
    # FOMO penalty
    try:
        fomo_data  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/fomo_output.json", {})
        for fomo in fomo_data.get("results", []):
            if fomo.get("symbol") == symbol:
                if fomo["status"] == "REJECTED":
                    confidence -= 30
                elif fomo["status"] == "HIGH_FOMO":
                    confidence -= 15
                elif fomo["status"] == "MODERATE_FOMO":
                    confidence -= 5
                break
    except:
        pass
    
    # Clamp confidence
    confidence = max(0, min(100, confidence))
    
    # Get raw data for profit calculation
    raw = pair_data if pair_data else {}
    buys = raw.get("buys_24h", 0) or 0
    sells = raw.get("sells_24h", 0) or 0
    vol_ratio = vol / liq if liq > 0 else 0
    age_hours = raw.get("age_hours", 999)
    
    # ========== PROFIT POTENTIAL SCORING ==========
    # Calculate estimated profit potential based on multiple factors
    
    # 1. Momentum trajectory (how much upside is left)
    momentum_score = 0
    if chg24 < 50 and chg6 > 0 and chg1 > 0:
        # Early momentum — lots of upside left
        momentum_score = min((50 - chg24) * 2, 40)
    elif chg24 < 100 and chg6 > 0:
        # Moderate momentum — some upside left
        momentum_score = min((100 - chg24), 25)
    else:
        # Late momentum — limited upside
        momentum_score = max(0, 10 - (chg24 - 100) * 0.5)
    
    # 2. Volume-to-liquidity ratio (how hot is the token)
    hotness = min(vol_ratio * 10, 30)
    
    # 3. Buy pressure intensity
    buy_pressure_score = 0
    if buys > sells:
        buy_pressure_score = min((buys / sells - 1) * 15, 20)
    
    # 4. Age bonus (newer tokens have more upside)
    age_hours = pair_data.get("age_hours", 999)
    age_score = 0
    if age_hours < 1:
        age_score = 15  # Brand new = high potential
    elif age_hours < 6:
        age_score = 10
    elif age_hours < 24:
        age_score = 5
    
    # 5. Price accessibility (lower price = easier pump)
    price_score = 0
    if price < 0.001:
        price_score = 15  # Microcap = easy 10x
    elif price < 0.01:
        price_score = 10
    elif price < 0.1:
        price_score = 5
    
    # Total profit potential (0-100)
    profit_potential = min(
        momentum_score + hotness + buy_pressure_score + age_score + price_score,
        100
    )
    
    # 6. Execution probability (how likely to hit targets)
    # Based on liquidity, volume trend, and momentum consistency
    exec_prob = 50
    if liq > 100000:
        exec_prob += 15
    elif liq > 50000:
        exec_prob += 10
    if vol_ratio > 1:
        exec_prob += 10
    if chg1 > 0 and chg6 > 0 and chg24 > 0:
        exec_prob += 15  # Consistent momentum
    exec_prob = min(exec_prob, 100)
    
    # 7. Risk-adjusted return estimate
    # Estimated % gain if trade works out
    est_gain_pct = (tp1 - entry) / entry * 100
    
    # Risk-adjusted: probability of success × potential gain
    expected_return = (exec_prob / 100) * est_gain_pct
    
    # ========== RANKING TIER ==========
    # Only the BEST opportunities get through
    tier = "REJECT"
    if profit_potential >= 60 and exec_prob >= 65 and confidence >= 50:
        tier = "TIER_1"  # Exceptional opportunity
    elif profit_potential >= 45 and exec_prob >= 55 and confidence >= 40:
        tier = "TIER_2"  # Good opportunity
    elif profit_potential >= 30 and exec_prob >= 45 and confidence >= 35:
        tier = "TIER_3"  # Moderate opportunity
    
    # Override: Always reject if profit potential too low
    if profit_potential < 25:
        tier = "REJECT"
    
    return {
        "symbol": symbol,
        "price": price,
        "liquidity": liq,
        "volume_24h": vol,
        "entry_zone": {
            "primary": round(entry, 10),
            "aggressive": round(price, 10),
            "conservative": round(price * 0.95, 10)
        },
        "stop_loss": round(stop, 10),
        "stop_distance_pct": round(stop_distance_pct, 1),
        "take_profits": {
            "tp1_2x_risk": round(tp1, 10),
            "tp2_3x_risk": round(tp2, 10),
            "tp3_4x_risk": round(tp3, 10)
        },
        "risk_reward_ratio": rr,
        "position_size_pct": position_pct,
        "risk_level": risk_level,
        "confidence": confidence,
        "atr_proxy": round(atr, 2),
        "regime_multiplier": regime_mult,
        "liquidity_multiplier": liq_mult,
        "profit_potential": round(profit_potential, 1),
        "execution_probability": round(exec_prob, 1),
        "expected_return_pct": round(expected_return, 1),
        "tier": tier,
        "status": "APPROVED" if tier in ["TIER_1", "TIER_2"] else "REJECTED",
        "timestamp": datetime.now().isoformat()
    }

def main():
    print("[DYNAMIC RISK ENGINE] ATR-based stops active")
    print("[DYNAMIC RISK ENGINE] Fixed -20% replaced with technical invalidation")
    
    while True:
        try:
            # Load validator output
            validator  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/validator_output.json", {})
            
            # Load regime data
            regime_data = None
            try:
                regime_data  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", {})
            except:
                pass
            
            results = []
            for v in validator.get("validated", []):
                p = v.get("raw_data", {})
                risk = calculate_dynamic_levels(p, regime_data)
                results.append(risk)
                
                status_emoji = "✅" if risk["status"] == "APPROVED" else "❌"
                print(f"\n{status_emoji} {risk['symbol']} — {risk['status']}")
                print(f"   Entry: ${risk['entry_zone']['primary']:.8f}")
                print(f"   Stop:  ${risk['stop_loss']:.8f} ({-risk['stop_distance_pct']:.1f}%)")
                print(f"   TP1:   ${risk['take_profits']['tp1_2x_risk']:.8f}")
                print(f"   R:R:   1:{risk['risk_reward_ratio']}")
                print(f"   ATR:   {risk['atr_proxy']:.1f}% | Regime: {risk['regime_multiplier']}x")
                print(f"   Conf:  {risk['confidence']}/100 | Risk: {risk['risk_level']}")
                print(f"   Size:  {risk['position_size_pct']}% of portfolio")
            
            output = {
                "timestamp": datetime.now().isoformat(),
                "opportunities": results,
                "approved": [r for r in results if r["status"] == "APPROVED"],
                "rejected": [r for r in results if r["status"] == "REJECTED"]
            }
            
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", output)
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Risk: {len(output['approved'])} approved, {len(output['rejected'])} rejected")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
