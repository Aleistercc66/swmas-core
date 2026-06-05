"""Configuration settings for Kimi Telegram Agent."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Telegram
    BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")
    
    # OpenAI / LLM
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Optional Search APIs
    BING_API_KEY: str | None = None
    GOOGLE_CSE_ID: str | None = None
    GOOGLE_API_KEY: str | None = None
    
    # Bot Behavior
    MAX_SEARCH_RESULTS: int = 10
    MAX_SCRAPE_CONTENT_LENGTH: int = 50000
    MEMORY_MESSAGE_LIMIT: int = 20
    REQUEST_TIMEOUT: int = 30
    RATE_LIMIT_PER_MINUTE: int = 20
    
    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    TESSERACT_LANG: str = "eng+ell"
    
    # Database
    DATABASE_URL: str = "sqlite:///./kimi_agent.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
