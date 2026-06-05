#!/usr/bin/env python3
"""
🛡️ AGENT 5: RISK MANAGER
Calculate EXACT profit points — entry, stop, TP1, TP2, TP3.
"""
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def calculate_risk_reward(entry, stop, tp1):
    """Calculate risk:reward ratio"""
    risk = abs(entry - stop)
    reward = abs(tp1 - entry)
    if risk == 0:
        return 0
    return round(reward / risk, 1)

def assess_risk(validated_signal):
    p = validated_signal.get("raw_data", {})
    symbol = p.get("symbol", "???")
    price = p.get("price", 0)
    chg24 = p.get("change_24h", 0)
    chg1 = p.get("change_1h", 0)
    liq = p.get("liquidity", 0)
    vol = p.get("volume_24h", 0)
    vol_ratio = vol / liq if liq > 0 else 0
    age = p.get("age_hours", 999)
    
    # ENTRY ZONE calculation
    entry_primary = price * 0.98  # 2% discount
    entry_aggressive = price
    entry_conservative = price * 0.95  # 5% discount (wait for dip)
    
    # STOP LOSS — sacred
    stop_loss = entry_primary * 0.80  # -20% from entry
    
    # TAKE PROFITS
    tp1 = entry_primary * 1.50   # +50%
    tp2 = entry_primary * 2.00   # +100%
    tp3 = entry_primary * 3.00   # +200%
    
    # RISK/REWARD
    rr = calculate_risk_reward(entry_primary, stop_loss, tp1)
    
    # POSITION SIZING logic
    if rr >= 3:
        position_pct = 5  # 5% of portfolio (high quality)
    elif rr >= 2:
        position_pct = 3  # 3% of portfolio (good)
    else:
        position_pct = 1  # 1% of portfolio (minimum)
    
    # RISK LEVEL
    risk_factors = []
    risk_score = 0
    
    if chg24 > 100:
        risk_score += 25
        risk_factors.append("Parabolic pump — late entry risk")
    elif chg24 > 50:
        risk_score += 15
        risk_factors.append("Strong pump — manage carefully")
    
    if chg1 < -3:
        risk_score += 20
        risk_factors.append("Currently dumping — wait for support")
    elif chg1 < 0:
        risk_score += 10
        risk_factors.append("Losing hourly momentum")
    
    if vol_ratio > 10:
        risk_score += 15
        risk_factors.append("Extreme volume spike — volatility")
    
    if liq < 50000:
        risk_score += 20
        risk_factors.append("Low liquidity — slippage risk")
    elif liq < 100000:
        risk_score += 10
        risk_factors.append("Moderate liquidity")
    
    if age < 24:
        risk_score += 15
        risk_factors.append("Very new token — unproven")
    
    # Determine risk level
    if risk_score >= 60:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Confidence score (inverse of risk)
    confidence = max(0, 100 - risk_score)
    
    # If R:R < 2, downgrade confidence
    if rr < 2:
        confidence = int(confidence * 0.5)
        risk_factors.append("Poor R:R ratio — reduce size")
    
    return {
        "symbol": symbol,
        "price": price,
        "entry_zone": {
            "primary": round(entry_primary, 10),
            "aggressive": round(entry_aggressive, 10),
            "conservative": round(entry_conservative, 10)
        },
        "stop_loss": round(stop_loss, 10),
        "take_profits": {
            "tp1_50pct": round(tp1, 10),
            "tp2_100pct": round(tp2, 10),
            "tp3_200pct": round(tp3, 10)
        },
        "risk_reward_ratio": rr,
        "position_size_pct": position_pct,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "confidence": confidence,
        "risk_factors": risk_factors,
        "status": "APPROVED" if confidence >= 60 and rr >= 2 else "REJECTED",
        "timestamp": datetime.now().isoformat()
    }

def main():
    print("[RISK MANAGER] Agent started — Calculating exact profit points")
    print("[RISK MANAGER] Sacred rules: R:R >= 1:2 | Stop -20% | TP +50%/+100%/+200%")
    
    while True:
        try:
            # Load validator output
            validator = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/validator_output.json", {})
            if not validator:
                time.sleep(60)
                continue
            
            results = []
            for v in validator.get("validated", []):
                risk_assessment = assess_risk(v)
                results.append(risk_assessment)
                
                status_emoji = "✅" if risk_assessment["status"] == "APPROVED" else "❌"
                print(f"\n{status_emoji} {risk_assessment['symbol']} — {risk_assessment['status']}")
                print(f"   Entry: ${risk_assessment['entry_zone']['primary']:.8f}")
                print(f"   Stop:  ${risk_assessment['stop_loss']:.8f} (-20%)")
                print(f"   TP1:   ${risk_assessment['take_profits']['tp1_50pct']:.8f} (+50%)")
                print(f"   TP2:   ${risk_assessment['take_profits']['tp2_100pct']:.8f} (+100%)")
                print(f"   TP3:   ${risk_assessment['take_profits']['tp3_200pct']:.8f} (+200%)")
                print(f"   R:R:   1:{risk_assessment['risk_reward_ratio']}")
                print(f"   Confidence: {risk_assessment['confidence']}/100 | Risk: {risk_assessment['risk_level']}")
                print(f"   Position: {risk_assessment['position_size_pct']}% of portfolio")
                if risk_assessment['risk_factors']:
                    print(f"   ⚠️  {', '.join(risk_assessment['risk_factors'])}")
            
            output = {
                "timestamp": datetime.now().isoformat(),
                "opportunities": results,
                "approved": [r for r in results if r["status"] == "APPROVED"],
                "rejected": [r for r in results if r["status"] == "REJECTED"]
            }
            
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/risk_output.json", output)
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Risk assessment: {len(output['approved'])} approved, {len(output['rejected'])} rejected")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
