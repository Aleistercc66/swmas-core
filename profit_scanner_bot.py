#!/usr/bin/env python3
"""
High-Profit Altcoin Scanner + Telegram Alert System
Runs every 30 minutes via cron
"""
import requests
import json
import sys
import os
from datetime import datetime

# Telegram config
TELEGRAM_BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
TELEGRAM_CHAT_ID = "158923136"  # Hardcoded for user G:A.C

BASE_URL = "https://api.dexscreener.com"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

class DexScreenerAPI:
    def __init__(self):
        self.session = requests.Session()
    
    def search_pairs(self, query, limit=10):
        url = f"{BASE_URL}/latest/dex/search"
        try:
            resp = self.session.get(url, params={"q": query}, timeout=15)
            return resp.json().get("pairs", [])[:limit]
        except:
            return []
    
    def get_boosted_tokens(self):
        url = f"{BASE_URL}/token-boosts/latest/v1"
        try:
            resp = self.session.get(url, timeout=15)
            return resp.json()
        except:
            return []
    
    def get_trending_metas(self):
        url = f"{BASE_URL}/metas/trending/v1"
        try:
            resp = self.session.get(url, timeout=15)
            return resp.json()
        except:
            return []

class ProfitAnalyzer:
    """AGGRESSIVE profit-focused analyzer"""
    
    MIN_LIQUIDITY_USD = 25000  # Lower for more opportunities
    MIN_VOLUME_24H = 5000
    MIN_CONFIDENCE = 55
    MAX_OPPORTUNITIES = 5
    
    def analyze_pair(self, pair):
        base_token = pair.get("baseToken", {})
        symbol = base_token.get("symbol", "UNKNOWN")
        
        # Fix: API returns strings, not numbers
        def safe_float(val):
            if val is None or val == "":
                return 0.0
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        
        def safe_int(val):
            if val is None or val == "":
                return 0
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0
        
        price_usd = safe_float(pair.get("priceUsd"))
        liq_data = pair.get("liquidity") or {}
        liq_usd = safe_float(liq_data.get("usd"))
        vol_data = pair.get("volume") or {}
        vol_24h = safe_float(vol_data.get("h24"))
        vol_6h = safe_float(vol_data.get("h6"))
        vol_1h = safe_float(vol_data.get("h1"))
        
        price_change = pair.get("priceChange") or {}
        chg_24h = safe_float(price_change.get("h24"))
        chg_6h = safe_float(price_change.get("h6"))
        chg_1h = safe_float(price_change.get("h1"))
        chg_5m = safe_float(price_change.get("m5"))
        
        txns_data = pair.get("txns") or {}
        txns_24h = txns_data.get("h24") or {}
        buys_24h = safe_int(txns_24h.get("buys"))
        sells_24h = safe_int(txns_24h.get("sells"))
        
        if liq_usd < self.MIN_LIQUIDITY_USD or vol_24h < self.MIN_VOLUME_24H:
            return None
        
        signals = []
        confidence = 0
        profit_potential = 0
        
        # TREND - Must be strong
        if chg_24h > 10:
            signals.append(f"🔥 24h EXPLOSION: +{chg_24h:.1f}%")
            confidence += 15
            profit_potential += chg_24h
        elif chg_24h > 5:
            signals.append(f"📈 24h Strong: +{chg_24h:.1f}%")
            confidence += 10
            profit_potential += chg_24h
        elif chg_24h > 3:
            signals.append(f"📊 24h Positive: +{chg_24h:.1f}%")
            confidence += 5
            profit_potential += chg_24h
        
        if chg_6h > 0 and chg_24h > 0:
            signals.append("⬆️ 6h/24h aligned")
            confidence += 10
        elif chg_6h > -2 and chg_24h > 5:
            signals.append("⬆️ 6h holding (uptrend)")
            confidence += 5
        
        if chg_1h > 0:
            signals.append("⚡ 1h momentum")
            confidence += 10
        elif chg_1h > -1 and chg_24h > 10:
            signals.append("⚡ 1h stable in uptrend")
            confidence += 5
        
        # VOLUME
        if vol_24h > liq_usd * 2:
            signals.append("💰 High volume (2x liquidity)")
            confidence += 15
        elif vol_24h > liq_usd:
            signals.append("💎 Healthy volume")
            confidence += 10
        
        # BUY PRESSURE
        if buys_24h > 0 and sells_24h > 0:
            ratio = buys_24h / sells_24h
            if ratio > 2:
                signals.append(f"🐋 Whale accumulation ({ratio:.1f}:1)")
                confidence += 15
            elif ratio > 1.3:
                signals.append(f"👥 Buy pressure ({ratio:.1f}:1)")
                confidence += 10
        
        # MICRO MOMENTUM
        if chg_5m > 3:
            signals.append(f"⚡ 5m spike: +{chg_5m:.1f}%")
            confidence += 10
        
        # PROFIT POTENTIAL CALCULATION
        if chg_24h > 30:
            profit_potential = 100  # 2x potential
        elif chg_24h > 15:
            profit_potential = 50   # 50% potential
        elif chg_24h > 5:
            profit_potential = 25   # 25% potential
        
        if len(signals) < 3 or confidence < 40:
            return None
        
        direction = "LONG"
        
        # ENTRY based on micro pullback
        entry = price_usd * 0.97 if chg_5m > 0 else price_usd * 0.95
        stop = price_usd * 0.80  # Wider stop for volatile plays
        tp1 = price_usd * 1.50   # 50%
        tp2 = price_usd * 2.00   # 100% 
        tp3 = price_usd * 3.00   # 200% (moonshot)
        
        rr = f"1:{(tp1-entry)/(entry-stop):.1f}"
        
        return {
            "asset": symbol,
            "direction": direction,
            "price": price_usd,
            "entry": entry,
            "stop": stop,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr": rr,
            "confidence": min(confidence, 100),
            "profit_potential": profit_potential,
            "signals": signals,
            "liq": liq_usd,
            "vol": vol_24h,
            "chg_24h": chg_24h,
            "url": pair.get("url", "")
        }

def format_alert(opp):
    lines = [
        f"🎯 *{opp['asset']} — {opp['direction']}*",
        "",
        f"💰 *Profit Potential: {opp['profit_potential']}%+*",
        "",
        f"📍 Entry: `${opp['entry']:.8f}`",
        f"🛑 Stop: `${opp['stop']:.8f}`",
        f"🎯 TP1 (50%): `${opp['tp1']:.8f}`",
        f"🚀 TP2 (100%): `${opp['tp2']:.8f}`",
        f"🌕 TP3 (200%): `${opp['tp3']:.8f}`",
        "",
        f"📊 R/R: {opp['rr']}",
        f"🎲 Confidence: {opp['confidence']}/100",
        "",
        "*Signals:*",
    ]
    for s in opp['signals']:
        lines.append(f"• {s}")
    
    lines.extend([
        "",
        f"💧 Liq: ${opp['liq']:,.0f} | Vol24h: ${opp['vol']:,.0f}",
        f"📈 24h: +{opp['chg_24h']:.1f}%",
        f"[DexScreener]({opp['url']})"
    ])
    
    return "\n".join(lines)

def send_telegram(message):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def scan_profit_opportunities():
    api = DexScreenerAPI()
    analyzer = ProfitAnalyzer()
    
    # Dynamic search — scan ALL hot sources, not just hardcoded tokens
    all_pairs = []
    seen_addresses = set()
    
    def add_pair(pair):
        """Add pair if not duplicate"""
        addr = pair.get("pairAddress", "")
        if addr and addr not in seen_addresses:
            seen_addresses.add(addr)
            all_pairs.append(pair)
    
    print("🔥 HIGH-PROFIT SCAN STARTED")
    
    # --- SOURCE 1: Solana pairs (widest net) ---
    try:
        resp = api.session.get(f"{BASE_URL}/latest/dex/search", params={"q": "solana"}, timeout=15)
        sol_pairs = resp.json().get("pairs", [])[:30]
        for p in sol_pairs:
            add_pair(p)
        print(f"  ✅ Solana pairs: {len(sol_pairs)}")
    except Exception as e:
        print(f"  ⚠️ Solana scan failed: {e}")
    
    # --- SOURCE 2: Boosted tokens (trending/hyped) ---
    try:
        boosted = api.get_boosted_tokens()
        if isinstance(boosted, list):
            # For each boosted token, search its pairs
            for b in boosted[:15]:
                token_addr = b.get("tokenAddress", "")
                if token_addr:
                    try:
                        resp = api.session.get(f"{BASE_URL}/latest/dex/search", params={"q": token_addr}, timeout=10)
                        bpairs = resp.json().get("pairs", [])[:2]
                        for p in bpairs:
                            add_pair(p)
                    except:
                        pass
            print(f"  ✅ Boosted tokens: {len(boosted)} checked")
    except Exception as e:
        print(f"  ⚠️ Boosted scan failed: {e}")
    
    # --- SOURCE 3: Trending metas ---
    try:
        trending = api.get_trending_metas()
        if isinstance(trending, list):
            for t in trending[:10]:
                meta = t.get("meta", "")
                if meta:
                    try:
                        resp = api.session.get(f"{BASE_URL}/latest/dex/search", params={"q": meta}, timeout=10)
                        tpairs = resp.json().get("pairs", [])[:2]
                        for p in tpairs:
                            add_pair(p)
                    except:
                        pass
            print(f"  ✅ Trending metas: {len(trending)} checked")
    except Exception as e:
        print(f"  ⚠️ Trending scan failed: {e}")
    
    # --- SOURCE 4: Keep the known tokens as fallback ---
    fallback_terms = ["SOL", "ETH", "PEPE", "BONK", "WIF", "JUP", "JTO", "PYTH", "FLOKI", "BOME"]
    for term in fallback_terms:
        try:
            pairs = api.search_pairs(term, limit=2)
            for p in pairs:
                add_pair(p)
        except:
            pass
    print(f"  ✅ Fallback terms checked")
    
    print(f"📊 TOTAL UNIQUE PAIRS TO ANALYZE: {len(all_pairs)}")
    
    # Analyze
    opps = []
    for pair in all_pairs:
        opp = analyzer.analyze_pair(pair)
        if opp:
            opps.append(opp)
    
    # Sort by profit potential
    opps.sort(key=lambda x: (x["profit_potential"] * 0.6 + x["confidence"] * 0.4), reverse=True)
    
    return opps[:analyzer.MAX_OPPORTUNITIES]

def main():
    print(f"[{datetime.now()}] Starting profit scan...")
    
    opps = scan_profit_opportunities()
    
    if not opps:
        msg = "🕵️ *Scan Complete*\n\nNo high-profit opportunities detected right now.\n\nMarket is quiet — waiting for the next move! ⏳"
        send_telegram(msg)
        print("No opportunities found")
        return
    
    # Send header
    header = f"🔥 *PROFIT ALERT — {datetime.now().strftime('%H:%M')}* 🔥\n\nFound {len(opps)} high-profit opportunities!\n"
    send_telegram(header)
    
    # Send each opportunity
    for i, opp in enumerate(opps, 1):
        alert = format_alert(opp)
        send_telegram(alert)
        print(f"Sent alert #{i}: {opp['asset']} ({opp['profit_potential']}% potential)")

if __name__ == "__main__":
    main()
