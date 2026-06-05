#!/usr/bin/env python3
"""
🎯 AGENT 1: SCANNER v3.1 — VALIDATED SYMBOL SEARCH
Searches by symbol, then validates price range & liquidity to pick the REAL token.
"""
import requests
import json
import time
from datetime import datetime
import sys

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json

API_BASE = "https://api.dexscreener.com"

# Known token validation rules
VALIDATION_RULES = {
    "SOL": {"min_price": 50, "max_price": 200, "min_liq": 100000},
    "ETH": {"min_price": 1000, "max_price": 10000, "min_liq": 500000},
    "BTC": {"min_price": 40000, "max_price": 200000, "min_liq": 1000000},
    "JUP": {"min_price": 0.1, "max_price": 10, "min_liq": 50000},
    "JTO": {"min_price": 0.5, "max_price": 20, "min_liq": 30000},
    "BONK": {"min_price": 0.000001, "max_price": 0.0001, "min_liq": 50000},
    "WIF": {"min_price": 0.1, "max_price": 10, "min_liq": 30000},
    "PEPE": {"min_price": 0.0000001, "max_price": 0.0001, "min_liq": 30000},
    "DOGE": {"min_price": 0.05, "max_price": 1, "min_liq": 50000},
    "SHIB": {"min_price": 0.000001, "max_price": 0.0001, "min_liq": 30000},
    "FLOKI": {"min_price": 0.00001, "max_price": 0.01, "min_liq": 30000},
    "XRP": {"min_price": 0.5, "max_price": 5, "min_liq": 100000},
    "ADA": {"min_price": 0.1, "max_price": 5, "min_liq": 50000},
    "TRUMP": {"min_price": 0.5, "max_price": 50, "min_liq": 50000},
    "LINK": {"min_price": 5, "max_price": 50, "min_liq": 50000},
}

FALLBACK_TOKENS = ["SOL", "ETH", "BTC"]

def api_get(url, params=None, timeout=15):
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  API error: {type(e).__name__}: {str(e)[:40]}")
        return None

def get_boosted_tokens():
    tokens = set()
    try:
        data = api_get(f"{API_BASE}/token-boosts/latest/v1")
        for item in data:
            token = item.get("tokenAddress", "")
            if token:
                tokens.add(token)
    except Exception as e:
        print(f"  Boosted API error: {e}")
    return list(tokens)

def get_top_movers():
    tokens = set()
    try:
        data = api_get(f"{API_BASE}/latest/dex/search", {"q": "solana"})
        for p in data.get("pairs", [])[:15]:
            sym = p.get("baseToken", {}).get("symbol", "")
            if sym:
                tokens.add(sym)
    except Exception as e:
        print(f"  Top movers API error: {e}")
    return list(tokens)

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def validate_pair(pair, symbol):
    """Validate that this pair matches the expected token"""
    price = parse_val(pair.get("priceUsd"))
    liq = parse_val((pair.get("liquidity") or {}).get("usd"))
    
    rules = VALIDATION_RULES.get(symbol.upper())
    if rules:
        if price < rules["min_price"] or price > rules["max_price"]:
            return False, f"price ${price} outside [{rules['min_price']}, {rules['max_price']}]"
        if liq < rules["min_liq"]:
            return False, f"liq ${liq:,.0f} < ${rules['min_liq']:,.0f}"
    
    return True, "OK"

def extract_pair_data(pair):
    base = pair.get("baseToken", {})
    sym = base.get("symbol", "???")
    chain = pair.get("chainId", "???")
    price = parse_val(pair.get("priceUsd"))
    liq = parse_val((pair.get("liquidity") or {}).get("usd"))
    vol = parse_val((pair.get("volume") or {}).get("h24"))
    vol6 = parse_val((pair.get("volume") or {}).get("h6"))
    vol1 = parse_val((pair.get("volume") or {}).get("h1"))
    vol5 = parse_val((pair.get("volume") or {}).get("m5"))
    pc = pair.get("priceChange") or {}
    chg24 = parse_val(pc.get("h24"))
    chg6 = parse_val(pc.get("h6"))
    chg1 = parse_val(pc.get("h1"))
    chg5 = parse_val(pc.get("m5"))
    txns = pair.get("txns", {})
    t24 = txns.get("h24", {})
    buys24 = parse_val(t24.get("buys"))
    sells24 = parse_val(t24.get("sells"))
    t1 = txns.get("h1", {})
    buys1 = parse_val(t1.get("buys"))
    sells1 = parse_val(t1.get("sells"))
    fdv = parse_val(pair.get("fdv"))
    mcap = parse_val(pair.get("marketCap"))
    age_ms = pair.get("pairCreatedAt", 0)
    age_h = (datetime.now().timestamp()*1000 - age_ms)/3600000 if age_ms else 999
    url = pair.get("url", "")
    
    return {
        "symbol": sym, "chain": chain, "price": price,
        "liquidity": liq, "volume_24h": vol, "volume_6h": vol6,
        "volume_1h": vol1, "volume_5m": vol5,
        "change_24h": chg24, "change_6h": chg6,
        "change_1h": chg1, "change_5m": chg5,
        "buys_24h": buys24, "sells_24h": sells24,
        "buys_1h": buys1, "sells_1h": sells1,
        "fdv": fdv, "market_cap": mcap,
        "age_hours": round(age_h, 1), "url": url,
        "timestamp": datetime.now().isoformat(),
        "address": base.get("address", "")
    }

def scan_token(term):
    """Scan a single token — search then validate, pick highest VOLUME pair"""
    pairs = []
    try:
        data = api_get(f"{API_BASE}/latest/dex/search", {"q": term})
        if not data or "pairs" not in data:
            return []
        
        raw_pairs = data["pairs"]
        
        # For known tokens: validate and pick the pair with highest VOLUME (not just liquidity)
        if term.upper() in VALIDATION_RULES:
            valid_pairs = []
            for p in raw_pairs:
                is_valid, reason = validate_pair(p, term)
                if is_valid:
                    valid_pairs.append(p)
            
            if valid_pairs:
                # Pick the pair with highest 24h volume (most active = most real)
                best = max(valid_pairs, key=lambda p: parse_val((p.get("volume") or {}).get("h24", 0)))
                pairs.append(extract_pair_data(best))
        else:
            # Unknown tokens: use strict filters
            for p in raw_pairs[:2]:
                pair_data = extract_pair_data(p)
                if pair_data["liquidity"] < 20000: continue
                if pair_data["volume_24h"] < 5000: continue
                if pair_data["change_24h"] < 5: continue
                if pair_data["change_24h"] > 50 and pair_data["change_1h"] < -3: continue
                if pair_data["change_24h"] > 200: continue
                pairs.append(pair_data)
    except Exception as e:
        pass
    return pairs

def get_all_trending():
    all_tokens = set(FALLBACK_TOKENS)
    
    boosted = get_boosted_tokens()
    all_tokens.update(boosted)
    
    movers = get_top_movers()
    all_tokens.update(movers)
    
    baseline = ["SOL", "ETH", "BTC", "JTO", "JUP", "RAY", "BONK", "WIF", "PEPE", "DOGE", "SHIB", "FLOKI", "XRP", "ADA", "TRUMP", "LINK"]
    all_tokens.update(baseline)
    
    print(f"  [DISCOVERY] Boosted: {len(boosted)}, Movers: {len(movers)}, Total unique: {len(all_tokens)}")
    return list(all_tokens)

def scan():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Discovering tokens...")
    
    tokens = get_all_trending()
    all_pairs = []
    
    # Phase 1: Known tokens (validated)
    known = [t for t in tokens if t.upper() in VALIDATION_RULES]
    if known:
        print(f"  [PHASE 1] Validating {len(known)} known tokens...")
        for term in known:
            pairs = scan_token(term)
            all_pairs.extend(pairs)
        print(f"  ✅ Known tokens: {len([p for p in all_pairs if p['symbol'].upper() in VALIDATION_RULES])} valid")
    
    # Phase 2: New/discovery tokens
    new = [t for t in tokens if t.upper() not in VALIDATION_RULES]
    if new:
        print(f"  [PHASE 2] Discovery scan: {len(new)} tokens...")
        for term in new:
            pairs = scan_token(term)
            all_pairs.extend(pairs)
    
    # Deduplicate
    seen = {}
    unique_pairs = []
    for p in all_pairs:
        key = f"{p['symbol']}:{p['chain']}:{p['address'][:8]}"
        if key not in seen:
            seen[key] = True
            unique_pairs.append(p)
    
    unique_pairs.sort(key=lambda x: x["change_24h"], reverse=True)
    return unique_pairs[:15]

def main():
    print("[SCANNER v3.1] VALIDATED — Price range checks for known tokens + Discovery for new ones")
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
                validated = "✅" if p["symbol"].upper() in VALIDATION_RULES else "?"
                print(f"  → {p['symbol']}@{p['chain']}: ${p['price']:.8f} | 24h: +{p['change_24h']:.1f}% | 1h: {p['change_1h']:+.1f}% | Liq: ${p['liquidity']:,.0f} | {status} {validated} | {p['address'][:8]}...")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
