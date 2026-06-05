#!/usr/bin/env python3
"""
🐋 AGENT 3: WHALE & LIQUIDITY MONITOR
Track liquidity health and whale accumulation patterns.
"""
import requests
import json
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

TERMS = ["PEPE", "WIF", "BONK", "SOL", "ETH", "DOGE", "SHIB", "FLOKI", "BOME"]

def parse_val(val):
    if val is None or val == "": return 0.0
    try: return float(val)
    except: return 0.0

def monitor():
    results = []
    
    for term in TERMS:
        try:
            resp = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={term}",
                timeout=10
            )
            data = resp.json()
            pairs = data.get("pairs", [])[:1]
            if not pairs:
                continue
            p = pairs[0]
            sym = p.get("baseToken", {}).get("symbol", "???")
            liq = parse_val((p.get("liquidity") or {}).get("usd"))
            vol = parse_val((p.get("volume") or {}).get("h24"))
            vol6 = parse_val((p.get("volume") or {}).get("h6"))
            chg24 = parse_val((p.get("priceChange") or {}).get("h24"))
            chg1 = parse_val((p.get("priceChange") or {}).get("h1"))
            txns = p.get("txns", {})
            t24 = txns.get("h24", {})
            buys = parse_val(t24.get("buys"))
            sells = parse_val(t24.get("sells"))
            
            # Liquidity health scoring
            liq_score = 0
            liq_health = "HEALTHY"
            
            if liq > 500000:
                liq_score = 90
            elif liq > 100000:
                liq_score = 70
            elif liq > 50000:
                liq_score = 50
            elif liq > 20000:
                liq_score = 30
            else:
                liq_score = 10
                liq_health = "RISKY"
            
            # Volume-to-liquidity ratio (activity intensity)
            vol_ratio = vol / liq if liq > 0 else 0
            if vol_ratio > 5:
                liq_health = "HOT" if liq > 50000 else "RISKY"
            
            # Whale accumulation proxy (buy/sell ratio)
            whale_signal = "NEUTRAL"
            if buys > 0 and sells > 0:
                ratio = buys / sells
                if ratio > 2.0:
                    whale_signal = "STRONG_ACCUMULATION"
                elif ratio > 1.5:
                    whale_signal = "ACCUMULATION"
                elif ratio > 1.2:
                    whale_signal = "SLIGHT_BUY"
                elif ratio < 0.8:
                    whale_signal = "DISTRIBUTION"
                elif ratio < 0.5:
                    whale_signal = "STRONG_DISTRIBUTION"
            
            # Liquidity declining detection (volume 6h vs 24h ratio)
            if vol6 > 0 and vol > 0:
                expected_6h = vol / 4
                if vol6 < expected_6h * 0.5:
                    liq_health = "DECLINING"
            
            results.append({
                "symbol": sym,
                "liquidity_usd": liq,
                "liquidity_score": liq_score,
                "liquidity_health": liq_health,
                "volume_liquidity_ratio": round(vol_ratio, 2),
                "whale_signal": whale_signal,
                "buy_sell_ratio": round(buys / sells, 2) if sells > 0 else 0,
                "price_change_24h": chg24,
                "price_change_1h": chg1,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
    
    return results

def main():
    print("[WHALE/LIQUIDITY] Agent started — Monitoring smart money")
    while True:
        try:
            report = monitor()
            output = {
                "timestamp": datetime.now().isoformat(),
                "tokens": report
            }
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/whale_output.json", output)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitored {len(report)} tokens")
            for r in report:
                emoji = "🐋" if "ACCUMULATION" in r["whale_signal"] else "⚠️" if "DISTRIBUTION" in r["whale_signal"] else "➖"
                print(f"  {emoji} {r['symbol']}: Liq=${r['liquidity_usd']:,.0f} ({r['liquidity_health']}) | Whale: {r['whale_signal']}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1800)  # 30 minutes

if __name__ == "__main__":
    main()
