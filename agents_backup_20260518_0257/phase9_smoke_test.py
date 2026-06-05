#!/usr/bin/env python3
"""Phase 9 smoke test: Docker + Observability config validation."""
import asyncio
import sys
import os
import subprocess

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType
from core.metrics import (
    TOKENS_SCANNED_TOTAL, TOKENS_APPROVED_TOTAL, POSITIONS_OPEN,
    PORTFOLIO_BALANCE, WIN_RATE, AGENT_HEALTH,
    start_metrics_server, set_agent_metric, record_event_published,
)


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def check_files():
    """Check all required files exist."""
    required = [
        "docker-compose.yml",
        "Dockerfile",
        "requirements.txt",
        "prometheus/prometheus.yml",
        "grafana/datasources/datasources.yml",
        "core/metrics.py",
    ]
    
    base = "/root/.openclaw/workspace/agents"
    results = {}
    
    for path in required:
        full = os.path.join(base, path)
        exists = os.path.exists(full)
        size = os.path.getsize(full) if exists else 0
        results[path] = {"exists": exists, "size": size}
    
    return results


async def test_prometheus_metrics():
    """Test that metrics can be recorded."""
    print("\n--- Testing Prometheus Metrics ---")
    
    # Record some metrics
    TOKENS_SCANNED_TOTAL.labels(source="dexscreener").inc(100)
    TOKENS_APPROVED_TOTAL.labels(tier="TIER_1").inc(5)
    TOKENS_APPROVED_TOTAL.labels(tier="TIER_2").inc(10)
    POSITIONS_OPEN.labels(symbol="SOL").set(2)
    PORTFOLIO_BALANCE.set(10500.50)
    WIN_RATE.set(65.5)
    set_agent_metric("scanner", "healthy")
    set_agent_metric("validator", "healthy")
    set_agent_metric("master", "healthy")
    record_event_published("tokens_discovered")
    record_event_published("risk_assessed")
    
    # Generate output
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    metrics_output = generate_latest().decode("utf-8")
    
    # Check key metrics present
    checks = {
        "tokens_scanned_total": "tokens_scanned_total" in metrics_output,
        "tokens_approved_total": "tokens_approved_total" in metrics_output,
        "positions_open": "positions_open" in metrics_output,
        "portfolio_balance_usd": "portfolio_balance_usd" in metrics_output,
        "win_rate_percent": "win_rate_percent" in metrics_output,
        "agent_health": "agent_health" in metrics_output,
        "events_published_total": "events_published_total" in metrics_output,
    }
    
    for metric, present in checks.items():
        status = "✅" if present else "❌"
        print(f"  {status} {metric}")
    
    return all(checks.values())


async def phase9_smoke_test():
    """Run Phase 9 smoke test."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     📊 PHASE 9: DOCKER + OBSERVABILITY TEST              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Check Docker
    print("\n--- Docker Check ---")
    docker_ok, docker_msg = check_docker()
    if docker_ok:
        print(f"  ✅ Docker: {docker_msg}")
    else:
        print(f"  ⚠️ Docker not available: {docker_msg}")
        print(f"  ℹ️ Config files created — ready for Docker deployment")
    
    # Check files
    print("\n--- File Structure ---")
    files = check_files()
    all_ok = True
    for path, info in files.items():
        status = "✅" if info["exists"] else "❌"
        size = info["size"]
        print(f"  {status} {path} ({size} bytes)")
        if not info["exists"]:
            all_ok = False
    
    # Test metrics
    metrics_ok = await test_prometheus_metrics()
    
    # Check Redis
    print("\n--- Redis Check ---")
    try:
        bus = await get_event_bus()
        print(f"  ✅ Redis: {'Connected' if bus.is_connected else 'Fallback'}")
        redis_ok = bus.is_connected
        await bus.disconnect()
    except Exception as e:
        print(f"  ❌ Redis error: {e}")
        redis_ok = False
    
    # Results
    print(f"\n{'═' * 60}")
    print("║                    📊 RESULTS                              ║")
    print(f"{'═' * 60}")
    
    success = all_ok and metrics_ok and redis_ok
    
    if success:
        print(f"\n  🔥 PHASE 9 PASSED ✅")
        print(f"  All configs ready for Docker deployment!")
        print(f"\n  🚀 To deploy:")
        print(f"     docker compose build")
        print(f"     docker compose up -d")
        print(f"\n  📊 Access:")
        print(f"     Prometheus: http://localhost:9090")
        print(f"     Grafana:    http://localhost:3000")
        print(f"     Redis:      localhost:6379")
        print(f"     DB:         localhost:5432")
    else:
        print(f"\n  ❌ PHASE 9 FAILED")
        if not all_ok:
            print(f"  Missing config files")
        if not metrics_ok:
            print(f"  Prometheus metrics not working")
        if not redis_ok:
            print(f"  Redis not connected")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(phase9_smoke_test())
    sys.exit(0 if success else 1)
