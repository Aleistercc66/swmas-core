#!/usr/bin/env python3
"""
📊 POSITION MONITOR — Real-time stop loss & take profit tracker
Monitors all open positions and auto-closes when SL/TP hit.
"""
import json
import time
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

AGENTS_DIR = "/root/.openclaw/workspace/agents"
PAPER_TRADING = f"{AGENTS_DIR}/logs/paper_trading.json"
LOG_FILE = f"{AGENTS_DIR}/logs/position_monitor.log"

TELEGRAM_BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
TELEGRAM_CHAT_ID = "158923136"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def send_telegram(message):
    """Send alert via Telegram"""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        log(f"Telegram network error: {e}")
        time.sleep(5)  # Wait before retry
    except Exception as e:
        log(f"Telegram unexpected error: {e}")
        traceback.print_exc()

def format_price(price):
    """Smart price formatting"""
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

def get_current_price(symbol):
    """Get current price from DexScreener"""
    try:
        import urllib.request
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            pairs = data.get("pairs", [])
            if pairs:
                return float(pairs[0].get("priceUsd", 0))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log(f"Price fetch network/parse error for {symbol}: {e}")
    except Exception as e:
        log(f"Price fetch unexpected error for {symbol}: {e}")
        traceback.print_exc()
    return None

def update_metrics(pt):
    """Calculate and update trading metrics"""
    history = pt.get("history", [])
    closed_trades = [h for h in history if h.get("type") == "CLOSE"]
    
    if not closed_trades:
        return
    
    wins = sum(1 for t in closed_trades if t.get("pnl", 0) > 0)
    losses = len(closed_trades) - wins
    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
    total_fees = pt.get("total_fees_paid", 0)
    
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0
    
    # Calculate average win/loss
    winning_trades = [t for t in closed_trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in closed_trades if t.get("pnl", 0) <= 0]
    
    avg_win = sum(t.get("pnl", 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.get("pnl", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Profit factor
    gross_profit = sum(max(0, t.get("pnl", 0)) for t in closed_trades)
    gross_loss = abs(sum(min(0, t.get("pnl", 0)) for t in closed_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    pt["metrics"] = {
        "total_trades": len(closed_trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "total_fees": round(total_fees, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "starting_balance": 10000.0,
        "current_balance": round(pt.get("balance", 10000), 2),
        "return_pct": round((pt.get("balance", 10000) - 10000) / 100 * 100, 2),
        "updated_at": datetime.now().isoformat()
    }

def check_positions():
    """Check all open positions for SL/TP hits"""
    pt = safe_read_json(PAPER_TRADING, {
        "balance": 10000.0,
        "positions": [],
        "history": [],
        "total_fees_paid": 0,
        "total_slippage_cost": 0
    })
    
    positions = pt.get("positions", [])
    if not positions:
        return
    
    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    if not open_positions:
        return
    
    log(f"Checking {len(open_positions)} open positions...")
    
    alerts_sent = []
    
    for pos in open_positions:
        symbol = pos["symbol"]
        current_price = get_current_price(symbol)
        if not current_price:
            continue
        
        entry_price = pos.get("entry_price", 0)
        stop_price = pos.get("stop_price", 0)
        tp1 = pos.get("tp1", 0)
        tp2 = pos.get("tp2", 0)
        tp3 = pos.get("tp3", 0)
        position_usdt = pos.get("position_usdt", 0)
        
        # Calculate current PnL
        price_change = (current_price - entry_price) / entry_price
        pnl = position_usdt * price_change
        
        pos["current_price"] = current_price
        pos["current_pnl"] = round(pnl, 2)
        pos["current_change_pct"] = round(price_change * 100, 2)
        pos["last_checked"] = datetime.now().isoformat()
        
        # Check stop loss
        if current_price <= stop_price:
            # CLOSE POSITION — STOP HIT
            slippage = abs((stop_price - current_price) / current_price) if current_price > 0 else 0
            exit_fee = position_usdt * 0.003
            total_pnl = position_usdt * ((stop_price - entry_price) / entry_price) - exit_fee
            
            pos["status"] = "CLOSED"
            pos["exit_price"] = current_price
            pos["exit_reason"] = "STOP_HIT"
            pos["pnl"] = round(total_pnl, 2)
            pos["exit_fee"] = round(exit_fee, 2)
            pos["exit_slippage"] = round(slippage * 100, 2)
            pos["closed_at"] = datetime.now().isoformat()
            
            pt["balance"] = pt.get("balance", 10000) + total_pnl
            pt["total_fees_paid"] = pt.get("total_fees_paid", 0) + exit_fee
            
            # Add to history
            pt["history"].append({
                "id": pos["id"],
                "symbol": symbol,
                "type": "CLOSE",
                "price": current_price,
                "pnl": round(total_pnl, 2),
                "reason": "STOP_HIT",
                "fee": round(exit_fee, 2),
                "timestamp": datetime.now().isoformat()
            })
            
            alert = (
                f"🛑 *STOP LOSS HIT*\n"
                f"📉 {symbol}\n"
                f"Entry: {format_price(entry_price)}\n"
                f"Stop: {format_price(stop_price)}\n"
                f"Exit: {format_price(current_price)}\n"
                f"💸 Loss: *${abs(round(total_pnl, 2))}*\n"
                f"Balance: ${round(pt['balance'], 2)}"
            )
            alerts_sent.append(alert)
            log(f"STOP HIT: {symbol} at {format_price(current_price)} | Loss: ${abs(round(total_pnl, 2))}")
            continue
        
        # Check take profits
        for tp_level, tp_price in [("TP1", tp1), ("TP2", tp2), ("TP3", tp3)]:
            if tp_price and current_price >= tp_price and tp_level not in pos.get("hit_tps", []):
                # Mark TP hit
                if "hit_tps" not in pos:
                    pos["hit_tps"] = []
                pos["hit_tps"].append(tp_level)
                
                alert = (
                    f"🎯 *{tp_level} HIT!*\n"
                    f"📈 {symbol}\n"
                    f"Entry: {format_price(entry_price)}\n"
                    f"{tp_level}: {format_price(tp_price)}\n"
                    f"Current: {format_price(current_price)}\n"
                    f"Change: *+{round(price_change * 100, 1)}%*\n"
                    f"Current PnL: *${round(pnl, 2)}*"
                )
                alerts_sent.append(alert)
                log(f"TP HIT: {symbol} {tp_level} at {format_price(current_price)}")
                
                # If TP3 hit, close full position
                if tp_level == "TP3":
                    exit_fee = position_usdt * 0.003
                    total_pnl = pnl - exit_fee
                    
                    pos["status"] = "CLOSED"
                    pos["exit_price"] = current_price
                    pos["exit_reason"] = "TP3_HIT"
                    pos["pnl"] = round(total_pnl, 2)
                    pos["exit_fee"] = round(exit_fee, 2)
                    pos["closed_at"] = datetime.now().isoformat()
                    
                    pt["balance"] = pt.get("balance", 10000) + total_pnl
                    pt["total_fees_paid"] = pt.get("total_fees_paid", 0) + exit_fee
                    
                    pt["history"].append({
                        "id": pos["id"],
                        "symbol": symbol,
                        "type": "CLOSE",
                        "price": current_price,
                        "pnl": round(total_pnl, 2),
                        "reason": "TP3_HIT",
                        "fee": round(exit_fee, 2),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    alert = (
                        f"🎉 *POSITION CLOSED — ALL TARGETS HIT!*\n"
                        f"📈 {symbol}\n"
                        f"Profit: *+${round(total_pnl, 2)}*\n"
                        f"Balance: ${round(pt['balance'], 2)}"
                    )
                    alerts_sent.append(alert)
                    log(f"CLOSED: {symbol} TP3 | Profit: ${round(total_pnl, 2)}")
    
    # Update metrics
    update_metrics(pt)
    
    # Save position status to separate file (NOT paper_trading to avoid race condition)
    position_status = {
        "timestamp": datetime.now().isoformat(),
        "balance": pt.get("balance", 10000),
        "open_positions": len(open_positions),
        "positions": [{"symbol": p["symbol"], "current_pnl": p.get("current_pnl", 0), "current_change_pct": p.get("current_change_pct", 0)} for p in open_positions],
        "metrics": pt.get("metrics", {}),
        "alerts_sent": len(alerts_sent)
    }
    safe_write_json(f"{AGENTS_DIR}/tmp_state/position_status.json", position_status)
    
    # Send alerts
    for alert in alerts_sent:
        send_telegram(alert)
        time.sleep(1)  # Rate limit

def print_portfolio_summary():
    """Print current portfolio status"""
    pt = safe_read_json(PAPER_TRADING, {})
    balance = pt.get("balance", 10000)
    positions = [p for p in pt.get("positions", []) if p.get("status") == "OPEN"]
    metrics = pt.get("metrics", {})
    
    log("═" * 50)
    log("📊 PORTFOLIO SUMMARY")
    log("═" * 50)
    log(f"Balance: ${round(balance, 2)} (from $10,000)")
    log(f"Open Positions: {len(positions)}")
    
    if metrics:
        log(f"Win Rate: {metrics.get('win_rate', 0)}%")
        log(f"Total PnL: ${metrics.get('total_pnl', 0)}")
        log(f"Profit Factor: {metrics.get('profit_factor', 0)}")
        log(f"Trades: {metrics.get('total_trades', 0)}")
    
    for pos in positions:
        sym = pos["symbol"]
        pnl = pos.get("current_pnl", 0)
        change = pos.get("current_change_pct", 0)
        emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        log(f"  {emoji} {sym}: ${round(pnl, 2)} ({round(change, 1)}%)")
    
    log("═" * 50)

def main():
    log("📊 POSITION MONITOR starting...")
    log("Checking stops/TPs every 60 seconds...")
    
    while True:
        try:
            check_positions()
            print_portfolio_summary()
            time.sleep(60)
        except Exception as e:
            log(f"ERROR: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
