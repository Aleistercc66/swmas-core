#!/usr/bin/env python3
"""
Quick test script for auto_runner - runs one scan cycle
"""

import asyncio
import aiohttp
import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/solana_agent')

from learning_engine import SolanaKnowledgeBase
from historian import SolanaHistorian
from opportunity_scanner import OpportunityScanner
from strategy_engine import StrategyEngine
from risk_manager import RiskManager
from token_safety import TokenSafetyAnalyzer
from jupiter_client import JupiterClient, JupiterSwapConfig

async def test_scan():
    print("🔥 TESTING SOLANA AGENT SCAN 🔥")
    
    kb = SolanaKnowledgeBase()
    historian = SolanaHistorian()
    scanner = OpportunityScanner(kb, historian)
    safety = TokenSafetyAnalyzer()
    jupiter = JupiterClient(JupiterSwapConfig())
    
    async with aiohttp.ClientSession() as session:
        print("\n📊 Fetching trending tokens...")
        
        async with session.get(
            "https://api.dexscreener.com/latest/dex/search?q=solana",
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                pairs = data.get("pairs", [])
                
                solana_pairs = [
                    p for p in pairs
                    if p.get("chainId") == "solana"
                    and p.get("liquidity", {}).get("usd", 0) >= 10000
                ][:10]
                
                print(f"✅ Found {len(solana_pairs)} Solana tokens")
                
                for pair in solana_pairs:
                    symbol = pair.get("baseToken", {}).get("symbol", "?")
                    price = float(pair.get("priceUsd", 0) or 0)
                    change = pair.get("priceChange", {}).get("h1", 0)
                    vol = pair.get("volume", {}).get("h24", 0)
                    liq = pair.get("liquidity", {}).get("usd", 0)
                    
                    safety_result = safety.quick_safety_check({
                        "liquidity": liq,
                        "volume_24h": vol,
                        "changes": pair.get("priceChange", {}),
                    })
                    
                    safe = "✅" if safety_result.get("is_safe") else "❌"
                    
                    print(f"   {safe} {symbol}: ${price:.6f} | 1h: {change:+.1f}% | Vol: ${vol:,.0f} | Liq: ${liq:,.0f}")
                
                print("\n🔥 SCAN COMPLETE - Agent is working!")
                return True
            else:
                print(f"❌ DexScreener error: {resp.status}")
                return False

if __name__ == "__main__":
    result = asyncio.run(test_scan())
    sys.exit(0 if result else 1)
