#!/usr/bin/env python3
"""
Quick test of auto_runner startup
"""
import sys
sys.path.insert(0, '/root/.openclaw/workspace/solana_agent')

# Test imports
print("Testing imports...")
from learning_engine import SolanaKnowledgeBase
print("✅ learning_engine")
from historian import SolanaHistorian
print("✅ historian")
from opportunity_scanner import OpportunityScanner
print("✅ opportunity_scanner")
from strategy_engine import StrategyEngine
print("✅ strategy_engine")
from execution_layer import ExecutionEngine
print("✅ execution_layer")
from risk_manager import RiskManager
print("✅ risk_manager")
from telegram_alerts import TelegramAlerter, AlertConfig
print("✅ telegram_alerts")
from pumpfun_tracker import PumpFunTracker
print("✅ pumpfun_tracker")
from token_safety import TokenSafetyAnalyzer
print("✅ token_safety")
from mev_protection import MEVProtection, MEVConfig
print("✅ mev_protection")
from websocket_sniper import WebSocketSniper
print("✅ websocket_sniper")
from jupiter_client import JupiterClient, JupiterSwapConfig
print("✅ jupiter_client")
from training_engine import SuperiorTrainingEngine
print("✅ training_engine")

print("\n🔥 ALL IMPORTS OK - Auto runner can start!")
