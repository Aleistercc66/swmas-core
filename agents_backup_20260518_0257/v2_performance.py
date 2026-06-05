#!/usr/bin/env python3
"""
📊 AGENT 6: PERFORMANCE ANALYST
Track every signal. Measure accuracy. Improve continuously.
"""
import json
import os
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

PERFORMANCE_FILE = "/root/.openclaw/workspace/agents/logs/performance_history.json"

def load_history():
    return safe_read_json(PERFORMANCE_FILE, {"signals": [], "summary": {}})

def save_history(history):
    safe_write_json(PERFORMANCE_FILE, history)

def record_signal(risk_output):
    """Record a signal for later outcome tracking"""
    history = load_history()
    
    for opp in risk_output.get("approved", []):
        signal = {
            "timestamp": opp["timestamp"],
            "symbol": opp["symbol"],
            "entry": opp["entry_zone"]["primary"],
            "stop": opp["stop_loss"],
            "tp1": opp["take_profits"]["tp1_50pct"],
            "tp2": opp["take_profits"]["tp2_100pct"],
            "tp3": opp["take_profits"]["tp3_200pct"],
            "rr": opp["risk_reward_ratio"],
            "confidence": opp["confidence"],
            "risk_level": opp["risk_level"],
            "status": "PENDING",
            "outcome": None,
            "max_profit_pct": None,
            "max_loss_pct": None,
            "exit_price": None,
            "exit_reason": None
        }
        history["signals"].append(signal)
    
    save_history(history)
    return len(risk_output.get("approved", []))

def analyze_performance():
    """Analyze all historical signals"""
    history = load_history()
    signals = history.get("signals", [])
    
    if not signals:
        return {"error": "No signals recorded yet"}
    
    total = len(signals)
    wins = sum(1 for s in signals if s["status"] == "WIN")
    losses = sum(1 for s in signals if s["status"] == "LOSS")
    pending = sum(1 for s in signals if s["status"] == "PENDING")
    be = sum(1 for s in signals if s["status"] == "BREAK_EVEN")
    
    completed = wins + losses + be
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_signals": total,
        "completed": completed,
        "pending": pending,
        "wins": wins,
        "losses": losses,
        "break_even": be,
        "win_rate": round(wins / completed * 100, 1) if completed > 0 else 0,
        "loss_rate": round(losses / completed * 100, 1) if completed > 0 else 0,
        "avg_rr": round(sum(s["rr"] for s in signals if s["status"] != "PENDING") / max(completed, 1), 2),
        "best_confidence": max((s["confidence"] for s in signals), default=0),
        "avg_confidence": round(sum(s["confidence"] for s in signals) / max(total, 1), 1),
        "by_risk_level": {},
        "recommendations": []
    }
    
    # Analysis by risk level
    for level in ["LOW", "MEDIUM", "HIGH"]:
        level_signals = [s for s in signals if s["risk_level"] == level and s["status"] != "PENDING"]
        if level_signals:
            level_wins = sum(1 for s in level_signals if s["status"] == "WIN")
            report["by_risk_level"][level] = {
                "count": len(level_signals),
                "win_rate": round(level_wins / len(level_signals) * 100, 1)
            }
    
    # Generate recommendations
    if report["win_rate"] < 40 and completed >= 5:
        report["recommendations"].append("Win rate below 40% — tighten validation criteria")
    if report["avg_rr"] < 2 and completed >= 5:
        report["recommendations"].append("Average R:R below 2 — be more selective with entries")
    if report["loss_rate"] > 50 and completed >= 5:
        report["recommendations"].append("Loss rate too high — widen stop losses or reduce position sizes")
    
    if not report["recommendations"]:
        report["recommendations"].append("System performing within acceptable parameters")
    
    return report

def main():
    print("[PERFORMANCE] Agent started — Tracking all signals for accuracy")
    print("[PERFORMANCE] Recording every approved setup for outcome analysis")
    
    while True:
        try:
            # Load risk manager output and record signals
            try:
                with open("/root/.openclaw/workspace/agents/tmp_state/risk_output.json", "r") as f:
                    risk_output = json.load(f)
                recorded = record_signal(risk_output)
                if recorded > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recorded {recorded} new signals for tracking")
            except:
                pass
            
            # Generate performance report
            report = analyze_performance()
            
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/performance_output.json", report)
            
            if "error" not in report:
                print(f"\n📊 PERFORMANCE REPORT")
                print(f"   Total Signals: {report['total_signals']}")
                print(f"   Win Rate: {report['win_rate']}% ({report['wins']}W / {report['losses']}L / {report['break_even']}BE)")
                print(f"   Avg R:R: 1:{report['avg_rr']}")
                print(f"   Avg Confidence: {report['avg_confidence']}/100")
                if report['by_risk_level']:
                    for level, stats in report['by_risk_level'].items():
                        print(f"   {level} Risk: {stats['win_rate']}% WR ({stats['count']} signals)")
                print(f"\n   💡 Recommendations:")
                for rec in report['recommendations']:
                    print(f"      → {rec}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(3600)  # 1 hour

if __name__ == "__main__":
    main()
