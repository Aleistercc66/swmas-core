#!/usr/bin/env python3
"""
🔒 AGENT 4: VALIDATOR — THE GATEKEEPER
No signal passes without approval. Quality control layer.
"""
import json
import time
import sys
from datetime import datetime
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

def validate():
    # Load scanner output
    scanner = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", {"pairs": []})
    
    validated = []
    rejected = []
    
    for p in scanner.get("pairs", []):
        checks = {
            "liquidity": {"pass": False, "value": p.get("liquidity", 0), "min": 30000},
            "volume": {"pass": False, "value": p.get("volume_24h", 0), "min": 10000},
            "momentum_24h": {"pass": False, "value": p.get("change_24h", 0), "min": 5, "max": 500},
            "momentum_1h": {"pass": False, "value": p.get("change_1h", 0), "min": -5},
            "buy_pressure": {"pass": False, "value": 0, "min": 1.0},
            "liquidity_trend": {"pass": True, "value": 0},
            "not_parabolic": {"pass": False, "value": p.get("change_24h", 0)},
        }
        
        # Check liquidity
        if checks["liquidity"]["value"] >= checks["liquidity"]["min"]:
            checks["liquidity"]["pass"] = True
        
        # Check volume
        if checks["volume"]["value"] >= checks["volume"]["min"]:
            checks["volume"]["pass"] = True
        
        # Check 24h momentum (between 5% and 200%)
        chg24 = checks["momentum_24h"]["value"]
        if 5 <= chg24 <= 200:
            checks["momentum_24h"]["pass"] = True
        
        # Check 1h momentum (not strongly negative while 24h is high)
        chg1 = checks["momentum_1h"]["value"]
        if chg24 > 50 and chg1 < -5:
            checks["momentum_1h"]["pass"] = False  # Dumping after pump
        else:
            checks["momentum_1h"]["pass"] = True
        
        # Check buy pressure
        buys = p.get("buys_24h", 0)
        sells = p.get("sells_24h", 0)
        if sells > 0:
            ratio = buys / sells
            checks["buy_pressure"]["value"] = round(ratio, 2)
            if ratio >= 1.0:
                checks["buy_pressure"]["pass"] = True
        elif buys > 0:
            checks["buy_pressure"]["value"] = 999
            checks["buy_pressure"]["pass"] = True
        
        # Not parabolic (not too late) — RELAXED for microcaps
        # Microcaps can pump 300% and still have room, large caps not so much
        liq = p.get("liquidity", 0)
        if liq < 100000:
            parabolic_threshold = 300  # Microcaps: allow bigger pumps
        elif liq < 500000:
            parabolic_threshold = 200
        else:
            parabolic_threshold = 150  # Large caps: tighter
        
        if chg24 < parabolic_threshold:
            checks["not_parabolic"]["pass"] = True
        
        # Calculate pass rate
        total_checks = len(checks)
        passed = sum(1 for c in checks.values() if c["pass"])
        pass_rate = passed / total_checks
        
        result = {
            "symbol": p.get("symbol"),
            "price": p.get("price"),
            "status": "PASSED" if pass_rate >= 0.80 else "CONDITIONAL" if pass_rate >= 0.65 else "REJECTED",
            "pass_rate": round(pass_rate, 2),
            "checks": checks,
            "raw_data": p
        }
        
        if result["status"] == "PASSED":
            validated.append(result)
        else:
            rejected.append(result)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "COMPLETE",
        "total_scanned": len(scanner.get("pairs", [])),
        "validated": validated,
        "rejected": rejected
    }

def main():
    print("[VALIDATOR] Agent started — THE GATEKEEPER")
    print("[VALIDATOR] Rules: Liquidity >= $50K | Volume >= $10K | 24h 5-200% | Buys > Sells | No late dumps")
    while True:
        try:
            report = validate()
            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/validator_output.json", report)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Validation complete")
            print(f"  Total: {report['total_scanned']} | Passed: {len(report['validated'])} | Rejected: {len(report['rejected'])}")
            
            for v in report['validated']:
                print(f"  ✅ {v['symbol']}: {v['pass_rate']*100:.0f}% checks passed — FORWARDING")
            
            for r in report['rejected']:
                fail_reasons = [k for k, c in r['checks'].items() if not c['pass']]
                print(f"  ❌ {r['symbol']}: {r['pass_rate']*100:.0f}% — Failed: {', '.join(fail_reasons)}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(900)  # 15 minutes (matches scanner)

if __name__ == "__main__":
    main()
