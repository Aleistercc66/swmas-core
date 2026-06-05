#!/usr/bin/env python3
"""
🧪 PAPER TRADING ENGINE v2 — SWMAS
Simulates trades with REALISTIC price movement, tests strategy before live.
"""

import json, time, random
from datetime import datetime
from pathlib import Path

# Config
PAPER_WALLET = 10.0
TRADE_SIZE = 0.065
STOP_LOSS = 0.15
TAKE_PROFIT = 4.0
MIN_LIQUIDITY = 20000
MIN_FDV = 50000
MIN_VOLUME_24H = 25000

positions = []
trades_history = []
profits = []

MOCK_PAIRS = [
    {"symbol": "MOON/SOL", "price": 0.001, "volatility": 0.08, "liquidity": {"usd": 25000}, "fdv": 60000, "volume": {"h24": 30000}, "priceChange": {"h24": 15, "h6": 8, "h1": 3, "m5": 1}},
    {"symbol": "APE/SOL", "price": 0.002, "volatility": 0.12, "liquidity": {"usd": 30000}, "fdv": 75000, "volume": {"h24": 35000}, "priceChange": {"h24": 25, "h6": 12, "h1": 5, "m5": 2}},
    {"symbol": "RUG/SOL", "price": 0.0005, "volatility": 0.25, "liquidity": {"usd": 15000}, "fdv": 40000, "volume": {"h24": 20000}, "priceChange": {"h24": -50, "h6": -30, "h1": -10, "m5": -5}},
    {"symbol": "GEM/SOL", "price": 0.003, "volatility": 0.05, "liquidity": {"usd": 50000}, "fdv": 100000, "volume": {"h24": 50000}, "priceChange": {"h24": 50, "h6": 20, "h1": 8, "m5": 3}},
    {"symbol": "DOGE/SOL", "price": 0.0001, "volatility": 0.15, "liquidity": {"usd": 35000}, "fdv": 80000, "volume": {"h24": 40000}, "priceChange": {"h24": 30, "h6": 15, "h1": 7, "m5": 2}},
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_filters(pair):
    liq = pair.get("liquidity", {}).get("usd", 0)
    fdv = pair.get("fdv", 0)
    vol = pair.get("volume", {}).get("h24", 0)
    if liq < MIN_LIQUIDITY: return False, f"Liquidity ${liq:,.0f} < ${MIN_LIQUIDITY:,.0f}"
    if fdv < MIN_FDV: return False, f"FDV ${fdv:,.0f} < ${MIN_FDV:,.0f}"
    if vol < MIN_VOLUME_24H: return False, f"Volume ${vol:,.0f} < ${MIN_VOLUME_24H:,.0f}"
    return True, "PASS"

def calculate_momentum(pair):
    changes = pair.get("priceChange", {})
    score = (changes.get("h24", 0) * 0.3) + (changes.get("h6", 0) * 0.3) + (changes.get("h1", 0) * 0.2) + (changes.get("m5", 0) * 0.2)
    return min(100, max(0, score + 50))

def simulate_price_movement(entry_price, volatility):
    change = random.gauss(0.002, volatility)
    return entry_price * (1 + change)

def simulate_buy(pair):
    global PAPER_WALLET
    if PAPER_WALLET < TRADE_SIZE + 0.01: return None, "Insufficient paper SOL"
    entry_price = pair["price"]
    tokens = TRADE_SIZE / entry_price
    position = {
        "id": f"paper_{len(trades_history)}", "symbol": pair["symbol"], "entry": entry_price,
        "current_price": entry_price, "tokens": tokens, "size": TRADE_SIZE,
        "stop_loss": entry_price * (1 - STOP_LOSS), "take_profit": entry_price * (1 + TAKE_PROFIT),
        "entry_time": datetime.now().isoformat(), "status": "OPEN", "volatility": pair["volatility"],
    }
    PAPER_WALLET -= TRADE_SIZE
    positions.append(position)
    trades_history.append(position)
    return position, None

def simulate_sell(position, current_price, reason):
    global PAPER_WALLET
    value = position["tokens"] * current_price
    profit = value - position["size"]
    profit_pct = (profit / position["size"]) * 100
    PAPER_WALLET += value
    position["exit"] = current_price
    position["exit_time"] = datetime.now().isoformat()
    position["profit"] = profit
    position["profit_pct"] = profit_pct
    position["status"] = "CLOSED"
    position["exit_reason"] = reason
    profits.append(profit_pct)
    return profit, profit_pct

def check_positions():
    closed = []
    for pos in positions[:]:
        if pos["status"] != "OPEN": continue
        pos["current_price"] = simulate_price_movement(pos["current_price"], pos["volatility"])
        current_price = pos["current_price"]
        if current_price <= pos["stop_loss"]:
            profit, pct = simulate_sell(pos, current_price, "STOP_LOSS")
            closed.append({"symbol": pos["symbol"], "profit_pct": pct, "reason": "SL"})
            log(f"🛑 SL: {pos['symbol']} @ {pct:+.1f}% | Price: {current_price:.6f}")
        elif current_price >= pos["take_profit"]:
            profit, pct = simulate_sell(pos, current_price, "TAKE_PROFIT")
            closed.append({"symbol": pos["symbol"], "profit_pct": pct, "reason": "TP"})
            log(f"🎯 TP: {pos['symbol']} @ {pct:+.1f}% | Price: {current_price:.6f}")
    return closed

def paper_trade_cycle():
    log("🧪 PAPER TRADING CYCLE START")
    log(f"💰 Paper wallet: {PAPER_WALLET:.3f} SOL")
    closed = check_positions()
    opportunities = []
    for pair in MOCK_PAIRS:
        passes, reason = check_filters(pair)
        if not passes: continue
        momentum = calculate_momentum(pair)
        if momentum < 60: continue
        opportunities.append({"pair": pair, "momentum": momentum})
    opportunities.sort(key=lambda x: x["momentum"], reverse=True)
    open_count = len([p for p in positions if p["status"] == "OPEN"])
    if opportunities and open_count < 4 and PAPER_WALLET >= TRADE_SIZE + 0.01:
        best = opportunities[0]
        pos, err = simulate_buy(best["pair"])
        if pos: log(f"🟢 BUY: {pos['symbol']} @ {pos['entry']:.6f} | Momentum: {best['momentum']:.0f}/100")
    open_positions = [p for p in positions if p["status"] == "OPEN"]
    closed_positions = [p for p in positions if p["status"] == "CLOSED"]
    log(f"📊 Open: {len(open_positions)} | Closed: {len(closed_positions)}")
    if profits:
        avg_profit = sum(profits) / len(profits)
        win_rate = len([p for p in profits if p > 0]) / len(profits) * 100
        log(f"📊 Avg: {avg_profit:+.1f}% | Win rate: {win_rate:.0f}%")
    log(f"💰 Paper wallet: {PAPER_WALLET:.3f} SOL")
    save_state()
    return len(closed) > 0 or len(opportunities) > 0

def save_state():
    state = {"wallet": PAPER_WALLET, "positions": positions, "trades": trades_history, "profits": profits, "timestamp": datetime.now().isoformat()}
    state_dir = Path("/root/.openclaw/workspace/paper_trading")
    state_dir.mkdir(exist_ok=True)
    with open(state_dir / "state.json", "w") as f: json.dump(state, f, indent=2, default=str)

def load_state():
    global PAPER_WALLET, positions, trades_history, profits
    state_file = Path("/root/.openclaw/workspace/paper_trading/state.json")
    if state_file.exists():
        with open(state_file) as f: state = json.load(f)
        PAPER_WALLET = state.get("wallet", PAPER_WALLET)
        positions = state.get("positions", [])
        trades_history = state.get("trades", [])
        profits = state.get("profits", [])
        log("📂 State loaded")

if __name__ == "__main__":
    load_state()
    for i in range(20):
        log(f"\n=== CYCLE {i+1}/20 ===")
        paper_trade_cycle()
        time.sleep(0.2)
    log("\n🏁 PAPER TRADING COMPLETE")
    log(f"Final wallet: {PAPER_WALLET:.3f} SOL")
    if profits:
        log(f"Total trades: {len(profits)}")
        log(f"Avg profit: {sum(profits)/len(profits):+.1f}%")
        log(f"Win rate: {len([p for p in profits if p > 0])/len(profits)*100:.0f}%")
        log(f"Best: {max(profits):+.1f}% | Worst: {min(profits):+.1f}%")
