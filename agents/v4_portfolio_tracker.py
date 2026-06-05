#!/usr/bin/env python3
"""
📊 PORTFOLIO & PERFORMANCE TRACKER
Logs every signal, outcome, and capital state.
Required for 200+ trade validation before semi-auto mode.
"""
import json
import time
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

TRADE_LOG = "/root/.openclaw/workspace/agents/logs/trade_history.json"
PORTFOLIO_STATE = "/root/.openclaw/workspace/agents/logs/portfolio_state.json"

class PortfolioTracker:
    def __init__(self):
        self.trades = []
        self.state = {
            "starting_balance": 10000.0,
            "current_balance": 10000.0,
            "daily_pnl": 0.0,
            "daily_trades": 0,
            "consecutive_losses": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_exposure": 0.0,
            "mode": "MANUAL",
            "emergency_active": False,
            "last_reset": datetime.now().isoformat(),
        }
        self.load()
    
    def load(self):
        self.trades = safe_read_json(TRADE_LOG, [])
        self.state = safe_read_json(PORTFOLIO_STATE, self.state)
    
    def save(self):
        safe_write_json(TRADE_LOG, self.trades)
        safe_write_json(PORTFOLIO_STATE, self.state)
    
    def log_signal(self, signal_data):
        """Log a new signal (before execution)"""
        trade = {
            "id": f"{signal_data['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "symbol": signal_data["symbol"],
            "entry": signal_data["entry_zone"]["primary"],
            "stop": signal_data["stop_loss"],
            "tp1": signal_data["take_profits"]["tp1_2x_risk"],
            "tp2": signal_data["take_profits"]["tp2_3x_risk"],
            "tp3": signal_data["take_profits"]["tp3_4x_risk"],
            "rr": signal_data["risk_reward_ratio"],
            "confidence": signal_data["confidence"],
            "position_size_pct": signal_data["position_size_pct"],
            "risk_level": signal_data["risk_level"],
            "atr_proxy": signal_data.get("atr_proxy", 0),
            "status": "PENDING",
            "outcome": None,
            "pnl": None,
            "exit_price": None,
            "exit_reason": None,
        }
        self.trades.append(trade)
        self.save()
        return trade["id"]
    
    def update_outcome(self, trade_id, outcome, pnl, exit_price, exit_reason):
        """Update trade outcome after close"""
        for t in self.trades:
            if t["id"] == trade_id:
                t["status"] = "CLOSED"
                t["outcome"] = outcome  # WIN / LOSS / BREAKEVEN
                t["pnl"] = pnl
                t["exit_price"] = exit_price
                t["exit_reason"] = exit_reason
                t["closed_at"] = datetime.now().isoformat()
                
                # Update state
                self.state["current_balance"] += pnl
                self.state["daily_pnl"] += pnl
                self.state["total_trades"] += 1
                self.state["daily_trades"] += 1
                
                if outcome == "WIN":
                    self.state["wins"] += 1
                    self.state["consecutive_losses"] = 0
                elif outcome == "LOSS":
                    self.state["losses"] += 1
                    self.state["consecutive_losses"] += 1
                
                self.save()
                return True
        return False
    
    def get_stats(self):
        """Calculate performance statistics"""
        if self.state["total_trades"] == 0:
            return {"message": "No trades logged yet"}
        
        win_rate = self.state["wins"] / self.state["total_trades"] * 100
        avg_win = sum(t["pnl"] for t in self.trades if t.get("outcome") == "WIN") / max(self.state["wins"], 1)
        avg_loss = sum(t["pnl"] for t in self.trades if t.get("outcome") == "LOSS") / max(self.state["losses"], 1)
        
        # Expectancy = (Win% × AvgWin) - (Loss% × |AvgLoss|)
        win_pct = self.state["wins"] / self.state["total_trades"]
        loss_pct = self.state["losses"] / self.state["total_trades"]
        expectancy = (win_pct * avg_win) - (loss_pct * abs(avg_loss))
        
        # Max drawdown
        running_balance = self.state["starting_balance"]
        max_balance = running_balance
        max_drawdown = 0
        for t in sorted(self.trades, key=lambda x: x["timestamp"]):
            if t.get("pnl"):
                running_balance += t["pnl"]
                max_balance = max(max_balance, running_balance)
                dd = (max_balance - running_balance) / max_balance * 100
                max_drawdown = max(max_drawdown, dd)
        
        return {
            "total_trades": self.state["total_trades"],
            "wins": self.state["wins"],
            "losses": self.state["losses"],
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "max_drawdown": round(max_drawdown, 1),
            "current_balance": round(self.state["current_balance"], 2),
            "daily_pnl": round(self.state["daily_pnl"], 2),
            "consecutive_losses": self.state["consecutive_losses"],
            "mode": self.state["mode"],
            "ready_for_semi_auto": (
                self.state["total_trades"] >= 100
                and expectancy >= 0.3
                and max_drawdown < 15
                and win_rate > 45
            ),
            "ready_for_auto": (
                self.state["total_trades"] >= 500
                and expectancy >= 0.5
                and max_drawdown < 10
                and win_rate > 45
            )
        }
    
    def daily_reset(self):
        """Reset daily counters at midnight"""
        self.state["daily_pnl"] = 0.0
        self.state["daily_trades"] = 0
        self.state["last_reset"] = datetime.now().isoformat()
        self.save()
    
    def check_upgrade_eligibility(self):
        """Check if system can upgrade execution mode"""
        stats = self.get_stats()
        if stats.get("ready_for_auto"):
            return "AUTO", "500+ trades, expectancy > 0.5, drawdown < 10%"
        elif stats.get("ready_for_semi_auto"):
            return "SEMI_AUTO", "100+ trades, expectancy > 0.3, drawdown < 15%"
        return "MANUAL", f"{stats.get('total_trades', 0)} trades logged — need 100 for semi-auto"

def main():
    tracker = PortfolioTracker()
    
    print("[PORTFOLIO TRACKER] Performance tracking active")
    print(f"[PORTFOLIO TRACKER] Current balance: ${tracker.state['current_balance']:.2f}")
    print(f"[PORTFOLIO TRACKER] Mode: {tracker.state['mode']}")
    
    # Check upgrade eligibility
    mode, reason = tracker.check_upgrade_eligibility()
    print(f"[PORTFOLIO TRACKER] Execution mode: {mode} ({reason})")
    
    # Print stats
    stats = tracker.get_stats()
    if "message" not in stats:
        print(f"\n📊 PERFORMANCE:")
        print(f"  Win rate: {stats['win_rate']}%")
        print(f"  Expectancy: {stats['expectancy']}")
        print(f"  Max drawdown: {stats['max_drawdown']}%")
        print(f"  Total trades: {stats['total_trades']}")
    
    # Monitor mode
    while True:
        try:
            new_mode, reason = tracker.check_upgrade_eligibility()
            if new_mode != tracker.state["mode"]:
                print(f"\n🎉 MODE UPGRADE: {tracker.state['mode']} → {new_mode}")
                print(f"   Reason: {reason}")
                tracker.state["mode"] = new_mode
                tracker.save()
            
            # Daily reset check
            now = datetime.now()
            last_reset = datetime.fromisoformat(tracker.state["last_reset"])
            if now.date() != last_reset.date():
                print(f"\n🌅 Daily reset — PNL: ${tracker.state['daily_pnl']:+.2f}")
                tracker.daily_reset()
            
            time.sleep(3600)  # Check every hour
            
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(3600)

if __name__ == "__main__":
    main()
