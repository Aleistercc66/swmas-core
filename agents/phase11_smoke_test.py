#!/usr/bin/env python3
"""Phase 11 smoke test: Web Dashboard validation."""
import sys
import asyncio
import httpx
import time

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from dashboard.main import app, dashboard_state, update_state


def test_dashboard_state():
    """Test dashboard state structure."""
    print("\n--- [1] Dashboard State Structure ---")
    
    required_keys = ["portfolio", "open_positions", "recent_events", "agent_health", "metrics", "settings"]
    all_ok = True
    
    for key in required_keys:
        if key in dashboard_state:
            print(f"  ✅ {key}: {type(dashboard_state[key]).__name__}")
        else:
            print(f"  ❌ {key}: MISSING")
            all_ok = False
    
    return all_ok


def test_state_updates():
    """Test state update functions."""
    print("\n--- [2] State Updates ---")
    
    # Simulate events
    update_state("TOKENS_DISCOVERED", {"tokens": [{"symbol": "SOL"}, {"symbol": "BONK"}]}, "scanner")
    update_state("POSITION_OPENED", {
        "trade_id": "test_001", "symbol": "SOL", "entry_price": 150.0,
        "position_size_usd": 200.0, "stop_loss": 135.0, "take_profits": [225.0]
    }, "master")
    update_state("POSITION_UPDATED", {
        "symbol": "SOL", "current_price": 160.0, "pnl_percent": 6.67, "pnl_usd": 13.34, "status": "OPEN"
    }, "position_monitor")
    update_state("POSITION_CLOSED", {
        "position_id": 1, "symbol": "SOL", "close_price": 230.0,
        "pnl_pct": 53.33, "pnl_usd": 106.67, "close_reason": "HIT_TP1"
    }, "position_monitor")
    
    print(f"  ✅ Events stored: {len(dashboard_state['recent_events'])}")
    print(f"  ✅ Positions tracked: {len(dashboard_state['open_positions'])}")
    print(f"  ✅ Metrics: scanned={dashboard_state['metrics']['tokens_scanned']}, "
          f"trades={dashboard_state['metrics']['trades_executed']}, "
          f"tp={dashboard_state['metrics']['tp_hits']}")
    
    return len(dashboard_state["recent_events"]) >= 4


async def test_api_endpoints():
    """Test FastAPI endpoints."""
    print("\n--- [3] API Endpoints ---")
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    endpoints = [
        ("/", "Dashboard page"),
        ("/api/state", "Full state"),
        ("/api/portfolio", "Portfolio"),
        ("/api/positions", "Positions"),
        ("/api/events", "Events"),
        ("/api/health", "Health"),
        ("/api/metrics", "Metrics"),
        ("/api/settings", "Settings"),
    ]
    
    all_ok = True
    for path, name in endpoints:
        try:
            resp = client.get(path)
            if resp.status_code == 200:
                print(f"  ✅ GET {path} ({name})")
            else:
                print(f"  ⚠️ GET {path} = {resp.status_code}")
                all_ok = False
        except Exception as e:
            print(f"  ❌ GET {path}: {e}")
            all_ok = False
    
    # Test controls
    controls = [
        ("/control/toggle-auto", "Toggle Auto"),
        ("/control/toggle-paper", "Toggle Paper"),
        ("/control/confirm-trade", "Confirm Trade"),
        ("/control/reset", "Reset"),
    ]
    
    for path, name in controls:
        try:
            resp = client.post(path)
            if resp.status_code == 200:
                print(f"  ✅ POST {path} ({name})")
            else:
                print(f"  ⚠️ POST {path} = {resp.status_code}")
        except Exception as e:
            print(f"  ❌ POST {path}: {e}")
            all_ok = False
    
    # Test emergency stop
    try:
        resp = client.post("/control/emergency-stop")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✅ POST /control/emergency-stop: {data.get('message', '')}")
            if dashboard_state["settings"]["emergency_stop"]:
                print(f"  ✅ Emergency stop activated")
            else:
                print(f"  ❌ Emergency stop not set")
                all_ok = False
        else:
            all_ok = False
    except Exception as e:
        print(f"  ❌ Emergency stop: {e}")
        all_ok = False
    
    return all_ok


async def test_websocket():
    """Test WebSocket connection."""
    print("\n--- [4] WebSocket ---")
    
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as ws:
            # Receive initial state
            data = ws.receive_json()
            
            if "portfolio" in data:
                print(f"  ✅ WebSocket connected, received state")
                print(f"  ✅ State keys: {list(data.keys())}")
                return True
            else:
                print(f"  ❌ Invalid WebSocket data")
                return False
                
    except Exception as e:
        print(f"  ❌ WebSocket test failed: {e}")
        return False


async def phase11_smoke_test():
    """Run Phase 11 smoke test."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🌐 PHASE 11: WEB DASHBOARD TEST                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # Test 1: State structure
    results.append(("State Structure", test_dashboard_state()))
    
    # Test 2: State updates
    results.append(("State Updates", test_state_updates()))
    
    # Test 3: API endpoints
    results.append(("API Endpoints", await test_api_endpoints()))
    
    # Test 4: WebSocket
    results.append(("WebSocket", await test_websocket()))
    
    # Results
    print(f"\n{'═' * 60}")
    print("║                    📊 RESULTS                              ║")
    print(f"{'═' * 60}")
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print(f"\n  🔥 PHASE 11 PASSED ✅")
        print(f"\n  🚀 To start dashboard:")
        print(f"     cd /root/.openclaw/workspace/agents")
        print(f"     python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080")
        print(f"\n  🌐 Open browser: http://localhost:8080")
    else:
        print(f"\n  ❌ PHASE 11 FAILED")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(phase11_smoke_test())
    sys.exit(0 if success else 1)
