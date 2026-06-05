#!/usr/bin/env python3
"""
🤖 AGENT 4: RISK MANAGER
Job: Assess risk for opportunities (on-demand)
"""
import requests
import json
from datetime import datetime

def assess_risk(pair_data):
    """Assess risk for a token opportunity"""
    risk_score = 0  # 0-100, higher = more risky
    warnings = []
    
    try:
        price = float(pair_data.get("priceUsd", 0) or 0)
        liq = float((pair_data.get("liquidity") or {}).get("usd", 0) or 0)
        vol = float((pair_data.get("volume") or {}).get("h24", 0) or 0)
        
        pc = pair_data.get("priceChange") or {}
        chg_24h = float(pc.get("h24", 0) or 0)
        chg_1h = float(pc.get("h1", 0) or 0)
        chg_5m = float(pc.get("m5", 0) or 0)
        
        # 1. Liquidity Risk
        if liq < 10000:
            risk_score += 40
            warnings.append("🚨 VERY LOW LIQUIDITY — easy to manipulate!")
        elif liq < 50000:
            risk_score += 20
            warnings.append("⚠️ Low liquidity — careful with size")
        
        # 2. Volume Risk
        if vol < 1000:
            risk_score += 30
            warnings.append("🚨 Almost no volume — dead token?")
        elif vol < 5000:
            risk_score += 15
            warnings.append("⚠️ Low volume")
        
        # 3. Pump Risk
        if chg_24h > 500:
            risk_score += 35
            warnings.append("🎰 MEGA PUMP — likely dump incoming!")
        elif chg_24h > 100:
            risk_score += 25
            warnings.append("🔥 Already pumped hard — late entry?")
        elif chg_24h > 50:
            risk_score += 15
            warnings.append("📈 Significant pump — watch for pullback")
        
        # 4. Momentum Risk
        if chg_1h < -5:
            risk_score += 20
            warnings.append("📉 Dropping fast now!")
        elif chg_1h < -2:
            risk_score += 10
            warnings.append("⬇️ Losing momentum")
        
        # 5. Dump Risk (5min)
        if chg_5m < -3:
            risk_score += 15
            warnings.append("💥 Dumping in real-time!")
        
        # 6. Age Risk
        created = pair_data.get("pairCreatedAt", 0)
        if created:
            age_hours = (datetime.now().timestamp() * 1000 - created) / 3600000
            if age_hours < 1:
                risk_score += 25
                warnings.append("👶 Brand new — high risk!")
            elif age_hours < 6:
                risk_score += 15
                warnings.append("🆕 Very new token")
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": "EXTREME" if risk_score > 70 else "HIGH" if risk_score > 50 else "MEDIUM" if risk_score > 30 else "LOW",
            "warnings": warnings,
            "safe_to_enter": risk_score < 50
        }
        
    except Exception as e:
        return {"risk_score": 100, "risk_level": "UNKNOWN", "warnings": [f"Error: {e}"], "safe_to_enter": False}

if __name__ == "__main__":
    # Test mode
    print("[RISK MANAGER] Agent ready (on-demand mode)")
    print("Call assess_risk(pair_data) when needed")
