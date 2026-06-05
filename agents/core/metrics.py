# ───────────────────────────────────────────────
# Prometheus Metrics for Trading Swarm
# ───────────────────────────────────────────────
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server
import asyncio
import logging

logger = logging.getLogger("metrics")

# ── System Info ──
SWARM_INFO = Info("trading_swarm", "Trading swarm metadata")

# ── Scanner Metrics ──
TOKENS_SCANNED_TOTAL = Counter("tokens_scanned_total", "Total tokens scanned", ["source"])
TOKENS_SAVED_TOTAL = Counter("tokens_saved_total", "Quality tokens saved to DB")
SCAN_LATENCY = Histogram("scan_latency_seconds", "Time per scan cycle")

# ── Validator Metrics ──
TOKENS_VALIDATED_TOTAL = Counter("tokens_validated_total", "Total tokens validated")
TOKENS_APPROVED_TOTAL = Counter("tokens_approved_total", "Approved tokens", ["tier"])
TOKENS_REJECTED_TOTAL = Counter("tokens_rejected_total", "Rejected tokens", ["reason"])
VALIDATE_LATENCY = Histogram("validate_latency_seconds", "Time per validation cycle")

# ── Risk Engine Metrics ──
RISK_ASSESSMENTS_TOTAL = Counter("risk_assessments_total", "Total risk assessments")
SIGNALS_ACTIVE = Gauge("signals_active", "Currently active signals")
SIGNALS_EXECUTABLE = Gauge("signals_executable", "Executable signals")
RISK_LATENCY = Histogram("risk_latency_seconds", "Time per risk assessment")

# ── Master / Executor Metrics ──
TRADES_APPROVED_TOTAL = Counter("trades_approved_total", "Approved trades", ["tier"])
TRADES_REJECTED_TOTAL = Counter("trades_rejected_total", "Rejected trades", ["reason"])
POSITIONS_OPENED_TOTAL = Counter("positions_opened_total", "Positions opened", ["symbol", "tier"])
POSITIONS_CLOSED_TOTAL = Counter("positions_closed_total", "Positions closed", ["symbol", "reason"])
CIRCUIT_BREAKER_ACTIVE = Gauge("circuit_breaker_active", "Circuit breaker status (1=active)")

# ── Position Monitor Metrics ──
POSITIONS_OPEN = Gauge("positions_open", "Currently open positions", ["symbol"])
POSITION_PNL = Gauge("position_pnl_percent", "Position PnL %", ["symbol"])
POSITION_PNL_USD = Gauge("position_pnl_usd", "Position PnL $", ["symbol"])
TP_HITS_TOTAL = Counter("tp_hits_total", "Take profit hits", ["level"])
SL_HITS_TOTAL = Counter("sl_hits_total", "Stop loss hits", ["symbol"])

# ── Portfolio Metrics ──
PORTFOLIO_BALANCE = Gauge("portfolio_balance_usd", "Portfolio balance in USD")
PORTFOLIO_DAILY_PNL = Gauge("portfolio_daily_pnl", "Daily PnL")
PORTFOLIO_DRAWDOWN = Gauge("portfolio_drawdown_percent", "Current drawdown %")
WIN_RATE = Gauge("win_rate_percent", "Win rate %")
DAILY_TRADES = Gauge("daily_trades_count", "Trades today")

# ── Event Bus Metrics ──
EVENTS_PUBLISHED = Counter("events_published_total", "Events published", ["event_type"])
EVENTS_CONSUMED = Counter("events_consumed_total", "Events consumed", ["event_type", "consumer"])
EVENT_BUS_CONNECTED = Gauge("event_bus_connected", "Event bus connected (1=yes)")

# ── Agent Health ──
AGENT_HEALTH = Gauge("agent_health", "Agent health status", ["agent"])
# 0=unknown, 1=healthy, 2=degraded, 3=down


async def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    logger.info(f"📊 Prometheus metrics at http://0.0.0.0:{port}/metrics")


def set_agent_metric(agent: str, status: str):
    """Set agent health metric."""
    status_map = {"unknown": 0, "healthy": 1, "degraded": 2, "down": 3}
    AGENT_HEALTH.labels(agent=agent).set(status_map.get(status, 0))


def record_event_published(event_type: str):
    """Record event published."""
    EVENTS_PUBLISHED.labels(event_type=event_type).inc()


def record_event_consumed(event_type: str, consumer: str):
    """Record event consumed."""
    EVENTS_CONSUMED.labels(event_type=event_type, consumer=consumer).inc()
