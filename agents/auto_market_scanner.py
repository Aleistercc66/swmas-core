#!/usr/bin/env python3
"""
Autonomous Market Scanner + Alert Bot
Runs every 15 minutes via cron
Sends Telegram alerts for high-confidence opportunities
"""
import requests, json, os, sys
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
TELEGRAM_CHAT_ID = "158923136"

def send_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def scan_market():
    print(f"🔍 Scanning at {datetime.now().strftime('%H:%M')}")
    
    # Get boosted tokens
    try:
        r = requests.get('https://api.dexscreener.com/token-boosts/top/v1', timeout=15)
        boosted = r.json() if r.status_code == 200 else []
    except:
        boosted = []
    
    alerts = []
    
    for b in boosted[:10]:
        addr = b.get('tokenAddress', '')
        if not addr:
            continue
        
        try:
            pr = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{addr}', timeout=10)
            if pr.status_code != 200:
                continue
            
            pdata = pr.json()
            pairs = pdata.get('pairs', [])
            if not pairs:
                continue
            
            p = pairs[0]
            symbol = p['baseToken']['symbol']
            liq = p.get('liquidity', {}).get('usd', 0)
            vol = p.get('volume', {}).get('h24', 0)
            ch24 = p.get('priceChange', {}).get('h24', 0) or 0
            ch1h = p.get('priceChange', {}).get('h1', 0) or 0
            ch5m = p.get('priceChange', {}).get('m5', 0) or 0
            mc = p.get('marketCap', 0) or p.get('fdv', 0) or 0
            buys = p.get('txns', {}).get('h24', {}).get('buys', 0) or 0
            sells = p.get('txns', {}).get('h24', {}).get('sells', 0) or 0
            
            ratio = buys / max(sells, 1)
            
            # Alert criteria:
            # - MC < $300K (micro-cap)
            # - Liq > $5K
            # - Vol > $10K
            # - 24h change > 50%
            # - 1h change > 10% (momentum)
            # - Buy/Sell ratio > 1.2x
            # - 5m change > 0% (not dumping right now)
            
            if (mc < 300000 and liq > 5000 and vol > 10000 and 
                ch24 > 50 and ch1h > 10 and ratio > 1.2 and ch5m > -5):
                
                score = (ch24 * 0.3) + (ch1h * 0.4) + (ch5m * 0.3) + (ratio * 10)
                
                alert = f"""🔥 **HIGH-CONFIDENCE GEM ALERT** 🔥

💎 **{symbol}** | Score: {score:.1f}/100
📊 MC: ${mc:,.0f} | Liq: ${liq:,.0f} | Vol: ${vol:,.0f}
📈 24h: {ch24:+.1f}% | 1h: {ch1h:+.1f}% | 5m: {ch5m:+.1f}%
🛒 Buy/Sell: {ratio:.1f}x | Buys: {buys:,}

📍 https://dexscreener.com/solana/{addr}
⚠️ DYOR — Micro-cap = high risk!
"""
                alerts.append(alert)
                
        except Exception as e:
            print(f"Error scanning {addr}: {e}")
            continue
    
    # Send alerts
    for alert in alerts:
        send_alert(alert)
        print(f"Alert sent: {alert[:100]}...")
    
    if not alerts:
        print("No high-confidence gems found this scan.")
    
    return len(alerts)

if __name__ == "__main__":
    count = scan_market()
    print(f"Scan complete. {count} alerts sent.")
