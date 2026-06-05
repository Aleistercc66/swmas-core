#!/usr/bin/env python3
"""
🚫 FOMO FILTER AGENT
Anti-hype protection. Rejects emotionally driven setups.
"""
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def fomo_filter(pair_data):
    """Apply FOMO rejection criteria"""
    
    chg24 = pair_data.get("change_24h", 0)
    chg1 = pair_data.get("change_1h", 0)
    chg5 = pair_data.get("change_5m", 0)
    vol = pair_data.get("volume_24h", 0)
    liq = pair_data.get("liquidity", 0)
    vol_ratio = vol / liq if liq > 0 else 0
    buys = pair_data.get("buys_24h", 0)
    sells = pair_data.get("sells_24h", 0)
    
    rejections = []
    fomo_score = 0  # 0 = clean, higher = more FOMO
    
    # 1. Parabolic move (>40% = high FOMO)
    if chg24 > 100:
        fomo_score += 40
        rejections.append("Already pumped >100% — extreme FOMO territory")
    elif chg24 > 50:
        fomo_score += 25
        rejections.append("Already pumped >50% — late entry risk")
    elif chg24 > 25:
        fomo_score += 15
        rejections.append("Pumped >25% — momentum may be exhausted")
    
    # 2. Volume climax (volume > 10x liquidity)
    if vol_ratio > 15:
        fomo_score += 30
        rejections.append("Volume climax — blow-off top pattern")
    elif vol_ratio > 10:
        fomo_score += 20
        rejections.append("Extreme volume spike — euphoric activity")
    
    # 3. Single candle too large (>8% in 1h)
    if chg1 > 8:
        fomo_score += 20
        rejections.append(f"1h candle +{chg1:.1f}% — chasing parabolic")
    elif chg1 > 5:
        fomo_score += 10
        rejections.append("Large 1h candle — may be overextended")
    
    # 4. 5m extreme (too fast)
    if chg5 > 3:
        fomo_score += 15
        rejections.append(f"5m +{chg5:.1f}% — velocity too high for entry")
    
    # 5. Social explosion without consolidation
    if chg24 > 30 and vol_ratio > 5 and chg1 > 3:
        fomo_score += 20
        rejections.append("All-time high hype velocity — retail FOMO")
    
    # 6. Buy/sell imbalance (too one-sided = unsustainable)
    if sells > 0 and buys / sells > 3:
        fomo_score += 15
        rejections.append(f"Buy/sell ratio {buys/sells:.1f}x — unsustainable buying")
    
    # 7. Dumping in real-time (5m negative while 24h positive)
    if chg24 > 20 and chg5 < -1:
        fomo_score += 25
        rejections.append("Dumping in real-time — don't catch a falling knife")
    
    # Decision
    if fomo_score >= 60:
        status = "REJECTED"
    elif fomo_score >= 40:
        status = "HIGH_FOMO"
    elif fomo_score >= 20:
        status = "MODERATE_FOMO"
    else:
        status = "CLEAN"
    
    return {
        "symbol": pair_data.get("symbol", "???"),
        "fomo_score": fomo_score,
        "status": status,
        "rejections": rejections,
        "timestamp": datetime.now().isoformat()
    }

def main():
    print("[FOMO FILTER] Anti-hype protection active")
    while True:
        try:
            scanner  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", {})
            
            results = []
            for pair in scanner.get("pairs", []):
                fomo = fomo_filter(pair)
                results.append(fomo)
                
                emoji = "✅" if fomo["status"] == "CLEAN" else "⚠️" if fomo["status"] == "MODERATE_FOMO" else "🚫"
                print(f"{emoji} {fomo['symbol']}: {fomo['status']} (score: {fomo['fomo_score']})")
                if fomo["rejections"]:
                    print(f"   → {fomo['rejections'][0]}")
            
            output = {
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/fomo_output.json", output)
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
