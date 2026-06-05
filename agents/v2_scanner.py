#!/usr/bin/env python3
"""
🎯 AGENT 1: SCANNER — DYNAMIC TOKEN DISCOVERY
Scans ALL trending tokens, not just a static list.
Uses DexScreener boosted tokens + top movers.
"""
import requests
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json

# Fallback tokens only used if APIs fail
FALLBACK_TOKENS = ["SOL", "ETH", "BTC"]

def get_boosted_tokens():
    """Fetch latest boosted/trending tokens from DexScreener"""
    tokens = set()
    try:
        resp = requests.get("https://api.dexscreener.com/token-boosts/latest/v1", timeout=15)
        data = resp.json()
        for item in data:
            token = item.get("tokenAddress", "")
            if token:
                tokens.add(token)
    except Exception as e:
        print(f"  Boosted API error: {e}")
    return list(tokens)

def get_top_movers():
    """Fetch top volume/movers from DexScreener search"""
    tokens = set()
    try:
        # Search for top SOL movers
        resp = requests.get(
            "https://api.dexscreener.com/latest/dex/search",
            params={"q": "solana"}, timeout=15
        )
        data = resp.json()
        for p in data.get("pairs", [])[:15]:
            sym = p.get("baseToken", {}).get("symbol", "")
            if sym:
                tokens.add(sym)
    except Exception as e:
        print(f"  Top movers API error: {e}")
    return list(tokens)

def get_all_trending():
    """Combine multiple sources for maximum coverage"""
    all_tokens = set(FALLBACK_TOKENS)
    
    boosted = get_boosted_tokens()
    all_tokens.update(boosted)
    
    movers = get_top_movers()
    all_tokens.update(movers)
    
    # Add some known high-volume tokens for baseline coverage
    baseline = ["SOL", "ETH", "BTC", "JTO", "JUP", "RAY", "BONK", "WIF", "PEPE", "DOGE", "SHIB", "FLOKI"]
    all_tokens.update(baseline)
    
    print(f"  [DISCOVERY] Boosted: {len(boosted)}, Movers: {len(movers)}, Total unique: {len(all_tokens)}")
    return list(all_tokens)

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def scan_token(term):
    """Scan a single token and return valid pairs"""
    pairs = []
    try:
        resp = requests.get(
            "https://api.dexscreener.com/latest/dex/search",
            params={"q": term}, timeout=15
        )
        data = resp.json()
        for p in data.get("pairs", [])[:2]:
            base = p.get("baseToken", {})
            quote = p.get("quoteToken", {})
            sym = base.get("symbol", "???")
            chain = p.get("chainId", "???")
            price = parse_val(p.get("priceUsd"))
            liq = parse_val((p.get("liquidity") or {}).get("usd"))
            vol = parse_val((p.get("volume") or {}).get("h24"))
            vol6 = parse_val((p.get("volume") or {}).get("h6"))
            vol1 = parse_val((p.get("volume") or {}).get("h1"))
            vol5 = parse_val((p.get("volume") or {}).get("m5"))
            pc = p.get("priceChange") or {}
            chg24 = parse_val(pc.get("h24"))
            chg6 = parse_val(pc.get("h6"))
            chg1 = parse_val(pc.get("h1"))
            chg5 = parse_val(pc.get("m5"))
            txns = p.get("txns", {})
            t24 = txns.get("h24", {})
            buys24 = parse_val(t24.get("buys"))
            sells24 = parse_val(t24.get("sells"))
            t1 = txns.get("h1", {})
            buys1 = parse_val(t1.get("buys"))
            sells1 = parse_val(t1.get("sells"))
            fdv = parse_val(p.get("fdv"))
            mcap = parse_val(p.get("marketCap"))
            age_ms = p.get("pairCreatedAt", 0)
            age_h = (datetime.now().timestamp()*1000 - age_ms)/3600000 if age_ms else 999
            url = p.get("url", "")
            
            # STRICT FILTERS
            if liq < 20000: continue
            if vol < 5000: continue
            if chg24 < 5: continue
            
            # Late pump detection
            if chg24 > 50 and chg1 < -3: continue
            if chg24 > 200: continue
            
            pair_data = {
                "symbol": sym, "chain": chain, "price": price,
                "liquidity": liq, "volume_24h": vol, "volume_6h": vol6,
                "volume_1h": vol1, "volume_5m": vol5,
                "change_24h": chg24, "change_6h": chg6,
                "change_1h": chg1, "change_5m": chg5,
                "buys_24h": buys24, "sells_24h": sells24,
                "buys_1h": buys1, "sells_1h": sells1,
                "fdv": fdv, "market_cap": mcap,
                "age_hours": round(age_h, 1), "url": url,
                "timestamp": datetime.now().isoformat()
            }
            pairs.append(pair_data)
    except Exception as e:
        pass
    return pairs

def scan():
    """Dynamic scan — discovers tokens automatically"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Discovering tokens...")
    
    tokens = get_all_trending()
    all_pairs = []
    
    for term in tokens:
        pairs = scan_token(term)
        all_pairs.extend(pairs)
    
    # Deduplicate by symbol
    seen = set()
    unique_pairs = []
    for p in all_pairs:
        key = p["symbol"] + p["chain"]
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)
    
    # Sort by 24h change desc
    unique_pairs.sort(key=lambda x: x["change_24h"], reverse=True)
    return unique_pairs[:15]  # Return top 15 instead of 10

def main():
    print("[SCANNER] DYNAMIC DISCOVERY — All tokens, not just a list")
    while True:
        try:
            pairs = scan()
            output = {
                "timestamp": datetime.now().isoformat(),
                "count": len(pairs),
                "pairs": pairs
            }
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", output)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanned: {len(pairs)} candidates")
            for p in pairs[:5]:
                status = "BREAKOUT" if p["change_24h"] > 50 else "MOMENTUM" if p["change_24h"] > 20 else "ACCUMULATION"
                print(f"  → {p['symbol']}: ${p['price']:.8f} | 24h: +{p['change_24h']:.1f}% | 1h: {p['change_1h']:+.1f}% | Liq: ${p['liquidity']:,.0f} | {status}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
