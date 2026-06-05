#!/usr/bin/env python3
"""
Wallet Setup — Recreate wallet with correct password
Usage: Save your private key to /tmp/solana_key.txt first, then run:
  python3 setup_wallet.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/agents')
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')

from core.wallet_manager import WalletManager, SecureKeyStorage

WALLETS_FILE = Path("/root/.openclaw/workspace/orchestrator/config/wallets.json")
KEY_FILE = Path("/tmp/solana_key.txt")

def setup_wallet():
    if not KEY_FILE.exists():
        print("❌ No key file found!")
        print(f"\n1. Export your private key from Solflare/MetaMask")
        print(f"2. Save it to: {KEY_FILE}")
        print(f"3. Run this script again")
        print(f"\nExample:")
        print(f"  echo 'your_private_key_here' > {KEY_FILE}")
        return
    
    private_key = KEY_FILE.read_text().strip()
    password = "239607"
    
    print(f"🔐 Setting up wallet with password: {password}")
    print(f"📍 Key length: {len(private_key)} chars")
    
    wm = WalletManager()
    
    # Remove old wallet if exists
    if WALLETS_FILE.exists():
        data = json.loads(WALLETS_FILE.read_text())
        # Remove solana wallets
        to_remove = [k for k, v in data.items() if v.get('chain') == 'solana']
        for k in to_remove:
            del data[k]
        WALLETS_FILE.write_text(json.dumps(data, indent=2))
        print(f"🗑️  Removed {len(to_remove)} old Solana wallets")
    
    # Add new wallet
    try:
        wallet = asyncio.run(wm.add_wallet(
            name="Wallet 2",
            private_key=private_key,
            chain='solana',
            password=password
        ))
        print(f"✅ Wallet created!")
        print(f"   Name: {wallet.name}")
        print(f"   Address: {wallet.address}")
        print(f"   Chain: {wallet.chain}")
        
        # Remove key file for security
        KEY_FILE.unlink()
        print(f"🗑️  Key file removed for security")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import asyncio
    setup_wallet()
