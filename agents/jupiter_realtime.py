#!/usr/bin/env python3
"""
⚡ JUPITER REAL-TIME AGENT — No API Key Required!
Uses Jupiter Price API + DexScreener + Solana RPC
Free, fast, no registration needed.
"""
import json
import time
import sys
import threading
from datetime import datetime
import urllib.request
import urllib.parse

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json, safe_read_json

AGENTS_DIR = "/root/.openclaw/workspace/agents"
LOG_FILE = f"{AGENTS_DIR}/logs/jupiter_agent.log"

# Free APIs — NO KEY NEEDED
JUPITER_PRICE = "https://price.jup.ag/v6/price"
JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def api_get(url, timeout=10):
    """Generic API fetch — no auth needed"""
    try:
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"⚠️ API error: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# JUPITER PRICE API (FREE — NO KEY)
# ═══════════════════════════════════════════════════════════

def get_jupiter_prices(token_ids):
    """
    Get real-time prices from Jupiter — FREE, no key!
    token_ids: list of token addresses or symbols
    """
    ids_param = ",".join(token_ids)
    url = f"{JUPITER_PRICE}?ids={ids_param}"
    return api_get(url)

def get_jupiter_solana_tokens():
    """Get popular Solana token prices"""
    # Common Solana tokens (addresses)
    tokens = [
        "So11111111111111111111111111111111111111112",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
        "7iT9p9D2rDZTdPqHkZrH1jMQVL9pG7vH4xZhYqK8Z7",    # JUP
        "6p6xgHyF7AeE6TZkSmFiYK4T6z1x7Z1v9a7zF5q9j7",    # FLOKI (example)
    ]
    return get_jupiter_prices(tokens)

# ═══════════════════════════════════════════════════════════
# JUPITER QUOTE API — SWAP PRICES (FREE — NO KEY)
# ═══════════════════════════════════════════════════════════

def get_jupiter_quote(input_mint, output_mint, amount_lamports=1000000000):
    """
    Get swap quote — tells you how much you'd get for a trade
    Useful for detecting arbitrage and price impact
    """
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount_lamports),
        "slippageBps": "50"  # 0.5% slippage
    }
    url = f"{JUPITER_QUOTE}?{urllib.parse.urlencode(params)}"
    return api_get(url, timeout=15)

# ═══════════════════════════════════════════════════════════
# DEXSCREENER — ALREADY FREE, NO KEY
# ═══════════════════════════════════════════════════════════

def get_dexscreener_solana():
    """Get all Solana pairs from DexScreener"""
    url = f"{DEXSCREENER_API}/pairs/solana"
    return api_get(url)

def search_dexscreener(query):
    """Search for specific token"""
    url = f"{DEXSCREENER_API}/search?q={urllib.parse.quote(query)}"
    return api_get(url)

# ═══════════════════════════════════════════════════════════
# SOLANA RPC — DIRECT CHAIN ACCESS (FREE PUBLIC NODES)
# ═══════════════════════════════════════════════════════════

def solana_rpc_call(method, params=None):
    """Call Solana RPC directly — free public nodes"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or []
    }
    try:
        req = urllib.request.Request(
            SOLANA_RPC,
            data=json.dumps(payload).encode(),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log(f"⚠️ RPC error: {e}")
        return None

def get_solana_slot():
    """Get current blockchain slot"""
    result = solana_rpc_call("getSlot")
    return result.get("result") if result else None

# ═══════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════

def analyze_jupiter_opportunities():
    """
    Main opportunity detection — combines Jupiter + DexScreener
    """
    log("🔄 Scanning Jupiter + DexScreener...")
    
    # 1. Get DexScreener hot pairs (free, no key)
    dex_data = get_dexscreener_solana()
    
    if not dex_data or "pairs" not in dex_data:
        log("❌ DexScreener failed")
        return []
    
    pairs = dex_data["pairs"]
    log(f"📡 DexScreener: {len(pairs)} pairs")
    
    opportunities = []
    
    # Analyze top 30 by volume
    for pair in pairs[:30]:
        try:
            price = float(pair.get("priceUsd", 0) or 0)
            liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
            vol24 = float(pair.get("volume", {}).get("h24", 0) or 0)
            
            chg5m = float(pair.get("priceChange", {}).get("m5", 0) or 0)
            chg1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
            chg24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
            
            txns = pair.get("txns", {})
            buys24 = txns.get("h24", {}).get("buys", 0)
            sells24 = txns.get("h24", {}).get("sells", 0)
            
            # Skip if no data
            if price == 0 or liq == 0:
                continue
            
            # Calculate opportunity score
            momentum = (chg5m * 0.4) + (chg1h * 0.3) + (chg24h * 0.1)
            vol_liq_ratio = vol24 / liq if liq > 0 else 0
            buy_pressure = buys24 / (sells24 or 1)
            
            # Opportunity criteria
            if liq >= 25000 and vol24 >= 5000 and momentum > 5 and buy_pressure > 1.0:
                opp = {
                    "symbol": pair.get("baseToken", {}).get("symbol", "???"),
                    "name": pair.get("baseToken", {}).get("name", ""),
                    "address": pair.get("baseToken", {}).get("address", ""),
                    "price": price,
                    "liquidity": liq,
                    "volume_24h": vol24,
                    "change_5m": chg5m,
                    "change_1h": chg1h,
                    "change_24h": chg24h,
                    "buy_ratio": round(buy_pressure, 2),
                    "momentum": round(momentum, 2),
                    "vol_liq_ratio": round(vol_liq_ratio, 2),
                    "dex": pair.get("dexId", "unknown"),
                    "url": pair.get("url", ""),
                    "score": round(momentum * buy_pressure * min(vol_liq_ratio, 10), 1),
                    "timestamp": datetime.now().isoformat()
                }
                opportunities.append(opp)
        except Exception as e:
            continue
    
    # Sort by composite score
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    
    log(f"✅ Found {len(opportunities)} opportunities")
    
    return opportunities[:15]  # Top 15

# ═══════════════════════════════════════════════════════════
# MAIN LOOPS
# ═══════════════════════════════════════════════════════════

def run_opportunity_scanner():
    """Scan every 30 seconds for opportunities"""
    log("⚡ JUPITER AGENT starting (NO API KEY NEEDED)...")
    log("Sources: Jupiter Price API + DexScreener + Solana RPC")
    
    scan_count = 0
    while True:
        try:
            start = time.time()
            scan_count += 1
            
            # Scan opportunities
            opps = analyze_jupiter_opportunities()
            
            if opps:
                # Save state
                safe_write_json(f"{AGENTS_DIR}/tmp_state/jupiter_opportunities.json", {
                    "timestamp": datetime.now().isoformat(),
                    "scan_number": scan_count,
                    "opportunities": opps,
                    "latency_ms": int((time.time() - start) * 1000),
                    "sources": ["dexscreener", "jupiter_price_api"]
                })
                
                log(f"✅ Scan #{scan_count}: {len(opps)} opportunities")
                
                # Log top 5
                for i, opp in enumerate(opps[:5], 1):
                    log(f"  {i}. {opp['symbol']}: Score={opp['score']} | "
                        f"5m={opp['change_5m']:+.1f}% | 1h={opp['change_1h']:+.1f}% | "
                        f"Buy={opp['buy_ratio']:.1f}x | Liq=${opp['liquidity']:,.0f}")
            else:
                log(f"⚠️ Scan #{scan_count}: No opportunities")
            
            elapsed = time.time() - start
            log(f"⏱️ Scan took {elapsed:.1f}s")
            
            time.sleep(max(0, 30 - elapsed))
            
        except Exception as e:
            log(f"💥 Scanner error: {e}")
            time.sleep(10)

def run_price_tracker():
    """Track key token prices via Jupiter every 10 seconds"""
    log("📈 PRICE TRACKER starting...")
    
    # Popular tokens to track
    track_tokens = [
        "So11111111111111111111111111111111111111112",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
    ]
    
    while True:
        try:
            prices = get_jupiter_prices(track_tokens)
            
            if prices and "data" in prices:
                price_data = {
                    "timestamp": datetime.now().isoformat(),
                    "prices": {}
                }
                
                for token_id, info in prices["data"].items():
                    price_data["prices"][token_id] = {
                        "price": info.get("price"),
                        "vsToken": info.get("vsToken", "USDC")
                    }
                
                safe_write_json(f"{AGENTS_DIR}/tmp_state/jupiter_prices.json", price_data)
                
                # Log SOL price
                sol_data = prices["data"].get("So11111111111111111111111111111111111111112", {})
                if sol_data:
                    log(f"💎 SOL Price: ${sol_data.get('price', 0):.2f} USDC")
            
            time.sleep(10)
            
        except Exception as e:
            log(f"💥 Price tracker error: {e}")
            time.sleep(5)

def main():
    log("═══════════════════════════════════════")
    log("⚡ JUPITER REAL-TIME AGENT")
    log("100% FREE — NO API KEYS NEEDED")
    log("═══════════════════════════════════════")
    log("")
    log("Data Sources:")
    log("  • Jupiter Price API (free, no key)")
    log("  • Jupiter Quote API (free, no key)")
    log("  • DexScreener API (free, no key)")
    log("  • Solana RPC (free public nodes)")
    log("")
    log("Output:")
    log("  • tmp_state/jupiter_opportunities.json")
    log("  • tmp_state/jupiter_prices.json")
    log("")
    
    # Start scanner thread
    scanner_thread = threading.Thread(target=run_opportunity_scanner, name="jupiter_scanner")
    scanner_thread.daemon = True
    scanner_thread.start()
    
    # Start price tracker
    tracker_thread = threading.Thread(target=run_price_tracker, name="jupiter_tracker")
    tracker_thread.daemon = True
    tracker_thread.start()
    
    log("✅ Both threads active")
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Shutting down...")

if __name__ == "__main__":
    main()
