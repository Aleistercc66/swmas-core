#!/usr/bin/env python3
"""
📱 HOURLY TELEGRAM REPORTER
Sends portfolio updates every hour since dashboard isn't externally accessible.
"""
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def get_portfolio_data():
    try:
        with open("/root/.openclaw/workspace/agents/logs/paper_trading.json", "r") as f:
            return json.load(f)
    except:
        return {"balance": 10000, "positions": [], "history": [], "daily_pnl": 0}

def get_circuit_state():
    try:
        with open("/root/.openclaw/workspace/agents/logs/circuit_breaker.json", "r") as f:
            return json.load(f)
    except:
        return {"status": "NORMAL", "daily_drawdown": 0}

def generate_report():
    portfolio = get_portfolio_data()
    circuit = get_circuit_state()
    
    balance = portfolio.get("balance", 10000)
    positions = portfolio.get("positions", [])
    history = portfolio.get("history", [])
    daily_pnl = portfolio.get("daily_pnl", 0)
    
    total_trades = len([h for h in history if h.get("type") == "CLOSE"])
    wins = len([h for h in history if h.get("type") == "CLOSE" and h.get("pnl", 0) > 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate expectancy
    if total_trades > 0:
        avg_win = sum(h.get("pnl", 0) for h in history if h.get("type") == "CLOSE" and h.get("pnl", 0) > 0) / max(wins, 1)
        losses = total_trades - wins
        avg_loss = abs(sum(h.get("pnl", 0) for h in history if h.get("type") == "CLOSE" and h.get("pnl", 0) < 0)) / max(losses, 1)
        win_prob = wins / total_trades
        loss_prob = losses / total_trades
        expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)
    else:
        expectancy = 0
    
    uptime_hours = (datetime.now() - datetime(2026, 5, 7, 9, 45)).total_seconds() / 3600
    
    report = f"""🤖 <b>SWARM v4.0 — HOURLY REPORT</b>

⏰ <b>Uptime:</b> {uptime_hours:.1f} hours
⚡ <b>Circuit:</b> {circuit.get('status', 'NORMAL')}

💰 <b>PAPER PORTFOLIO</b>
• Balance: ${balance:,.2f}
• Daily P&L: ${daily_pnl:+.2f}
• Open Positions: {len(positions)}

📊 <b>PERFORMANCE</b>
• Total Trades: {total_trades}
• Wins: {wins} | Losses: {total_trades - wins}
• Win Rate: {win_rate:.1f}%
• Expectancy: ${expectancy:+.2f}

🎯 <b>OPEN POSITIONS</b>
"""
    
    if positions:
        for pos in positions[-3:]:
            report += f"• {pos.get('symbol', '?')}: ${pos.get('pnl', 0):+.2f}\n"
    else:
        report += "• No open positions\n"
    
    # Best/worst trades
    if history:
        closed = [h for h in history if h.get("type") == "CLOSE"]
        if closed:
            best = max(closed, key=lambda x: x.get("pnl", 0))
            worst = min(closed, key=lambda x: x.get("pnl", 0))
            report += f"\n🏆 Best: {best.get('symbol', '?')} ${best.get('pnl', 0):+.2f}\n"
            report += f"💀 Worst: {worst.get('symbol', '?')} ${worst.get('pnl', 0):+.2f}\n"
    
    report += f"\n📈 Next report in 1 hour..."
    
    return report

def main():
    print("[HOURLY REPORTER] Started — Sending updates to Telegram")
    
    # Send initial report
    send_telegram(generate_report())
    
    while True:
        time.sleep(3600)  # Every hour
        try:
            report = generate_report()
            send_telegram(report)
            print(f"[{datetime.now().strftime('%H:%M')}] Report sent")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
