#!/usr/bin/env python3
"""
🧠 META AGENT — Self-Healing & Self-Improving System
Monitors health, researches new tools, auto-fixes problems.
The ultimate guardian of your trading system.
"""
import subprocess
import json
import time
import os
import sys
import threading
from datetime import datetime, timedelta
import requests
import traceback

sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

# Configuration
HEALTH_CHECK_INTERVAL = 60  # seconds
RESEARCH_INTERVAL = 1800   # 30 minutes
REPAIR_INTERVAL = 300        # 5 minutes
LOG_RETENTION_DAYS = 3

AGENTS_DIR = "/root/.openclaw/workspace/agents"
LOGS_DIR = f"{AGENTS_DIR}/logs"
TMP_STATE_DIR = f"{AGENTS_DIR}/tmp_state"
META_LOG = f"{LOGS_DIR}/meta_agent.log"
KNOWLEDGE_FILE = f"{AGENTS_DIR}/knowledge_base.json"

class MetaAgent:
    def __init__(self):
        self.running = True
        self.health_stats = {}
        self.research_findings = []
        self.repairs_done = []
        self.start_time = datetime.now()
        self.knowledge = self.load_knowledge()
        
    def log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line)
        with open(META_LOG, 'a') as f:
            f.write(line + '\n')
    
    def load_knowledge(self):
        return safe_read_json(KNOWLEDGE_FILE, {
            "known_errors": {},
            "fixes_applied": [],
            "research_history": [],
            "system_patterns": {},
            "last_updated": datetime.now().isoformat()
        })
    
    def save_knowledge(self):
        self.knowledge["last_updated"] = datetime.now().isoformat()
        safe_write_json(KNOWLEDGE_FILE, self.knowledge)
    
    # ═══════════════════════════════════════════
    # HEALTH MONITORING
    # ═══════════════════════════════════════════
    
    def check_tmux_sessions(self):
        """Check if all expected tmux sessions are running"""
        expected = [
            "v2-scanner", "v2-validator", "v2-dynamic-risk",
            "v4-master", "v4-backtest", "telegram-poll",
            "meta-agent"
        ]
        
        try:
            result = subprocess.run(
                ["tmux", "list-sessions"],
                capture_output=True, text=True, timeout=5
            )
            running = result.stdout
            
            status = {}
            for session in expected:
                if session in running:
                    status[session] = "✅ RUNNING"
                else:
                    status[session] = "❌ DEAD"
                    self.attempt_restart(session)
            
            return status
        except Exception as e:
            self.log("ERROR", f"Tmux check failed: {e}")
            return {}
    
    def attempt_restart(self, session_name):
        """Restart a dead tmux session"""
        self.log("REPAIR", f"Restarting {session_name}...")
        
        restart_commands = {
            "v2-scanner": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 v2_scanner.py 2>&1 | tee logs/v2_scanner.log",
            "v2-validator": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 v2_validator.py 2>&1 | tee logs/v2_validator.log",
            "v2-dynamic-risk": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 v2_dynamic_risk.py 2>&1 | tee logs/v2_dynamic_risk.log",
            "v4-master": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 v4_master_controller.py 2>&1 | tee logs/v4_master.log",
            "v4-backtest": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 v4_realistic_backtest.py 2>&1 | tee logs/v4_backtest.log",
            "telegram-poll": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 poll_telegram.py 2>&1 | tee logs/poll_telegram.log",
            "meta-agent": f"cd {AGENTS_DIR} && PYTHONUNBUFFERED=1 python3 meta_agent.py 2>&1 | tee logs/meta_agent.log",
        }
        
        if session_name in restart_commands:
            try:
                cmd = f"tmux new-session -d -s {session_name} '{restart_commands[session_name]}'"
                subprocess.run(cmd, shell=True, timeout=5)
                self.log("REPAIR", f"✅ {session_name} restarted")
                self.repairs_done.append({
                    "time": datetime.now().isoformat(),
                    "type": "restart",
                    "session": session_name
                })
            except Exception as e:
                self.log("ERROR", f"Failed to restart {session_name}: {e}")
    
    def check_log_errors(self):
        """Scan recent log files for errors"""
        error_patterns = [
            "Error", "Exception", "Traceback", "Failed",
            "Connection refused", "Timeout", "JSON decode",
            "KeyError", "IndexError", "NameError"
        ]
        
        errors_found = []
        log_files = [
            "v2_scanner.log", "v2_validator.log", "v2_dynamic_risk.log",
            "v4_master.log", "v4_backtest.log", "poll_telegram.log"
        ]
        
        for log_file in log_files:
            path = f"{LOGS_DIR}/{log_file}"
            if not os.path.exists(path):
                continue
                
            try:
                # Read last 50 lines
                with open(path, 'r') as f:
                    lines = f.readlines()[-50:]
                
                for line in lines:
                    for pattern in error_patterns:
                        if pattern in line and "meta_agent" not in line:
                            errors_found.append({
                                "file": log_file,
                                "line": line.strip()[:200],
                                "pattern": pattern,
                                "time": datetime.now().isoformat()
                            })
                            break
            except (IOError, OSError, UnicodeDecodeError) as e:
                self.log("ERROR", f"Log check failed for {log_file}: {e}")
            except Exception as e:
                self.log("ERROR", f"Unexpected error reading {log_file}: {e}")
                traceback.print_exc()
        
        return errors_found
    
    def check_disk_space(self):
        """Check if disk is getting full"""
        try:
            result = subprocess.run(
                ["df", "-h", "."],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                usage = parts[4]  # e.g., "75%"
                self.log("INFO", f"Disk usage: {usage}")
                
                # Clean old logs if >80%
                if int(usage.replace('%', '')) > 80:
                    self.clean_old_logs()
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.log("ERROR", f"Disk check subprocess error: {e}")
        except (IndexError, ValueError) as e:
            self.log("ERROR", f"Disk check parse error: {e}")
        except Exception as e:
            self.log("ERROR", f"Disk check unexpected error: {e}")
            traceback.print_exc()
    
    def clean_old_logs(self):
        """Remove log files older than retention period"""
        self.log("REPAIR", "Cleaning old log files...")
        try:
            cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
            for filename in os.listdir(LOGS_DIR):
                if filename.endswith('.log'):
                    filepath = os.path.join(LOGS_DIR, filename)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        os.remove(filepath)
                        self.log("REPAIR", f"Removed old log: {filename}")
        except (OSError, PermissionError) as e:
            self.log("ERROR", f"Log cleanup OS error: {e}")
        except Exception as e:
            self.log("ERROR", f"Log cleanup unexpected error: {e}")
            traceback.print_exc()
    
    def check_json_integrity(self):
        """Check if state JSON files are valid"""
        json_files = [
            "tmp_state/scanner_output.json",
            "tmp_state/validator_output.json",
            "tmp_state/dynamic_risk_output.json",
            "tmp_state/regime_output.json",
            "tmp_state/fomo_output.json",
            "tmp_state/auto_mode.json"
        ]
        
        for filepath in json_files:
            full_path = os.path.join(AGENTS_DIR, filepath)
            if not os.path.exists(full_path):
                continue
                
            try:
                with open(full_path, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.log("ERROR", f"Corrupted JSON: {filepath} — fixing...")
                # Backup and reset
                backup = full_path + ".broken"
                os.rename(full_path, backup)
                safe_write_json(full_path, {})
                self.repairs_done.append({
                    "time": datetime.now().isoformat(),
                    "type": "json_fix",
                    "file": filepath
                })
    
    # ═══════════════════════════════════════════
    # RESEARCH MODULE
    # ═══════════════════════════════════════════
    
    def research_crypto_tools(self):
        """Research new crypto APIs and tools"""
        self.log("RESEARCH", "Scanning for new crypto tools...")
        
        findings = []
        
        # Check DexScreener API status
        try:
            resp = requests.get(
                "https://api.dexscreener.com/latest/dex/search?q=solana",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                pair_count = len(data.get("pairs", []))
                findings.append({
                    "tool": "DexScreener API",
                    "status": "✅ ACTIVE",
                    "pairs_found": pair_count,
                    "time": datetime.now().isoformat()
                })
        except Exception as e:
            findings.append({
                "tool": "DexScreener API",
                "status": f"❌ ERROR: {str(e)[:50]}",
                "time": datetime.now().isoformat()
            })
        
        # Check Jupiter API (Solana DEX aggregator)
        try:
            resp = requests.get(
                "https://price.jup.ag/v4/price?ids=So11111111111111111111111111111111111111112",
                timeout=10
            )
            if resp.status_code == 200:
                findings.append({
                    "tool": "Jupiter Price API",
                    "status": "✅ ACTIVE",
                    "time": datetime.now().isoformat()
                })
        except Exception as e:
            findings.append({
                "tool": "Jupiter Price API",
                "status": f"❌ UNAVAILABLE: {str(e)[:50]}",
                "time": datetime.now().isoformat()
            })
        
        # Check Birdeye API
        try:
            resp = requests.get(
                "https://public-api.birdeye.so/public/price?address=So11111111111111111111111111111111111111112",
                timeout=10
            )
            if resp.status_code == 200:
                findings.append({
                    "tool": "Birdeye API",
                    "status": "✅ ACTIVE",
                    "time": datetime.now().isoformat()
                })
        except Exception as e:
            findings.append({
                "tool": "Birdeye API",
                "status": f"❌ UNAVAILABLE",
                "time": datetime.now().isoformat()
            })
        
        # Check Pump.fun
        try:
            resp = requests.get("https://pump.fun", timeout=10)
            findings.append({
                "tool": "Pump.fun",
                "status": "✅ ACTIVE" if resp.status_code == 200 else "❌ DOWN",
                "time": datetime.now().isoformat()
            })
        except:
            findings.append({
                "tool": "Pump.fun",
                "status": "❌ UNREACHABLE",
                "time": datetime.now().isoformat()
            })
        
        self.research_findings = findings
        self.log("RESEARCH", f"Found {len(findings)} tools, {sum(1 for f in findings if '✅' in f['status'])} active")
        
        # Update knowledge base
        self.knowledge["research_history"].append({
            "time": datetime.now().isoformat(),
            "findings": findings
        })
        self.save_knowledge()
        
        return findings
    
    def scan_for_improvements(self):
        """Analyze system performance and suggest improvements"""
        self.log("RESEARCH", "Analyzing system performance...")
        
        # Check signal quality from recent history
        try:
            history = safe_read_json(f"{AGENTS_DIR}/logs/trade_history.json", [])
            if len(history) >= 5:
                # Calculate win rate
                wins = sum(1 for h in history if h.get("result") == "WIN")
                total = len(history)
                win_rate = wins / total * 100
                
                self.log("INFO", f"Recent win rate: {win_rate:.1f}% ({wins}/{total})")
                
                if win_rate < 40:
                    self.log("RESEARCH", "⚠️ Win rate below 40% — suggest tightening filters")
                    self.knowledge["system_patterns"]["low_win_rate"] = {
                        "rate": win_rate,
                        "suggestion": "Increase confidence threshold or reduce scan frequency",
                        "time": datetime.now().isoformat()
                    }
                elif win_rate > 70:
                    self.log("RESEARCH", "🚀 Win rate excellent — can be more aggressive")
                    self.knowledge["system_patterns"]["high_win_rate"] = {
                        "rate": win_rate,
                        "suggestion": "Consider increasing position sizes",
                        "time": datetime.now().isoformat()
                    }
        except Exception as e:
            self.log("ERROR", f"Performance analysis failed: {e}")
        
        self.save_knowledge()
    
    # ═══════════════════════════════════════════
    # AUTO-REPAIR ENGINE
    # ═══════════════════════════════════════════
    
    def auto_repair(self):
        """Run all auto-repair checks"""
        self.log("REPAIR", "Running auto-repair cycle...")
        
        # 1. Check and fix JSON files
        self.check_json_integrity()
        
        # 2. Check if state files are stale (>10 min old)
        stale_threshold = datetime.now() - timedelta(minutes=10)
        state_files = [
            ("tmp_state/scanner_output.json", "v2-scanner"),
            ("tmp_state/validator_output.json", "v2-validator"),
            ("tmp_state/dynamic_risk_output.json", "v2-dynamic-risk"),
        ]
        
        for filepath, session in state_files:
            full_path = os.path.join(AGENTS_DIR, filepath)
            if os.path.exists(full_path):
                mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                if mtime < stale_threshold:
                    self.log("REPAIR", f"{filepath} is stale — restarting {session}")
                    self.attempt_restart(session)
        
        # 3. Check paper trading file
        paper_trading = f"{AGENTS_DIR}/logs/paper_trading.json"
        if not os.path.exists(paper_trading):
            self.log("REPAIR", "Creating fresh paper_trading.json...")
            safe_write_json(paper_trading, {
                "balance": 10000.0,
                "positions": [],
                "history": [],
                "metrics": {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0
                }
            })
            self.repairs_done.append({
                "time": datetime.now().isoformat(),
                "type": "file_creation",
                "file": "paper_trading.json"
            })
        
        # 4. Check auto_mode config
        auto_mode = f"{AGENTS_DIR}/tmp_state/auto_mode.json"
        if not os.path.exists(auto_mode):
            self.log("REPAIR", "Creating auto_mode.json...")
            safe_write_json(auto_mode, {"enabled": False})
        
        self.save_knowledge()
    
    def generate_health_report(self):
        """Generate system health report"""
        uptime = datetime.now() - self.start_time
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "uptime_hours": round(uptime.total_seconds() / 3600, 2),
            "tmux_status": self.check_tmux_sessions(),
            "recent_errors": self.check_log_errors()[:5],
            "repairs_done_24h": len([r for r in self.repairs_done 
                if datetime.fromisoformat(r["time"]) > datetime.now() - timedelta(hours=24)]),
            "research_findings": len(self.research_findings),
            "knowledge_entries": len(self.knowledge.get("fixes_applied", []))
        }
        
        safe_write_json(f"{AGENTS_DIR}/tmp_state/meta_health_report.json", report)
        return report
    
    # ═══════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════
    
    def health_loop(self):
        """Continuous health monitoring"""
        while self.running:
            try:
                self.log("HEALTH", "Running health check...")
                self.check_tmux_sessions()
                self.check_disk_space()
                self.check_log_errors()
                self.generate_health_report()
                
                time.sleep(HEALTH_CHECK_INTERVAL)
            except Exception as e:
                self.log("ERROR", f"Health loop error: {e}")
                time.sleep(10)
    
    def research_loop(self):
        """Continuous research and improvement discovery"""
        while self.running:
            try:
                self.log("RESEARCH", "Running research cycle...")
                self.research_crypto_tools()
                self.scan_for_improvements()
                
                time.sleep(RESEARCH_INTERVAL)
            except Exception as e:
                self.log("ERROR", f"Research loop error: {e}")
                time.sleep(60)
    
    def repair_loop(self):
        """Continuous auto-repair"""
        while self.running:
            try:
                self.log("REPAIR", "Running repair cycle...")
                self.auto_repair()
                
                time.sleep(REPAIR_INTERVAL)
            except Exception as e:
                self.log("ERROR", f"Repair loop error: {e}")
                time.sleep(30)
    
    def start(self):
        """Start all monitoring threads"""
        self.log("INFO", "🧠 META AGENT starting...")
        self.log("INFO", f"Monitoring {AGENTS_DIR}")
        self.log("INFO", f"Health: {HEALTH_CHECK_INTERVAL}s | Research: {RESEARCH_INTERVAL}s | Repair: {REPAIR_INTERVAL}s")
        
        # Start all loops in separate threads
        threads = [
            threading.Thread(target=self.health_loop, name="health"),
            threading.Thread(target=self.research_loop, name="research"),
            threading.Thread(target=self.repair_loop, name="repair")
        ]
        
        for t in threads:
            t.daemon = True
            t.start()
        
        self.log("INFO", f"✅ {len(threads)} monitoring threads active")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("INFO", "Shutting down Meta Agent...")
            self.running = False

def main():
    agent = MetaAgent()
    agent.start()

if __name__ == "__main__":
    main()
