#!/usr/bin/env python3
"""
🤖 DATA COLLECTOR — Just gathers raw market data
No decisions here. Brain (the AI) does all thinking.
"""
import requests
import json
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
TELEGRAM_CHAT_ID = "158923136"

def collect_and_save():
    """Collect raw DexScreener data and save for brain analysis"""
    
    # Search hot terms
    terms = ["SOL", "ETH", "PEPE", "BONK", "WIF", "DOGE", "SHIB", "TRUMP", "USA", "AI", "FLOKI"]
    all_pairs = []
    
    for term in terms:
        try:
            resp = requests.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": term},
                timeout=15
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:3]  # Top 3 per term
            all_pairs.extend(pairs)
        except:
            pass
    
    # Also get boosted tokens
    try:
        resp = requests.get("https://api.dexscreener.com/token-boosts/latest/v1", timeout=15)
        boosted = resp.json()
    except:
        boosted = []
    
    # Save raw data
    timestamp = datetime.now().isoformat()
    scan_data = {
        "timestamp": timestamp,
        "pairs": all_pairs,
        "boosted_tokens": boosted,
        "total_pairs": len(all_pairs),
        "total_boosted": len(boosted)
    }
    
    with open("/tmp/dexscreener_raw.json", "w") as f:
        json.dump(scan_data, f, indent=2)
    
    print(f"[{timestamp}] Collected {len(all_pairs)} pairs, {len(boosted)} boosted tokens")
    
    # Send notification to brain (AI agent) via Telegram
    # This message will trigger the brain to do analysis
    try:
        msg = f"🧠 BRAIN SCAN REQUEST\n\n📊 New market data collected!\n• {len(all_pairs)} pairs scanned\n• {len(boosted)} boosted tokens\n\nData ready for analysis at: /tmp/dexscreener_raw.json"
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
    except:
        pass

if __name__ == "__main__":
    collect_and_save()
