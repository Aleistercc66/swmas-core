#!/usr/bin/env python3
"""
📊 SYSTEM SCORECARD
Reality check. Measures actual edge, not theoretical beauty.
"""
import json
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

class SystemScorecard:
    def __init__(self):
        self.log_dir = Path("/root/.openclaw/workspace/agents/logs")
        self.scorecard_file = self.log_dir / "system_scorecard.json"
        self.history_file = self.log_dir / "scorecard_history.json"
        
    def load_trades(self):
        try:
            with open(self.log_dir / "paper_trading.json", "r") as f:
                data = json.load(f)
            return data.get("history", [])
        except:
            return []
    
    def load_circuit(self):
        try:
            with open(self.log_dir / "circuit_breaker.json", "r") as f:
                return json.load(f)
        except:
            return {}
    
    def calculate_expectancy(self, trades):
        if not trades:
            return {"value": 0, "status": "NO_DATA", "message": "Zero trades logged"}
        
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]
        
        total = len(wins) + len(losses)
        if total == 0:
            return {"value": 0, "status": "NO_CLOSED_TRADES", "message": "No closed trades"}
        
        win_rate = len(wins) / total
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        status = "NEGATIVE" if expectancy < 0 else "BREAKEVEN" if expectancy == 0 else "POSITIVE"
        
        return {
            "value": round(expectancy, 2),
            "status": status,
            "win_rate": round(win_rate * 100, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "message": f"${expectancy:+.2f} per trade (need > $0.30 for semi-auto)"
        }
    
    def calculate_drawdown(self, trades):
        if not trades:
            return {"max_dd_pct": 0, "current_dd_pct": 0, "status": "NO_DATA"}
        
        # Sort by timestamp
        sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""))
        
        peak = 10000  # Starting balance
        max_dd = 0
        current_balance = peak
        
        for trade in sorted_trades:
            if trade.get("type") == "CLOSE":
                current_balance += trade.get("pnl", 0)
                if current_balance > peak:
                    peak = current_balance
                dd = (peak - current_balance) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        
        current_dd = (peak - current_balance) / peak * 100 if peak > 0 else 0
        
        status = "CRITICAL" if max_dd > 20 else "WARNING" if max_dd > 10 else "HEALTHY"
        
        return {
            "max_dd_pct": round(max_dd, 2),
            "current_dd_pct": round(current_dd, 2),
            "current_balance": round(current_balance, 2),
            "peak_balance": round(peak, 2),
            "status": status
        }
    
    def analyze_regime_performance(self, trades):
        """Which regimes make/lose money"""
        regime_pnl = defaultdict(list)
        
        for trade in trades:
            if trade.get("type") == "CLOSE":
                regime = trade.get("regime_at_entry", "UNKNOWN")
                regime_pnl[regime].append(trade.get("pnl", 0))
        
        if not regime_pnl:
            return {"status": "NO_DATA", "message": "No regime data logged"}
        
        analysis = {}
        for regime, pnls in regime_pnl.items():
            avg = sum(pnls) / len(pnls)
            wins = sum(1 for p in pnls if p > 0)
            win_rate = wins / len(pnls) * 100
            analysis[regime] = {
                "total_trades": len(pnls),
                "avg_pnl": round(avg, 2),
                "win_rate": round(win_rate, 1),
                "status": "PROFITABLE" if avg > 0 else "UNPROFITABLE"
            }
        
        # Find best and worst regimes
        best = max(analysis.items(), key=lambda x: x[1]["avg_pnl"]) if analysis else None
        worst = min(analysis.items(), key=lambda x: x[1]["avg_pnl"]) if analysis else None
        
        return {
            "regimes": analysis,
            "best_regime": best[0] if best else None,
            "worst_regime": worst[0] if worst else None,
            "status": "ANALYZED"
        }
    
    def analyze_dna_performance(self, trades):
        """Which setup types work"""
        dna_pnl = defaultdict(list)
        
        for trade in trades:
            if trade.get("type") == "CLOSE":
                dna = trade.get("dna_at_entry", "UNKNOWN")
                dna_pnl[dna].append(trade.get("pnl", 0))
        
        if not dna_pnl:
            return {"status": "NO_DATA", "message": "No DNA data logged"}
        
        analysis = {}
        for dna, pnls in dna_pnl.items():
            avg = sum(pnls) / len(pnls)
            wins = sum(1 for p in pnls if p > 0)
            win_rate = wins / len(pnls) * 100
            analysis[dna] = {
                "total_trades": len(pnls),
                "avg_pnl": round(avg, 2),
                "win_rate": round(win_rate, 1),
                "status": "PROFITABLE" if avg > 0 else "UNPROFITABLE"
            }
        
        best = max(analysis.items(), key=lambda x: x[1]["avg_pnl"]) if analysis else None
        worst = min(analysis.items(), key=lambda x: x[1]["avg_pnl"]) if analysis else None
        
        return {
            "dna_types": analysis,
            "best_dna": best[0] if best else None,
            "worst_dna": worst[0] if worst else None,
            "status": "ANALYZED"
        }
    
    def detect_false_signals(self, trades):
        """Signals that hit stop loss quickly"""
        if not trades:
            return {"status": "NO_DATA"}
        
        quick_losses = [t for t in trades 
                       if t.get("type") == "CLOSE" 
                       and t.get("pnl", 0) < 0
                       and t.get("holding_time_minutes", 999) < 30]
        
        total_losses = len([t for t in trades if t.get("type") == "CLOSE" and t.get("pnl", 0) < 0])
        
        false_rate = (len(quick_losses) / total_losses * 100) if total_losses > 0 else 0
        
        return {
            "quick_losses": len(quick_losses),
            "total_losses": total_losses,
            "false_signal_rate": round(false_rate, 1),
            "status": "HIGH" if false_rate > 50 else "MODERATE" if false_rate > 25 else "LOW"
        }
    
    def calculate_agent_overlap(self):
        """Detect which agents might be redundant"""
        # Read agent logs to check if they're producing unique value
        agents = {
            "scanner": "v2_scanner.log",
            "sentiment": "v2_sentiment.log",
            "whale": "v2_whale.log",
            "regime": "v2_regime.log",
            "dna": "v2_dna.log",
            "fomo": "v2_fomo.log",
            "validator": "v2_validator.log",
            "risk": "v2_dynamic_risk.log"
        }
        
        overlap_report = {}
        
        for agent_name, log_file in agents.items():
            try:
                with open(self.log_dir / log_file, "r") as f:
                    content = f.read()
                
                # Check if agent is active (has recent entries)
                lines = content.strip().split("\n")
                recent_lines = [l for l in lines if "2026-05-07" in l or "2026-05-08" in l]
                
                overlap_report[agent_name] = {
                    "log_entries_24h": len(recent_lines),
                    "status": "ACTIVE" if len(recent_lines) > 5 else "LOW_ACTIVITY" if len(recent_lines) > 0 else "NO_ACTIVITY",
                    "recommendation": "KEEP" if len(recent_lines) > 5 else "REVIEW"
                }
            except:
                overlap_report[agent_name] = {
                    "log_entries_24h": 0,
                    "status": "ERROR",
                    "recommendation": "CHECK"
                }
        
        return overlap_report
    
    def generate_scorecard(self):
        trades = self.load_trades()
        
        scorecard = {
            "timestamp": datetime.now().isoformat(),
            "system_phase": "PAPER_TRADING_AUDIT",
            "total_trades_logged": len(trades),
            "performance": self.calculate_expectancy(trades),
            "drawdown": self.calculate_drawdown(trades),
            "regime_analysis": self.analyze_regime_performance(trades),
            "dna_analysis": self.analyze_dna_performance(trades),
            "false_signals": self.detect_false_signals(trades),
            "agent_health": self.calculate_agent_overlap(),
            "readiness": {
                "semi_auto": "NOT_READY",
                "testnet": "NOT_READY",
                "real_capital": "NOT_READY"
            }
        }
        
        # Determine readiness
        perf = scorecard["performance"]
        dd = scorecard["drawdown"]
        
        if perf["total_trades"] >= 100:
            if perf["value"] > 0.3 and dd["max_dd_pct"] < 15:
                scorecard["readiness"]["semi_auto"] = "READY"
            if perf["value"] > 0.5 and dd["max_dd_pct"] < 10 and perf["total_trades"] >= 500:
                scorecard["readiness"]["full_auto"] = "READY"
        
        # Save
        safe_write_json(self.scorecard_file, scorecard)
        
        # Save to history
        history = safe_read_json(self.history_file, [])
        
        history.append({
            "timestamp": scorecard["timestamp"],
            "expectancy": perf["value"],
            "win_rate": perf.get("win_rate", 0),
            "max_dd": dd["max_dd_pct"],
            "total_trades": perf["total_trades"]
        })
        
        safe_write_json(self.history_file, history[-50:])  # Keep last 50
        
        return scorecard
    
    def print_scorecard(self, scorecard):
        print("\n" + "="*60)
        print("📊 SYSTEM SCORECARD — REALITY CHECK")
        print("="*60)
        
        perf = scorecard["performance"]
        print(f"\n🎯 EXPECTANCY: ${perf['value']:+.2f} per trade")
        print(f"   Status: {perf['status']}")
        if perf["total_trades"] > 0:
            print(f"   Win Rate: {perf['win_rate']}%")
            print(f"   Trades: {perf['wins']}W / {perf['losses']}L")
        print(f"   → {perf['message']}")
        
        dd = scorecard["drawdown"]
        print(f"\n📉 DRAWDOWN:")
        print(f"   Max: {dd['max_dd_pct']}%")
        print(f"   Current: {dd['current_dd_pct']}%")
        print(f"   Balance: ${dd.get('current_balance', 10000):,.2f}")
        print(f"   Status: {dd['status']}")
        
        regime = scorecard["regime_analysis"]
        if regime["status"] == "ANALYZED":
            print(f"\n🌍 REGIME PERFORMANCE:")
            for r, data in regime["regimes"].items():
                emoji = "🟢" if data["avg_pnl"] > 0 else "🔴"
                print(f"   {emoji} {r}: {data['avg_pnl']:+.2f}/trade ({data['win_rate']}% WR)")
        
        dna = scorecard["dna_analysis"]
        if dna["status"] == "ANALYZED":
            print(f"\n🧬 DNA PERFORMANCE:")
            for d, data in dna["dna_types"].items():
                emoji = "🟢" if data["avg_pnl"] > 0 else "🔴"
                print(f"   {emoji} {d}: {data['avg_pnl']:+.2f}/trade ({data['win_rate']}% WR)")
        
        false = scorecard["false_signals"]
        if false["status"] != "NO_DATA":
            print(f"\n⚠️ FALSE SIGNALS:")
            print(f"   Quick losses (<30min): {false['quick_losses']}/{false['total_losses']}")
            print(f"   False rate: {false['false_signal_rate']}%")
        
        print(f"\n📋 READINESS:")
        for phase, status in scorecard["readiness"].items():
            emoji = "🟢" if status == "READY" else "🔴"
            print(f"   {emoji} {phase}: {status}")
        
        print(f"\n{'='*60}")
        print(f"Total trades logged: {scorecard['total_trades_logged']}")
        print(f"Phase: {scorecard['system_phase']}")
        print(f"{'='*60}\n")

def main():
    print("[SYSTEM SCORECARD] Reality check initiated")
    print("[SYSTEM SCORECARD] Measuring actual edge, not theory...")
    
    scorecard = SystemScorecard()
    
    while True:
        try:
            result = scorecard.generate_scorecard()
            scorecard.print_scorecard(result)
            
            # If we have data, also send to Telegram
            if result["total_trades_logged"] > 0:
                send_telegram_summary(result)
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1800)  # Every 30 minutes

def send_telegram_summary(scorecard):
    """Send scorecard to Telegram if significant"""
    try:
        import requests
        
        perf = scorecard["performance"]
        dd = scorecard["drawdown"]
        
        if perf["total_trades"] == 0:
            return
        
        msg = f"""📊 SYSTEM SCORECARD

🎯 Expectancy: ${perf['value']:+.2f}/trade
📈 Win Rate: {perf['win_rate']}%
📉 Max Drawdown: {dd['max_dd_pct']}%
💰 Balance: ${dd.get('current_balance', 10000):,.2f}
📊 Trades: {perf['total_trades']}

Phase: {scorecard['system_phase']}"""
        
        url = "https://api.telegram.org/bot8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc/sendMessage"
        requests.post(url, json={"chat_id": "158923136", "text": msg}, timeout=5)
    except:
        pass

if __name__ == "__main__":
    main()
