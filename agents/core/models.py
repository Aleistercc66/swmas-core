#!/usr/bin/env python3
"""
📊 CORE MODELS — SQLModel + Pydantic v2
Every state object is strictly typed, versioned, and database-persisted.
"""
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

# ───────────────────────────────────────────────
# Enums
# ───────────────────────────────────────────────

class TradeTier(str, Enum):
    TIER_1 = "TIER_1"      # Highest conviction
    TIER_2 = "TIER_2"      # Good setup
    TIER_3 = "TIER_3"      # Speculative
    REJECT = "REJECT"      # Failed validation

class TradeSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"

class CloseReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT_1 = "TAKE_PROFIT_1"
    TAKE_PROFIT_2 = "TAKE_PROFIT_2"
    TAKE_PROFIT_3 = "TAKE_PROFIT_3"
    MANUAL = "MANUAL"
    TIMEOUT = "TIMEOUT"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"

class MarketRegime(str, Enum):
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    PANIC = "PANIC"
    EUPHORIC = "EUPHORIC"
    RANGING = "RANGING"
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    UNKNOWN = "UNKNOWN"

class AgentHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"

# ───────────────────────────────────────────────
# Scanner Output
# ───────────────────────────────────────────────

class ScannerOutput(SQLModel, table=True):
    """Raw discovery output from DexScreener / Jupiter / MevX."""
    __tablename__ = "scanner_outputs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    symbol: str = Field(index=True)
    name: str = Field(default="")
    token_address: str = Field(default="", index=True)
    chain: str = Field(default="solana", index=True)
    
    price: float = Field(default=0.0)
    liquidity: float = Field(default=0.0)
    volume_24h: float = Field(default=0.0)
    
    change_5m: float = Field(default=0.0)
    change_1h: float = Field(default=0.0)
    change_6h: float = Field(default=0.0)
    change_24h: float = Field(default=0.0)
    
    buys_24h: int = Field(default=0)
    sells_24h: int = Field(default=0)
    buy_ratio: float = Field(default=0.0)
    
    dex_id: str = Field(default="")
    pair_address: str = Field(default="")
    url: str = Field(default="")
    
    source: str = Field(default="dexscreener")
    scan_batch_id: str = Field(default="", index=True)
    
    momentum_score: float = Field(default=0.0)
    vol_liq_ratio: float = Field(default=0.0)
    is_hot: bool = Field(default=False)

class ScannerOutputCreate(BaseModel):
    """Used when creating a new scanner output."""
    symbol: str
    name: str = ""
    token_address: str = ""
    chain: str = "solana"
    price: float = 0.0
    liquidity: float = 0.0
    volume_24h: float = 0.0
    change_5m: float = 0.0
    change_1h: float = 0.0
    change_6h: float = 0.0
    change_24h: float = 0.0
    buys_24h: int = 0
    sells_24h: int = 0
    dex_id: str = ""
    pair_address: str = ""
    url: str = ""
    source: str = "dexscreener"
    scan_batch_id: str = ""

# ───────────────────────────────────────────────
# Validator Output
# ───────────────────────────────────────────────

class ValidationCheck(BaseModel):
    """Individual check result."""
    name: str
    passed: bool
    value: float = 0.0
    threshold: float = 0.0
    message: str = ""

class ValidatorOutput(SQLModel, table=True):
    """Quality gate results."""
    __tablename__ = "validator_outputs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    scanner_output_id: int = Field(foreign_key="scanner_outputs.id", index=True)
    symbol: str = Field(index=True)
    
    checks_json: str = Field(default="[]")
    pass_rate: float = Field(default=0.0)
    total_checks: int = Field(default=0)
    passed_checks: int = Field(default=0)
    
    is_approved: bool = Field(default=False, index=True)
    tier: str = Field(default=TradeTier.REJECT.value, index=True)
    confidence: float = Field(default=0.0)
    buy_sell_ratio: float = Field(default=0.0)
    
    rejection_reason: str = Field(default="")
    
    @property
    def checks(self) -> List[ValidationCheck]:
        import json
        return [ValidationCheck(**c) for c in json.loads(self.checks_json)]
    
    @checks.setter
    def checks(self, value: List[ValidationCheck]):
        import json
        self.checks_json = json.dumps([c.model_dump() for c in value])

# ───────────────────────────────────────────────
# Risk Assessment
# ───────────────────────────────────────────────

class RiskAssessment(SQLModel, table=True):
    """Dynamic risk engine output with entry/stop/TP levels."""
    __tablename__ = "risk_assessments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    validator_output_id: int = Field(foreign_key="validator_outputs.id", index=True)
    symbol: str = Field(index=True)
    
    entry_price: float = Field(default=0.0)
    stop_loss_price: float = Field(default=0.0)
    take_profit_1: float = Field(default=0.0)
    take_profit_2: float = Field(default=0.0)
    take_profit_3: float = Field(default=0.0)
    
    stop_distance_pct: float = Field(default=0.0)
    risk_reward_ratio: float = Field(default=0.0)
    position_size_usd: float = Field(default=0.0)
    position_size_pct: float = Field(default=0.0)
    
    profit_potential: float = Field(default=0.0)
    execution_probability: float = Field(default=0.0)
    composite_score: float = Field(default=0.0)
    
    atr_proxy: float = Field(default=0.0)
    volatility_regime: str = Field(default=MarketRegime.UNKNOWN.value)
    liquidity_tier: str = Field(default="")
    
    tier: str = Field(default=TradeTier.REJECT.value, index=True)
    
    is_active: bool = Field(default=True, index=True)
    expires_at: Optional[datetime] = Field(default=None)
    
    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v):
        if v not in [t.value for t in TradeTier]:
            raise ValueError(f"Invalid tier: {v}")
        return v

# ───────────────────────────────────────────────
# Position
# ───────────────────────────────────────────────

class Position(SQLModel, table=True):
    """Open or closed trading position."""
    __tablename__ = "positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    symbol: str = Field(index=True)
    token_address: str = Field(default="", index=True)
    side: str = Field(default=TradeSide.LONG.value)
    
    entry_price: float = Field(default=0.0)
    entry_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    position_size_usd: float = Field(default=0.0)
    quantity: float = Field(default=0.0)
    
    stop_loss_price: float = Field(default=0.0)
    take_profit_1: float = Field(default=0.0)
    take_profit_2: float = Field(default=0.0)
    take_profit_3: float = Field(default=0.0)
    
    current_price: float = Field(default=0.0)
    current_pnl_usd: float = Field(default=0.0)
    current_pnl_pct: float = Field(default=0.0)
    highest_price: float = Field(default=0.0)
    
    status: str = Field(default=PositionStatus.OPEN.value, index=True)
    close_reason: Optional[str] = Field(default=None)
    closed_at: Optional[datetime] = Field(default=None)
    exit_price: Optional[float] = Field(default=None)
    realized_pnl_usd: Optional[float] = Field(default=None)
    realized_pnl_pct: Optional[float] = Field(default=None)
    
    entry_fee: float = Field(default=0.0)
    exit_fee: float = Field(default=0.0)
    slippage_cost: float = Field(default=0.0)
    
    risk_assessment_id: int = Field(default=0)
    confidence_at_entry: float = Field(default=0.0)
    tier_at_entry: str = Field(default="")
    signal_source: str = Field(default="")
    
    tp1_hit: bool = Field(default=False)
    tp2_hit: bool = Field(default=False)
    tp3_hit: bool = Field(default=False)
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in [s.value for s in PositionStatus]:
            raise ValueError(f"Invalid status: {v}")
        return v

# ───────────────────────────────────────────────
# Trade Execution Log
# ───────────────────────────────────────────────

class TradeLog(SQLModel, table=True):
    """Immutable record of every trade action."""
    __tablename__ = "trade_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    position_id: int = Field(foreign_key="positions.id", index=True)
    symbol: str = Field(index=True)
    action: str = Field(default="")
    
    price: float = Field(default=0.0)
    quantity: float = Field(default=0.0)
    value_usd: float = Field(default=0.0)
    fee: float = Field(default=0.0)
    slippage: float = Field(default=0.0)
    
    pnl_before: float = Field(default=0.0)
    pnl_after: float = Field(default=0.0)
    balance_before: float = Field(default=0.0)
    balance_after: float = Field(default=0.0)
    
    metadata_json: str = Field(default="{}")
    
    @property
    def metadata_dict(self) -> Dict[str, Any]:
        import json
        return json.loads(self.metadata_json)
    
    @metadata_dict.setter
    def metadata_dict(self, value: Dict[str, Any]):
        import json
        self.metadata_json = json.dumps(value)

# ───────────────────────────────────────────────
# Portfolio State (Singleton row, updated atomically)
# ───────────────────────────────────────────────

class PortfolioState(SQLModel, table=True):
    """Single source of truth for portfolio."""
    __tablename__ = "portfolio_state"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    balance: float = Field(default=10000.0)
    starting_balance: float = Field(default=10000.0)
    
    total_trades: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    total_pnl: float = Field(default=0.0)
    total_fees: float = Field(default=0.0)
    total_slippage: float = Field(default=0.0)
    
    avg_win: float = Field(default=0.0)
    avg_loss: float = Field(default=0.0)
    profit_factor: float = Field(default=0.0)
    max_drawdown_pct: float = Field(default=0.0)
    
    daily_pnl: float = Field(default=0.0)
    daily_trades: int = Field(default=0)
    consecutive_losses: int = Field(default=0)
    
    circuit_breaker_active: bool = Field(default=False)
    circuit_breaker_reason: str = Field(default="")
    circuit_breaker_activated_at: Optional[datetime] = Field(default=None)
    
    kill_switch_active: bool = Field(default=False)
    
    @property
    def return_pct(self) -> float:
        if self.starting_balance == 0:
            return 0.0
        return ((self.balance - self.starting_balance) / self.starting_balance) * 100

# ───────────────────────────────────────────────
# Alert
# ───────────────────────────────────────────────

class Alert(SQLModel, table=True):
    """Telegram / notification records."""
    __tablename__ = "alerts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    alert_type: str = Field(default="", index=True)
    symbol: Optional[str] = Field(default=None, index=True)
    risk_assessment_id: Optional[int] = Field(default=None)
    position_id: Optional[int] = Field(default=None)
    
    title: str = Field(default="")
    body: str = Field(default="")
    
    telegram_message_id: Optional[str] = Field(default=None)
    telegram_sent: bool = Field(default=False)
    telegram_error: Optional[str] = Field(default=None)
    
    user_response: Optional[str] = Field(default=None)
    user_responded_at: Optional[datetime] = Field(default=None)
    
    confirmed: bool = Field(default=False)
    executed: bool = Field(default=False)
    executed_at: Optional[datetime] = Field(default=None)

# ───────────────────────────────────────────────
# Agent Health
# ───────────────────────────────────────────────

class AgentHealth(SQLModel, table=True):
    """Health check records per agent."""
    __tablename__ = "agent_health"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    agent_name: str = Field(index=True)
    status: str = Field(default=AgentHealthStatus.UNKNOWN.value, index=True)
    
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_successful_run: Optional[datetime] = Field(default=None)
    
    error_count_24h: int = Field(default=0)
    warning_count_24h: int = Field(default=0)
    
    avg_cycle_time_ms: float = Field(default=0.0)
    max_cycle_time_ms: float = Field(default=0.0)
    
    pid: Optional[int] = Field(default=None)
    uptime_seconds: int = Field(default=0)
    memory_mb: float = Field(default=0.0)
    cpu_percent: float = Field(default=0.0)
    
    auto_restarted: bool = Field(default=False)
    restart_count: int = Field(default=0)
    last_restart_at: Optional[datetime] = Field(default=None)

# ───────────────────────────────────────────────
# Knowledge Base Entry (for Meta Agent / LLM RAG)
# ───────────────────────────────────────────────

class KnowledgeEntry(SQLModel, table=True):
    """Learned patterns, fixes, insights for RAG."""
    __tablename__ = "knowledge_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    category: str = Field(index=True)
    topic: str = Field(default="", index=True)
    
    content: str = Field(default="")
    embedding_vector: Optional[str] = Field(default=None)
    
    related_symbols: str = Field(default="[]")
    related_strategies: str = Field(default="[]")
    
    success_count: int = Field(default=0)
    failure_count: int = Field(default=0)
    confidence: float = Field(default=0.0)
    
    source_agent: str = Field(default="")
    source_version: str = Field(default="")
    
    @property
    def related_symbols_list(self) -> List[str]:
        import json
        return json.loads(self.related_symbols)
    
    @related_symbols_list.setter
    def related_symbols_list(self, value: List[str]):
        import json
        self.related_symbols = json.dumps(value)

# ───────────────────────────────────────────────
# Market Regime (for Master Agent)
# ───────────────────────────────────────────────

class MarketRegimeState(SQLModel, table=True):
    """Detected market regime with confidence."""
    __tablename__ = "market_regimes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    overall: str = Field(default=MarketRegime.UNKNOWN.value, index=True)
    confidence: float = Field(default=0.0)
    
    volatility_index: float = Field(default=0.0)
    trend_strength: float = Field(default=0.0)
    breadth_score: float = Field(default=0.0)
    funding_rate_bias: float = Field(default=0.0)
    
    top_movers_count: int = Field(default=0)
    avg_liquidity: float = Field(default=0.0)
    avg_volume: float = Field(default=0.0)
    
    data_sources: str = Field(default="[]")

# ───────────────────────────────────────────────
# Event Log (for event-driven audit trail)
# ───────────────────────────────────────────────

class EventLog(SQLModel, table=True):
    """Immutable event stream — the source of truth."""
    __tablename__ = "event_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    
    event_type: str = Field(index=True)
    event_name: str = Field(default="", index=True)
    
    agent_name: str = Field(default="", index=True)
    correlation_id: str = Field(default="", index=True)
    
    payload_json: str = Field(default="{}")
    
    processed: bool = Field(default=False, index=True)
    processed_at: Optional[datetime] = Field(default=None)
    processed_by: Optional[str] = Field(default=None)
    
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    
    @property
    def payload(self) -> Dict[str, Any]:
        import json
        return json.loads(self.payload_json)
    
    @payload.setter
    def payload(self, value: Dict[str, Any]):
        import json
        self.payload_json = json.dumps(value)

# ───────────────────────────────────────────────
# Pydantic-only models (not DB tables)
# ───────────────────────────────────────────────

class HotPair(BaseModel):
    """Real-time hot pair from scanners."""
    symbol: str
    price: float
    change_5m: float
    change_1h: float
    liquidity: float
    volume_24h: float
    buy_ratio: float
    momentum_score: float
    vol_liq_ratio: float
    score: float
    source: str
    timestamp: datetime

class OpportunitySignal(BaseModel):
    """Final signal ready for user confirmation."""
    symbol: str
    name: str
    token_address: str
    chain: str
    
    price: float
    entry_zone: tuple[float, float]
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    confidence: float
    tier: TradeTier
    profit_potential: float
    execution_probability: float
    risk_reward_ratio: float
    
    buy_ratio: float
    momentum_5m: float
    momentum_1h: float
    momentum_24h: float
    liquidity: float
    volume_24h: float
    
    dex_id: str
    url: str
    
    expires_at: datetime
    correlation_id: str

class PortfolioSummary(BaseModel):
    """Real-time portfolio snapshot."""
    balance: float
    starting_balance: float
    return_pct: float
    
    open_positions_count: int
    open_positions: List[Dict[str, Any]]
    
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    profit_factor: float
    max_drawdown_pct: float
    
    daily_pnl: float
    daily_trades: int
    circuit_breaker_active: bool
    kill_switch_active: bool
    
    timestamp: datetime
