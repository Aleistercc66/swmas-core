#!/usr/bin/env python3
"""
🩺 SWMAS AUTO-HEAL MONITOR
Checks every 60 seconds if critical sessions are running.
Restarts any dead sessions automatically.
"""
import subprocess
import time
from datetime import datetime

SESSIONS = {
    "v2-scanner": {
        "cmd": "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_scanner_v31.py 2>&1 | tee logs/v2_scanner.log",
        "critical": True
    },
    "signal-gen": {
        "cmd": "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 signal_generator.py 2>&1 | tee logs/signal_generator.log",
        "critical": True
    },
    "realtime-dex": {
        "cmd": "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 realtime_dexscreener_v2.py 2>&1 | tee logs/realtime_dex.log",
        "critical": True
    }
}

def get_running_sessions():
    try:
        out = subprocess.check_output("tmux ls 2>/dev/null", shell=True, text=True)
        return {line.split(":")[0] for line in out.strip().split("\n") if line.strip()}
    except:
        return set()

def restart_session(name, cmd):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 {name} DOWN — Restarting...")
    subprocess.run(f"tmux kill-session -t {name} 2>/dev/null", shell=True)
    time.sleep(1)
    subprocess.run(f"tmux new-session -d -s {name} '{cmd}'", shell=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {name} RESTARTED")

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🩺 SWMAS Auto-Heal started")
    print(f"Monitoring: {', '.join(SESSIONS.keys())}")
    print("="*50)
    
    while True:
        running = get_running_sessions()
        
        for name, info in SESSIONS.items():
            if name not in running:
                restart_session(name, info["cmd"])
            else:
                pass  # Running fine
        
        time.sleep(60)

if __name__ == "__main__":
    main()
