#!/usr/bin/env python3
"""
🧬 AGENT: SETUP DNA CLASSIFIER
Classifies each setup into its structural DNA type.
"""
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def classify_dna(pair_data):
    """Classify setup into DNA type with evidence"""
    
    chg24 = pair_data.get("change_24h", 0)
    chg6 = pair_data.get("change_6h", 0)
    chg1 = pair_data.get("change_1h", 0)
    chg5 = pair_data.get("change_5m", 0)
    vol = pair_data.get("volume_24h", 0)
    vol6 = pair_data.get("volume_6h", 0)
    liq = pair_data.get("liquidity", 0)
    buys = pair_data.get("buys_24h", 0)
    sells = pair_data.get("sells_24h", 0)
    age = pair_data.get("age_hours", 999)
    
    evidence = []
    dna_type = "UNCLASSIFIED"
    confidence = 50
    
    # Calculate ATR proxy (simplified)
    price = pair_data.get("price", 0)
    atr_proxy = abs(chg24) / 24 if chg24 != 0 else 0
    
    # Check for volume climax
    vol_ratio = vol / liq if liq > 0 else 0
    volume_climax = vol_ratio > 10
    
    # Check for consolidation before move
    consolidation = abs(chg6) < abs(chg24) * 0.3 if chg24 != 0 else False
    
    # Check for wick/rejection pattern
    rejection = chg1 < -3 and chg24 > 20
    
    # Check for steady accumulation
    steady_climb = chg1 > 0 and chg5 > 0 and abs(chg24) < 50 and abs(chg24) > 5
    
    # Check for mean reversion conditions
    overextended = chg24 > 100 or chg24 < -50
    declining_volume = vol6 < vol / 4 if vol > 0 else False
    
    # BREAKOUT: Breaks resistance + volume spike + consolidation before
    if chg24 > 20 and vol_ratio > 3 and consolidation:
        dna_type = "BREAKOUT"
        evidence.append(f"Volume spike: {vol_ratio:.1f}x liquidity")
        evidence.append(f"Consolidation before: 6h change only {chg6:.1f}%")
        evidence.append(f"Break of resistance: +{chg24:.1f}% in 24h")
        confidence = 75
    
    # REVERSAL: Extreme overextension + volume climax + rejection
    elif chg24 > 50 and (volume_climax or rejection):
        dna_type = "REVERSAL"
        evidence.append(f"Extreme overextension: +{chg24:.1f}%")
        evidence.append("Volume climax detected" if volume_climax else "Rejection candle on 1h")
        confidence = 60
    
    # ACCUMULATION: Low volume, steady climb, buy pressure
    elif steady_climb and vol_ratio < 2 and buys > sells * 1.2:
        dna_type = "ACCUMULATION"
        evidence.append(f"Steady climb: 1h +{chg1:.1f}%, 5m +{chg5:.1f}%")
        evidence.append(f"Low volume: {vol_ratio:.1f}x liquidity")
        evidence.append(f"Buy pressure: {buys/sells:.1f}x sells" if sells > 0 else "Buy pressure dominant")
        confidence = 70
    
    # MOMENTUM CONTINUATION: Trending, shallow pullbacks, sustained volume
    elif chg24 > 20 and chg1 > 0 and vol_ratio > 1 and not volume_climax:
        dna_type = "MOMENTUM_CONTINUATION"
        evidence.append(f"Strong trend: +{chg24:.1f}%")
        evidence.append(f"1h momentum still positive: +{chg1:.1f}%")
        evidence.append(f"Volume sustaining: {vol_ratio:.1f}x")
        confidence = 65
    
    # MEAN REVERSION: Overextended, declining volume
    elif overextended and declining_volume:
        dna_type = "MEAN_REVERSION"
        evidence.append(f"Overextended: {chg24:+.1f}%")
        evidence.append("Volume declining at extreme")
        evidence.append(f"ATR proxy: {atr_proxy:.1f}%")
        confidence = 55
    
    # LIQUIDITY SWEEP: Quick wick + immediate reclaim (detected via 1h vs 24h)
    elif chg24 > 10 and chg1 < -5 and chg5 > 0:
        dna_type = "LIQUIDITY_SWEEP"
        evidence.append(f"Wick below support: 1h {chg1:.1f}%")
        evidence.append(f"Reclaiming: 5m +{chg5:.1f}%")
        evidence.append("Stop hunt pattern")
        confidence = 50
    
    # Default classification based on primary characteristic
    elif chg24 > 50:
        dna_type = "REVERSAL"  # Likely overextended
        evidence.append(f"Extreme move: +{chg24:.1f}%")
        confidence = 45
    elif chg24 > 20:
        dna_type = "MOMENTUM_CONTINUATION"
        evidence.append(f"Momentum: +{chg24:.1f}%")
        confidence = 50
    elif chg24 > 5:
        dna_type = "ACCUMULATION"
        evidence.append(f"Gradual climb: +{chg24:.1f}%")
        confidence = 40
    
    return {
        "symbol": pair_data.get("symbol", "???"),
        "dna_type": dna_type,
        "confidence": confidence,
        "evidence": evidence,
        "timestamp": datetime.now().isoformat(),
        "raw_metrics": {
            "chg24": chg24, "chg6": chg6, "chg1": chg1, "chg5": chg5,
            "vol_ratio": vol_ratio, "volume_climax": volume_climax,
            "consolidation": consolidation, "rejection": rejection,
            "steady_climb": steady_climb, "overextended": overextended
        }
    }

def main():
    print("[DNA CLASSIFIER] Setup structural classification active")
    while True:
        try:
            # Load scanner output
            scanner  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", {})
            
            classifications = []
            for pair in scanner.get("pairs", []):
                dna = classify_dna(pair)
                classifications.append(dna)
                
                emoji = "🧬" if dna["confidence"] >= 60 else "❓"
                print(f"{emoji} {dna['symbol']}: {dna['dna_type']} (conf: {dna['confidence']})")
                for ev in dna["evidence"][:2]:
                    print(f"   → {ev}")
            
            output = {
                "timestamp": datetime.now().isoformat(),
                "classifications": classifications
            }
            
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/dna_output.json", output)
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
