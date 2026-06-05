#!/usr/bin/env python3
"""
🎯 REALISTIC BACKTESTING ENGINE
Critical fix: Paper trading was using unrealistic simulation.
Now uses real market constraints: spread, slippage, liquidity, fees, latency.
"""
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

PAPER_STATE = "/root/.openclaw/workspace/agents/logs/paper_trading.json"

def get_current_price(symbol):
    """Get current price from DexScreener with spread"""
    try:
        resp = requests.get(
            "https://api.dexscreener.com/latest/dex/search",
            params={"q": symbol},
            timeout=10
        )
        data = resp.json()
        for p in data.get("pairs", [])[:1]:
            price = float(p.get("priceUsd", 0))
            liquidity = float(p.get("liquidity", {}).get("usd", 0))
            volume24h = float(p.get("volume", {}).get("h24", 0))
            # Calculate spread from buy/sell ratio
            txns = p.get("txns", {}).get("h24", {})
            buys = txns.get("buys", 0)
            sells = txns.get("sells", 0)
            total = buys + sells
            buy_pressure = buys / total if total > 0 else 0.5
            # Spread: 0.5% base + up to 1% based on liquidity
            spread = 0.005 + max(0, (50000 - liquidity) / 50000 * 0.01)
            return {
                "price": price,
                "liquidity": liquidity,
                "volume24h": volume24h,
                "spread": spread,
                "buy_pressure": buy_pressure
            }
    except:
        pass
    return None

def simulate_realistic_entry(price_data, signal_size_usd):
    """
    Simulate realistic entry with:
    - Spread (bid-ask gap)
    - Slippage based on liquidity
    - Partial fill if position too large
    - Latency impact
    """
    base_price = price_data["price"]
    liquidity = price_data["liquidity"]
    spread = price_data["spread"]
    
    # 1. Spread: You buy at ask (higher), sell at bid (lower)
    # For long: entry = price * (1 + spread/2)
    entry_price = base_price * (1 + spread / 2)
    
    # 2. Slippage: Based on position size vs liquidity
    # If position > 1% of liquidity, significant slippage
    liquidity_ratio = signal_size_usd / liquidity if liquidity > 0 else 1
    slippage = min(0.05, liquidity_ratio * 0.02)  # Max 5% slippage
    
    entry_price *= (1 + slippage)
    
    # 3. Transaction fee (DEX swap fee ~0.3%)
    fee = signal_size_usd * 0.003
    
    # 4. Latency: Price moves during execution (1-5 seconds)
    # Simulate 0.1-0.5% adverse move
    latency_slippage = 0.001 + (liquidity_ratio * 0.004)
    entry_price *= (1 + latency_slippage)
    
    # 5. Max position check: Cannot take more than 5% of liquidity
    max_position = liquidity * 0.05 if liquidity > 0 else 100
    actual_size = min(signal_size_usd, max_position)
    
    # 6. Partial fill check
    if actual_size < signal_size_usd * 0.9:
        fill_rate = actual_size / signal_size_usd
    else:
        fill_rate = 1.0
    
    return {
        "entry_price": entry_price,
        "slippage_total": (entry_price / base_price - 1) * 100,
        "fee": fee,
        "max_position": max_position,
        "actual_size": actual_size,
        "fill_rate": fill_rate,
        "base_price": base_price
    }

def simulate_realistic_exit(price_data, position, exit_type="MARKET"):
    """
    Simulate realistic exit:
    - Forced market order (no guaranteed limit fill)
    - Spread loss
    - Slippage based on position size
    - Exit fees
    """
    base_price = price_data["price"]
    liquidity = price_data["liquidity"]
    spread = price_data["spread"]
    position_size = position["position_usdt"]
    
    # 1. Spread: Sell at bid (lower)
    exit_price = base_price * (1 - spread / 2)
    
    # 2. Slippage for exiting (usually worse for large positions)
    liquidity_ratio = position_size / liquidity if liquidity > 0 else 1
    exit_slippage = min(0.05, liquidity_ratio * 0.025)
    exit_price *= (1 - exit_slippage)
    
    # 3. Exit fee
    exit_fee = position_size * 0.003
    
    # 4. Latency
    latency_slippage = 0.001 + (liquidity_ratio * 0.004)
    exit_price *= (1 - latency_slippage)
    
    # Calculate P&L
    entry_price = position["entry_price"]
    token_amount = position["token_amount"]
    
    gross_pnl = (exit_price - entry_price) * token_amount
    net_pnl = gross_pnl - exit_fee - position.get("entry_fee", 0)
    
    return {
        "exit_price": exit_price,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "exit_fee": exit_fee,
        "slippage": (exit_price / base_price - 1) * 100
    }

def run_realistic_backtest():
    """Main backtest loop — runs every 5 minutes"""
    print("[REALISTIC BACKTEST] Starting with $10,000 virtual")
    print("[REALISTIC BACKTEST] Using: spread, liquidity-based slippage, fees, latency")
    
    # Reset state
    state = {
        "balance": 10000.0,
        "positions": [],
        "history": [],
        "total_fees_paid": 0,
        "total_slippage_cost": 0,
        "trades_executed": 0,
        "settings": {
            "spread_enabled": True,
            "slippage_model": "liquidity_based",
            "fee_rate": 0.003,
            "latency_model": "random_1_5s",
            "max_liquidity_pct": 0.05,
            "partial_fills": True
        }
    }
    
    # Only reset if state doesn't exist or is empty
    try:
        with open(PAPER_STATE, "r") as f:
            existing = json.load(f)
        if existing.get("trades_executed", 0) > 0:
            print("[REALISTIC BACKTEST] Existing state found — preserving trades")
            state = existing
        else:
            safe_write_json(PAPER_STATE, state)
            print("[REALISTIC BACKTEST] State reset — $10,000 clean start")
    except:
        safe_write_json(PAPER_STATE, state)
        print("[REALISTIC BACKTEST] State reset — $10,000 clean start")
    
    while True:
        try:
            # Check for CONFIRMED trades (not auto-trade from risk output)
            confirmed = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", {"confirmed": []})
            
            for opp in confirmed.get("confirmed", []):
                symbol = opp["symbol"]
                
                # Remove from confirmed so we don't process again
                confirmed["confirmed"] = [c for c in confirmed["confirmed"] if c.get("symbol") != symbol]
                safe_write_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", confirmed)
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎯 CONFIRMED TRADE: {symbol}")
                
                # Check duplicate
                with open(PAPER_STATE, "r") as f:
                    state = json.load(f)
                
                existing = [p for p in state["positions"] if p.get("symbol") == symbol and p.get("status") == "OPEN"]
                if existing:
                    print(f"   ⚠️ Already holding {symbol} — skip")
                    continue
                
                # Max 3 positions
                open_count = len([p for p in state["positions"] if p.get("status") == "OPEN"])
                if open_count >= 3:
                    print(f"   ⚠️ Max 3 positions — skip")
                    break
                
                # Get real market data
                price_data = get_current_price(symbol)
                if not price_data:
                    print(f"   ❌ Cannot get price for {symbol}")
                    continue
                
                # Check liquidity
                if price_data["liquidity"] < 50000:
                    print(f"   ❌ {symbol} liquidity too low (${price_data['liquidity']:,.0f} < $50K)")
                    continue
                
                # Check auto mode for position sizing
                auto_mode = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/auto_mode.json", {"position_size_pct": 5})
                position_size_pct = auto_mode.get("position_size_pct", 5)
                
                # Calculate position size (1% risk base, up to position_size_pct max)
                entry_zone = opp["entry_zone"]["primary"]
                stop = opp["stop_loss"]
                risk_distance = abs(entry_zone - stop) / entry_zone
                risk_amount = state["balance"] * 0.01  # 1% risk
                position_size = risk_amount / risk_distance if risk_distance > 0 else 100
                position_size = min(position_size, state["balance"] * (position_size_pct / 100))  # Max % of balance
                
                print(f"   📊 Position size: ${position_size:.2f} ({position_size_pct}% max, risk: 1%)")
                
                # Simulate realistic entry
                sim = simulate_realistic_entry(price_data, position_size)
                
                # Check if fill rate acceptable
                if sim["fill_rate"] < 0.8:
                    print(f"   ❌ {symbol} partial fill too low ({sim['fill_rate']:.1%})")
                    continue
                
                # Deduct from balance
                actual_cost = sim["actual_size"]
                state["balance"] -= actual_cost
                state["total_fees_paid"] += sim["fee"]
                state["total_slippage_cost"] += sim["slippage_total"] / 100 * actual_cost
                
                # Record position
                position = {
                    "id": f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "symbol": symbol,
                    "entry_price": sim["entry_price"],
                    "base_price": sim["base_price"],
                    "stop_price": stop,
                    "tp1": opp["take_profits"]["tp1_2x_risk"],
                    "tp2": opp["take_profits"]["tp2_3x_risk"],
                    "tp3": opp["take_profits"]["tp3_4x_risk"],
                    "position_usdt": actual_cost,
                    "token_amount": actual_cost / sim["entry_price"],
                    "status": "OPEN",
                    "opened_at": datetime.now().isoformat(),
                    "entry_fee": sim["fee"],
                    "entry_slippage_pct": sim["slippage_total"],
                    "liquidity_at_entry": price_data["liquidity"],
                    "fill_rate": sim["fill_rate"],
                    "current_pnl": -sim["fee"]  # Start negative due to fees
                }
                
                state["positions"].append(position)
                state["trades_executed"] += 1
                
                state["history"].append({
                    "id": position["id"],
                    "symbol": symbol,
                    "type": "OPEN",
                    "price": sim["entry_price"],
                    "amount": actual_cost,
                    "fee": sim["fee"],
                    "slippage": sim["slippage_total"],
                    "timestamp": datetime.now().isoformat()
                })
                
                safe_write_json(PAPER_STATE, state)
                
                print(f"\n📝 REALISTIC ENTRY: {symbol}")
                print(f"   Base price: ${sim['base_price']:.8f}")
                print(f"   Entry: ${sim['entry_price']:.8f} (+{sim['slippage_total']:.2f}% slippage)")
                print(f"   Fee: ${sim['fee']:.2f}")
                print(f"   Position: ${actual_cost:.2f} USDT")
                print(f"   Liquidity: ${price_data['liquidity']:,.0f}")
                print(f"   Balance left: ${state['balance']:.2f}")
            
            # Check exits
            for pos in state["positions"]:
                if pos.get("status") != "OPEN":
                    continue
                
                symbol = pos["symbol"]
                price_data = get_current_price(symbol)
                if not price_data:
                    continue
                
                current_price = price_data["price"]
                entry = pos["entry_price"]
                stop = pos["stop_price"]
                tp1 = pos["tp1"]
                
                # Check stop loss (with slippage)
                if current_price <= stop * 0.995:  # 0.5% buffer
                    # BUG FIX: Exit at stop loss level, not current market price!
                    # In real trading, stop is a market order that executes near stop.
                    
                    # Simulate exit at stop with slippage
                    exit_target = stop
                    
                    # For long stop loss: exit below stop (slippage against us)
                    liquidity_ratio = pos["position_usdt"] / price_data["liquidity"] if price_data["liquidity"] > 0 else 1
                    exit_slippage = min(0.05, liquidity_ratio * 0.025)
                    
                    # Sell at bid, below stop
                    exit_price = exit_target * (1 - exit_slippage)
                    
                    # Apply spread
                    spread = price_data["spread"]
                    exit_price *= (1 - spread / 2)
                    
                    # Latency
                    latency_slippage = 0.001 + (liquidity_ratio * 0.004)
                    exit_price *= (1 - latency_slippage)
                    
                    # Fees
                    exit_fee = pos["position_usdt"] * 0.003
                    
                    # Calculate P&L
                    entry_price = pos["entry_price"]
                    token_amount = pos["token_amount"]
                    gross_pnl = (exit_price - entry_price) * token_amount
                    net_pnl = gross_pnl - exit_fee - pos.get("entry_fee", 0)
                    
                    pos["status"] = "CLOSED"
                    pos["exit_price"] = exit_price
                    pos["exit_reason"] = "STOP_HIT"
                    pos["pnl"] = net_pnl
                    pos["exit_fee"] = exit_fee
                    pos["closed_at"] = datetime.now().isoformat()
                    
                    state["balance"] += pos["position_usdt"] + net_pnl
                    state["total_fees_paid"] += exit_fee
                    
                    state["history"].append({
                        "id": pos["id"],
                        "symbol": symbol,
                        "type": "CLOSE",
                        "price": exit_price,
                        "pnl": net_pnl,
                        "reason": "STOP_HIT",
                        "fee": exit_fee,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"\n🔴 REALISTIC EXIT: {symbol} — STOP HIT")
                    print(f"   Target stop: ${stop:.8f}")
                    print(f"   Exit: ${exit_price:.8f} (slippage: {exit_slippage*100:.2f}%)")
                    print(f"   P&L: ${net_pnl:+.2f}")
                    print(f"   Fee: ${exit_fee:.2f}")
                    print(f"   Balance: ${state['balance']:.2f}")
                
                # Check TP1 (with realistic partial fill)
                elif current_price >= tp1:
                    # BUG FIX: Exit at TP1, not at current market price!
                    # In real trading, TP1 is a limit order target.
                    # We capture profit AT TP1, not beyond it.
                    
                    # Simulate exit at TP1 with slippage
                    exit_target = tp1  # This is the take profit level
                    
                    # Apply realistic exit slippage below TP1
                    liquidity_ratio = pos["position_usdt"] / price_data["liquidity"] if price_data["liquidity"] > 0 else 1
                    exit_slippage = min(0.05, liquidity_ratio * 0.025)
                    
                    # For long: exit below TP1 (slippage against us)
                    exit_price = exit_target * (1 - exit_slippage)
                    
                    # Also apply spread (sell at bid)
                    spread = price_data["spread"]
                    exit_price *= (1 - spread / 2)
                    
                    # Latency
                    latency_slippage = 0.001 + (liquidity_ratio * 0.004)
                    exit_price *= (1 - latency_slippage)
                    
                    # Fees
                    exit_fee = pos["position_usdt"] * 0.003
                    
                    # Calculate P&L based on TP1 execution
                    entry_price = pos["entry_price"]
                    token_amount = pos["token_amount"]
                    gross_pnl = (exit_price - entry_price) * token_amount
                    net_pnl = gross_pnl - exit_fee - pos.get("entry_fee", 0)
                    
                    pos["status"] = "CLOSED"
                    pos["exit_price"] = exit_price
                    pos["exit_reason"] = "TP1_HIT"
                    pos["pnl"] = net_pnl
                    pos["exit_fee"] = exit_fee
                    pos["closed_at"] = datetime.now().isoformat()
                    
                    state["balance"] += pos["position_usdt"] + net_pnl
                    state["total_fees_paid"] += exit_fee
                    
                    state["history"].append({
                        "id": pos["id"],
                        "symbol": symbol,
                        "type": "CLOSE",
                        "price": exit_price,
                        "pnl": net_pnl,
                        "reason": "TP1_HIT",
                        "fee": exit_fee,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"\n🟢 REALISTIC EXIT: {symbol} — TP1 HIT")
                    print(f"   Target TP1: ${tp1:.8f}")
                    print(f"   Exit: ${exit_price:.8f} (slippage: {exit_slippage*100:.2f}%)")
                    print(f"   P&L: ${net_pnl:+.2f}")
                    print(f"   Fee: ${exit_fee:.2f}")
                    print(f"   Balance: ${state['balance']:.2f}")
            
            # Save state
            safe_write_json(PAPER_STATE, state)
            
            # Print summary every cycle
            open_count = len([p for p in state["positions"] if p.get("status") == "OPEN"])
            closed_trades = [h for h in state["history"] if h.get("type") == "CLOSE"]
            if closed_trades:
                total_pnl = sum(h.get("pnl", 0) for h in closed_trades)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Summary: {len(closed_trades)} closed, ${total_pnl:+.2f} P&L, ${state['balance']:.2f} balance")
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(300)  # Every 5 minutes

if __name__ == "__main__":
    run_realistic_backtest()
