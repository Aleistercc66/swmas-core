#!/usr/bin/env python3
"""
😊 AGENT 2: SENTIMENT ANALYZER
Track social mood and narrative shifts.
"""
import requests
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

TERMS = ["PEPE", "WIF", "BONK", "SOL", "ETH", "DOGE", "SHIB", "FLOKI", "BOME", "POPCAT"]

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def analyze():
    results = {}
    overall_bull = 0
    overall_bear = 0
    
    for term in TERMS:
        try:
            resp = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={term}",
                timeout=10
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:1]
            if not pairs:
                continue
            p = pairs[0]
            chg24 = parse_val((p.get("priceChange") or {}).get("h24"))
            chg1 = parse_val((p.get("priceChange") or {}).get("h1"))
            vol = parse_val((p.get("volume") or {}).get("h24"))
            liq = parse_val((p.get("liquidity") or {}).get("usd"))
            
            # Sentiment scoring
            if chg24 > 20:
                mood = "EUPHORIC" if chg24 > 100 else "BULLISH"
                overall_bull += 1
            elif chg24 > 5:
                mood = "BULLISH"
                overall_bull += 1
            elif chg24 > -5:
                mood = "CAUTIOUS"
            else:
                mood = "BEARISH"
                overall_bear += 1
            
            # Divergence detection
            divergence = (chg24 > 20 and chg1 < -5)  # Price up but dumping now
            
            results[term] = {
                "mood": mood,
                "price_change_24h": chg24,
                "price_change_1h": chg1,
                "volume": vol,
                "liquidity": liq,
                "divergence_warning": divergence,
                "confidence": min(abs(chg24) * 2, 100)
            }
        except:
            pass
    
    # Overall sentiment
    if overall_bull > overall_bear + 2:
        overall = "BULLISH"
    elif overall_bear > overall_bull + 2:
        overall = "BEARISH"
    elif overall_bull > overall_bear:
        overall = "CAUTIOUS_BULLISH"
    else:
        overall = "NEUTRAL"
    
    # Hot topics (top movers)
    hot = sorted(results.items(), key=lambda x: x[1]["price_change_24h"], reverse=True)[:5]
    hot_topics = [f"{k} ({v['mood']}, {v['price_change_24h']:+.1f}%)" for k, v in hot]
    
    # Divergence alerts
    div_alerts = [k for k, v in results.items() if v["divergence_warning"]]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_market_mood": overall,
        "bullish_count": overall_bull,
        "bearish_count": overall_bear,
        "token_sentiment": results,
        "hot_topics": hot_topics,
        "divergence_alerts": div_alerts
    }

def main():
    print("[SENTIMENT] Agent started — Social mood tracking")
    while True:
        try:
            report = analyze()
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/sentiment_output.json", report)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Mood: {report['overall_market_mood']}")
            print(f"  Hot: {', '.join(report['hot_topics'][:3])}")
            if report['divergence_alerts']:
                print(f"  ⚠️ Divergence: {', '.join(report['divergence_alerts'])}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1800)  # 30 minutes

if __name__ == "__main__":
    main()
