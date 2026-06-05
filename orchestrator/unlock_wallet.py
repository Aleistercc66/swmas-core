#!/usr/bin/env python3
"""
Wallet Unlock Script — Run this to unlock your wallet for live trading
Usage: python3 unlock_wallet.py <password>
"""
import sys
import json
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from core.wallet_manager import WalletManager, SecureKeyStorage

WALLETS_FILE = Path("/root/.openclaw/workspace/orchestrator/config/wallets.json")

def unlock_wallet(password: str):
    """Unlock wallet and test decryption."""
    wm = WalletManager()
    
    # Initialize with password
    asyncio.run(wm.initialize(master_password=password))
    
    print(f"✅ Wallet Manager initialized ({len(wm.wallets)} wallets)")
    
    # Test decrypt each wallet
    for name, wallet in wm.wallets.items():
        print(f"\n🔓 Testing: {name} ({wallet.chain})")
        pk = asyncio.run(wm.get_private_key(name, password=password))
        if pk:
            print(f"   ✅ Decryption successful!")
            print(f"   Address: {wallet.address}")
            print(f"   Key length: {len(pk)} chars")
        else:
            print(f"   ❌ Decryption failed — wrong password?")
    
    # Save a flag file indicating successful unlock
    flag_file = Path("/root/.openclaw/workspace/orchestrator/config/.wallet_unlocked")
    flag_file.write_text("unlocked")
    print(f"\n🚀 Wallet unlocked! Flag saved: {flag_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 unlock_wallet.py <password>")
        print("Example: python3 unlock_wallet.py mypassword123")
        sys.exit(1)
    
    password = sys.argv[1]
    unlock_wallet(password)
