#!/usr/bin/env python3
"""
🌎 AGENT: REGIME DETECTOR
Detects market regime: trending, ranging, volatile, panic, euphoric, illiquid
"""
import requests
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def detect_regime():
    """Analyze BTC, ETH, SOL to determine overall market regime"""
    
    regime = {
        "timestamp": datetime.now().isoformat(),
        "overall": "UNKNOWN",
        "btc_state": {},
        "indicators": {},
        "recommendations": []
    }
    
    try:
        # Get BTC data as market proxy
        resp = requests.get("https://api.dexscreener.com/latest/dex/search?q=BTC", timeout=15)
        data = resp.json()
        btc_pairs = data.get("pairs", [])
        
        if not btc_pairs:
            return regime
        
        btc = btc_pairs[0]
        btc_price = parse_val(btc.get("priceUsd"))
        btc_chg24 = parse_val((btc.get("priceChange") or {}).get("h24"))
        btc_chg1 = parse_val((btc.get("priceChange") or {}).get("h1"))
        btc_chg6 = parse_val((btc.get("priceChange") or {}).get("h6"))
        btc_vol = parse_val((btc.get("volume") or {}).get("h24"))
        btc_liq = parse_val((btc.get("liquidity") or {}).get("usd"))
        
        # Get ETH for correlation
        resp2 = requests.get("https://api.dexscreener.com/latest/dex/search?q=ETH", timeout=15)
        eth_data = resp2.json()
        eth_pairs = eth_data.get("pairs", [])
        eth_chg24 = parse_val((eth_pairs[0].get("priceChange") or {}).get("h24")) if eth_pairs else 0
        
        # Calculate volatility proxy (max swing in last 24h)
        volatility = abs(btc_chg24)
        
        # Trend strength (alignment across timeframes)
        timeframe_alignment = 0
        if btc_chg24 > 0 and btc_chg6 > 0 and btc_chg1 > 0:
            timeframe_alignment = 1  # Strong uptrend
        elif btc_chg24 < 0 and btc_chg6 < 0 and btc_chg1 < 0:
            timeframe_alignment = -1  # Strong downtrend
        else:
            timeframe_alignment = 0  # Mixed/choppy
        
        # BTC-ETH correlation (are they moving together?)
        correlation = "aligned" if (btc_chg24 > 0 and eth_chg24 > 0) or (btc_chg24 < 0 and eth_chg24 < 0) else "divergent"
        
        # Classify regime
        if volatility > 15:
            if btc_chg24 > 10:
                regime["overall"] = "EUPHORIC"
                regime["recommendations"].append("Reduce position sizes by 50%")
                regime["recommendations"].append("Avoid new momentum entries")
                regime["recommendations"].append("Focus on mean reversion setups")
            else:
                regime["overall"] = "PANIC"
                regime["recommendations"].append("Cash is a position — stay flat")
                regime["recommendations"].append("Wait for V-bottom confirmation")
                regime["recommendations"].append("No breakout trades")
        elif volatility > 8:
            regime["overall"] = "HIGH_VOLATILITY"
            regime["recommendations"].append("Widen stops by 30%")
            regime["recommendations"].append("Reduce position sizes")
            regime["recommendations"].append("Focus on liquid large-caps")
        elif abs(btc_chg24) < 3 and abs(btc_chg6) < 2:
            regime["overall"] = "RANGING"
            regime["recommendations"].append("Mean reversion preferred")
            regime["recommendations"].append("Breakout trades need extra confirmation")
            regime["recommendations"].append("Reduce scan frequency to 30min")
        elif timeframe_alignment == 1:
            regime["overall"] = "BULLISH_TREND"
            regime["recommendations"].append("Momentum continuation preferred")
            regime["recommendations"].append("Breakout trades have higher success")
            regime["recommendations"].append("Standard position sizing OK")
        elif timeframe_alignment == -1:
            regime["overall"] = "BEARISH_TREND"
            regime["recommendations"].append("Short setups or cash")
            regime["recommendations"].append("Avoid long breakouts")
            regime["recommendations"].append("Wait for trend reversal")
        else:
            regime["overall"] = "CHOPPY"
            regime["recommendations"].append("Reduce trade frequency")
            regime["recommendations"].append("Tighter risk control")
            regime["recommendations"].append("Accumulation setups only")
        
        regime["btc_state"] = {
            "price": btc_price,
            "change_24h": btc_chg24,
            "change_6h": btc_chg6,
            "change_1h": btc_chg1,
            "volatility": volatility,
            "timeframe_alignment": timeframe_alignment
        }
        
        regime["indicators"] = {
            "btc_eth_correlation": correlation,
            "volatility_proxy": volatility,
            "trend_strength": abs(btc_chg24),
            "momentum_consistency": timeframe_alignment
        }
        
    except Exception as e:
        regime["error"] = str(e)
    
    return regime

def main():
    print("[REGIME DETECTOR] Market regime identification active")
    while True:
        try:
            regime = detect_regime()
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", regime)
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] REGIME: {regime['overall']}")
            if regime.get('btc_state'):
                btc = regime['btc_state']
                print(f"  BTC: ${btc['price']:,.0f} | 24h: {btc['change_24h']:+.1f}% | Vol: {btc['volatility']:.1f}%")
            print(f"  Recommendations:")
            for rec in regime.get('recommendations', []):
                print(f"    → {rec}")
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(1800)  # 30 minutes

if __name__ == "__main__":
    main()
