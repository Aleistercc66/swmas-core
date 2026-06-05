import fcntl
import json
import os

# Persistent state directory (not /tmp/ which gets cleared on restart)
STATE_DIR = "/root/.openclaw/workspace/agents/tmp_state"
os.makedirs(STATE_DIR, exist_ok=True)

def safe_write_json(filepath, data):
    """Write JSON with exclusive file lock to prevent corruption."""
    with open(filepath, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)

def safe_read_json(filepath, default=None):
    """Read JSON with shared file lock. Returns default if file missing."""
    if not os.path.exists(filepath):
        return default if default is not None else {}
    with open(filepath, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            data = default if default is not None else {}
        fcntl.flock(f, fcntl.LOCK_UN)
    return data

def get_state_path(filename):
    """Get persistent state path (not /tmp/)."""
    return os.path.join(STATE_DIR, filename)

# Backward compatibility: if /tmp/ file exists and state dir doesn't, migrate

def migrate_tmp_files():
    """Migrate old /tmp/ files to persistent state directory."""
    tmp_files = [
        "scanner_output.json",
        "sentiment_output.json",
        "whale_output.json",
        "regime_output.json",
        "dna_output.json",
        "fomo_output.json",
        "validator_output.json",
        "dynamic_risk_output.json",
    ]
    for fname in tmp_files:
        tmp_path = f"/tmp/{fname}"
        state_path = os.path.join(STATE_DIR, fname)
        if os.path.exists(tmp_path) and not os.path.exists(state_path):
            try:
                data = safe_read_json(tmp_path)
                safe_write_json(state_path, data)
                print(f"[MIGRATE] {tmp_path} -> {state_path}")
            except Exception as e:
                print(f"[MIGRATE ERROR] {fname}: {e}")

if __name__ == "__main__":
    migrate_tmp_files()
    print("[file_lock] Initialized. State directory:", STATE_DIR)
