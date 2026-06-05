#!/usr/bin/env python3
"""
⚡ REAL-TIME DEXSCREENER AGENT — Fixed Version
Uses CORRECT DexScreener API endpoints.
"""
import json
import time
import sys
import threading
from datetime import datetime
import urllib.request

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json

AGENTS_DIR = "/root/.openclaw/workspace/agents"
LOG_FILE = f"{AGENTS_DIR}/logs/realtime_dexscreener.log"

API_BASE = "https://api.dexscreener.com"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def api_get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"API error: {type(e).__name__}: {str(e)[:60]}")
        return None

def get_solana_pairs_fast():
    """CORRECT endpoint: /latest/dex/search?q=solana"""
    url = f"{API_BASE}/latest/dex/search?q=solana"
    return api_get(url)

def get_token_pairs(chain, token_address):
    """Get all pairs for a specific token"""
    url = f"{API_BASE}/token-pairs/v1/{chain}/{token_address}"
    return api_get(url)

def get_boosted_tokens():
    url = f"{API_BASE}/token-boosts/latest/v1"
    return api_get(url)

def get_token_batch(chain, addresses):
    """Get up to 30 tokens by address"""
    if len(addresses) > 30:
        addresses = addresses[:30]
    url = f"{API_BASE}/tokens/v1/{chain}/{','.join(addresses)}"
    return api_get(url)

def enrich_pair_data(pair):
    price = float(pair.get("priceUsd", 0) or 0)
    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
    vol24 = float(pair.get("volume", {}).get("h24", 0) or 0)
    
    chg5m = float(pair.get("priceChange", {}).get("m5", 0) or 0)
    chg1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
    chg6h = float(pair.get("priceChange", {}).get("h6", 0) or 0)
    chg24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
    
    txns = pair.get("txns", {})
    buys24 = txns.get("h24", {}).get("buys", 0)
    sells24 = txns.get("h24", {}).get("sells", 0)
    buy_ratio = buys24 / (sells24 or 1)
    
    momentum = (chg5m * 0.4) + (chg1h * 0.3) + (chg6h * 0.2) + (chg24h * 0.1)
    vol_liq_ratio = vol24 / liq if liq > 0 else 0
    
    return {
        "symbol": pair.get("baseToken", {}).get("symbol", "???"),
        "name": pair.get("baseToken", {}).get("name", ""),
        "address": pair.get("baseToken", {}).get("address", ""),
        "price": price,
        "liquidity": liq,
        "volume_24h": vol24,
        "change_5m": chg5m,
        "change_1h": chg1h,
        "change_6h": chg6h,
        "change_24h": chg24h,
        "buy_ratio": round(buy_ratio, 2),
        "momentum": round(momentum, 2),
        "vol_liq_ratio": round(vol_liq_ratio, 2),
        "dex": pair.get("dexId", "unknown"),
        "pair_address": pair.get("pairAddress", ""),
        "url": pair.get("url", ""),
        "timestamp": datetime.now().isoformat()
    }

def scan_all_solana():
    log("🔄 Running full Solana scan via API...")
    data = get_solana_pairs_fast()
    
    if not data or "pairs" not in data:
        log("❌ API returned no data")
        return []
    
    pairs = data["pairs"]
    log(f"📡 API returned {len(pairs)} pairs")
    
    enriched = [enrich_pair_data(p) for p in pairs if p]
    
    quality = [
        p for p in enriched
        if p["liquidity"] >= 25000
        and p["volume_24h"] >= 5000
    ]
    
    log(f"✅ {len(quality)} quality pairs after filtering")
    
    quality.sort(key=lambda x: x["momentum"], reverse=True)
    return quality

def run_fast_scanner():
    log("⚡ REAL-TIME DEXSCANNER starting...")
    log("Mode: API-first | Fixed endpoints")
    
    while True:
        try:
            start = time.time()
            
            pairs = scan_all_solana()
            
            if pairs:
                safe_write_json(f"{AGENTS_DIR}/tmp_state/realtime_scan.json", {
                    "timestamp": datetime.now().isoformat(),
                    "pair_count": len(pairs),
                    "top_20": pairs[:20],
                    "hot_5": pairs[:5],
                    "latency_ms": int((time.time() - start) * 1000)
                })
                
                for i, p in enumerate(pairs[:3], 1):
                    log(f"  {i}. {p['symbol']}: ${p['price']:.8f} | "
                        f"5m: {p['change_5m']:+.1f}% | 1h: {p['change_1h']:+.1f}% | "
                        f"Liq: ${p['liquidity']:,.0f} | Mom: {p['momentum']:.1f}")
            
            elapsed = time.time() - start
            log(f"⏱️ Scan took {elapsed:.1f}s")
            
            time.sleep(max(0, 30 - elapsed))
            
        except Exception as e:
            log(f"💥 Scanner error: {e}")
            time.sleep(10)

def run_hot_tracker():
    log("🔥 HOT PAIR TRACKER starting...")
    
    while True:
        try:
            data = get_solana_pairs_fast()
            if data and "pairs" in data:
                pairs = [enrich_pair_data(p) for p in data["pairs"] if p]
                pairs.sort(key=lambda x: abs(x["change_5m"]), reverse=True)
                
                hot_5 = pairs[:5]
                safe_write_json(f"{AGENTS_DIR}/tmp_state/hot_pairs.json", {
                    "timestamp": datetime.now().isoformat(),
                    "pairs": hot_5,
                    "scan_interval": 10
                })
                
                for p in hot_5:
                    log(f"🔥 {p['symbol']}: 5m={p['change_5m']:+.1f}% | "
                        f"1h={p['change_1h']:+.1f}% | v/l={p['vol_liq_ratio']:.1f}")
            
            time.sleep(10)
            
        except Exception as e:
            log(f"💥 Hot tracker error: {e}")
            time.sleep(5)

def main():
    log("═══════════════════════════════════════")
    log("⚡ REAL-TIME DEXSCREENER AGENT v2")
    log("Fixed API endpoints | No more 404s")
    log("═══════════════════════════════════════")
    
    scanner_thread = threading.Thread(target=run_fast_scanner, name="fast_scanner")
    tracker_thread = threading.Thread(target=run_hot_tracker, name="hot_tracker")
    
    scanner_thread.daemon = True
    tracker_thread.daemon = True
    
    scanner_thread.start()
    tracker_thread.start()
    
    log("✅ Both threads active")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Shutting down...")

if __name__ == "__main__":
    main()
