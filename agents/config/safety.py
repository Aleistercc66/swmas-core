#!/usr/bin/env python3
"""🛡️ Central Safety Configuration — Production Safety Net."""
from pydantic import BaseModel, Field
from typing import List, Optional


class SafetyConfig(BaseModel):
    """Safety configuration for real-money trading."""
    
    # ── Trading Mode ──
    trading_mode: str = Field(default="paper", pattern="^(paper|real)$")
    
    # ── Position Limits ──
    max_single_position_usd: float = Field(default=250.0, gt=0)
    max_daily_risk_usd: float = Field(default=500.0, gt=0)
    max_drawdown_percent: float = Field(default=15.0, gt=0, le=100)
    
    # ── Wallet Safety ──
    min_wallet_balance_sol: float = Field(default=3.0, ge=0)
    min_wallet_balance_usd: float = Field(default=100.0, ge=0)
    
    # ── Execution Safety ──
    require_manual_approval_real: bool = Field(default=True)
    slippage_tolerance_percent: float = Field(default=1.2, gt=0, le=10)
    max_slippage_percent: float = Field(default=3.0, gt=0, le=10)
    
    # ── Chain Support ──
    allowed_chains: List[str] = Field(default=["solana"])
    default_chain: str = Field(default="solana")
    
    # ── Rate Limits ──
    daily_trade_limit: int = Field(default=5, ge=1, le=50)
    hourly_trade_limit: int = Field(default=2, ge=1, le=20)
    
    # ── Kill Switch ──
    emergency_kill_switch: bool = Field(default=True)
    kill_switch_on_drawdown: float = Field(default=20.0, gt=0, le=100)
    
    # ── Audit ──
    audit_all_decisions: bool = Field(default=True)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")


# Global instance
safety_config = SafetyConfig()


def update_safety_config(**kwargs):
    """Update safety config (use carefully)."""
    global safety_config
    for key, value in kwargs.items():
        if hasattr(safety_config, key):
            setattr(safety_config, key, value)
    safety_config = SafetyConfig(**safety_config.model_dump())


def is_paper_mode() -> bool:
    """Check if running in paper mode."""
    return safety_config.trading_mode == "paper"


def is_real_mode() -> bool:
    """Check if running in real mode."""
    return safety_config.trading_mode == "real"
