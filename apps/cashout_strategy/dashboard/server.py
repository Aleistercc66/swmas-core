#!/usr/bin/env python3
"""
Stoiximan Cashout Dashboard Server
=================================
FastAPI backend serving the web dashboard and providing API endpoints
"""

import sys
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# Add parent to path
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from app import CashoutApp, Database, OpportunityStatus

# Create app
server = FastAPI(title="Cashout Strategy Dashboard", version="1.0")

# Static files
server.mount("/static", StaticFiles(directory=str(APP_DIR / "dashboard/static")), name="static")

# Global app instance
_cashout_app: Optional[CashoutApp] = None
_app_thread: Optional[threading.Thread] = None


def get_app() -> CashoutApp:
    global _cashout_app
    if _cashout_app is None:
        _cashout_app = CashoutApp(use_demo=True)  # Demo mode by default
    return _cashout_app


# Pydantic models
class SettingsUpdate(BaseModel):
    scan_interval: Optional[int] = None
    min_drop: Optional[float] = None
    min_confidence: Optional[int] = None
    bankroll: Optional[float] = None
    max_stake_pct: Optional[float] = None
    telegram_alerts: Optional[bool] = None


class ExecuteRequest(BaseModel):
    profit_pct: Optional[float] = None
    notes: Optional[str] = None


# Routes
@server.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML"""
    html_path = APP_DIR / "dashboard/templates/index.html"
    return FileResponse(str(html_path))


@server.get("/api/dashboard")
async def api_dashboard():
    """Get all dashboard data"""
    app = get_app()
    return app.get_dashboard_data()


@server.post("/api/start")
async def api_start():
    """Start the cashout app"""
    global _app_thread
    app = get_app()
    
    if app.running:
        return {"success": True, "message": "Already running"}
    
    def run_app():
        asyncio.run(app.start())
    
    _app_thread = threading.Thread(target=run_app, daemon=True)
    _app_thread.start()
    
    return {"success": True, "message": "App started"}


@server.post("/api/stop")
async def api_stop():
    """Stop the cashout app"""
    app = get_app()
    app.stop()
    return {"success": True, "message": "App stopped"}


@server.post("/api/settings")
async def api_settings(settings: SettingsUpdate):
    """Update app settings"""
    app = get_app()
    
    if settings.scan_interval:
        app.scan_interval = settings.scan_interval
    if settings.min_drop:
        app.pinnacle.min_drop_pct = settings.min_drop
    if settings.min_confidence:
        # Store in db
        pass
    if settings.bankroll:
        pass
    
    return {"success": True, "settings": settings.dict()}


@server.post("/api/opportunities/{match_id}/execute")
async def api_execute(match_id: str, req: ExecuteRequest):
    """Mark an opportunity as executed"""
    app = get_app()
    
    updates = {
        "status": "executed",
        "cashed_out_at": datetime.now(),
        "profit_pct": req.profit_pct or 2.0,
        "notes": req.notes or ""
    }
    
    app.db.update_opportunity(match_id, updates)
    
    if match_id in app.engine.active_opportunities:
        del app.engine.active_opportunities[match_id]
    
    return {"success": True, "message": f"Marked {match_id} as executed"}


@server.get("/api/opportunities")
async def api_opportunities(status: str = None, limit: int = 50):
    """Get opportunities list"""
    app = get_app()
    return app.db.get_opportunities(status=status, limit=limit)


@server.get("/api/stats")
async def api_stats():
    """Get performance statistics"""
    app = get_app()
    return app.db.get_stats()


@server.get("/api/health")
async def api_health():
    """Health check"""
    app = get_app()
    return {
        "status": "healthy" if app.running else "idle",
        "running": app.running,
        "timestamp": datetime.now().isoformat()
    }


# Serve the docx guide
@server.get("/guide")
async def serve_guide():
    """Serve the strategy guide docx"""
    docx_path = APP_DIR / "Stoiximan_Cashout_Strategy_Guide.docx"
    if docx_path.exists():
        return FileResponse(
            str(docx_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="Stoiximan_Cashout_Strategy_Guide.docx"
        )
    raise HTTPException(status_code=404, detail="Guide not found")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server"""
    print(f"🚀 Dashboard server starting at http://{host}:{port}")
    print(f"📊 Open your browser and navigate to http://localhost:{port}")
    uvicorn.run(server, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
