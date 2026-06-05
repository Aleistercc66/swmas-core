"""Pydantic event payload models for type-safe inter-agent communication."""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from core.models import ValidationCheck, TradeTier


# ───────────────────────────────────────────────
# Scanner Events
# ───────────────────────────────────────────────

class TokenDiscoveredEvent(BaseModel):
    """Scanner output published to event bus."""
    tokens: List[Dict[str, Any]]  # Scanner output data
    batch_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "scanner"
    count: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.count = len(self.tokens)


# ───────────────────────────────────────────────
# Validator Events
# ───────────────────────────────────────────────

class TokenValidation(BaseModel):
    """Single token validation result."""
    scanner_output_id: int
    symbol: str
    is_approved: bool
    tier: str
    confidence: float
    pass_rate: float
    total_checks: int
    passed_checks: int
    checks: List[Dict[str, Any]]  # ValidationCheck as dicts
    rejection_reason: str = ""
    buy_sell_ratio: float = 0.0


class TokensValidatedEvent(BaseModel):
    """Validator output published to event bus."""
    validated_tokens: List[TokenValidation]
    approved_count: int = 0
    rejected_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "validator"
    batch_id: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.approved_count = sum(1 for t in self.validated_tokens if t.is_approved)
        self.rejected_count = len(self.validated_tokens) - self.approved_count


# ───────────────────────────────────────────────
# Risk Engine Events
# ───────────────────────────────────────────────

class RiskSignal(BaseModel):
    """Single risk assessment signal."""
    validator_output_id: int
    symbol: str
    tier: str
    entry_price: float
    stop_loss_price: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    stop_distance_pct: float
    risk_reward_ratio: float
    position_size_pct: float
    composite_score: float
    atr_proxy: float
    volatility_regime: str
    is_active: bool
    is_executable: bool = False  # True if score >= 60
    
    @property
    def is_high_quality(self) -> bool:
        return self.composite_score >= 60 and self.risk_reward_ratio >= 1.5


class RiskAssessedEvent(BaseModel):
    """Risk engine output published to event bus."""
    signals: List[RiskSignal]
    active_count: int = 0
    high_quality_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "risk_engine"
    batch_id: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.active_count = sum(1 for s in self.signals if s.is_active)
        self.high_quality_count = sum(1 for s in self.signals if s.is_high_quality)


# ───────────────────────────────────────────────
# Executor Events
# ───────────────────────────────────────────────

class PositionOpenedEvent(BaseModel):
    """Position execution event."""
    position_id: int
    symbol: str
    entry_price: float
    position_size_usd: float
    stop_loss: float
    take_profit: float
    tier: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "executor"


class PositionClosedEvent(BaseModel):
    """Position close event."""
    position_id: int
    symbol: str
    close_price: float
    pnl_pct: float
    pnl_usd: float
    close_reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "executor"


# ───────────────────────────────────────────────
# Alert Events
# ───────────────────────────────────────────────

class AlertEvent(BaseModel):
    """Alert/notification event."""
    alert_type: str  # SIGNAL, STOP_HIT, TAKE_PROFIT, ERROR, INFO
    symbol: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0  # 0=info, 1=warning, 2=critical
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "system"


# ───────────────────────────────────────────────
# Trade Decision Events
# ───────────────────────────────────────────────

class TradeDecision(BaseModel):
    """Trading decision output."""
    symbol: str
    decision: str = "REJECT"  # APPROVE | REJECT | MODIFY
    tier: str = "TIER_3"
    position_size_usd: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profits: List[float] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    risk_reward: float = 0.0
    portfolio_heat_pct: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "master"


class PortfolioState(BaseModel):
    """Current portfolio state."""
    balance_usd: float = 10000.0
    open_positions: List[Dict[str, Any]] = Field(default_factory=list)
    closed_positions: List[Dict[str, Any]] = Field(default_factory=list)
    daily_trades: int = 0
    daily_pnl: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    last_trade_time: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.utcnow())


class PositionUpdatedEvent(BaseModel):
    """Position status update during monitoring."""
    trade_id: str
    symbol: str
    current_price: float
    entry_price: float
    pnl_percent: float
    pnl_usd: float
    status: str = "OPEN"  # OPEN, BREACHED_SL, HIT_TP1, HIT_TP2, HIT_TP3, CLOSED
    highest_price: float = 0.0
    lowest_price: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "position_monitor"


# ───────────────────────────────────────────────
# Heartbeat Event
# ───────────────────────────────────────────────

class HeartbeatEvent(BaseModel):
    """Agent health heartbeat."""
    agent: str
    status: str  # healthy, degraded, down
    uptime_seconds: float
    last_action: str
    errors_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    source: str = "system"
