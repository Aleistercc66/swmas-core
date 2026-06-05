#!/usr/bin/env python3
"""
Recreate wallet with correct password.
Uses existing wallet address but re-encrypts with working password.
"""
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from core.wallet_manager import WalletManager, SecureKeyStorage

WALLETS_FILE = Path("/root/.openclaw/workspace/orchestrator/config/wallets.json")

def recreate_wallet(password: str):
    """Recreate wallet with correct password."""
    
    # Load existing wallets
    if not WALLETS_FILE.exists():
        print("❌ No wallets file found")
        return
    
    data = json.loads(WALLETS_FILE.read_text())
    
    # Find Solana wallet
    solana_wallet = None
    for name, wallet in data.items():
        if wallet.get('chain') == 'solana':
            solana_wallet = wallet
            break
    
    if not solana_wallet:
        print("❌ No Solana wallet found")
        return
    
    address = solana_wallet['address']
    print(f"📍 Found Solana wallet: {address}")
    
    # We need the private key — since we can't decrypt, we need user to provide it
    # OR we generate a new one
    print("\n⚠️  Cannot decrypt existing wallet — need to recreate")
    print("Option 1: Provide private key (if you have it)")
    print("Option 2: Generate new wallet (you'll lose current one)")
    
    # For now, let's create a new wallet with the password
    # But we need the private key... 
    
    # Actually, the user needs to provide their private key or we need to 
    # extract it somehow. Since we can't decrypt, the only way is:
    # 1. User provides private key from their wallet app
    # 2. Or we use a different approach

if __name__ == "__main__":
    print("🔐 Wallet Recreation Tool")
    print("Since we can't decrypt the existing wallet, we need your private key.")
    print("\nGet your private key from Solflare/MetaMask:")
    print("  Solflare: Settings → Export Private Key")
    print("  MetaMask: Account → Account Details → Export Private Key")
    print("\n⚠️  NEVER share your private key in chat! Save it to a file.")
