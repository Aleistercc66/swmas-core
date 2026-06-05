#!/usr/bin/env python3
"""
🎯 Simple & Fun DexScreener Profit Scanner
One file, one job, big wins.
"""
import requests
import json
import sys

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def tg(msg):
    """Send Telegram message. Simple."""
    try:
        requests.post(
            f"{API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10,
        )
    except:
        pass


def ds(endpoint):
    """Call DexScreener API."""
    try:
        r = requests.get(f"https://api.dexscreener.com{endpoint}", timeout=15)
        return r.json()
    except:
        return None


def score(pair):
    """
    Simple scoring: Green across the board = good.
    Returns (score 0-100, reason list)
    """
    # Pull numbers safely
    def f(x):
        return float(x) if x else 0.0

    def i(x):
        return int(float(x)) if x else 0

    pc = pair.get("priceChange") or {}
    chg_24h = f(pc.get("h24"))
    chg_1h = f(pc.get("h1"))
    chg_5m = f(pc.get("m5"))

    vol = pair.get("volume") or {}
    vol_24h = f(vol.get("h24"))

    liq = pair.get("liquidity") or {}
    liq_usd = f(liq.get("usd"))

    txns = pair.get("txns") or {}
    t24 = txns.get("h24") or {}
    buys = i(t24.get("buys"))
    sells = i(t24.get("sells"))

    # --- FILTERS (hard rejects) ---
    if liq_usd < 20_000:
        return 0, []
    if vol_24h < 3_000:
        return 0, []
    if chg_24h < 2:
        return 0, []

    score = 0
    reasons = []

    # 1. Price looking good?
    if chg_24h > 20:
        score += 30
        reasons.append(f"🔥 +{chg_24h:.0f}% in 24h")
    elif chg_24h > 10:
        score += 20
        reasons.append(f"📈 +{chg_24h:.0f}% in 24h")
    elif chg_24h > 5:
        score += 10
        reasons.append(f"📊 +{chg_24h:.0f}% in 24h")

    # 2. Still climbing?
    if chg_1h > 0:
        score += 15
        reasons.append("⬆️ climbing now")
    elif chg_1h > -1:
        score += 5
        reasons.append("⏸️ holding steady")

    if chg_5m > 0:
        score += 5
        reasons.append("⚡ little push")

    # 3. Volume backing it?
    if vol_24h > liq_usd:
        score += 20
        reasons.append("💰 volume > liquidity (hot)")
    elif vol_24h > liq_usd * 0.5:
        score += 10
        reasons.append("💎 good volume")

    # 4. Buyers > sellers?
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
    """
    Main scan. Look at boosted + search a few hot terms.
    Return top 3 opportunities.
    """
    all_pairs = []

    # --- SOURCE 1: Solana pairs (widest net, ANY token) ---
    try:
        data = ds("/latest/dex/search?q=solana")
        if data and "pairs" in data:
            all_pairs.extend(data["pairs"][:25])  # Top 25 Solana pairs
    except:
        pass
    
    # --- SOURCE 2: Boosted tokens (trending/hyped) ---
    try:
        boosted = ds("/token-boosts/latest/v1") or []
        if isinstance(boosted, list):
            for b in boosted[:15]:
                token_addr = b.get("tokenAddress", "")
                if token_addr:
                    try:
                        bdata = ds(f"/latest/dex/search?q={token_addr}")
                        if bdata and "pairs" in bdata:
                            all_pairs.extend(bdata["pairs"][:2])
                    except:
                        pass
    except:
        pass
    
    # --- SOURCE 3: Fallback known terms ---
    fallback = ["SOL", "ETH", "PEPE", "BONK", "WIF", "DOGE", "FLOKI", "JUP", "BOME"]
    for term in fallback:
        try:
            data = ds(f"/latest/dex/search?q={term}")
            if data and "pairs" in data:
                all_pairs.extend(data["pairs"][:2])
        except:
            pass

    # Score everything
    results = []
    seen = set()
    for pair in all_pairs:
        addr = pair.get("pairAddress", "")
        if addr in seen:
            continue
        seen.add(addr)

        s, reasons = score(pair)
        if s >= 50 and reasons:  # Minimum 50/100 + at least one reason
            pair["_score"] = s
            pair["_reasons"] = reasons
            results.append(pair)

    # Sort by score descending
    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:3]


def alert(pair):
    """Build and send ONE alert."""
    base = pair.get("baseToken", {})
    sym = base.get("symbol", "???")
    name = base.get("name", sym)
    price = float((pair.get("priceUsd") or "0") or 0)
    chg_24h = float(((pair.get("priceChange") or {}).get("h24") or "0") or 0)
    vol = float(((pair.get("volume") or {}).get("h24") or "0") or 0)
    liq = float(((pair.get("liquidity") or {}).get("usd") or "0") or 0)

    score = pair["_score"]
    reasons = pair["_reasons"]

    # Levels
    entry = price * 0.97
    stop = price * 0.80
    tp1 = price * 1.50
    tp2 = price * 2.00
    tp3 = price * 3.00

    msg = f"""🎯 *{sym} — LONG*

📍 Entry: `${entry:.8f}`
🛑 Stop: `${stop:.8f}`
🎯 TP1 (+50%): `${tp1:.8f}`
🚀 TP2 (+100%): `${tp2:.8f}`
🌕 TP3 (+200%): `${tp3:.8f}`

🎲 Confidence: {score}/100
📈 24h: +{chg_24h:.1f}%
💧 Liquidity: ${liq:,.0f}
💰 Volume: ${vol:,.0f}

*Why:*
"""
    for r in reasons:
        msg += f"• {r}\n"

    msg += f"\n[DexScreener]({pair.get('url', '')})"

    tg(msg)


def run():
    """Full run: scan → alert."""
    opps = scan()

    if not opps:
        tg("🕵️ *Scan complete*\n\nNo hot setups right now.\n\nMarket sleeping... 😴\n\n_Next scan: 30 min_")
        return

    # Header
    tg(f"🔥 *{len(opps)} OPPORTUNITIES* 🔥\n\n_DexScreener scan — {len(opps)} hot setups found!_")

    # Each alert
    for p in opps:
        alert(p)


if __name__ == "__main__":
    run()
