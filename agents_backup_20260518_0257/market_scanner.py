#!/usr/bin/env python3
"""
🤖 AGENT 1: MARKET SCANNER
Job: Collect raw market data every 15 minutes
"""
import requests
import json
import time
from datetime import datetime

SEARCH_TERMS = ["SOL", "ETH", "PEPE", "BONK", "WIF", "DOGE", "SHIB", "TRUMP", "USA", "AI", "FLOKI", "JTO", "BOME"]

def fetch_all():
    all_pairs = []
    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": term},
                timeout=15
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:2]
            all_pairs.extend(pairs)
        except:
            pass
    return all_pairs

def save_data(pairs):
    data = {
        "timestamp": datetime.now().isoformat(),
        "pairs": pairs,
        "count": len(pairs)
    }
    with open("/tmp/market_scanner_data.json", "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("[MARKET SCANNER] Agent started!")
    while True:
        try:
            pairs = fetch_all()
            save_data(pairs)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanned {len(pairs)} pairs")
            
            # Check for hot movers (>10% in 24h)
            hot = []
            for p in pairs:
                chg = float((p.get("priceChange") or {}).get("h24", 0) or 0)
                if chg > 10:
                    sym = p.get("baseToken", {}).get("symbol", "???")
                    hot.append(f"{sym}: +{chg:.1f}%")
            
            if hot:
                print(f"  🔥 HOT: {', '.join(hot)}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
