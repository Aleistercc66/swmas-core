# Core package initialization
from core.config import settings
from core.logging_config import get_logger, LogContext
from core.models import (
    ScannerOutput, ValidatorOutput, RiskAssessment, Position,
    PortfolioState, TradeLog, Alert, AgentHealth, EventLog,
    TradeTier, PositionStatus, CloseReason, MarketRegime, AgentHealthStatus,
    ScannerOutputCreate, ValidationCheck, HotPair, OpportunitySignal, PortfolioSummary,
)
from core.database import init_db, AtomicTransaction, get_session
from core.state_manager import (
    ScannerStateManager, ValidatorStateManager, RiskStateManager,
    PositionStateManager, PortfolioManager, EventLogManager,
)
from core.redis_client import get_redis, cache_set, cache_get, rate_limit_check
from core.event_bus import (
    get_event_bus, emit_event, SystemEvent,
    EventType, SwarmEvent, EventBus,
    emit_token_discovered, emit_validated, emit_risk_assessed,
    emit_position_opened, emit_position_closed, emit_alert,
)
from core.events import (
    TokenDiscoveredEvent, TokensValidatedEvent,
    TokenValidation, RiskSignal, RiskAssessedEvent,
    PositionOpenedEvent, PositionClosedEvent,
    AlertEvent, HeartbeatEvent, TradeDecision,
)
from core.observability import (
    start_metrics_server, timed, count_exceptions,
    set_agent_healthy, set_agent_degraded, set_agent_down,
    update_portfolio_metrics,
    SCANNER_RUNS, SCAN_LATENCY, API_REQUEST_LATENCY, ERRORS_TOTAL,
    VALIDATOR_CHECKS, VALIDATE_LATENCY,
    RISK_ASSESSMENTS, RISK_LATENCY,
    POSITIONS_OPENED, POSITIONS_CLOSED,
    ACTIVE_POSITIONS, PORTFOLIO_BALANCE, PORTFOLIO_PNL,
    WIN_RATE, DAILY_TRADES, CIRCUIT_BREAKER,
    ALERTS_SENT,
    AGENT_HEALTH,
    REGISTRY,
)


def get_settings():
    """Return the global settings instance."""
    return settings

__version__ = "2.0.0"
__all__ = [
    "settings", "get_settings",
    "get_logger",
    "LogContext",
    "init_db",
    "AtomicTransaction",
    "get_session",
    # Models
    "ScannerOutput", "ValidatorOutput", "RiskAssessment", "Position",
    "PortfolioState", "TradeLog", "Alert", "AgentHealth", "EventLog",
    "TradeTier", "PositionStatus", "CloseReason", "MarketRegime", "AgentHealthStatus",
    "ScannerOutputCreate", "ValidationCheck", "HotPair", "OpportunitySignal", "PortfolioSummary",
    # State managers
    "ScannerStateManager", "ValidatorStateManager", "RiskStateManager",
    "PositionStateManager", "PortfolioManager", "EventLogManager",
    # Redis
    "get_redis", "cache_set", "cache_get", "rate_limit_check",
    # Events
    "get_event_bus", "emit_event", "SystemEvent", "EventType", "SwarmEvent", "EventBus",
    "emit_token_discovered", "emit_validated", "emit_risk_assessed",
    "emit_position_opened", "emit_position_closed", "emit_alert",
    # Event Models
    "TokenDiscoveredEvent", "TokensValidatedEvent", "TokenValidation",
    "RiskSignal", "RiskAssessedEvent",
    "PositionOpenedEvent", "PositionClosedEvent", "AlertEvent", "HeartbeatEvent", "TradeDecision",
    # Observability
    "start_metrics_server", "timed", "count_exceptions",
    "set_agent_healthy", "set_agent_degraded", "set_agent_down",
    "update_portfolio_metrics",
    "SCANNER_RUNS", "SCAN_LATENCY", "API_REQUEST_LATENCY", "ERRORS_TOTAL",
    "VALIDATOR_CHECKS", "VALIDATE_LATENCY",
    "RISK_ASSESSMENTS", "RISK_LATENCY",
    "POSITIONS_OPENED", "POSITIONS_CLOSED",
    "ACTIVE_POSITIONS", "PORTFOLIO_BALANCE", "PORTFOLIO_PNL",
    "WIN_RATE", "DAILY_TRADES", "CIRCUIT_BREAKER",
    "ALERTS_SENT", "AGENT_HEALTH", "REGISTRY",
]
