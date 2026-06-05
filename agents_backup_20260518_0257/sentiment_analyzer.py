#!/usr/bin/env python3
"""
🤖 AGENT 2: SENTIMENT ANALYZER
Job: Analyze Telegram crypto groups sentiment every 30 minutes
"""
import requests
import json
import time
from datetime import datetime

# Top crypto Telegram groups to monitor
GROUPS = {
    "memewars25": {"url": "https://t.me/memewars25", "focus": "memecoins"},
    "apingdegen": {"url": "https://t.me/apingdegen", "focus": "degen plays"},
    "SonicsAlphacalls": {"url": "https://t.me/SonicsAlphacalls", "focus": "alpha calls"},
    "aifirstbrain": {"url": "https://t.me/aifirstbrain", "focus": "AI tokens"},
    "blumcrypto": {"url": "https://t.me/blumcrypto", "focus": "general crypto"},
}

# Note: We can't directly read Telegram groups without being a member
# This agent will use web scraping and search for sentiment signals

def analyze_sentiment():
    """Analyze crypto sentiment from web sources"""
    try:
        # Use search to find current crypto sentiment
        # In production, this would connect to Telegram API
        
        sentiment = {
            "timestamp": datetime.now().isoformat(),
            "overall": "neutral",  # bullish/bearish/neutral
            "hot_topics": [],
            "mentions": {},
        }
        
        # Check trending searches as proxy for sentiment
        terms = ["PEPE", "WIF", "BONK", "SOL", "AI crypto"]
        for term in terms:
            try:
                resp = requests.get(
                    "https://api.dexscreener.com/latest/dex/search",
                    params={"q": term},
                    timeout=10
                )
                data = resp.json()
                pairs = data.get("pairs", [])[:1]
                if pairs:
                    p = pairs[0]
                    chg_24h = float((p.get("priceChange") or {}).get("h24", 0) or 0)
                    vol = float((p.get("volume") or {}).get("h24", 0) or 0)
                    sentiment["mentions"][term] = {
                        "price_change": chg_24h,
                        "volume": vol,
                        "mood": "bullish" if chg_24h > 5 else "bearish" if chg_24h < -5 else "neutral"
                    }
            except:
                pass
        
        # Determine overall sentiment
        bull_count = sum(1 for v in sentiment["mentions"].values() if v["mood"] == "bullish")
        bear_count = sum(1 for v in sentiment["mentions"].values() if v["mood"] == "bearish")
        
        if bull_count > bear_count:
            sentiment["overall"] = "bullish"
        elif bear_count > bull_count:
            sentiment["overall"] = "bearish"
        
        # Hot topics (top movers)
        hot = sorted(sentiment["mentions"].items(), key=lambda x: x[1]["price_change"], reverse=True)[:3]
        sentiment["hot_topics"] = [f"{k} ({v['price_change']:+.1f}%)" for k, v in hot]
        
        return sentiment
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

def save_sentiment(sentiment):
    with open("/tmp/sentiment_data.json", "w") as f:
        json.dump(sentiment, f, indent=2)

def main():
    print("[SENTIMENT ANALYZER] Agent started!")
    while True:
        try:
            sentiment = analyze_sentiment()
            save_sentiment(sentiment)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sentiment: {sentiment.get('overall', 'unknown').upper()}")
            if sentiment.get("hot_topics"):
                print(f"  🔥 Hot: {', '.join(sentiment['hot_topics'])}")
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(1800)  # 30 minutes

if __name__ == "__main__":
    main()
