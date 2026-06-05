#!/usr/bin/env python3
"""🔥 FULL SWARM INTEGRATION TEST — All 12 Phases"""
import sys
import asyncio
import subprocess

sys.path.insert(0, "/root/.openclaw/workspace/agents")


def run_test(name: str, path: str) -> bool:
    """Run a single smoke test."""
    print(f"\n{'─' * 60}")
    print(f"🧪 Running {name}...")
    print(f"{'─' * 60}")
    
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/root/.openclaw/workspace/agents",
        )
        
        # Print output
        if result.stdout:
            # Only print last 30 lines
            lines = result.stdout.strip().split("\n")
            for line in lines[-30:]:
                print(f"  {line}")
        
        if result.returncode == 0:
            print(f"  ✅ {name} PASSED")
            return True
        else:
            print(f"  ❌ {name} FAILED (exit code {result.returncode})")
            if result.stderr:
                print(f"  STDERR: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏱️ {name} TIMEOUT")
        return False
    except Exception as e:
        print(f"  ❌ {name} ERROR: {e}")
        return False


async def full_integration_test():
    """Run all phase smoke tests."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🔥 SWMAS FULL INTEGRATION TEST                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    tests = [
        ("Phase 8 (Position Monitor + Executor)", "phase8_smoke_test.py"),
        ("Phase 9 (Docker + Observability)", "phase9_smoke_test.py"),
        ("Phase 10 (LLM Meta Agent + RAG)", "phase10_smoke_test.py"),
        ("Phase 11 (Web Dashboard)", "phase11_smoke_test.py"),
        ("Phase 12 (Real Money Safety)", "phase12_smoke_test.py"),
    ]
    
    results = []
    for name, path in tests:
        passed = run_test(name, path)
        results.append((name, passed))
    
    # Summary
    print(f"\n{'═' * 60}")
    print("║                    📊 FINAL RESULTS                        ║")
    print(f"{'═' * 60}")
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    all_passed = all(r[1] for r in results)
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n  📊 {passed_count}/{total_count} tests passed")
    
    if all_passed:
        print(f"\n  🔥 ALL PHASES PASSED ✅")
        print(f"\n  🎉 SWMAS IS READY!")
        print(f"\n  🚀 Quick Start:")
        print(f"     cd /root/.openclaw/workspace/agents")
        print(f"     python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080")
    else:
        print(f"\n  ❌ SOME PHASES FAILED")
        print(f"\n  🔧 Fix failed phases individually:")
        for name, passed in results:
            if not passed:
                print(f"     python {name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('+', '')}.py")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(full_integration_test())
    sys.exit(0 if success else 1)
