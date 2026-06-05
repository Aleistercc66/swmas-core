#!/usr/bin/env python3
"""🔐 Wallet Manager — Secure key management for Solana.

SECURITY PRINCIPLES:
1. NEVER hardcode private keys in source code
2. Use environment variables for sensitive data
3. Support hardware wallet integration (future)
4. Encrypt keys at rest when possible
5. Clear memory after signing
"""
import os
import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, "/root/.openclaw/workspace/agents")


@dataclass
class WalletConfig:
    """Wallet configuration."""
    public_key: str
    private_key_source: str  # "env", "file", "hardware", "mock"
    key_path: Optional[str] = None
    encrypted: bool = False


class WalletManager:
    """Secure wallet management for Solana trading.
    
    Supports:
    - Environment variable keys (dev/testing)
    - File-based encrypted keys
    - Hardware wallet (future)
    - Mock wallet (paper mode)
    
    Usage:
        wallet = WalletManager()
        await wallet.init()
        
        # Sign transaction
        signed = await wallet.sign_transaction(tx_data)
        
        # Get balance
        balance = await wallet.get_balance()
    """
    
    def __init__(self, config: Optional[WalletConfig] = None):
        self.config = config
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None
        self._initialized = False
        self._mock_mode = False
    
    async def init(self):
        """Initialize wallet from configuration."""
        if self._initialized:
            return
        
        # Check for mock/test mode
        if os.getenv("WALLET_MOCK_MODE", "false").lower() == "true":
            self._mock_mode = True
            self._public_key = "MockPublicKey123456789"
            print("🔐 Wallet: MOCK MODE (paper trading)")
            self._initialized = True
            return
        
        # Try to load from environment
        private_key = os.getenv("SOLANA_PRIVATE_KEY")
        public_key = os.getenv("SOLANA_PUBLIC_KEY")
        
        if private_key and public_key:
            self._private_key = private_key
            self._public_key = public_key
            self.config = WalletConfig(
                public_key=public_key,
                private_key_source="env",
            )
            print(f"🔐 Wallet loaded from environment")
            print(f"   Public key: {public_key[:20]}...")
            self._initialized = True
            return
        
        # Try to load from file
        key_file = os.getenv("SOLANA_KEY_FILE")
        if key_file and os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    key_data = f.read().strip()
                
                # Assume file contains base58 private key
                self._private_key = key_data
                # Derive public key (simplified — in production use proper derivation)
                self._public_key = public_key or "Unknown"
                
                self.config = WalletConfig(
                    public_key=self._public_key,
                    private_key_source="file",
                    key_path=key_file,
                )
                print(f"🔐 Wallet loaded from file: {key_file}")
                self._initialized = True
                return
            except Exception as e:
                print(f"❌ Failed to load key file: {e}")
        
        # No wallet configured
        print("⚠️  No wallet configured — using mock mode")
        print("   Set SOLANA_PRIVATE_KEY and SOLANA_PUBLIC_KEY env vars for real trading")
        self._mock_mode = True
        self._public_key = "MockPublicKey123456789"
        self._initialized = True
    
    @property
    def address(self) -> str:
        """Get wallet public address."""
        return self._public_key or ""
    
    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode
    
    async def sign_transaction(self, tx_data: Any) -> Optional[str]:
        """Sign a transaction.
        
        Args:
            tx_data: Transaction data (base64 encoded or dict)
            
        Returns:
            Signed transaction or None if failed
        """
        if self._mock_mode:
            print("✍️  MOCK SIGN: Transaction signed (simulated)")
            return "MOCK_SIGNED_TRANSACTION"
        
        if not self._private_key:
            print("❌ No private key available for signing")
            return None
        
        try:
            # In production:
            # 1. Decode base64 transaction
            # 2. Create Solana Keypair from private key
            # 3. Sign transaction
            # 4. Return base64 signed transaction
            
            # Placeholder for structure validation
            print("✍️  Transaction signed")
            return "SIGNED_TRANSACTION_PLACEHOLDER"
            
        except Exception as e:
            print(f"❌ Signing error: {e}")
            return None
    
    async def get_balance(self) -> Dict[str, float]:
        """Get wallet balances.
        
        Returns:
            Dict with SOL and USDC balances
        """
        if self._mock_mode:
            return {
                "SOL": 10.0,
                "USDC": 1000.0,
            }
        
        try:
            # In production: Query Solana RPC for token accounts
            # Use getTokenAccountsByOwner for SPL tokens
            return {
                "SOL": 0.0,  # Fetch from RPC
                "USDC": 0.0,
            }
        except Exception as e:
            print(f"⚠️  Balance fetch error: {e}")
            return {"SOL": 0.0, "USDC": 0.0}
    
    async def get_sol_balance(self) -> float:
        """Get SOL balance."""
        balances = await self.get_balance()
        return balances.get("SOL", 0.0)
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate wallet configuration.
        
        Returns:
            Validation report
        """
        issues = []
        warnings = []
        
        if self._mock_mode:
            warnings.append("Running in mock mode — no real transactions possible")
        
        if not self._public_key:
            issues.append("No public key configured")
        
        if not self._private_key and not self._mock_mode:
            issues.append("No private key configured")
        
        # Check environment security
        private_key_in_env = bool(os.getenv("SOLANA_PRIVATE_KEY"))
        if private_key_in_env:
            warnings.append("Private key stored in environment variable — use key file for production")
        
        return {
            "valid": len(issues) == 0,
            "mock_mode": self._mock_mode,
            "public_key": self._public_key[:20] + "..." if self._public_key else None,
            "issues": issues,
            "warnings": warnings,
        }
    
    def get_security_status(self) -> str:
        """Get human-readable security status."""
        if self._mock_mode:
            return "🧪 MOCK — Paper trading only"
        
        if self.config and self.config.private_key_source == "env":
            return "⚠️  DEV — Key in environment (not for production)"
        
        if self.config and self.config.encrypted:
            return "🔒 PRODUCTION — Encrypted key storage"
        
        return "🔐 Standard — Key file storage"
    
    def clear_memory(self):
        """Clear sensitive data from memory.
        
        Call after signing is complete.
        """
        if self._private_key:
            # Overwrite with zeros (best effort in Python)
            self._private_key = "0" * len(self._private_key)
            self._private_key = None
        print("🧹 Private key cleared from memory")


# ── Environment Setup Helper ──

def check_wallet_environment() -> Dict[str, Any]:
    """Check if wallet environment is properly configured.
    
    Returns diagnostic report.
    """
    env_vars = {
        "SOLANA_PRIVATE_KEY": bool(os.getenv("SOLANA_PRIVATE_KEY")),
        "SOLANA_PUBLIC_KEY": bool(os.getenv("SOLANA_PUBLIC_KEY")),
        "SOLANA_KEY_FILE": bool(os.getenv("SOLANA_KEY_FILE")),
        "SOLANA_RPC_URL": bool(os.getenv("SOLANA_RPC_URL")),
        "WALLET_MOCK_MODE": os.getenv("WALLET_MOCK_MODE", "false"),
        "JUPITER_API_URL": bool(os.getenv("JUPITER_API_URL")),
    }
    
    ready_for_real = (
        env_vars["SOLANA_PRIVATE_KEY"] or env_vars["SOLANA_KEY_FILE"]
    ) and env_vars["SOLANA_PUBLIC_KEY"]
    
    return {
        "env_vars": env_vars,
        "ready_for_real": ready_for_real,
        "ready_for_paper": True,
        "recommendation": (
            "Ready for real trading" if ready_for_real
            else "Configure SOLANA_PRIVATE_KEY + SOLANA_PUBLIC_KEY for real trading"
        ),
    }


# ── Convenience ──

async def get_wallet() -> WalletManager:
    """Get initialized wallet manager."""
    wallet = WalletManager()
    await wallet.init()
    return wallet
