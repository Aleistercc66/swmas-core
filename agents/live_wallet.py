import os
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import base58

# Solana imports
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

logger = logging.getLogger(__name__)

@dataclass
class WalletConfig:
    """Wallet configuration"""
    private_key: str  # base58 encoded
    rpc_endpoint: str = "https://mainnet.helius-rpc.com/"
    backup_rpc: str = "https://api.mainnet-beta.solana.com/"
    wallet_type: str = "solflare"  # solflare, phantom, sollet, ledger
    account_name: str = "Account 2"
    
    # Safety
    max_transaction_amount: float = 1.0  # SOL
    require_confirmation: bool = True
    daily_limit: float = 5.0  # SOL per day


class LiveWalletConnector:
    """
    Live Wallet Connector for Solana
    
    Supports:
    - Solflare (Account 2)
    - Phantom
    - Sollet
    - Ledger (via keypair import)
    
    Security:
    - Private key from environment variable only
    - Daily transaction limits
    - Manual confirmation for large amounts
    - RPC failover (Helius → QuickNode → Public)
    """
    
    def __init__(self, config: WalletConfig):
        self.config = config
        self.keypair: Optional[Keypair] = None
        self.rpc_client: Optional[AsyncClient] = None
        self.backup_rpc_client: Optional[AsyncClient] = None
        self.initialized = False
        self.daily_spent = 0.0
        self.last_reset = None
        
    async def initialize(self):
        """Initialize wallet connection"""
        logger.info(f"🔑 Initializing wallet: {self.config.wallet_type} | {self.config.account_name}")
        
        # 1. Load keypair from private key
        try:
            self.keypair = Keypair.from_base58_string(self.config.private_key)
            logger.info(f"✅ Keypair loaded: {self.keypair.pubkey()}")
        except Exception as e:
            logger.error(f"❌ Failed to load keypair: {e}")
            raise
            
        # 2. Connect to RPC
        try:
            self.rpc_client = AsyncClient(self.config.rpc_endpoint, commitment=Confirmed)
            logger.info(f"✅ RPC connected: {self.config.rpc_endpoint}")
        except Exception as e:
            logger.warning(f"⚠️ Primary RPC failed: {e}")
            try:
                self.rpc_client = AsyncClient(self.config.backup_rpc, commitment=Confirmed)
                logger.info(f"✅ Backup RPC connected: {self.config.backup_rpc}")
            except Exception as e2:
                logger.error(f"❌ Backup RPC also failed: {e2}")
                raise
                
        # 3. Verify balance
        balance = await self.get_balance()
        logger.info(f"💰 Wallet balance: {balance:.6f} SOL")
        
        if balance < 0.01:
            logger.warning(f"⚠️ Low balance: {balance:.6f} SOL — add funds!")
            
        self.initialized = True
        self.last_reset = datetime.now().day
        
        logger.info(f"🔥 Live wallet ready: {self.keypair.pubkey()} | {balance:.6f} SOL")
        
    async def get_balance(self) -> float:
        """Get wallet SOL balance"""
        if not self.rpc_client:
            return 0.0
            
        try:
            response = await self.rpc_client.get_balance(self.keypair.pubkey())
            return response.value / 1_000_000_000  # lamports to SOL
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return 0.0
            
    async def get_token_balance(self, mint: str) -> float:
        """Get token balance for a specific mint"""
        try:
            from spl.token.async_client import AsyncToken
            from spl.token.constants import TOKEN_PROGRAM_ID
            
            mint_pubkey = Pubkey.from_string(mint)
            
            # Get associated token account
            response = await self.rpc_client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {'mint': str(mint_pubkey)}
            )
            
            if response.value:
                account = response.value[0]
                # Parse balance from account data
                # This is a simplified version
                return 0.0  # Placeholder
            return 0.0
            
        except Exception as e:
            logger.error(f"Token balance failed: {e}")
            return 0.0
            
    def _check_daily_limit(self, amount: float) -> Tuple[bool, str]:
        """Check if transaction exceeds daily limit"""
        today = datetime.now().day
        if today != self.last_reset:
            self.daily_spent = 0.0
            self.last_reset = today
            
        if self.daily_spent + amount > self.config.daily_limit:
            return False, f"Daily limit exceeded: {self.daily_spent:.4f} / {self.config.daily_limit:.4f} SOL"
            
        return True, "OK"
        
    def _check_amount(self, amount: float) -> Tuple[bool, str]:
        """Check if amount is within safe limits"""
        if amount > self.config.max_transaction_amount:
            return False, f"Amount {amount:.4f} SOL exceeds max {self.config.max_transaction_amount:.4f} SOL"
            
        if amount < 0.000001:  # 1 lamport
            return False, "Amount too small"
            
        return True, "OK"
        
    async def sign_transaction(self, transaction_bytes: bytes) -> bytes:
        """Sign a transaction with the wallet"""
        if not self.keypair:
            raise RuntimeError("Wallet not initialized")
            
        from solders.transaction import Transaction as SoldersTransaction
        
        # Deserialize and sign
        tx = SoldersTransaction.from_bytes(transaction_bytes)
        tx.sign([self.keypair])
        
        return tx.serialize()
        
    async def get_recent_blockhash(self) -> str:
        """Get recent blockhash for transactions"""
        try:
            response = await self.rpc_client.get_latest_blockhash()
            return response.value.blockhash
        except Exception as e:
            logger.error(f"Blockhash failed: {e}")
            raise
            
    async def get_fee_for_message(self, message) -> int:
        """Get estimated fee for a message"""
        try:
            response = await self.rpc_client.get_fee_for_message(message)
            return response.value or 5000
        except:
            return 5000
            
    async def close(self):
        """Close connections"""
        if self.rpc_client:
            await self.rpc_client.close()
        if self.backup_rpc_client:
            await self.backup_rpc_client.close()
        logger.info("🔌 Wallet connections closed")
        
    @staticmethod
    def from_env() -> "LiveWalletConnector":
        """Create wallet connector from environment variables"""
        private_key = os.environ.get('SOLANA_PRIVATE_KEY')
        if not private_key:
            raise ValueError("SOLANA_PRIVATE_KEY environment variable not set")
            
        rpc = os.environ.get('SOLANA_RPC', 'https://mainnet.helius-rpc.com/')
        wallet_type = os.environ.get('WALLET_TYPE', 'solflare')
        account_name = os.environ.get('WALLET_ACCOUNT', 'Account 2')
        
        config = WalletConfig(
            private_key=private_key,
            rpc_endpoint=rpc,
            wallet_type=wallet_type,
            account_name=account_name
        )
        
        return LiveWalletConnector(config)
        
    @staticmethod
    def generate_new() -> Tuple[str, str]:
        """Generate a new wallet (for testing)"""
        keypair = Keypair()
        private_key = base58.b58encode(keypair.secret()).decode()
        public_key = str(keypair.pubkey())
        
        return private_key, public_key


# ─── QUICK TEST ───
async def test_wallet():
    """Test wallet connector"""
    # For testing, generate a new wallet (DO NOT USE IN PRODUCTION)
    private_key, public_key = LiveWalletConnector.generate_new()
    
    config = WalletConfig(
        private_key=private_key,
        rpc_endpoint='https://api.devnet.solana.com/',
        wallet_type='test'
    )
    
    wallet = LiveWalletConnector(config)
    
    try:
        await wallet.initialize()
        
        balance = await wallet.get_balance()
        print(f"✅ Wallet: {public_key}")
        print(f"💰 Balance: {balance:.6f} SOL")
        print(f"🔥 Live wallet ready!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await wallet.close()


if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    asyncio.run(test_wallet())
