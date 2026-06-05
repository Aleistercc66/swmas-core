"""
Stock Trading Platform — Configuration
All settings for the US stock trading brain.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os

# ───────────────────────────
# UNIVERSE & DATA
# ───────────────────────────

US_STOCK_UNIVERSE: List[str] = [
    # S&P 500 — top 50 by market cap for scanning
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK.B",
    "AVGO", "WMT", "JPM", "V", "MA", "UNH", "HD", "PG", "KO", "PEP",
    "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "COST", "ADBE", "CRM",
    "NFLX", "AMD", "INTC", "QCOM", "TXN", "IBM", "ORCL", "CSCO",
    "DIS", "NKE", "VZ", "T", "PFE", "BAC", "GS", "MS", "C", "WFC",
    "USB", "AXP", "BLK", "SCHW", "PNC",
    # NASDAQ-100 additions
    "PYPL", "INTU", "AMAT", "LRCX", "MU", "KLAC", "MRVL", "SNPS",
    "CDNS", "FTNT", "PANW", "CRWD", "ZS", "OKTA", "DDOG", "PLTR",
    "SNOW", "MDB", "NET", "RBLX", "SQ", "SHOP", "ROKU", "ZM",
    "DOCU", "UBER", "LYFT", "DASH", "ABNB", "COIN", "HOOD", "SOFI",
]

# Scan parameters
SCAN_INTERVAL_MINUTES: int = 5  # How often to scan
MARKET_OPEN_US: str = "09:30"  # US market open (ET)
MARKET_CLOSE_US: str = "16:00"  # US market close (ET)

# ───────────────────────────
# SIGNAL PARAMETERS
# ───────────────────────────

@dataclass
class SignalConfig:
    """Configuration for signal generation."""
    # RSI
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Moving Averages
    ema_short: int = 9
    ema_medium: int = 20
    ema_long: int = 50
    sma_long: int = 200
    
    # Volume
    volume_avg_period: int = 20
    volume_anomaly_threshold: float = 2.0  # 2x average = anomaly
    
    # ATR for volatility
    atr_period: int = 14
    
    # Signal thresholds
    signal_score_threshold: float = 70.0  # Min score to consider
    min_edge_percent: float = 2.0  # Min edge %
    min_rr_ratio: float = 1.5  # Min risk:reward

# ───────────────────────────
# RISK PARAMETERS
# ───────────────────────────

@dataclass
class RiskConfig:
    """Risk management configuration."""
    # Position sizing
    max_position_percent: float = 5.0  # Max 5% of portfolio per position
    base_position_percent: float = 2.0  # Base 2% per trade
    kelly_fraction: float = 0.25  # Quarter Kelly
    
    # Drawdown & limits
    max_drawdown_percent: float = 10.0  # Circuit breaker at 10%
    daily_loss_limit_percent: float = 2.0  # Hard stop at 2% daily loss
    
    # Loss streak adjustments
    loss_streak_3_reduce: float = 0.50  # Reduce to 50% after 3 losses
    loss_streak_5_pause_minutes: int = 60  # Pause 1 hour after 5 losses
    
    # Portfolio heat
    max_portfolio_heat_percent: float = 30.0  # Max 30% deployed
    max_positions: int = 10  # Max concurrent positions
    
    # Correlation
    max_correlation: float = 0.70  # Max correlation between positions
    
    # Stop losses & take profits
    stop_loss_percent: float = 2.0  # Base stop loss
    tp1_percent: float = 4.0  # Take profit 1
    tp2_percent: float = 8.0  # Take profit 2
    tp3_percent: float = 15.0  # Take profit 3
    trailing_stop_percent: float = 3.0  # Trailing stop activation

# ───────────────────────────
# DECISION ENGINE
# ───────────────────────────

@dataclass
class DecisionConfig:
    """Decision engine configuration."""
    min_signal_score: float = 70.0
    min_edge_percent: float = 2.0
    min_rr_ratio: float = 1.5
    max_portfolio_heat: float = 30.0
    
    # Confidence tiers
    confidence_tiers: Dict[str, float] = field(default_factory=lambda: {
        "HIGH": 85.0,
        "MEDIUM": 70.0,
        "LOW": 60.0,
    })
    
    # Action thresholds
    action_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "STRONG_BUY": 85.0,
        "BUY": 70.0,
        "WEAK_BUY": 60.0,
        "HOLD": 50.0,
        "AVOID": 0.0,
    })

# ───────────────────────────
# DATABASE
# ───────────────────────────

DB_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "stock_trading.db"
)

# ───────────────────────────
# ALERTS
# ───────────────────────────

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ───────────────────────────
# IBKR CONFIG
# ───────────────────────────

IBKR_GATEWAY_HOST: str = os.getenv("IBKR_GATEWAY_HOST", "127.0.0.1")
IBKR_GATEWAY_PORT: int = int(os.getenv("IBKR_GATEWAY_PORT", "7497"))
IBKR_CLIENT_ID: int = int(os.getenv("IBKR_CLIENT_ID", "1"))

# ───────────────────────────
# DEFAULTS
# ───────────────────────────

DEFAULT_SIGNAL_CONFIG = SignalConfig()
DEFAULT_RISK_CONFIG = RiskConfig()
DEFAULT_DECISION_CONFIG = DecisionConfig()
