#!/usr/bin/env python3
"""🌐 FastAPI Dashboard — Real-time swarm control & visibility."""
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from dashboard.models import DashboardState, PortfolioSummary, PositionView, EventView, AgentHealthView

# ── App ──

app = FastAPI(title="KreoPoly Swarm Dashboard", version="1.0")

# Static & Templates
APP_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# ── Global State ──

dashboard_state: Dict[str, Any] = {
    "portfolio": {
        "balance": 10000.0,
        "open_positions": 0,
        "win_rate": 0.0,
        "daily_pnl": 0.0,
        "total_pnl": 0.0,
        "drawdown": 0.0,
    },
    "open_positions": [],
    "recent_events": [],
    "agent_health": [
        {"agent": "scanner", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
        {"agent": "validator", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
        {"agent": "risk_engine", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
        {"agent": "master", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
        {"agent": "position_monitor", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
        {"agent": "meta_agent", "status": "healthy", "last_check": datetime.utcnow().isoformat()},
    ],
    "metrics": {
        "tokens_scanned": 0,
        "signals_generated": 0,
        "trades_executed": 0,
        "tp_hits": 0,
        "sl_hits": 0,
    },
    "settings": {
        "auto_mode": False,
        "paper_mode": True,
        "emergency_stop": False,
    }
}

# WebSocket connections
websocket_clients: List[WebSocket] = []


# ── Helpers ──

def update_state(event_type: str, data: Dict[str, Any], source: str = "system"):
    """Update dashboard state from events."""
    timestamp = datetime.utcnow().isoformat()
    
    # Add to recent events
    event_entry = {
        "event_type": event_type,
        "source": source,
        "timestamp": timestamp,
        "data": data,
    }
    dashboard_state["recent_events"].insert(0, event_entry)
    if len(dashboard_state["recent_events"]) > 50:
        dashboard_state["recent_events"] = dashboard_state["recent_events"][:50]
    
    # Update positions
    if event_type == "POSITION_OPENED":
        dashboard_state["portfolio"]["open_positions"] += 1
        dashboard_state["metrics"]["trades_executed"] += 1
        pos = {
            "trade_id": data.get("trade_id", "?"),
            "symbol": data.get("symbol", "?"),
            "entry_price": data.get("entry_price", 0),
            "current_price": data.get("entry_price", 0),
            "pnl_percent": 0.0,
            "pnl_usd": 0.0,
            "status": "OPEN",
            "stop_loss": data.get("stop_loss", 0),
            "take_profits": data.get("take_profits", []),
        }
        dashboard_state["open_positions"].append(pos)
    
    elif event_type == "POSITION_UPDATED":
        symbol = data.get("symbol", "?")
        for pos in dashboard_state["open_positions"]:
            if pos["symbol"] == symbol:
                pos["current_price"] = data.get("current_price", pos["current_price"])
                pos["pnl_percent"] = data.get("pnl_percent", 0)
                pos["pnl_usd"] = data.get("pnl_usd", 0)
                pos["status"] = data.get("status", "OPEN")
                break
    
    elif event_type == "POSITION_CLOSED":
        dashboard_state["portfolio"]["open_positions"] -= 1
        symbol = data.get("symbol", "?")
        dashboard_state["open_positions"] = [
            p for p in dashboard_state["open_positions"] if p["symbol"] != symbol
        ]
        pnl = data.get("pnl_pct", 0)
        dashboard_state["portfolio"]["total_pnl"] += pnl
        dashboard_state["portfolio"]["daily_pnl"] += pnl
        if data.get("close_reason", "").startswith("HIT_TP"):
            dashboard_state["metrics"]["tp_hits"] += 1
        elif data.get("close_reason", "") == "BREACHED_SL":
            dashboard_state["metrics"]["sl_hits"] += 1
    
    elif event_type == "TOKENS_DISCOVERED":
        tokens = data.get("tokens", [])
        dashboard_state["metrics"]["tokens_scanned"] += len(tokens)
    
    elif event_type == "RISK_ASSESSED":
        signals = data.get("signals", [])
        dashboard_state["metrics"]["signals_generated"] += len(signals)
    
    elif event_type == "ALERT" and data.get("alert_type") == "META_DECISION":
        decision = data.get("decision", "")
        if decision == "SHUTDOWN":
            dashboard_state["settings"]["emergency_stop"] = True


async def broadcast_update():
    """Send state to all connected WebSocket clients."""
    disconnected = []
    for ws in websocket_clients:
        try:
            await ws.send_json(dashboard_state)
        except Exception:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in websocket_clients:
            websocket_clients.remove(ws)


# ── Routes ──

from fastapi.responses import FileResponse

@app.get("/")
async def index(request: Request):
    """Main dashboard page."""
    template_path = APP_DIR / "templates" / "index.html"
    return FileResponse(str(template_path))


@app.get("/api/state")
async def get_state():
    """Get full dashboard state."""
    return dashboard_state


@app.get("/api/portfolio")
async def get_portfolio():
    """Get portfolio summary."""
    return dashboard_state["portfolio"]


@app.get("/api/positions")
async def get_positions():
    """Get open positions."""
    return {"positions": dashboard_state["open_positions"]}


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events."""
    return {"events": dashboard_state["recent_events"][:limit]}


@app.get("/api/health")
async def get_health():
    """Get agent health status."""
    return {"agents": dashboard_state["agent_health"]}


@app.get("/api/metrics")
async def get_metrics():
    """Get trading metrics."""
    return dashboard_state["metrics"]


@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    return dashboard_state["settings"]


# ── Controls ──

@app.post("/control/confirm-trade")
async def confirm_trade():
    """Manually confirm a pending trade."""
    update_state("MANUAL_ACTION", {"action": "CONFIRM_TRADE"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "Trade confirmed"}


@app.post("/control/toggle-auto")
async def toggle_auto():
    """Toggle auto execution mode."""
    current = dashboard_state["settings"]["auto_mode"]
    dashboard_state["settings"]["auto_mode"] = not current
    status = "ON" if not current else "OFF"
    update_state("MANUAL_ACTION", {"action": "TOGGLE_AUTO", "status": status}, "user")
    await broadcast_update()
    return {"status": "ok", "message": f"Auto mode: {status}"}


@app.post("/control/toggle-paper")
async def toggle_paper():
    """Toggle paper/real trading mode."""
    current = dashboard_state["settings"]["paper_mode"]
    dashboard_state["settings"]["paper_mode"] = not current
    mode = "PAPER" if not current else "REAL"
    update_state("MANUAL_ACTION", {"action": "TOGGLE_PAPER", "mode": mode}, "user")
    await broadcast_update()
    return {"status": "ok", "message": f"Trading mode: {mode}"}


@app.post("/control/emergency-stop")
async def emergency_stop():
    """Emergency stop all trading."""
    dashboard_state["settings"]["emergency_stop"] = True
    dashboard_state["settings"]["auto_mode"] = False
    update_state("MANUAL_ACTION", {"action": "EMERGENCY_STOP"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "🛑 EMERGENCY STOP ACTIVATED"}


@app.post("/control/reset")
async def reset_system():
    """Reset dashboard state."""
    dashboard_state["portfolio"] = {
        "balance": 10000.0,
        "open_positions": 0,
        "win_rate": 0.0,
        "daily_pnl": 0.0,
        "total_pnl": 0.0,
        "drawdown": 0.0,
    }
    dashboard_state["open_positions"] = []
    dashboard_state["recent_events"] = []
    dashboard_state["metrics"] = {
        "tokens_scanned": 0,
        "signals_generated": 0,
        "trades_executed": 0,
        "tp_hits": 0,
        "sl_hits": 0,
    }
    dashboard_state["settings"]["emergency_stop"] = False
    update_state("MANUAL_ACTION", {"action": "RESET"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "System reset"}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        # Send initial state
        await websocket.send_json(dashboard_state)
        
        while True:
            # Keep connection alive and listen for ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)
    except Exception:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


# ── Event Bridge ──

async def event_bridge_listener():
    """Listen to swarm events and update dashboard."""
    try:
        from core import get_event_bus, EventType
        bus = await get_event_bus()
        
        async def handle_event(event):
            update_state(event.event_type, event.data, event.source)
            await broadcast_update()
        
        # Subscribe to all relevant events
        for et in [EventType.TOKENS_DISCOVERED, EventType.TOKENS_VALIDATED,
                   EventType.RISK_ASSESSED, EventType.POSITION_OPENED,
                   EventType.POSITION_UPDATED, EventType.POSITION_CLOSED,
                   EventType.ALERT, EventType.SIGNAL_GENERATED]:
            await bus.subscribe(et, "dashboard", handle_event)
        
        print("Dashboard event bridge connected")
        
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Event bridge error: {e}")


# ── Startup ──

@app.on_event("startup")
async def startup():
    """Start event bridge on startup."""
    asyncio.create_task(event_bridge_listener())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
