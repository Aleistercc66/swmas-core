#!/usr/bin/env python3
"""
🤖 AUTO EXECUTOR — Automatic paper trade executor
When auto mode is ON, automatically opens positions on approved signals.
Prevents duplicate positions on same coin.
"""
import json
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

AGENTS_DIR = "/root/.openclaw/workspace/agents"
PAPER_TRADING = f"{AGENTS_DIR}/logs/paper_trading.json"
AUTO_MODE_FILE = f"{AGENTS_DIR}/tmp_state/auto_mode.json"
DYNAMIC_RISK = f"{AGENTS_DIR}/tmp_state/dynamic_risk_output.json"
LOG_FILE = f"{AGENTS_DIR}/logs/auto_executor.log"

TELEGRAM_BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
TELEGRAM_CHAT_ID = "158923136"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def send_telegram(message):
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        log(f"Telegram network error: {e}")
        time.sleep(5)
    except Exception as e:
        log(f"Telegram unexpected error: {e}")
        traceback.print_exc()

def format_price(price):
    if price == 0:
        return "$0.00"
    abs_price = abs(price)
    if abs_price < 0.00000001:
        return f"${price:.12f}"
    elif abs_price < 0.000001:
        return f"${price:.10f}"
    elif abs_price < 0.0001:
        return f"${price:.8f}"
    elif abs_price < 0.01:
        return f"${price:.6f}"
    elif abs_price < 1:
        return f"${price:.4f}"
    elif abs_price < 1000:
        return f"${price:.2f}"
    else:
        return f"${price:,.2f}"

def is_auto_mode():
    auto = safe_read_json(AUTO_MODE_FILE, {"enabled": False})
    return auto.get("enabled", False)

def get_auto_settings():
    return safe_read_json(AUTO_MODE_FILE, {
        "enabled": False,
        "max_daily_trades": 3,
        "position_size_pct": 5,
        "min_confidence": 60,
        "min_tier": "TIER_2"
    })

def has_open_position(symbol):
    """Check if we already have an open position on this coin"""
    pt = safe_read_json(PAPER_TRADING, {"positions": []})
    positions = pt.get("positions", [])
    return any(
        p.get("symbol") == symbol and p.get("status") == "OPEN"
        for p in positions
    )

def count_trades_today():
    """Count trades executed today"""
    pt = safe_read_json(PAPER_TRADING, {"history": []})
    history = pt.get("history", [])
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for h in history if h.get("timestamp", "").startswith(today))

def open_position(signal):
    """Open a paper trading position"""
    symbol = signal["symbol"]
    entry_price = signal["entry_zone"]["primary"]
    stop_price = signal["stop_loss"]
    tp1 = signal["take_profits"]["tp1_2x_risk"]
    tp2 = signal["take_profits"]["tp2_3x_risk"]
    tp3 = signal["take_profits"]["tp3_4x_risk"]
    
    settings = get_auto_settings()
    position_size_pct = settings.get("position_size_pct", 5)
    
    pt = safe_read_json(PAPER_TRADING, {
        "balance": 10000.0,
        "positions": [],
        "history": [],
        "total_fees_paid": 0,
        "total_slippage_cost": 0
    })
    
    balance = pt.get("balance", 10000)
    position_usdt = balance * (position_size_pct / 100)
    
    # Simulate slippage
    slippage_pct = 0.35
    fill_price = entry_price * (1 + slippage_pct / 100)
    fee = position_usdt * 0.003
    
    token_amount = (position_usdt - fee) / fill_price
    
    pos_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    position = {
        "id": pos_id,
        "symbol": symbol,
        "entry_price": fill_price,
        "base_price": entry_price,
        "stop_price": stop_price,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "position_usdt": position_usdt,
        "token_amount": token_amount,
        "status": "OPEN",
        "opened_at": datetime.now().isoformat(),
        "entry_fee": fee,
        "entry_slippage_pct": slippage_pct,
        "liquidity_at_entry": signal.get("liquidity", 0),
        "fill_rate": 1.0,
        "current_pnl": -fee,
        "tier": signal.get("tier", "TIER_3"),
        "confidence": signal.get("confidence", 0),
        "expected_return": signal.get("expected_return_pct", 0),
        "profit_potential": signal.get("profit_potential", 0)
    }
    
    pt["positions"].append(position)
    pt["total_fees_paid"] = pt.get("total_fees_paid", 0) + fee
    
    pt["history"].append({
        "id": pos_id,
        "symbol": symbol,
        "type": "OPEN",
        "price": fill_price,
        "amount": position_usdt,
        "fee": fee,
        "slippage": slippage_pct,
        "timestamp": datetime.now().isoformat()
    })
    
    safe_write_json(PAPER_TRADING, pt)
    
    log(f"OPENED: {symbol} @ {format_price(fill_price)} | Size: ${round(position_usdt, 2)} | Fee: ${round(fee, 2)}")
    
    alert = (
        f"🚀 *AUTO TRADE EXECUTED*\n"
        f"📈 {symbol}\n"
        f"Entry: {format_price(fill_price)}\n"
        f"Stop: {format_price(stop_price)}\n"
        f"TP1: {format_price(tp1)} | TP2: {format_price(tp2)} | TP3: {format_price(tp3)}\n"
        f"Size: ${round(position_usdt, 2)}\n"
        f"Tier: {signal.get('tier', '?')} | Conf: {signal.get('confidence', 0)}%\n"
        f"Expected Return: +{signal.get('expected_return_pct', 0)}%"
    )
    # Escape markdown special chars in prices
    alert = alert.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    # But restore our intentional markdown
    alert = alert.replace('\\_\\_\\_', '___').replace('\\_\\_', '__').replace('\\_', '_')
    alert = alert.replace('\\*\\*\\*', '***').replace('\\*\\*', '**').replace('\\*', '*')
    send_telegram(alert)
    
    return position

def check_and_execute():
    """Check for new signals and execute if auto mode on"""
    if not is_auto_mode():
        return
    
    settings = get_auto_settings()
    max_trades = settings.get("max_daily_trades", 3)
    min_confidence = settings.get("min_confidence", 60)
    min_tier = settings.get("min_tier", "TIER_2")
    
    # Check daily limit
    trades_today = count_trades_today()
    if trades_today >= max_trades:
        log(f"Daily trade limit reached: {trades_today}/{max_trades}")
        return
    
    # Read latest signals
    risk_data = safe_read_json(DYNAMIC_RISK, {})
    approved = risk_data.get("approved", [])
    
    if not approved:
        return
    
    log(f"Checking {len(approved)} approved signals...")
    
    # Sort by profit potential
    approved.sort(key=lambda x: x.get("profit_potential", 0), reverse=True)
    
    tier_rank = {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3}
    min_tier_rank = tier_rank.get(min_tier, 2)
    
    executed = 0
    
    for signal in approved:
        symbol = signal["symbol"]
        confidence = signal.get("confidence", 0)
        tier = signal.get("tier", "TIER_3")
        tier_r = tier_rank.get(tier, 3)
        
        # Skip if doesn't meet criteria
        if confidence < min_confidence:
            continue
        if tier_r > min_tier_rank:
            continue
        
        # Skip if already have position
        if has_open_position(symbol):
            log(f"SKIP: {symbol} — already have open position")
            continue
        
        # Execute!
        try:
            open_position(signal)
            executed += 1
            trades_today += 1
            
            if trades_today >= max_trades:
                log(f"Reached daily limit after {trades_today} trades")
                break
                
            time.sleep(2)  # Brief pause between executions
        except Exception as e:
            log(f"ERROR executing {symbol}: {e}")
    
    if executed == 0:
        log("No new trades executed (all filtered or already positioned)")
    else:
        log(f"Executed {executed} new trades")

def main():
    log("🤖 AUTO EXECUTOR starting...")
    log(f"Auto mode: {'ON' if is_auto_mode() else 'OFF'}")
    
    # Initial check
    check_and_execute()
    
    while True:
        try:
            time.sleep(30)  # Check every 30 seconds for new signals
            check_and_execute()
        except Exception as e:
            log(f"ERROR: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
