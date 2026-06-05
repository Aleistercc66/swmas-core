#!/usr/bin/env python3
"""
🐺 Enhanced FastAPI Dashboard — Beast Mode v2
Multi-chain, composite scoring, real-time swarm control.
"""
import sys
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse

APP_DIR = Path(__file__).parent

# ── App ──
app = FastAPI(title="KreoPoly Swarm Dashboard v2", version="2.0")

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
        "risk_used": 0.0,
        "risk_budget": 500.0,
    },
    "open_positions": [],
    "active_signals": [],
    "recent_events": [],
    "agent_health": [
        {"agent": "scanner", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 92},
        {"agent": "validator", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 88},
        {"agent": "risk_engine", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 95},
        {"agent": "executor", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 90},
        {"agent": "position_monitor", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 87},
        {"agent": "meta_agent", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 85},
        {"agent": "telegram", "status": "healthy", "last_check": datetime.utcnow().isoformat(), "fitness": 93},
    ],
    "chains": {
        "solana": {"pairs": 30, "signals": 0, "volume": 2899677, "status": "active"},
        "base": {"pairs": 0, "signals": 0, "volume": 0, "status": "active"},
        "ethereum": {"pairs": 0, "signals": 0, "volume": 0, "status": "standby"},
    },
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
    },
    "market_regime": "CHOP",
    "whale_activity": [],
    "performance_history": [],
}

# WebSocket clients
websocket_clients: List[WebSocket] = []

# ── Helpers ──

def update_state(event_type: str, data: Dict[str, Any], source: str = "system"):
    """Update dashboard state from events."""
    timestamp = datetime.utcnow().isoformat()
    
    event_entry = {
        "event_type": event_type,
        "source": source,
        "timestamp": timestamp,
        "data": data,
    }
    dashboard_state["recent_events"].insert(0, event_entry)
    if len(dashboard_state["recent_events"]) > 100:
        dashboard_state["recent_events"] = dashboard_state["recent_events"][:100]
    
    # Position opened
    if event_type == "POSITION_OPENED":
        dashboard_state["portfolio"]["open_positions"] += 1
        dashboard_state["metrics"]["trades_executed"] += 1
        pos = {
            "trade_id": data.get("trade_id", "?"),
            "symbol": data.get("symbol", "?"),
            "chain": data.get("chain", "solana"),
            "entry_price": data.get("entry_price", 0),
            "current_price": data.get("entry_price", 0),
            "pnl_percent": 0.0,
            "pnl_usd": 0.0,
            "status": "OPEN",
            "stop_loss": data.get("stop_loss", 0),
            "take_profits": data.get("take_profits", []),
            "time_in_trade": "0m",
            "opened_at": time.time(),
            "score_at_entry": data.get("score", 0),
        }
        dashboard_state["open_positions"].append(pos)
        
        # Update risk used
        position_size = data.get("size_usd", 0)
        dashboard_state["portfolio"]["risk_used"] += position_size
    
    elif event_type == "POSITION_UPDATED":
        symbol = data.get("symbol", "?")
        for pos in dashboard_state["open_positions"]:
            if pos["symbol"] == symbol:
                pos["current_price"] = data.get("current_price", pos["current_price"])
                pos["pnl_percent"] = data.get("pnl_percent", 0)
                pos["pnl_usd"] = data.get("pnl_usd", 0)
                pos["time_in_trade"] = data.get("time_in_trade", pos["time_in_trade"])
                break
    
    elif event_type == "POSITION_CLOSED":
        dashboard_state["portfolio"]["open_positions"] -= 1
        symbol = data.get("symbol", "?")
        closed_pos = None
        for pos in dashboard_state["open_positions"]:
            if pos["symbol"] == symbol:
                closed_pos = pos
                break
        
        if closed_pos:
            dashboard_state["open_positions"] = [p for p in dashboard_state["open_positions"] if p["symbol"] != symbol]
            pnl = data.get("realized_pnl", 0)
            dashboard_state["portfolio"]["total_pnl"] += pnl
            dashboard_state["portfolio"]["daily_pnl"] += pnl
            dashboard_state["portfolio"]["risk_used"] -= closed_pos.get("size_usd", 0)
            
            if data.get("close_reason", "").startswith("TP"):
                dashboard_state["metrics"]["tp_hits"] += 1
            elif data.get("close_reason", "") == "STOP_LOSS":
                dashboard_state["metrics"]["sl_hits"] += 1
            
            # Add to performance history
            dashboard_state["performance_history"].append({
                "time": datetime.utcnow().isoformat(),
                "pnl": dashboard_state["portfolio"]["total_pnl"],
            })
            # Keep last 100
            if len(dashboard_state["performance_history"]) > 100:
                dashboard_state["performance_history"] = dashboard_state["performance_history"][-100:]
    
    elif event_type == "SIGNAL_GENERATED":
        signal = {
            "chain": data.get("chain", "solana"),
            "symbol": data.get("symbol", "?"),
            "score": data.get("score", 0),
            "score_details": data.get("score_details", {}),
            "price": data.get("price", 0),
            "tp1_pct": data.get("tp1_pct", 4),
            "sl_pct": data.get("sl_pct", -3.5),
            "reason": data.get("reason", "momentum"),
            "timestamp": time.time(),
        }
        dashboard_state["active_signals"].insert(0, signal)
        if len(dashboard_state["active_signals"]) > 20:
            dashboard_state["active_signals"] = dashboard_state["active_signals"][:20]
        dashboard_state["metrics"]["signals_generated"] += 1
    
    elif event_type == "TOKENS_DISCOVERED":
        tokens = data.get("tokens", [])
        dashboard_state["metrics"]["tokens_scanned"] += len(tokens)
        # Update chain stats
        chain = data.get("chain", "solana")
        if chain in dashboard_state["chains"]:
            dashboard_state["chains"][chain]["pairs"] = len(tokens)
    
    elif event_type == "WHALE_ACTIVITY":
        whale = {
            "symbol": data.get("symbol", "?"),
            "action": data.get("action", "buy"),
            "amount": data.get("amount", 0),
            "wallet": data.get("wallet", "?"),
            "timestamp": time.time(),
        }
        dashboard_state["whale_activity"].insert(0, whale)
        if len(dashboard_state["whale_activity"]) > 20:
            dashboard_state["whale_activity"] = dashboard_state["whale_activity"][:20]
    
    elif event_type == "MARKET_REGIME":
        dashboard_state["market_regime"] = data.get("regime", "CHOP")
    
    elif event_type == "ALERT" and data.get("alert_type") == "META_DECISION":
        decision = data.get("decision", "")
        if decision == "SHUTDOWN":
            dashboard_state["settings"]["emergency_stop"] = True
    
    elif event_type == "AGENT_HEALTH":
        agent_name = data.get("agent", "")
        for agent in dashboard_state["agent_health"]:
            if agent["agent"] == agent_name:
                agent["status"] = data.get("status", "healthy")
                agent["last_check"] = datetime.utcnow().isoformat()
                agent["fitness"] = data.get("fitness", 80)
                break


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


# ── Background: Read paper trading log ──
async def paper_log_reader():
    """Read paper trading log and update dashboard."""
    import os
    paper_log_path = "/root/.openclaw/workspace/agents/logs/paper_trading.json"
    last_mtime = 0
    
    while True:
        try:
            if os.path.exists(paper_log_path):
                mtime = os.path.getmtime(paper_log_path)
                if mtime > last_mtime:
                    last_mtime = mtime
                    with open(paper_log_path, 'r') as f:
                        data = json.load(f)
                    
                    # Update balance
                    dashboard_state["portfolio"]["balance"] = data.get("balance", 10000)
                    
                    # Update positions
                    open_positions = data.get("open_positions", [])
                    dashboard_state["portfolio"]["open_positions"] = len(open_positions)
                    
                    # Map positions to dashboard format
                    mapped_positions = []
                    for pos in open_positions:
                        mapped_positions.append({
                            "trade_id": pos.get("id", "?"),
                            "symbol": pos.get("symbol", "?"),
                            "chain": pos.get("chain", "solana"),
                            "entry_price": pos.get("entry_price", 0),
                            "current_price": pos.get("highest_price", pos.get("entry_price", 0)),
                            "pnl_percent": ((pos.get("highest_price", pos["entry_price"]) / pos["entry_price"]) - 1) * 100 if pos.get("entry_price") else 0,
                            "pnl_usd": 0,
                            "status": "OPEN",
                            "stop_loss": pos.get("stop", 0),
                            "take_profits": [pos.get("tp1", 0), pos.get("tp2", 0), pos.get("tp3", 0)],
                            "time_in_trade": f"{int((time.time() - pos.get('opened_at', time.time())) / 60)}m",
                            "score_at_entry": pos.get("score_at_entry", 0),
                        })
                    dashboard_state["open_positions"] = mapped_positions
                    
                    # Update metrics from history
                    history = data.get("history", [])
                    trades = [h for h in history if h.get("action") == "OPEN"]
                    closes = [h for h in history if h.get("action") == "CLOSE"]
                    dashboard_state["metrics"]["trades_executed"] = len(trades)
                    
                    # Calculate PnL
                    total_pnl = sum(p.get("realized_pnl", 0) for p in closes)
                    dashboard_state["portfolio"]["total_pnl"] = total_pnl
                    
                    # Win rate
                    winning_closes = [c for c in closes if c.get("realized_pnl", 0) > 0]
                    if closes:
                        dashboard_state["portfolio"]["win_rate"] = (len(winning_closes) / len(closes)) * 100
                    
                    # Count TP/SL
                    tp_hits = len([c for c in closes if c.get("close_reason", "").startswith("TP")])
                    sl_hits = len([c for c in closes if c.get("close_reason", "") == "STOP_LOSS"])
                    dashboard_state["metrics"]["tp_hits"] = tp_hits
                    dashboard_state["metrics"]["sl_hits"] = sl_hits
                    
                    # Add performance history point
                    if total_pnl != 0:
                        dashboard_state["performance_history"].append({
                            "time": datetime.utcnow().isoformat(),
                            "pnl": total_pnl,
                        })
                    
                    # Broadcast
                    await broadcast_update()
        except Exception as e:
            pass  # Silently ignore read errors
        
        await asyncio.sleep(5)  # Check every 5 seconds


# ── Routes ──

@app.get("/")
async def index(request: Request):
    return FileResponse(str(APP_DIR / "templates" / "index.html"))


@app.get("/api/state")
async def get_state():
    return dashboard_state


@app.get("/api/portfolio")
async def get_portfolio():
    return dashboard_state["portfolio"]


@app.get("/api/positions")
async def get_positions():
    return {"positions": dashboard_state["open_positions"]}


@app.get("/api/signals")
async def get_signals():
    return {"signals": dashboard_state["active_signals"]}


@app.get("/api/events")
async def get_events(limit: int = 50):
    return {"events": dashboard_state["recent_events"][:limit]}


@app.get("/api/health")
async def get_health():
    return {"agents": dashboard_state["agent_health"]}


@app.get("/api/metrics")
async def get_metrics():
    return dashboard_state["metrics"]


@app.get("/api/settings")
async def get_settings():
    return dashboard_state["settings"]


@app.get("/api/chains")
async def get_chains():
    return dashboard_state["chains"]


# ── Controls ──

@app.post("/control/confirm-trade")
async def confirm_trade():
    update_state("MANUAL_ACTION", {"action": "CONFIRM_TRADE"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "✅ Trade confirmed"}


@app.post("/control/toggle-auto")
async def toggle_auto():
    current = dashboard_state["settings"]["auto_mode"]
    dashboard_state["settings"]["auto_mode"] = not current
    status = "AUTO" if not current else "MANUAL"
    update_state("MANUAL_ACTION", {"action": "TOGGLE_AUTO", "status": status}, "user")
    await broadcast_update()
    return {"status": "ok", "message": f"🤖 Mode: {status}"}


@app.post("/control/toggle-paper")
async def toggle_paper():
    current = dashboard_state["settings"]["paper_mode"]
    dashboard_state["settings"]["paper_mode"] = not current
    mode = "PAPER" if not current else "REAL"
    update_state("MANUAL_ACTION", {"action": "TOGGLE_PAPER", "mode": mode}, "user")
    await broadcast_update()
    return {"status": "ok", "message": f"📊 Mode: {mode}"}


@app.post("/control/emergency-stop")
async def emergency_stop():
    dashboard_state["settings"]["emergency_stop"] = True
    dashboard_state["settings"]["auto_mode"] = False
    update_state("MANUAL_ACTION", {"action": "EMERGENCY_STOP"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "🛑 EMERGENCY STOP ACTIVATED"}


@app.post("/control/pause")
async def pause():
    update_state("MANUAL_ACTION", {"action": "PAUSE"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "⏸️ Trading paused"}


@app.post("/control/resume")
async def resume():
    update_state("MANUAL_ACTION", {"action": "RESUME"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "▶️ Trading resumed"}


@app.post("/control/close-all")
async def close_all():
    update_state("MANUAL_ACTION", {"action": "CLOSE_ALL"}, "user")
    await broadcast_update()
    return {"status": "ok", "message": "🔒 Closing all positions"}


@app.post("/control/reset")
async def reset_system():
    dashboard_state["portfolio"] = {
        "balance": 10000.0,
        "open_positions": 0,
        "win_rate": 0.0,
        "daily_pnl": 0.0,
        "total_pnl": 0.0,
        "drawdown": 0.0,
        "risk_used": 0.0,
        "risk_budget": 500.0,
    }
    dashboard_state["open_positions"] = []
    dashboard_state["active_signals"] = []
    dashboard_state["recent_events"] = []
    dashboard_state["performance_history"] = []
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
    return {"status": "ok", "message": "🔄 System reset"}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        await websocket.send_json(dashboard_state)
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)
    except Exception:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


# ── Startup ──

@app.on_event("startup")
async def startup():
    asyncio.create_task(paper_log_reader())
    print("🐺 Dashboard v2 started — reading paper trading logs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
