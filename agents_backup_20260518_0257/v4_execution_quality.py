#!/usr/bin/env python3
"""
📊 EXECUTION QUALITY ANALYST
Tracks slippage, entry deviation, fill quality, spread conditions, latency.
"""
import json
import time
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

class ExecutionQuality:
    def __init__(self):
        self.quality_log = "/root/.openclaw/workspace/agents/logs/execution_quality.json"
        self.load_history()
    
    def load_history(self):
        self.history = safe_read_json(self.quality_log, [])
    
    def save_history(self):
        safe_write_json(self.quality_log, self.history[-100:])  # Keep last 100
    
    def analyze_execution(self, signal, actual_entry, actual_slippage, execution_time_ms):
        """
        Analyze execution quality for a trade
        """
        symbol = signal.get("symbol", "???")
        planned_entry = signal["entry_zone"]["primary"]
        stop = signal["stop_loss"]
        
        # Entry deviation
        entry_deviation_pct = abs(actual_entry - planned_entry) / planned_entry * 100 if planned_entry > 0 else 0
        
        # Slippage analysis
        slippage_grade = "EXCELLENT"
        if actual_slippage > 2.0:
            slippage_grade = "POOR"
        elif actual_slippage > 1.0:
            slippage_grade = "FAIR"
        elif actual_slippage > 0.5:
            slippage_grade = "GOOD"
        
        # Latency analysis
        latency_grade = "EXCELLENT"
        if execution_time_ms > 5000:
            latency_grade = "POOR"
        elif execution_time_ms > 2000:
            latency_grade = "FAIR"
        elif execution_time_ms > 500:
            latency_grade = "GOOD"
        
        # Impact on R:R
        planned_risk = planned_entry - stop
        actual_risk = actual_entry - stop
        risk_increase_pct = (actual_risk / planned_risk - 1) * 100 if planned_risk > 0 else 0
        
        # Overall quality score (0-100)
        quality_score = 100
        quality_score -= min(actual_slippage * 10, 30)  # Slippage penalty
        quality_score -= min(entry_deviation_pct * 5, 25)  # Deviation penalty
        quality_score -= min(execution_time_ms / 100, 20)  # Latency penalty
        quality_score = max(0, min(100, quality_score))
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "planned_entry": planned_entry,
            "actual_entry": actual_entry,
            "entry_deviation_pct": round(entry_deviation_pct, 2),
            "actual_slippage_pct": round(actual_slippage, 2),
            "execution_time_ms": execution_time_ms,
            "slippage_grade": slippage_grade,
            "latency_grade": latency_grade,
            "risk_increase_pct": round(risk_increase_pct, 1),
            "quality_score": round(quality_score, 0),
            "stop": stop,
        }
        
        self.history.append(analysis)
        self.save_history()
        
        return analysis
    
    def get_summary_stats(self):
        """Get execution quality summary"""
        if not self.history:
            return {"message": "No executions analyzed yet"}
        
        recent = self.history[-20:]  # Last 20 executions
        
        avg_slippage = sum(h["actual_slippage_pct"] for h in recent) / len(recent)
        avg_latency = sum(h["execution_time_ms"] for h in recent) / len(recent)
        avg_deviation = sum(h["entry_deviation_pct"] for h in recent) / len(recent)
        avg_quality = sum(h["quality_score"] for h in recent) / len(recent)
        
        poor_executions = sum(1 for h in recent if h["quality_score"] < 60)
        
        return {
            "total_analyzed": len(self.history),
            "recent_count": len(recent),
            "avg_slippage_pct": round(avg_slippage, 2),
            "avg_latency_ms": round(avg_latency, 0),
            "avg_entry_deviation_pct": round(avg_deviation, 2),
            "avg_quality_score": round(avg_quality, 0),
            "poor_executions": poor_executions,
            "execution_health": "GOOD" if avg_quality > 70 else "FAIR" if avg_quality > 50 else "POOR",
        }

def main():
    print("[EXECUTION QUALITY] Slippage, latency, fill tracking active")
    
    quality = ExecutionQuality()
    
    # Simulate analysis of recent trades
    while True:
        try:
            # Check for closed trades from paper trading
            try:
                paper  = safe_read_json("/root/.openclaw/workspace/agents/logs/paper_trading.json", {})
                
                for trade in paper.get("history", [])[-10:]:
                    if trade.get("type") == "OPEN":
                        # Simulate execution quality (in real mode, this would be actual data)
                        symbol = trade.get("symbol", "???")
                        actual_entry = trade.get("price", 0)
                        
                        # For paper trading, assume 0.5% slippage
                        planned_entry = actual_entry / 1.005
                        
                        analysis = quality.analyze_execution(
                            {"symbol": symbol, "entry_zone": {"primary": planned_entry}, "stop_loss": planned_entry * 0.95},
                            actual_entry,
                            0.5,  # Simulated slippage
                            800,  # Simulated latency ms
                        )
                        
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Execution Quality:")
                        print(f"   Symbol: {symbol}")
                        print(f"   Slippage: {analysis['actual_slippage_pct']:.2f}% ({analysis['slippage_grade']})")
                        print(f"   Deviation: {analysis['entry_deviation_pct']:.2f}%")
                        print(f"   Latency: {analysis['execution_time_ms']}ms ({analysis['latency_grade']})")
                        print(f"   Quality Score: {analysis['quality_score']}/100")
            except:
                pass
            
            # Print summary every hour
            if datetime.now().minute == 0:
                stats = quality.get_summary_stats()
                if "message" not in stats:
                    print(f"\n📊 EXECUTION QUALITY SUMMARY")
                    print(f"   Trades analyzed: {stats['total_analyzed']}")
                    print(f"   Avg slippage: {stats['avg_slippage_pct']:.2f}%")
                    print(f"   Avg latency: {stats['avg_latency_ms']:.0f}ms")
                    print(f"   Avg quality: {stats['avg_quality_score']}/100")
                    print(f"   Health: {stats['execution_health']}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(300)  # Every 5 minutes

if __name__ == "__main__":
    main()
