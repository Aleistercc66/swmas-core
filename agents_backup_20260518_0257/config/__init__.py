"""Application configuration with environment variable support."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # Database
    db_url: str = Field(default="sqlite+aiosqlite:///./data/trading.db", alias="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_max_connections: int = Field(default=20, alias="REDIS_MAX_CONNECTIONS")
    
    # Event Bus
    use_event_bus: bool = Field(default=True, alias="USE_EVENT_BUS")
    event_stream_prefix: str = Field(default="swarm", alias="EVENT_STREAM_PREFIX")
    event_block_timeout_ms: int = Field(default=5000, alias="EVENT_BLOCK_TIMEOUT_MS")
    event_batch_size: int = Field(default=10, alias="EVENT_BATCH_SIZE")
    
    # Trading
    portfolio_size_usd: float = Field(default=10000.0, alias="PORTFOLIO_SIZE_USD")
    max_positions: int = Field(default=5, alias="MAX_POSITIONS")
    risk_per_trade_pct: float = Field(default=2.0, alias="RISK_PER_TRADE_PCT")
    
    # Scanner
    scan_interval_seconds: int = Field(default=300, alias="SCAN_INTERVAL_SECONDS")
    min_liquidity_usd: float = Field(default=50000.0, alias="MIN_LIQUIDITY_USD")
    min_volume_24h: float = Field(default=10000.0, alias="MIN_VOLUME_24H")
    
    # Telegram
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
