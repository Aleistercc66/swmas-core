#!/usr/bin/env python3
"""
⚡ CORE CONFIGURATION — Pydantic Settings v2
Environment-driven, type-safe, validated at startup.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn
from typing import Optional


class DatabaseSettings(BaseSettings):
    """Database configuration with SQLite default, PostgreSQL ready."""
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")
    
    url: str = Field(default="sqlite+aiosqlite:///./data/trading.db", description="Database URL")
    echo: bool = Field(default=False, description="Log SQL queries")
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    pool_pre_ping: bool = Field(default=True)
    
    @property
    def is_postgres(self) -> bool:
        return "postgresql" in self.url.lower()
    
    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.url.lower()


class RedisSettings(BaseSettings):
    """Redis configuration for cache, pub/sub, rate limiting."""
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")
    
    url: str = Field(default="redis://localhost:6379/0")
    decode_responses: bool = Field(default=True)
    socket_connect_timeout: int = Field(default=5)
    socket_timeout: int = Field(default=5)
    
    # Pub/sub channels
    channel_scanner: str = Field(default="scanner:output")
    channel_validator: str = Field(default="validator:output")
    channel_risk: str = Field(default="risk:assessment")
    channel_executor: str = Field(default="executor:signals")
    channel_positions: str = Field(default="positions:updates")
    channel_alerts: str = Field(default="alerts:telegram")
    channel_health: str = Field(default="health:heartbeat")
    
    # Rate limiting
    rate_limit_calls_per_second: int = Field(default=20, ge=1)
    rate_limit_window_seconds: int = Field(default=1, ge=1)


class TradingSettings(BaseSettings):
    """Trading parameters — all configurable via env."""
    model_config = SettingsConfigDict(env_prefix="TRADE_", extra="ignore")
    
    mode: str = Field(default="MANUAL", pattern="^(MANUAL|SEMI_AUTO|FULL_AUTO)$")
    enabled: bool = Field(default=False)
    
    starting_balance: float = Field(default=10000.0, gt=0)
    position_size_pct: float = Field(default=5.0, gt=0, le=100)
    max_daily_trades: int = Field(default=3, ge=0)
    min_confidence: float = Field(default=55.0, ge=0, le=100)
    min_tier: str = Field(default="TIER_2", pattern="^(TIER_1|TIER_2|TIER_3|REJECT)$")
    min_profit_potential: float = Field(default=50.0, ge=0)
    min_execution_probability: float = Field(default=70.0, ge=0, le=100)
    
    # Stop loss / Take profit
    min_stop_distance: float = Field(default=10.0, gt=0)
    max_stop_distance: float = Field(default=25.0, gt=0)
    tp1_pct: float = Field(default=50.0)
    tp2_pct: float = Field(default=100.0)
    tp3_pct: float = Field(default=200.0)
    
    # Simulation
    fee_rate: float = Field(default=0.003)
    slippage_model: str = Field(default="liquidity_based")
    spread_enabled: bool = Field(default=True)
    partial_fills: bool = Field(default=True)
    
    # Safety
    circuit_breaker_daily_loss_pct: float = Field(default=5.0)
    circuit_breaker_consecutive_losses: int = Field(default=3)
    kill_switch_enabled: bool = Field(default=True)


class ScannerSettings(BaseSettings):
    """Scanner configuration."""
    model_config = SettingsConfigDict(env_prefix="SCAN_", extra="ignore")
    
    interval_seconds: int = Field(default=900, ge=10)  # 15min default
    realtime_interval_seconds: int = Field(default=30, ge=5)
    hot_tracker_interval_seconds: int = Field(default=10, ge=5)
    min_liquidity: float = Field(default=25000.0)
    min_volume_24h: float = Field(default=5000.0)
    dexscreener_base_url: str = Field(default="https://api.dexscreener.com/latest/dex")
    jupiter_price_url: str = Field(default="https://price.jup.ag/v6/price")
    jupiter_quote_url: str = Field(default="https://api.jup.ag/swap/v1/quote")
    solana_rpc_url: str = Field(default="https://api.mainnet-beta.solana.com")


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""
    model_config = SettingsConfigDict(env_prefix="TG_", extra="ignore")
    
    bot_token: Optional[str] = Field(default=None)
    chat_id: Optional[str] = Field(default=None)
    poll_interval: int = Field(default=30, ge=5)
    timeout: int = Field(default=15)
    parse_mode: str = Field(default="Markdown")


class ObservabilitySettings(BaseSettings):
    """Metrics, logging, tracing."""
    model_config = SettingsConfigDict(env_prefix="OBS_", extra="ignore")
    
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    json_logs: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1, le=65535)
    enable_prometheus: bool = Field(default=True)
    enable_structlog: bool = Field(default=True)
    log_file: str = Field(default="./logs/trading_system.log")


class AppSettings(BaseSettings):
    """Root settings — all sections composed."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    app_name: str = Field(default="CryptoTradingSwarm")
    version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


# Singleton instance — imported everywhere
settings = AppSettings()
