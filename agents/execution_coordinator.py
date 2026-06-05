#!/usr/bin/env python3
"""
🤖 AGENT 5: EXECUTION COORDINATOR
Job: Read all agent data, compile, send Telegram alerts
"""
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send(msg):
    """Send Telegram alert"""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10,
        )
    except:
        pass

def load_agent_data():
    """Load data from all agents"""
    data = {}
    
    # Market Scanner
    try:
        with open("/tmp/market_scanner_data.json", "r") as f:
            data["market"] = json.load(f)
    except:
        data["market"] = None
    
    # Sentiment Analyzer
    try:
        with open("/tmp/sentiment_data.json", "r") as f:
            data["sentiment"] = json.load(f)
    except:
        data["sentiment"] = None
    
    # Alpha Hunter
    try:
        with open("/tmp/alpha_hunter_data.json", "r") as f:
            data["alpha"] = json.load(f)
    except:
        data["alpha"] = None
    
    return data

def compile_opportunities(data):
    """Compile all opportunities into actionable alerts"""
    opps = []
    
    # From market scanner
    if data.get("market") and data["market"].get("pairs"):
        for p in data["market"]["pairs"]:
            try:
                chg_24h = float((p.get("priceChange") or {}).get("h24", 0) or 0)
                if chg_24h > 5:
                    opps.append({
                        "symbol": p.get("baseToken", {}).get("symbol", "???"),
                        "price": float(p.get("priceUsd", 0) or 0),
                        "change_24h": chg_24h,
                        "volume": float((p.get("volume") or {}).get("h24", 0) or 0),
                        "liquidity": float((p.get("liquidity") or {}).get("usd", 0) or 0),
                        "source": "market_scanner",
                        "url": p.get("url", "")
                    })
            except:
                pass
    
    # From alpha hunter
    if data.get("alpha") and data["alpha"].get("new_pairs"):
        for p in data["alpha"]["new_pairs"]:
            opps.append({
                "symbol": p.get("symbol", "???"),
                "price": p.get("price", 0),
                "change_24h": p.get("change_24h", 0),
                "volume": p.get("volume_24h", 0),
                "liquidity": p.get("liquidity", 0),
                "source": "alpha_hunter",
                "age_hours": p.get("age_hours", 0),
                "url": p.get("url", "")
            })
    
    # Sort by 24h change
    opps.sort(key=lambda x: x.get("change_24h", 0), reverse=True)
    return opps[:5]  # Top 5

def build_alert(opp):
    """Build detailed alert"""
    sym = opp.get("symbol", "???")
    price = opp.get("price", 0)
    chg = opp.get("change_24h", 0)
    vol = opp.get("volume", 0)
    liq = opp.get("liquidity", 0)
    
    entry = price * 0.98
    stop = price * 0.80
    tp1 = price * 1.50
    tp2 = price * 2.00
    
    emoji = "🚀" if chg > 50 else "📈" if chg > 20 else "📊"
    
    msg = f"""{emoji} *{sym} — {chg:+.1f}% in 24h*

📍 Entry: `${entry:.8f}`
🛑 Stop: `${stop:.8f}` (-20%)
🎯 TP1 (+50%): `${tp1:.8f}`
🌕 TP2 (+100%): `${tp2:.8f}`

💧 Liquidity: ${liq:,.0f}
💰 Volume 24h: ${vol:,.0f}
🔍 Source: {opp.get('source', 'unknown')}

[View on DexScreener]({opp.get('url', '')})
"""
    return msg

def main():
    print("[EXECUTION COORDINATOR] Agent started!")
    
    # Send startup message
    tg_send("🤖 *SWARM ACTIVATED*\n\nAll agents are now running:\n• Market Scanner (every 15min)\n• Sentiment Analyzer (every 30min)\n• Alpha Hunter (every 1h)\n• Risk Manager (on-demand)\n\n_Ready to hunt opportunities!_")
    
    while True:
        try:
            data = load_agent_data()
            opps = compile_opportunities(data)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Compiled {len(opps)} opportunities")
            
            if opps:
                # Send header
                tg_send(f"🔥 *{len(opps)} OPPORTUNITIES DETECTED* 🔥\n\n_Swarm intelligence compiled these setups:_")
                
                # Send each opportunity
                for opp in opps:
                    alert = build_alert(opp)
                    tg_send(alert)
                    time.sleep(1)  # Rate limit
            else:
                print("  No opportunities right now")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
