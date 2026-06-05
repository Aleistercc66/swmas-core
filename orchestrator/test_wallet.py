#!/usr/bin/env python3
"""Quick test of wallet system"""
import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')

from core.wallet_manager import WalletManager

async def test():
    wm = WalletManager()
    await wm.initialize()
    
    print(f"Wallets loaded: {len(wm.wallets)}")
    for name, w in wm.wallets.items():
        print(f"  - {name}: {w.address} ({w.chain})")
    
    if wm.wallets:
        wallet = list(wm.wallets.values())[0]
        print(f"\nTesting get_token_balances for {wallet.address} on {wallet.chain}...")
        
        tokens = await wm.get_token_balances(wallet.address, wallet.chain)
        print(f"Result: {tokens}")
        
        print(f"\nTesting get_portfolio_with_value...")
        portfolio = await wm.get_portfolio_with_value(wallet.name, wallet.chain)
        print(f"Portfolio: {portfolio}")
    else:
        print("No wallets to test!")

if __name__ == "__main__":
    asyncio.run(test())
