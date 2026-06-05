#!/usr/bin/env python3
"""
Batch update remaining json.load calls to safe_read_json.
This handles the common pattern: with open("...", "r") as f: data = json.load(f)
"""

import os
import re

AGENTS_DIR = "/root/.openclaw/workspace/agents"

AGENTS = [
    "v2_dna_classifier.py",
    "v2_dynamic_risk.py",
    "v2_fomo_filter.py",
    "v4_circuit_breaker.py",
    "v4_duplicate_protection.py",
    "v4_master_controller.py",
    "v4_portfolio_tracker.py",
    "v4_realistic_backtest.py",
    "v4_trade_expiration.py",
    "v4_execution_quality.py",
    "v4_system_scorecard.py",
    "v4_position_sizing.py",
]

def update_reads(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern: try:\n    with open("...", "r") as f:\n        data = json.load(f)\nexcept:\n    pass
    # Replace with: data = safe_read_json("...", {})
    # But we need to handle the except block too
    
    # Simpler pattern: with open("...", "r") as f:\n        data = json.load(f)
    content = re.sub(
        r'with open\("([^"]+\.json)"\, "r"\) as f:\s*\n\s*([^=\n]+)\s*=\s*json\.load\(f\)',
        r'\2 = safe_read_json("\1", {})',
        content
    )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  [READS UPDATED] {os.path.basename(filepath)}")

if __name__ == "__main__":
    print("🔧 Updating read operations to safe_read_json...")
    for agent in AGENTS:
        filepath = os.path.join(AGENTS_DIR, agent)
        if os.path.exists(filepath):
            update_reads(filepath)
    print("✅ Done!")
