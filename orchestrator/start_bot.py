#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir('/root/.openclaw/workspace/orchestrator')
proc = subprocess.Popen(
    [sys.executable, 'telegram_orchestrator.py'],
    stdout=open('logs/bot_output.log', 'w'),
    stderr=subprocess.STDOUT
)
print(f'PID: {proc.pid}')
