#!/usr/bin/env python3
"""
🎯 AGENT 1: SCANNER v3 — FIXED VERSION
Uses contract addresses for known tokens to avoid wrong-token issues.
Validates price ranges and liquidity.
"""
import requests
import json
import time
from datetime import datetime
import sys
import os

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json

BASELINE_FILE = "/root/.openclaw/workspace/agents/baseline_tokens.json"
API_BASE = "https://api.dexscreener.com"

FALLBACK_TOKENS = ["SOL", "ETH", "BTC"]

def load_baseline():
    """Load known token addresses"""
    try:
        with open(BASELINE_FILE) as f:
            return json.load(f).get("baseline", {})
    except:
        return {}

def api_get(url, timeout=15):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  API error: {type(e).__name__}: {str(e)[:40]}")
        return None

def get_token_by_address(chain, address):
    """Fetch exact token by contract address — NO confusion"""
    url = f"{API_BASE}/tokens/v1/{chain}/{address}"
    data = api_get(url)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]  # DexScreener returns list of pairs for this token
    return None

def get_boosted_tokens():
    tokens = set()
    try:
        resp = requests.get(f"{API_BASE}/token-boosts/latest/v1", timeout=15)
        data = resp.json()
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
        resp = requests.get(
            f"{API_BASE}/latest/dex/search",
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

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def validate_token(pair, baseline_info=None):
    """Validate that this is the REAL token, not an impostor"""
    price = parse_val(pair.get("priceUsd"))
    liq = parse_val((pair.get("liquidity") or {}).get("usd"))
    
    if baseline_info:
        min_price, max_price = baseline_info.get("expected_price_range", [0, float('inf')])
        min_liq = baseline_info.get("expected_liq_min", 0)
        
        if price < min_price or price > max_price:
            return False, f"Price ${price} outside expected range [{min_price}, {max_price}]"
        if liq < min_liq:
            return False, f"Liquidity ${liq:,.0f} below expected ${min_liq:,.0f}"
    
    return True, "OK"

def extract_pair_data(pair):
    """Extract standardized data from a DexScreener pair"""
    base = pair.get("baseToken", {})
    quote = pair.get("quoteToken", {})
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

def scan_baseline_tokens(baseline):
    """Scan known tokens by contract address for accuracy"""
    all_pairs = []
    
    for symbol, info in baseline.items():
        addresses = info.get("addresses", {})
        for chain, address in addresses.items():
            token_data = get_token_by_address(chain, address)
            if token_data and "pairs" in token_data:
                # Get the pair with highest liquidity
                best_pair = max(token_data["pairs"], 
                              key=lambda p: parse_val((p.get("liquidity") or {}).get("usd", 0)),
                              default=None)
                if best_pair:
                    is_valid, reason = validate_token(best_pair, info)
                    if is_valid:
                        all_pairs.append(extract_pair_data(best_pair))
                    else:
                        print(f"  ⚠️ {symbol}@{chain} rejected: {reason}")
    
    return all_pairs

def scan_by_symbol(term):
    """Fallback: scan by symbol (less accurate but catches new tokens)"""
    pairs = []
    try:
        resp = requests.get(
            f"{API_BASE}/latest/dex/search",
            params={"q": term}, timeout=15
        )
        data = resp.json()
        for p in data.get("pairs", [])[:2]:
            pair_data = extract_pair_data(p)
            
            # STRICT FILTERS
            if pair_data["liquidity"] < 20000: continue
            if pair_data["volume_24h"] < 5000: continue
            if pair_data["change_24h"] < 5: continue
            
            # Late pump detection
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
    
    baseline = ["SOL", "ETH", "BTC", "JTO", "JUP", "RAY", "BONK", "WIF", "PEPE", "DOGE", "SHIB", "FLOKI"]
    all_tokens.update(baseline)
    
    print(f"  [DISCOVERY] Boosted: {len(boosted)}, Movers: {len(movers)}, Total unique: {len(all_tokens)}")
    return list(all_tokens)

def scan():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Discovering tokens...")
    
    baseline = load_baseline()
    all_pairs = []
    
    # Phase 1: Scan known tokens by address (ACCURATE)
    if baseline:
        print(f"  [PHASE 1] Scanning {len(baseline)} baseline tokens by contract address...")
        baseline_pairs = scan_baseline_tokens(baseline)
        all_pairs.extend(baseline_pairs)
        print(f"  ✅ Baseline scan: {len(baseline_pairs)} valid pairs")
    
    # Phase 2: Discovery scan by symbol (CATCH NEW TOKENS)
    print(f"  [PHASE 2] Discovery scan for new tokens...")
    tokens = get_all_trending()
    for term in tokens:
        symbol_pairs = scan_by_symbol(term)
        all_pairs.extend(symbol_pairs)
    
    # Deduplicate by symbol+chain+address
    seen = {}
    unique_pairs = []
    for p in all_pairs:
        key = f"{p['symbol']}:{p['chain']}:{p['address'][:8]}"
        if key not in seen:
            seen[key] = True
            unique_pairs.append(p)
    
    # Sort by 24h change desc
    unique_pairs.sort(key=lambda x: x["change_24h"], reverse=True)
    return unique_pairs[:15]

def main():
    print("[SCANNER v3] FIXED — Contract addresses for known tokens + Symbol discovery for new ones")
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
                print(f"  → {p['symbol']}@{p['chain']}: ${p['price']:.8f} | 24h: +{p['change_24h']:.1f}% | 1h: {p['change_1h']:+.1f}% | Liq: ${p['liquidity']:,.0f} | {status} | Addr: {p['address'][:8]}...")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
