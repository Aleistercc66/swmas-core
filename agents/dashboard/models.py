#!/usr/bin/env python3
"""Dashboard data models."""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class PositionView(BaseModel):
    """Position for dashboard display."""
    trade_id: str
    symbol: str
    entry_price: float
    current_price: float
    pnl_percent: float
    pnl_usd: float
    status: str
    stop_loss: float
    take_profits: List[float]


class PortfolioSummary(BaseModel):
    """Portfolio overview."""
    balance: float = 10000.0
    open_positions: int = 0
    win_rate: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    drawdown: float = 0.0


class EventView(BaseModel):
    """Event for dashboard display."""
    event_type: str
    source: str
    timestamp: str
    data: Dict[str, Any]


class AgentHealthView(BaseModel):
    """Agent health status."""
    agent: str
    status: str  # healthy, degraded, down
    last_check: str


class DashboardState(BaseModel):
    """Full dashboard state."""
    portfolio: PortfolioSummary
    open_positions: List[PositionView]
    recent_events: List[EventView]
    agent_health: List[AgentHealthView]
    metrics: Dict[str, Any]
