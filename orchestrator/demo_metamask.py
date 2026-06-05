#!/usr/bin/env python3
"""
MetaMask Integration Demo
Shows how the wallet system works.
"""
import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')
sys.path.insert(0, '/root/.openclaw/workspace/agents')

# Use the new wallet manager from orchestrator/core/
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator/core')
from wallet_manager import WalletManager

async def demo():
    print("🔥 META MASK INTEGRATION DEMO 🔥\n")
    
    # 1. Create wallet manager
    manager = WalletManager()
    await manager.initialize(master_password="demo_password_123")
    print("✅ Wallet Manager initialized\n")
    
    # 2. Show commands
    print("📱 TELEGRAM COMMANDS:")
    print("   /wallet_setup — Start MetaMask connection wizard")
    print("   /wallet — Show all connected wallets")
    print("   /balance — Check wallet balances")
    print("   /trade — Trading interface")
    print("   /swap ETH USDC 0.5 — Swap tokens")
    print("   /portfolio — View portfolio\n")
    
    # 3. Show security
    print("🔐 SECURITY FEATURES:")
    print("   ✅ Private keys encrypted with Fernet (AES-128)")
    print("   ✅ PBKDF2 key derivation (100K iterations)")
    print("   ✅ Keys never stored in plain text")
    print("   ✅ Master password required for decryption")
    print("   ✅ Auto-delete sensitive messages\n")
    
    # 4. Show chains
    print("⛓️  SUPPORTED CHAINS:")
    print("   • Ethereum (ETH)")
    print("   • Arbitrum (ETH)")
    print("   • Base (ETH)")
    print("   • Optimism (ETH)")
    print("   • Polygon (MATIC)")
    print("   • Solana (SOL)\n")
    
    # 5. Show trading
    print("📈 TRADING CAPABILITIES:")
    print("   • Token swaps via 1inch (EVM) / Jupiter (Solana)")
    print("   • Live price quotes")
    print("   • Gas optimization")
    print("   • Slippage protection")
    print("   • Transaction confirmation\n")
    
    print("🚀 TO START:")
    print("   1. Send /wallet_setup to @WorkSS11_bot")
    print("   2. Follow the 3-step wizard")
    print("   3. Use /balance to verify connection")
    print("   4. Start trading with /trade or /swap!\n")
    
    print("⚠️  SECURITY WARNING:")
    print("   Only use with wallets you're comfortable automating.")
    print("   Consider a dedicated trading wallet, not your main savings.")

if __name__ == "__main__":
    asyncio.run(demo())
