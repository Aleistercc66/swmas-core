#!/usr/bin/env python3
"""
🎯 SIGNAL GENERATOR — Reads scanner output, creates actionable signals
Ensures timestamps are fresh (< 30 min), generates entry/stop/TP levels.
"""
import json
import time
import sys
from datetime import datetime, timezone

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_write_json

SCANNER_FILE = "/root/.openclaw/workspace/agents/tmp_state/scanner_output.json"
ACTIVE_SIGNALS_FILE = "/root/.openclaw/workspace/agents/logs/active_signals.json"
MAX_AGE_MINUTES = 30

def parse_iso_ts(ts_str):
    """Parse ISO timestamp string to datetime"""
    try:
        # Handle both formats
        ts_str = ts_str.replace('Z', '+00:00')
        return datetime.fromisoformat(ts_str)
    except:
        return datetime.min.replace(tzinfo=timezone.utc)

def is_fresh(data, max_age=MAX_AGE_MINUTES):
    """Check if data is fresh enough"""
    ts = data.get("timestamp", "")
    if not ts:
        return False
    try:
        data_time = parse_iso_ts(ts)
        now = datetime.now(timezone.utc)
        if data_time.tzinfo is None:
            data_time = data_time.replace(tzinfo=timezone.utc)
        age = (now - data_time).total_seconds() / 60
        return age <= max_age
    except Exception as e:
        print(f"[SIGNAL GEN] Timestamp parse error: {e}")
        return False

def calculate_levels(price, direction="LONG", risk_pct=15):
    """Calculate entry, stop, and take-profit levels"""
    if direction == "LONG":
        entry_low = price * 0.98
        entry_high = price * 1.02
        stop = price * 0.85
        tp1 = price * 1.20
        tp2 = price * 1.35
        tp3 = price * 1.50
    else:
        entry_low = price * 0.98
        entry_high = price * 1.02
        stop = price * 1.15
        tp1 = price * 0.80
        tp2 = price * 0.70
        tp3 = price * 0.60
    
    return {
        "entry_low": round(entry_low, 10),
        "entry_high": round(entry_high, 10),
        "stop": round(stop, 10),
        "tp1": round(tp1, 10),
        "tp2": round(tp2, 10),
        "tp3": round(tp3, 10),
        "rr_ratio": f"1:{(tp1 - price) / (price - stop):.1f}" if direction == "LONG" else f"1:{(stop - price) / (price - tp1):.1f}"
    }

def determine_category(pair):
    """Determine signal category based on metrics"""
    chg24 = pair.get("change_24h", 0)
    chg1h = pair.get("change_1h", 0)
    liq = pair.get("liquidity", 0)
    
    if chg24 > 50 and chg1h > -5:
        return "BREAKOUT"
    elif chg24 > 20:
        return "MOMENTUM"
    elif chg24 > 5 and liq > 100000:
        return "ACCUMULATION"
    else:
        return "WATCH"

def determine_confidence(pair):
    """Calculate confidence score 0-100"""
    score = 0
    chg24 = pair.get("change_24h", 0)
    chg1h = pair.get("change_1h", 0)
    liq = pair.get("liquidity", 0)
    vol = pair.get("volume_24h", 0)
    buys = pair.get("buys_24h", 0)
    sells = pair.get("sells_24h", 0)
    
    # Trend score
    if chg24 > 50: score += 25
    elif chg24 > 20: score += 20
    elif chg24 > 10: score += 15
    elif chg24 > 5: score += 10
    
    # Hourly momentum
    if chg1h > 5: score += 15
    elif chg1h > 0: score += 10
    elif chg1h > -5: score += 5
    
    # Liquidity quality
    if liq > 500000: score += 20
    elif liq > 100000: score += 15
    elif liq > 50000: score += 10
    elif liq > 20000: score += 5
    
    # Volume confirmation
    if vol > 0 and liq > 0:
        turnover = vol / liq
        if turnover > 2: score += 15
        elif turnover > 1: score += 10
        elif turnover > 0.5: score += 5
    
    # Buy pressure
    if sells > 0:
        ratio = buys / sells
        if ratio > 2: score += 15
        elif ratio > 1.5: score += 10
        elif ratio > 1.2: score += 5
    
    return min(score, 100)

def determine_status(confidence, category, liq):
    """Determine signal status"""
    if confidence < 45:
        return "WATCH"
    if liq < 25000:
        return "HIGH_RISK"
    if category == "BREAKOUT" and confidence >= 65:
        return "ACTIVE"
    if category == "MOMENTUM" and confidence >= 60:
        return "ACTIVE"
    if category == "ACCUMULATION" and confidence >= 55:
        return "ACTIVE"
    return "WATCH"

def generate_signals():
    """Main function: read scanner output, generate signals"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎯 Signal Generator running...")
    
    # Read scanner output
    try:
        with open(SCANNER_FILE, 'r') as f:
            scanner_data = json.load(f)
    except Exception as e:
        print(f"[SIGNAL GEN] ❌ Cannot read scanner output: {e}")
        return None
    
    # Check freshness
    if not is_fresh(scanner_data):
        ts = scanner_data.get("timestamp", "unknown")
        print(f"[SIGNAL GEN] ⚠️ Scanner data stale (timestamp: {ts})")
        # Still process it but mark as stale
        stale = True
    else:
        stale = False
        print(f"[SIGNAL GEN] ✅ Fresh data from {scanner_data.get('timestamp')}")
    
    pairs = scanner_data.get("pairs", [])
    if not pairs:
        print("[SIGNAL GEN] ⚠️ No pairs found in scanner output")
        safe_write_json(ACTIVE_SIGNALS_FILE, {
            "generated_at": datetime.now().isoformat(),
            "stale": stale,
            "signals": [],
            "scanner_timestamp": scanner_data.get("timestamp", "unknown")
        })
        return []
    
    signals = []
    for i, pair in enumerate(pairs):
        symbol = pair.get("symbol", "???")
        price = pair.get("price", 0)
        chain = pair.get("chain", "unknown")
        
        category = determine_category(pair)
        confidence = determine_confidence(pair)
        status = determine_status(confidence, category, pair.get("liquidity", 0))
        
        levels = calculate_levels(price, "LONG")
        
        # Format prices nicely
        if price < 0.0001:
            price_str = f"{price:.10f}"
            entry_str = f"{levels['entry_low']:.10f} - {levels['entry_high']:.10f}"
            stop_str = f"{levels['stop']:.10f}"
            tp1_str = f"{levels['tp1']:.10f}"
            tp2_str = f"{levels['tp2']:.10f}"
            tp3_str = f"{levels['tp3']:.10f}"
        elif price < 0.01:
            price_str = f"{price:.6f}"
            entry_str = f"{levels['entry_low']:.6f} - {levels['entry_high']:.6f}"
            stop_str = f"{levels['stop']:.6f}"
            tp1_str = f"{levels['tp1']:.6f}"
            tp2_str = f"{levels['tp2']:.6f}"
            tp3_str = f"{levels['tp3']:.6f}"
        else:
            price_str = f"{price:.4f}"
            entry_str = f"{levels['entry_low']:.4f} - {levels['entry_high']:.4f}"
            stop_str = f"{levels['stop']:.4f}"
            tp1_str = f"{levels['tp1']:.4f}"
            tp2_str = f"{levels['tp2']:.4f}"
            tp3_str = f"{levels['tp3']:.4f}"
        
        signal = {
            "id": f"{symbol.lower()}-{chain[:3]}-{i+1:03d}",
            "token": symbol,
            "chain": chain,
            "price": price,
            "price_formatted": price_str,
            "direction": "LONG",
            "category": category,
            "confidence": confidence,
            "status": status,
            "change_24h": pair.get("change_24h", 0),
            "change_1h": pair.get("change_1h", 0),
            "liquidity": pair.get("liquidity", 0),
            "volume_24h": pair.get("volume_24h", 0),
            "entry": entry_str,
            "stop": stop_str,
            "tp1": tp1_str,
            "tp2": tp2_str,
            "tp3": tp3_str,
            "rr_ratio": levels["rr_ratio"],
            "url": pair.get("url", ""),
            "scanner_timestamp": scanner_data.get("timestamp", ""),
            "generated_at": datetime.now().isoformat(),
            "stale": stale
        }
        signals.append(signal)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "stale": stale,
        "scanner_timestamp": scanner_data.get("timestamp", "unknown"),
        "count": len(signals),
        "signals": signals
    }
    
    safe_write_json(ACTIVE_SIGNALS_FILE, output)
    
    print(f"[SIGNAL GEN] ✅ Generated {len(signals)} signals")
    for s in signals:
        emoji = "🔥" if s["status"] == "ACTIVE" else "⚠️" if s["status"] == "HIGH_RISK" else "👁️"
        print(f"  {emoji} {s['token']}: {s['price_formatted']} | 24h: {s['change_24h']:+.1f}% | Conf: {s['confidence']}/100 | {s['status']}")
    
    return signals

def main():
    print("="*60)
    print("🎯 SIGNAL GENERATOR — Live signal creation from scanner")
    print("="*60)
    print(f"Source: {SCANNER_FILE}")
    print(f"Output: {ACTIVE_SIGNALS_FILE}")
    print(f"Max age: {MAX_AGE_MINUTES} minutes")
    print()
    
    while True:
        try:
            generate_signals()
        except Exception as e:
            print(f"[SIGNAL GEN] 💥 Error: {e}")
        
        print(f"\n[SIGNAL GEN] Sleeping 60s...")
        time.sleep(60)

if __name__ == "__main__":
    main()
