import asyncio
import aiohttp
import base58
import json
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer

logger = logging.getLogger(__name__)

# Jito tip address
JITO_TIP_ADDRESS = Pubkey.from_string("ADaUMID9eUjuDMLhjwzrhMYaS2iKZxTjyKdPpQcpEJpW")

@dataclass
class MEVConfig:
    """MEV protection configuration"""
    jito_endpoint: str = "https://mainnet.block-engine.jito.wtf/api/v1/bundles"
    jito_tip_lamports: int = 100000  # 0.0001 SOL
    use_jito: bool = True
    fallback_rpc: bool = True
    max_bundle_wait_ms: int = 200
    

class MEVProtection:
    """
    MEV protection using Jito bundles.
    
    Protects against:
    - Sandwich attacks
    - Front-running
    - Back-running
    
    Strategy:
    1. Build transaction
    2. Add tip transaction
    3. Bundle together
    4. Submit to Jito Block Engine
    5. Wait for confirmation (200ms max)
    6. Fallback to direct RPC if timeout
    """
    
    def __init__(self, config: MEVConfig, wallet: Keypair):
        self.config = config
        self.wallet = wallet
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize HTTP session"""
        if self._initialized:
            return
            
        self.http_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=50,
                keepalive_timeout=60,
                enable_cleanup_closed=True,
            ),
            timeout=aiohttp.ClientTimeout(total=5)
        )
        self._initialized = True
        logger.info("✅ MEV protection initialized")
        
    async def submit_protected(self, tx: Transaction, recent_blockhash) -> Dict:
        """
        Submit transaction with MEV protection.
        
        Returns:
            {'status': 'SUCCESS'|'FAILED'|'TIMEOUT', 'tx_id': str, 'method': str}
        """
        if not self.config.use_jito:
            return {'status': 'SKIPPED', 'tx_id': None, 'method': 'NONE'}
            
        try:
            # Build tip transaction
            tip_tx = self._create_tip_transaction(recent_blockhash)
            
            # Build bundle
            bundle = [
                base58.b58encode(tx.serialize()).decode(),
                base58.b58encode(tip_tx.serialize()).decode()
            ]
            
            # Submit to Jito
            result = await self._send_bundle(bundle)
            
            if result['status'] == 'SUCCESS':
                return result
            elif result['status'] == 'TIMEOUT' and self.config.fallback_rpc:
                logger.warning("Jito timeout, falling back to direct RPC")
                return {'status': 'FALLBACK', 'tx_id': None, 'method': 'RPC_FALLBACK'}
            else:
                return result
                
        except Exception as e:
            logger.error(f"MEV protection error: {e}")
            if self.config.fallback_rpc:
                return {'status': 'FALLBACK', 'tx_id': None, 'method': 'RPC_FALLBACK', 'error': str(e)}
            return {'status': 'FAILED', 'tx_id': None, 'method': 'JITO', 'error': str(e)}
            
    def _create_tip_transaction(self, recent_blockhash) -> Transaction:
        """Create tip transaction for validator"""
        tip_ix = transfer(
            TransferParams(
                from_pubkey=self.wallet.pubkey(),
                to_pubkey=JITO_TIP_ADDRESS,
                lamports=self.config.jito_tip_lamports
            )
        )
        
        tx = Transaction()
        tx.add(tip_ix)
        tx.recent_blockhash = recent_blockhash
        tx.sign(self.wallet)
        
        return tx
        
    async def _send_bundle(self, bundle: List[str]) -> Dict:
        """Send bundle to Jito Block Engine"""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'sendBundle',
            'params': [bundle]
        }
        
        try:
            async with asyncio.timeout(self.config.max_bundle_wait_ms / 1000):
                async with self.http_session.post(
                    self.config.jito_endpoint,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'result' in result:
                            return {
                                'status': 'SUCCESS',
                                'tx_id': result['result'].get('bundleId', 'unknown'),
                                'method': 'JITO_BUNDLE'
                            }
                        else:
                            return {
                                'status': 'FAILED',
                                'tx_id': None,
                                'method': 'JITO',
                                'error': result.get('error', 'Unknown error')
                            }
                    else:
                        return {
                            'status': 'FAILED',
                            'tx_id': None,
                            'method': 'JITO',
                            'error': f'HTTP {response.status}'
                        }
                        
        except asyncio.TimeoutError:
            return {'status': 'TIMEOUT', 'tx_id': None, 'method': 'JITO'}
        except Exception as e:
            return {'status': 'FAILED', 'tx_id': None, 'method': 'JITO', 'error': str(e)}
            
    async def check_bundle_status(self, bundle_id: str) -> Dict:
        """Check if bundle was included"""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getBundleStatuses',
            'params': [[bundle_id]]
        }
        
        try:
            async with self.http_session.post(
                self.config.jito_endpoint,
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'status': 'CHECKED',
                        'bundle_id': bundle_id,
                        'result': result
                    }
                else:
                    return {
                        'status': 'ERROR',
                        'bundle_id': bundle_id,
                        'error': f'HTTP {response.status}'
                    }
                    
        except Exception as e:
            return {'status': 'ERROR', 'bundle_id': bundle_id, 'error': str(e)}
            
    async def close(self):
        """Cleanup"""
        if self.http_session:
            await self.http_session.close()


class TPUClient:
    """
    Direct TPU submission via QUIC (advanced).
    
    Bypasses the mempool entirely by submitting directly to validator
    transaction processing units (TPUs).
    
    WARNING: This requires running on infrastructure very close to
    Solana validators (same data center or very low latency).
    """
    
    def __init__(self, validator_endpoints: List[str], wallet: Keypair):
        self.validator_endpoints = validator_endpoints
        self.wallet = wallet
        self.quic_connections = {}
        self._use_quic = False  # Disabled by default (requires additional setup)
        
    def enable_quic(self):
        """Enable QUIC connections (requires quic-client library)"""
        self._use_quic = True
        logger.info("QUIC enabled for direct TPU submission")
        
    async def submit_direct(self, tx: Transaction) -> Dict:
        """
        Submit directly to validator TPU.
        
        Returns:
            {'status': 'SUCCESS'|'FAILED', 'tx_id': str, 'method': str}
        """
        if not self._use_quic:
            return {'status': 'DISABLED', 'tx_id': None, 'method': 'TPU'}
            
        try:
            # Round-robin across validators
            import random
            endpoint = random.choice(self.validator_endpoints)
            
            # Get or create QUIC connection
            # NOTE: This requires solana-quic-client or similar
            # For now, we return a placeholder
            
            return {
                'status': 'NOT_IMPLEMENTED',
                'tx_id': None,
                'method': 'TPU_QUIC',
                'note': 'QUIC submission requires solana-quic-client library'
            }
            
        except Exception as e:
            return {'status': 'FAILED', 'tx_id': None, 'method': 'TPU', 'error': str(e)}


# ─── QUICK TEST ───
async def test_mev_protection():
    """Test MEV protection with dummy transaction"""
    from solders.keypair import Keypair
    
    wallet = Keypair()
    config = MEVConfig()
    
    mev = MEVProtection(config, wallet)
    await mev.initialize()
    
    # Create dummy transaction
    tx = Transaction()
    
    # Test submission (will fail without real RPC, but tests the flow)
    result = await mev.submit_protected(tx, None)
    print(f"MEV result: {result}")
    
    await mev.close()
    
    return result


if __name__ == "__main__":
    asyncio.run(test_mev_protection())
