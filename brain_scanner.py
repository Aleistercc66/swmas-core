#!/usr/bin/env python3
"""
🧠 BRAIN EXECUTOR — Automated DexScreener Scan + Alert
Runs every 30 minutes via cron.
This is the "hands" — the brain (AI agent) sets the strategy.
"""
import requests
import json
import os
from datetime import datetime

# Telegram config
BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Strategy parameters (set by the brain)
MIN_LIQUIDITY_USD = 20000
MIN_VOLUME_24H = 5000
MIN_CONFIDENCE = 60
MAX_OPPORTUNITIES = 3

# Hot search terms
SEARCH_TERMS = ["SOL", "ETH", "PEPE", "BONK", "WIF", "DOGE", "SHIB", "TRUMP", "USA", "AI", "FLOKI"]

def tg_send(msg):
    """Send Telegram message"""
    try:
        print(f"[TELEGRAM] Sending message ({len(msg)} chars)...")
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10,
        )
        print(f"[TELEGRAM] Response: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        print(f"[TELEGRAM] Error: {e}")

def fetch_dexscreener():
    """Collect raw market data from DexScreener"""
    all_pairs = []
    
    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": term},
                timeout=15
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:3]
            all_pairs.extend(pairs)
        except:
            pass
    
    return all_pairs

def parse_value(val):
    """Safely parse string/number values"""
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except:
        return 0.0

def analyze_pair(pair):
    """
    Brain-powered analysis (simplified for automation)
    Returns (score, reasons) or (0, []) if rejected
    """
    base = pair.get("baseToken", {})
    symbol = base.get("symbol", "UNKNOWN")
    
    price = parse_value(pair.get("priceUsd"))
    liq = parse_value((pair.get("liquidity") or {}).get("usd"))
    vol = parse_value((pair.get("volume") or {}).get("h24"))
    
    pc = pair.get("priceChange") or {}
    chg_24h = parse_value(pc.get("h24"))
    chg_1h = parse_value(pc.get("h1"))
    chg_5m = parse_value(pc.get("m5"))
    
    txns = pair.get("txns") or {}
    t24 = txns.get("h24") or {}
    buys = parse_value(t24.get("buys"))
    sells = parse_value(t24.get("sells"))
    
    # --- HARD FILTERS ---
    if liq < MIN_LIQUIDITY_USD:
        return 0, []
    if vol < MIN_VOLUME_24H:
        return 0, []
    if chg_24h < 2:
        return 0, []
    
    score = 0
    reasons = []
    
    # 1. Trend strength
    if chg_24h > 20:
        score += 30
        reasons.append(f"🔥 +{chg_24h:.0f}% in 24h")
    elif chg_24h > 10:
        score += 20
        reasons.append(f"📈 +{chg_24h:.0f}% in 24h")
    elif chg_24h > 5:
        score += 10
        reasons.append(f"📊 +{chg_24h:.0f}% in 24h")
    
    # 2. Current momentum
    if chg_1h > 0:
        score += 15
        reasons.append("⬆️ climbing now")
    elif chg_1h > -1:
        score += 5
        reasons.append("⏸️ holding steady")
    
    if chg_5m > 0:
        score += 5
        reasons.append("⚡ little push")
    
    # 3. Volume backing
    if vol > liq:
        score += 20
        reasons.append("💰 volume > liquidity (hot)")
    elif vol > liq * 0.5:
        score += 10
        reasons.append("💎 good volume")
    
    # 4. Buy pressure
    if buys > 0 and sells > 0:
        ratio = buys / sells
        if ratio > 1.5:
            score += 20
            reasons.append(f"🐋 more buyers ({ratio:.1f}x)")
        elif ratio > 1.1:
            score += 10
            reasons.append(f"👥 buyers winning ({ratio:.1f}x)")
    
    return min(score, 100), reasons

def scan():
    """Full market scan"""
    pairs = fetch_dexscreener()
    results = []
    seen = set()
    
    for pair in pairs:
        addr = pair.get("pairAddress", "")
        if addr in seen:
            continue
        seen.add(addr)
        
        score, reasons = analyze_pair(pair)
        if score >= MIN_CONFIDENCE and reasons:
            pair["_score"] = score
            pair["_reasons"] = reasons
            results.append(pair)
    
    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:MAX_OPPORTUNITIES]

def build_alert(pair):
    """Build alert message"""
    base = pair.get("baseToken", {})
    sym = base.get("symbol", "???")
    price = parse_value(pair.get("priceUsd"))
    chg_24h = parse_value((pair.get("priceChange") or {}).get("h24"))
    vol = parse_value((pair.get("volume") or {}).get("h24"))
    liq = parse_value((pair.get("liquidity") or {}).get("usd"))
    
    score = pair["_score"]
    reasons = pair["_reasons"]
    
    entry = price * 0.97
    stop = price * 0.80
    tp1 = price * 1.50
    tp2 = price * 2.00
    tp3 = price * 3.00
    
    msg = f"""🎯 *{sym} — LONG SETUP*

📍 Entry: `${entry:.8f}`
🛑 Stop: `${stop:.8f}`
🎯 TP1 (+50%): `${tp1:.8f}`
🚀 TP2 (+100%): `${tp2:.8f}`
🌕 TP3 (+200%): `${tp3:.8f}`

🎲 Confidence: {score}/100
📈 24h: +{chg_24h:.1f}%
💧 Liquidity: ${liq:,.0f}
💰 Volume: ${vol:,.0f}

*Why this setup:*
"""
    for r in reasons:
        msg += f"• {r}\n"
    
    msg += f"\n[View on DexScreener]({pair.get('url', '')})"
    return msg

def run():
    """Main execution"""
    print("[BRAIN SCANNER] Starting scan...")
    opps = scan()
    print(f"[BRAIN SCANNER] Found {len(opps)} opportunities")
    
    if not opps:
        print("[BRAIN SCANNER] No opportunities - sending sleep alert")
        tg_send("🕵️ *Scan Complete*\n\nNo hot setups right now.\n\nMarket is sleeping... 😴\n\n_Next scan: 30 min_")
        return
    
    print(f"[BRAIN SCANNER] Sending {len(opps)} alerts")
    # Header
    tg_send(f"🔥 *{len(opps)} OPPORTUNITIES FOUND* 🔥\n\n_DexScreener automated scan — {len(opps)} hot setups detected!_")
    
    # Individual alerts
    for opp in opps:
        alert = build_alert(opp)
        tg_send(alert)

if __name__ == "__main__":
    run()
