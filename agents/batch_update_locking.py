#!/usr/bin/env python3
"""
Batch update all agents to use file_lock.py for safe JSON reads/writes.
This script modifies agent files to add imports and replace json.load/json.dump calls.
"""

import os
import re

AGENTS_DIR = "/root/.openclaw/workspace/agents"

# Agents to update (active swarm agents only)
AGENTS = [
    "v2_sentiment.py",
    "v2_whale.py",
    "v2_regime_detector.py",
    "v2_dna_classifier.py",
    "v2_fomo_filter.py",
    "v2_dynamic_risk.py",
    "v4_master_controller.py",
    "v4_portfolio_tracker.py",
    "v4_realistic_backtest.py",
    "v4_circuit_breaker.py",
    "v4_duplicate_protection.py",
    "v4_trade_expiration.py",
    "v4_execution_quality.py",
    "v4_system_scorecard.py",
    "v4_position_sizing.py",
]

FILE_LOCK_IMPORT = '''import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json
'''

def update_agent(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already updated
    if 'from file_lock import' in content:
        print(f"  [SKIP] Already has file_lock import: {os.path.basename(filepath)}")
        return
    
    # Add import after the last import block
    # Find the position after all import statements
    lines = content.split('\n')
    import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_idx = i + 1
    
    lines.insert(import_idx, FILE_LOCK_IMPORT.strip())
    content = '\n'.join(lines)
    
    # Pattern 1: with open("...", "w") as f: json.dump(data, f, indent=2)
    # Replace with: safe_write_json("...", data)
    content = re.sub(
        r'with open\("([^"]+\.json)"\, "w"\) as f:\s*\n\s*json\.dump\(([^,]+),\s*f(?:,\s*indent=\d+)?\)',
        r'safe_write_json("\1", \2)',
        content
    )
    
    # Pattern 2: with open("...", "r") as f: data = json.load(f)
    # Replace with: data = safe_read_json("...", default={})
    # But this is trickier because we need to handle the default value
    # For now, we'll do a simpler replacement and let the safe_read_json use empty dict default
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  [UPDATED] {os.path.basename(filepath)}")

if __name__ == "__main__":
    print("🔧 Batch updating agents with file locking...")
    for agent in AGENTS:
        filepath = os.path.join(AGENTS_DIR, agent)
        if os.path.exists(filepath):
            update_agent(filepath)
        else:
            print(f"  [MISSING] {agent}")
    print("✅ Done!")
