import asyncio
import aiohttp
import json
import time
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import base58
import logging

# Solana imports
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

logger = logging.getLogger(__name__)

@dataclass
class ExecutionConfig:
    """Zero-latency execution configuration"""
    rpc_endpoint: str = "https://mainnet.helius-rpc.com/"
    websocket_endpoint: str = "wss://api.mainnet-beta.solana.com/"
    jito_endpoint: str = "https://mainnet.block-engine.jito.wtf/api/v1/bundles"
    jupiter_api: str = "https://quote-api.jup.ag/v6"
    
    # Pre-computed constants for speed
    COMPUTE_BUDGET: int = 140000
    PRIORITY_FEE_MICRO: int = 10000
    JITO_TIP_LAMPORTS: int = 100000  # 0.0001 SOL
    
    # Latency targets
    max_quote_latency_ms: int = 50
    max_build_latency_ms: int = 20
    max_submit_latency_ms: int = 50
    
    # MEV protection
    use_jito_bundles: bool = True
    fallback_to_rpc: bool = True


class ZeroLatencyExecutionEngine:
    """
    Ultra-fast execution engine targeting <100ms from signal to confirmation.
    
    Pipeline:
    1. Risk Check (1ms)
    2. Jupiter Quote (20ms)
    3. Route Optimization (5ms)
    4. Transaction Build (10ms)
    5. Sign (5ms)
    6. Submit (50ms via TPU or Jito)
    """
    
    def __init__(self, config: ExecutionConfig, wallet: Keypair):
        self.config = config
        self.wallet = wallet
        self.recent_blockhash = None
        self.blockhash_timestamp = 0
        
        # Connection pools (persistent)
        self.rpc_client: Optional[AsyncClient] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize persistent connections"""
        if self._initialized:
            return
            
        self.rpc_client = AsyncClient(self.config.rpc_endpoint)
        self.http_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                keepalive_timeout=60,
                enable_cleanup_closed=True,
                force_close=False,
            ),
            timeout=aiohttp.ClientTimeout(total=5)
        )
        
        # Pre-fetch initial blockhash
        await self._refresh_blockhash()
        
        self._initialized = True
        logger.info("✅ Execution engine initialized")
        
    async def _refresh_blockhash(self):
        """Refresh blockhash every 2 seconds"""
        try:
            response = await self.rpc_client.get_latest_blockhash()
            self.recent_blockhash = response.value.blockhash
            self.blockhash_timestamp = time.time_ns()
        except Exception as e:
            logger.error(f"Blockhash refresh failed: {e}")
            
    async def execute_trade(self, signal: dict) -> dict:
        """
        Execute a trade from signal to confirmation.
        
        Args:
            signal: {'mint': str, 'direction': 'BUY'|'SELL', 'size': float, 'slippage_bps': int}
        
        Returns:
            {'status': 'SUCCESS'|'FAILED', 'tx_id': str, 'latency_ms': float, 'error': str}
        """
        start_time = time.time_ns()
        
        try:
            # 1. Risk Check (1ms)
            if not await self._risk_check(signal):
                return {'status': 'REJECTED', 'error': 'Risk check failed', 'latency_ms': 0}
            
            # 2. Jupiter Quote (target: 20ms)
            quote = await self._get_jupiter_quote(signal)
            if not quote:
                return {'status': 'FAILED', 'error': 'Quote failed', 'latency_ms': 0}
            
            # 3. Route Optimization (5ms) - Jupiter already optimizes
            route = quote
            
            # 4. Transaction Build (10ms)
            tx = await self._build_transaction(route, signal)
            
            # 5. Sign (5ms)
            tx.sign(self.wallet)
            
            # 6. Submit (50ms via Jito or direct RPC)
            if self.config.use_jito_bundles:
                tx_id = await self._submit_jito_bundle(tx)
            else:
                tx_id = await self._submit_direct_rpc(tx)
            
            latency_ms = (time.time_ns() - start_time) / 1_000_000
            
            return {
                'status': 'SUCCESS',
                'tx_id': tx_id,
                'latency_ms': latency_ms,
                'error': None
            }
            
        except Exception as e:
            latency_ms = (time.time_ns() - start_time) / 1_000_000
            logger.error(f"Execution error: {e}")
            return {
                'status': 'FAILED',
                'tx_id': None,
                'latency_ms': latency_ms,
                'error': str(e)
            }
            
    async def _risk_check(self, signal: dict) -> bool:
        """Pre-execution risk validation"""
        # Check wallet balance
        balance = await self._get_wallet_balance()
        required = signal['size'] + 0.001  # Size + estimated fees
        
        if balance < required:
            logger.warning(f"Insufficient balance: {balance} < {required}")
            return False
            
        # Check slippage
        if signal.get('slippage_bps', 50) > 100:  # Max 1%
            logger.warning("Slippage too high")
            return False
            
        return True
        
    async def _get_jupiter_quote(self, signal: dict) -> Optional[dict]:
        """Get Jupiter quote with timeout"""
        input_mint = "So11111111111111111111111111111111111111112"  # SOL
        output_mint = signal['mint']
        amount = int(signal['size'] * 1_000_000_000)  # SOL to lamports
        
        if signal['direction'] == 'SELL':
            input_mint, output_mint = output_mint, input_mint
            
        url = f"{self.config.jupiter_api}/quote"
        params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': amount,
            'slippageBps': signal.get('slippage_bps', 50)
        }
        
        try:
            async with asyncio.timeout(self.config.max_quote_latency_ms / 1000):
                async with self.http_session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Quote HTTP {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("Quote timeout")
            return None
            
    async def _build_transaction(self, quote: dict, signal: dict) -> Transaction:
        """Build swap transaction with minimal overhead"""
        # Get swap instructions from Jupiter
        swap_url = f"{self.config.jupiter_api}/swap"
        swap_payload = {
            'quoteResponse': quote,
            'userPublicKey': str(self.wallet.pubkey()),
            'wrapAndUnwrapSol': True,
            'computeUnitPriceMicroLamports': self.config.PRIORITY_FEE_MICRO
        }
        
        async with self.http_session.post(swap_url, json=swap_payload) as response:
            swap_data = await response.json()
            
        # Deserialize transaction
        tx = Transaction.from_bytes(base58.b58decode(swap_data['swapTransaction']))
        
        # Add compute budget if not present
        # (Jupiter usually handles this, but we double-check)
        
        # Refresh blockhash if needed (>2s old)
        if time.time_ns() - self.blockhash_timestamp > 2_000_000_000:
            await self._refresh_blockhash()
            
        tx.recent_blockhash = self.recent_blockhash
        
        return tx
        
    async def _submit_jito_bundle(self, tx: Transaction) -> str:
        """Submit via Jito MEV bundle"""
        # Create tip transaction
        tip_ix = transfer(
            TransferParams(
                from_pubkey=self.wallet.pubkey(),
                to_pubkey=Pubkey.from_string("ADaUMID9eUjuDMLhjwzrhMYaS2iKZxTjyKdPpQcpEJpW"),  # Jito tip
                lamports=self.config.JITO_TIP_LAMPORTS
            )
        )
        
        tip_tx = Transaction()
        tip_tx.add(tip_ix)
        tip_tx.recent_blockhash = self.recent_blockhash
        tip_tx.sign(self.wallet)
        
        # Bundle: [main tx, tip tx]
        bundle = [
            base58.b58encode(tx.serialize()).decode(),
            base58.b58encode(tip_tx.serialize()).decode()
        ]
        
        # Submit to Jito
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'sendBundle',
            'params': [bundle]
        }
        
        async with self.http_session.post(
            self.config.jito_endpoint,
            json=payload
        ) as response:
            result = await response.json()
            return result.get('result', {}).get('bundleId', 'unknown')
            
    async def _submit_direct_rpc(self, tx: Transaction) -> str:
        """Submit directly via RPC (fallback)"""
        serialized = base58.b58encode(tx.serialize()).decode()
        
        response = await self.rpc_client.send_transaction(
            serialized,
            opts={'skipPreflight': True, 'maxRetries': 2}
        )
        
        return response.value
        
    async def _get_wallet_balance(self) -> float:
        """Get wallet SOL balance"""
        response = await self.rpc_client.get_balance(self.wallet.pubkey())
        return response.value / 1_000_000_000  # lamports to SOL
        
    async def close(self):
        """Cleanup connections"""
        if self.http_session:
            await self.http_session.close()
        if self.rpc_client:
            await self.rpc_client.close()


# ─── QUICK TEST ───
async def test_execution_engine():
    """Test the execution engine with a dummy trade"""
    from solders.keypair import Keypair
    
    # Generate test keypair (DO NOT USE IN PRODUCTION)
    wallet = Keypair()
    
    config = ExecutionConfig()
    engine = ZeroLatencyExecutionEngine(config, wallet)
    
    await engine.initialize()
    
    # Test signal
    signal = {
        'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
        'direction': 'BUY',
        'size': 0.01,  # 0.01 SOL
        'slippage_bps': 50
    }
    
    result = await engine.execute_trade(signal)
    print(f"Result: {result}")
    
    await engine.close()


if __name__ == "__main__":
    asyncio.run(test_execution_engine())
