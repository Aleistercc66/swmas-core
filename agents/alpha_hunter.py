#!/usr/bin/env python3
"""
🤖 AGENT 3: ALPHA HUNTER
Job: Find early opportunities, new launches, trending tokens
"""
import requests
import json
import time
from datetime import datetime

def find_new_pairs():
    """Find recently created pairs with momentum"""
    try:
        # Check new pairs on DexScreener
        resp = requests.get(
            "https://api.dexscreener.com/latest/dex/search?q=solana",
            timeout=15
        )
        data = resp.json()
        pairs = data.get("pairs", [])[:20]
        
        new_pairs = []
        for p in pairs:
            created = p.get("pairCreatedAt", 0)
            age_hours = (datetime.now().timestamp() * 1000 - created) / 3600000 if created else 999
            
            if age_hours < 48:  # Less than 48 hours old
                chg_24h = float((p.get("priceChange") or {}).get("h24", 0) or 0)
                vol = float((p.get("volume") or {}).get("h24", 0) or 0)
                liq = float((p.get("liquidity") or {}).get("usd", 0) or 0)
                
                if chg_24h > 20 and vol > 5000 and liq > 10000:
                    new_pairs.append({
                        "symbol": p.get("baseToken", {}).get("symbol", "???"),
                        "price": float(p.get("priceUsd", 0) or 0),
                        "age_hours": round(age_hours, 1),
                        "change_24h": chg_24h,
                        "volume_24h": vol,
                        "liquidity": liq,
                        "url": p.get("url", ""),
                        "score": min(chg_24h + (vol/liq if liq else 0), 100)
                    })
        
        new_pairs.sort(key=lambda x: x["score"], reverse=True)
        return new_pairs[:5]
        
    except Exception as e:
        return []

def find_trending():
    """Find trending tokens"""
    try:
        # Use search for hot terms
        hot_terms = ["PEPE", "WIF", "BONK", "SHIB", "FLOKI", "DOGE"]
        trending = []
        
        for term in hot_terms:
            resp = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={term}",
                timeout=10
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:1]
            if pairs:
                p = pairs[0]
                chg = float((p.get("priceChange") or {}).get("h24", 0) or 0)
                if chg > 5:
                    trending.append({
                        "symbol": term,
                        "change_24h": chg,
                        "url": p.get("url", "")
                    })
        
        trending.sort(key=lambda x: x["change_24h"], reverse=True)
        return trending[:5]
        
    except:
        return []

def main():
    print("[ALPHA HUNTER] Agent started!")
    while True:
        try:
            new = find_new_pairs()
            trending = find_trending()
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "new_pairs": new,
                "trending": trending
            }
            
            with open("/tmp/alpha_hunter_data.json", "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(new)} new pairs, {len(trending)} trending")
            
            if new:
                for p in new[:3]:
                    print(f"  🆕 {p['symbol']}: +{p['change_24h']:.1f}% | Age: {p['age_hours']}h | Score: {p['score']:.1f}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(3600)  # 1 hour

if __name__ == "__main__":
    main()
