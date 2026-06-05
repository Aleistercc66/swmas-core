#!/usr/bin/env python3
"""
⚡ MEVX REAL-TIME AGENT
Direct API integration with MevX.io for live Solana data
Faster than DexScreener, more reliable, native execution-ready
"""
import json
import time
import sys
import threading
from datetime import datetime
import urllib.request
import urllib.error

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json, safe_read_json

AGENTS_DIR = "/root/.openclaw/workspace/agents"
LOG_FILE = f"{AGENTS_DIR}/logs/mevx_agent.log"

# MevX API Configuration
MEVX_BASE_URL = "https://api.mevx.io/api/v1"
MEVX_API_KEY = None  # Will be loaded from config

# Load API key from config if available
mevx_config = safe_read_json(f"{AGENTS_DIR}/tmp_state/mevx_config.json", {})
if mevx_config.get("api_key"):
    MEVX_API_KEY = mevx_config["api_key"]

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def mevx_request(endpoint, params=None, method="GET"):
    """Make authenticated request to MevX API"""
    if not MEVX_API_KEY:
        log("❌ No MEVX API key configured")
        return None
    
    url = f"{MEVX_BASE_URL}/{endpoint}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'X-API-KEY': MEVX_API_KEY,
                'Accept': 'application/json',
                'User-Agent': 'MevXAgent/1.0'
            },
            method=method
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
            
    except urllib.error.HTTPError as e:
        if e.code == 401:
            log("❌ Invalid MEVX API key")
        elif e.code == 429:
            log("⚠️ MEVX rate limit exceeded")
        else:
            log(f"❌ MEVX API error: {e.code}")
        return None
    except Exception as e:
        log(f"❌ Request failed: {e}")
        return None

def get_recent_trades(chain="sol", limit=50, pool_address=None):
    """Get recent trades from MevX"""
    params = {
        "chain": chain,
        "limit": min(limit, 100),
        "orderBy": "timestamp desc"
    }
    if pool_address:
        params["poolAddress"] = pool_address
    
    return mevx_request("trades", params)

def get_ohlcv(chain="sol", pool_address=None, timeframe="1m", limit=100):
    """Get OHLCV candlestick data"""
    params = {
        "chain": chain,
        "timeframe": timeframe,
        "limit": min(limit, 100)
    }
    if pool_address:
        params["poolAddress"] = pool_address
    
    return mevx_request("candlesticks", params)

def get_api_usage():
    """Check remaining API quota"""
    return mevx_request("usage")

def analyze_momentum_from_trades(trades_data):
    """Analyze trade momentum from MevX data"""
    if not trades_data or "data" not in trades_data:
        return None
    
    trades = trades_data["data"]
    if not trades:
        return None
    
    # Calculate metrics
    buy_volume = 0
    sell_volume = 0
    buy_count = 0
    sell_count = 0
    
    prices = []
    for trade in trades:
        price = float(trade.get("price", 0))
        amount = float(trade.get("amount", 0))
        side = trade.get("side", "").lower()
        
        prices.append(price)
        
        if side == "buy":
            buy_volume += amount * price
            buy_count += 1
        else:
            sell_volume += amount * price
            sell_count += 1
    
    if not prices:
        return None
    
    # Momentum indicators
    price_start = prices[-1]  # Most recent
    price_end = prices[0]     # Oldest
    price_change = ((price_start - price_end) / price_end * 100) if price_end > 0 else 0
    
    buy_pressure = buy_volume / (sell_volume or 1)
    
    return {
        "symbol": trades[0].get("tokenSymbol", "UNKNOWN"),
        "price_change_pct": round(price_change, 2),
        "buy_pressure": round(buy_pressure, 2),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "buy_volume_usd": round(buy_volume, 2),
        "sell_volume_usd": round(sell_volume, 2),
        "latest_price": price_start,
        "trade_count": len(trades),
        "timestamp": datetime.now().isoformat()
    }

def scan_hot_tokens():
    """Scan for hot tokens using MevX trade data"""
    log("🔥 Scanning hot tokens via MevX...")
    
    # Get recent Solana trades
    trades_data = get_recent_trades(chain="sol", limit=100)
    
    if not trades_data:
        log("❌ Failed to fetch trades")
        return []
    
    # Group by token
    token_trades = {}
    for trade in trades_data.get("data", []):
        token = trade.get("tokenSymbol", "UNKNOWN")
        if token not in token_trades:
            token_trades[token] = []
        token_trades[token].append(trade)
    
    # Analyze each token
    hot_tokens = []
    for token, trades in token_trades.items():
        if len(trades) < 5:  # Need minimum activity
            continue
        
        analysis = analyze_momentum_from_trades({"data": trades})
        if analysis and analysis["buy_pressure"] > 1.2:
            hot_tokens.append(analysis)
    
    # Sort by buy pressure
    hot_tokens.sort(key=lambda x: x["buy_pressure"], reverse=True)
    
    return hot_tokens[:10]

def run_mevx_scanner():
    """Main scanner loop"""
    log("⚡ MEVX REAL-TIME AGENT starting...")
    
    if not MEVX_API_KEY:
        log("❌ NO API KEY — Cannot start MevX scanner")
        log("   Get free API key at: https://landing-api.mevx.io/")
        log("   Save to: agents/tmp_state/mevx_config.json")
        return
    
    # Check API quota
    usage = get_api_usage()
    if usage:
        log(f"📊 API Quota: {usage}")
    
    scan_count = 0
    while True:
        try:
            start = time.time()
            scan_count += 1
            
            # Scan hot tokens
            hot = scan_hot_tokens()
            
            if hot:
                # Save state
                safe_write_json(f"{AGENTS_DIR}/tmp_state/mevx_hot_tokens.json", {
                    "timestamp": datetime.now().isoformat(),
                    "scan_number": scan_count,
                    "hot_tokens": hot,
                    "latency_ms": int((time.time() - start) * 1000)
                })
                
                log(f"✅ Scan #{scan_count}: {len(hot)} hot tokens found")
                
                # Log top 3
                for i, token in enumerate(hot[:3], 1):
                    log(f"  {i}. {token['symbol']}: "
                        f"BuyPressure={token['buy_pressure']:.1f}x | "
                        f"PriceChange={token['price_change_pct']:+.1f}% | "
                        f"Trades={token['trade_count']}")
            else:
                log(f"⚠️ Scan #{scan_count}: No hot tokens")
            
            elapsed = time.time() - start
            log(f"⏱️ Scan took {elapsed:.1f}s")
            
            # Sleep 30s between scans
            time.sleep(max(0, 30 - elapsed))
            
        except Exception as e:
            log(f"💥 Scanner error: {e}")
            time.sleep(10)

def run_ohlcv_tracker():
    """Track OHLCV for specific pools"""
    log("📈 OHLCV TRACKER starting...")
    
    # Load watchlist
    watchlist = safe_read_json(f"{AGENTS_DIR}/tmp_state/mevx_watchlist.json", {
        "pools": []  # List of pool addresses to track
    })
    
    while True:
        try:
            for pool in watchlist.get("pools", []):
                ohlcv = get_ohlcv(pool_address=pool, timeframe="5m", limit=20)
                if ohlcv:
                    safe_write_json(
                        f"{AGENTS_DIR}/tmp_state/mevx_ohlcv_{pool}.json",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "pool": pool,
                            "data": ohlcv
                        }
                    )
            
            time.sleep(60)  # Update every minute
            
        except Exception as e:
            log(f"💥 OHLCV error: {e}")
            time.sleep(10)

def main():
    log("═══════════════════════════════════════")
    log("⚡ MEVX REAL-TIME AGENT")
    log("API: https://api.mevx.io/api/v1")
    log("Free Tier: 1,000 CUs/month")
    log("═══════════════════════════════════════")
    
    if not MEVX_API_KEY:
        log("\n❌ NO API KEY CONFIGURED!")
        log("\n📝 To get started:")
        log("   1. Get free API key: https://landing-api.mevx.io/")
        log("   2. Create file: agents/tmp_state/mevx_config.json")
        log('   3. Content: {"api_key": "your-key-here"}')
        log("\n   The agent will auto-detect the key on restart.")
        return
    
    # Start scanner thread
    scanner_thread = threading.Thread(target=run_mevx_scanner, name="mevx_scanner")
    scanner_thread.daemon = True
    scanner_thread.start()
    
    # Start OHLCV tracker
    ohlcv_thread = threading.Thread(target=run_ohlcv_tracker, name="mevx_ohlcv")
    ohlcv_thread.daemon = True
    ohlcv_thread.start()
    
    log("✅ Both threads active")
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("🛑 Shutting down...")

if __name__ == "__main__":
    main()
