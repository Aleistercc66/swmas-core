#!/usr/bin/env python3
"""
📊 OBSERVABILITY — Prometheus metrics + health checks
Production-ready monitoring for every agent.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.exposition import start_http_server
from typing import Optional
import time
import asyncio

from core.config import settings
from core.logging_config import get_logger

logger = get_logger("observability")

# ───────────────────────────────────────────────
# Prometheus Registry
# ───────────────────────────────────────────────

REGISTRY = CollectorRegistry()

# System info
SYSTEM_INFO = Info("trading_system", "Trading system metadata", registry=REGISTRY)
SYSTEM_INFO.info({"version": settings.version, "app_name": settings.app_name})

# Counters
SCANNER_RUNS = Counter("scanner_runs_total", "Total scanner cycles", ["status"], registry=REGISTRY)
VALIDATOR_CHECKS = Counter("validator_checks_total", "Total validation checks", ["result"], registry=REGISTRY)
RISK_ASSESSMENTS = Counter("risk_assessments_total", "Total risk calculations", ["tier"], registry=REGISTRY)
POSITIONS_OPENED = Counter("positions_opened_total", "Total positions opened", ["symbol", "tier"], registry=REGISTRY)
POSITIONS_CLOSED = Counter("positions_closed_total", "Total positions closed", ["symbol", "reason"], registry=REGISTRY)
ALERTS_SENT = Counter("alerts_sent_total", "Total alerts sent", ["type"], registry=REGISTRY)
ERRORS_TOTAL = Counter("errors_total", "Total errors", ["agent", "type"], registry=REGISTRY)

# Histograms
SCAN_LATENCY = Histogram("scanner_latency_seconds", "Scanner cycle time", registry=REGISTRY)
VALIDATE_LATENCY = Histogram("validator_latency_seconds", "Validator cycle time", registry=REGISTRY)
RISK_LATENCY = Histogram("risk_latency_seconds", "Risk engine cycle time", registry=REGISTRY)
API_REQUEST_LATENCY = Histogram("api_request_latency_seconds", "External API call time", ["api"], registry=REGISTRY)

# Gauges
ACTIVE_POSITIONS = Gauge("active_positions", "Currently open positions", registry=REGISTRY)
PORTFOLIO_BALANCE = Gauge("portfolio_balance_usd", "Current balance", registry=REGISTRY)
PORTFOLIO_PNL = Gauge("portfolio_pnl_usd", "Total realized PnL", registry=REGISTRY)
WIN_RATE = Gauge("win_rate_percent", "Current win rate", registry=REGISTRY)
AGENT_HEALTH = Gauge("agent_health", "Agent health status (1=healthy, 0.5=degraded, 0=down)", ["agent"], registry=REGISTRY)
DAILY_TRADES = Gauge("daily_trades", "Trades today", registry=REGISTRY)
CIRCUIT_BREAKER = Gauge("circuit_breaker_active", "Circuit breaker state", registry=REGISTRY)

# ───────────────────────────────────────────────
# Metrics Server
# ───────────────────────────────────────────────

_metrics_server_started = False

def start_metrics_server():
    """Start Prometheus HTTP server on configured port."""
    global _metrics_server_started
    if _metrics_server_started:
        return
    
    if settings.observability.enable_prometheus:
        try:
            start_http_server(settings.observability.metrics_port, registry=REGISTRY)
            logger.info(f"Prometheus metrics server on port {settings.observability.metrics_port}")
            _metrics_server_started = True
        except Exception as e:
            logger.warning(f"Could not start metrics server: {e}")
    else:
        logger.info("Prometheus disabled")

def get_metrics_text() -> str:
    """Get metrics in Prometheus exposition format."""
    return generate_latest(REGISTRY).decode("utf-8")

# ───────────────────────────────────────────────
# Decorators for automatic instrumentation
# ───────────────────────────────────────────────

def timed(histogram):
    """Decorator to time function execution."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                histogram.observe(time.time() - start)
        
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                histogram.observe(time.time() - start)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

def count_exceptions(counter, agent_name: str, error_type: str = "generic"):
    """Decorator to count exceptions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                counter.labels(agent=agent_name, type=error_type).inc()
                raise
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                counter.labels(agent=agent_name, type=error_type).inc()
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# ───────────────────────────────────────────────
# Health Check Helpers
# ───────────────────────────────────────────────

def set_agent_healthy(agent_name: str):
    AGENT_HEALTH.labels(agent=agent_name).set(1.0)

def set_agent_degraded(agent_name: str):
    AGENT_HEALTH.labels(agent=agent_name).set(0.5)

def set_agent_down(agent_name: str):
    AGENT_HEALTH.labels(agent=agent_name).set(0.0)

# ───────────────────────────────────────────────
# Portfolio Metrics Update
# ───────────────────────────────────────────────

def update_portfolio_metrics(balance: float, pnl: float, win_rate_pct: float, open_count: int, daily_trades: int, circuit_active: bool):
    PORTFOLIO_BALANCE.set(balance)
    PORTFOLIO_PNL.set(pnl)
    WIN_RATE.set(win_rate_pct)
    ACTIVE_POSITIONS.set(open_count)
    DAILY_TRADES.set(daily_trades)
    CIRCUIT_BREAKER.set(1.0 if circuit_active else 0.0)
