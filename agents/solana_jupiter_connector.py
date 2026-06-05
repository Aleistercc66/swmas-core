#!/usr/bin/env python3
"""
Solana Jupiter DEX Trading Connector
Full programmatic access to Jupiter DEX aggregator on Solana.
Compatible with MetaMask (Phantom, Solflare wallets).

Features:
- Token swaps via Jupiter API
- Limit orders
- DCA (Dollar Cost Averaging)
- Price quotes and routing
- Multi-token support
"""
import asyncio
import base64
import json
import logging
import os
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Solana
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer

# Jupiter
try:
    from jupiter_python_sdk_public.jupiter import Jupiter, Jupiter_DCA
    JUPITER_SDK_AVAILABLE = True
except ImportError:
    JUPITER_SDK_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/agents/logs/solana_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('solana_jupiter')


@dataclass
class JupiterSwapQuote:
    """Jupiter swap quote"""
    input_mint: str
    output_mint: str
    input_amount: Decimal
    output_amount: Decimal
    price_impact_pct: Decimal
    route: List[dict]
    slippage_bps: int
    tx_data: str  # Serialized transaction
    timestamp: float = field(default_factory=time.time)


class SolanaJupiterConnector:
    """
    Solana DEX trading via Jupiter aggregator.
    
    Jupiter is the BEST aggregator on Solana:
    - Routes through all major DEXs (Raydium, Orca, Phoenix, etc.)
    - Smart routing for best prices
    - Trade splitting across multiple DEXs
    - Lowest slippage
    
    Usage:
        connector = SolanaJupiterConnector(private_key='base58_key')
        await connector.initialize()
        quote = await connector.get_quote('SOL', 'USDC', amount=0.1)
        tx_id = await connector.execute_swap(quote)
    """
    
    # Token mints on Solana
    TOKENS = {
        'SOL': 'So11111111111111111111111111111111111111112',
        'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
        'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        'JUP': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',
        'WIF': 'EKpQGSJtjMFqKZ9KQanSq7Rcj8HssmopJ5ueVAvzSavz',
        'RAY': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',
        'ORCA': 'orcaEKTdK7LKz57VaAYr9Q2N8mK7b66dkE6WmY7nFDE',
        'MSOL': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
        'JITO': 'J1to4oMm6V1bBAM7kzJr8rCjUqMsJf1DqiG8qouwb5uo',
    }
    
    # DEX endpoints — UPDATED for Jupiter API v1 (2026)
    # Old v6 API (quote-api.jup.ag) was sunset by Jupiter
    JUPITER_QUOTE_API = 'https://api.jup.ag/swap/v1/quote'
    JUPITER_SWAP_API = 'https://api.jup.ag/swap/v1/swap'
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        rpc_url: str = 'https://api.mainnet-beta.solana.com',
        paper_trading: bool = True,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.paper_trading = paper_trading
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Solana client
        self.client: Optional[AsyncClient] = None
        self.wallet: Optional[Keypair] = None
        self.jupiter: Optional[Jupiter] = None
        
        # Stats
        self.swaps_executed: int = 0
        self.total_volume_sol: Decimal = Decimal('0')
        self.trade_history: List[dict] = []
        
        logger.info(f"☀️ Solana Jupiter Connector initialized")
        logger.info(f"   RPC: {rpc_url}")
        logger.info(f"   Paper trading: {paper_trading}")
    
    async def initialize(self):
        """Initialize Solana connection"""
        # Initialize RPC client
        self.client = AsyncClient(self.rpc_url, commitment=Confirmed)
        
        # Test connection
        try:
            # Fix: Use get_slot() instead of get_health() for newer solana-py versions
            health = await self.client.get_slot()
            logger.info(f"✅ Solana RPC connected: slot {health}")
        except Exception as e:
            logger.error(f"❌ RPC connection failed: {e}")
            return
        
        # Initialize wallet
        if self.private_key:
            try:
                # Try base58 encoded key
                import base58
                decoded = base58.b58decode(self.private_key)
                self.wallet = Keypair.from_bytes(decoded)
                logger.info(f"   Wallet: {self.wallet.pubkey()}")
            except Exception as e:
                logger.error(f"Key decode error: {e}")
        else:
            logger.warning("   No private key - read-only mode")
        
        # Initialize Jupiter SDK
        if JUPITER_SDK_AVAILABLE and self.wallet:
            try:
                self.jupiter = Jupiter(
                    async_client=self.client,
                    keypair=self.wallet,
                    quote_api_url=self.JUPITER_QUOTE_API + '?',
                    swap_api_url=self.JUPITER_SWAP_API
                )
                logger.info("✅ Jupiter SDK initialized")
            except Exception as e:
                logger.error(f"Jupiter init error: {e}")
        else:
            logger.info("   Jupiter SDK not available - using direct API")
    
    async def get_balance(self, token: str = 'SOL') -> Decimal:
        """Get token balance"""
        if not self.client or not self.wallet:
            return Decimal('0')
        
        try:
            if token == 'SOL':
                # Native SOL balance
                response = await self.client.get_balance(self.wallet.pubkey())
                lamports = response.value
                return Decimal(lamports) / Decimal(10**9)
            else:
                # SPL token balance
                mint = self.TOKENS.get(token)
                if not mint:
                    return Decimal('0')
                
                # Get token accounts
                response = await self.client.get_token_accounts_by_owner(
                    self.wallet.pubkey(),
                    {'mint': Pubkey.from_string(mint)}
                )
                
                if response.value:
                    # Parse token balance
                    account = response.value[0]
                    # Would need to decode account data
                    return Decimal('0')  # Simplified
                
                return Decimal('0')
                
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return Decimal('0')
    
    async def get_quote(
        self,
        input_token: str,
        output_token: str,
        amount: Decimal,
        slippage_bps: int = 50  # 0.5%
    ) -> Optional[JupiterSwapQuote]:
        """
        Get swap quote from Jupiter.
        
        Args:
            input_token: Token to sell (symbol)
            output_token: Token to buy (symbol)
            amount: Amount to sell
            slippage_bps: Slippage tolerance in basis points
        """
        input_mint = self.TOKENS.get(input_token)
        output_mint = self.TOKENS.get(output_token)
        
        if not input_mint or not output_mint:
            logger.error(f"Token not found: {input_token} or {output_token}")
            return None
        
        # Convert amount to raw (lamports for SOL, decimals for others)
        if input_token == 'SOL':
            amount_raw = int(amount * Decimal(10**9))
        else:
            amount_raw = int(amount * Decimal(10**6))  # Most tokens have 6 decimals
        
        try:
            # ⚠️ Jupiter SDK uses sunset v6 API — use direct v1 API instead
            # if self.jupiter:
            #     quote_data = await self.jupiter.quote(...)  # DISABLED — v6 dead
            
            # Use direct Jupiter v1 API call
            return await self._get_quote_api(
                input_mint, output_mint, amount_raw, slippage_bps
            )
            
        except Exception as e:
            logger.error(f"Quote error: {e}")
            return None
    
    async def _get_quote_api(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int
    ) -> Optional[JupiterSwapQuote]:
        """Get quote directly from Jupiter v1 API"""
        import aiohttp
        
        url = self.JUPITER_QUOTE_API
        params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': str(amount),
            'slippageBps': slippage_bps,
            'onlyDirectRoutes': 'false',
            'asLegacyTransaction': 'false'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # v1 API returns amounts as strings
                        out_amount_str = str(data.get('outAmount', '0'))
                        output_amount = Decimal(out_amount_str)
                        
                        # Determine decimals for output token
                        if output_mint == self.TOKENS.get('SOL'):
                            output_amount = output_amount / Decimal(10**9)
                        else:
                            output_amount = output_amount / Decimal(10**6)
                        
                        # Input amount conversion for display
                        if input_mint == self.TOKENS.get('SOL'):
                            input_amount_ui = Decimal(str(amount)) / Decimal(10**9)
                        else:
                            input_amount_ui = Decimal(str(amount)) / Decimal(10**6)
                        
                        price_impact = Decimal(str(data.get('priceImpactPct', '0')))
                        
                        logger.info(f"📊 Quote: {input_amount_ui} → {output_amount} | Impact: {float(price_impact):.4f}%")
                        
                        return JupiterSwapQuote(
                            input_mint=input_mint,
                            output_mint=output_mint,
                            input_amount=input_amount_ui,
                            output_amount=output_amount,
                            price_impact_pct=price_impact,
                            route=data.get('routePlan', []),
                            slippage_bps=slippage_bps,
                            tx_data=json.dumps(data)
                        )
                    else:
                        error_text = await resp.text()
                        logger.error(f"API error: {resp.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"API quote error: {e}")
            return None
    
    async def execute_swap(self, quote: JupiterSwapQuote) -> Optional[str]:
        """
        Execute a swap on Jupiter.
        
        Returns:
            Transaction signature
        """
        if self.paper_trading:
            logger.info(f"🧪 PAPER SWAP: {quote.input_amount} → {quote.output_amount}")
            self.swaps_executed += 1
            self.total_volume_sol += quote.input_amount
            
            trade_record = {
                'type': 'PAPER',
                'timestamp': time.time(),
                'input': str(quote.input_amount),
                'output': str(quote.output_amount),
                'impact': float(quote.price_impact_pct)
            }
            self.trade_history.append(trade_record)
            
            await self._send_alert(quote)
            return f"paper_tx_{int(time.time())}"
        
        if not self.wallet:
            logger.error("Wallet not initialized")
            return None
        
        try:
            # Use Jupiter v1 API directly (SDK is v6, sunset)
            import aiohttp
            
            # Get swap transaction from v1 API
            swap_url = self.JUPITER_SWAP_API
            swap_body = {
                'quoteResponse': json.loads(quote.tx_data),
                'userPublicKey': str(self.wallet.pubkey()),
                'wrapAndUnwrapSol': True,
                'prioritizationFeeLamports': 'auto'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(swap_url, json=swap_body) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Swap API error: {resp.status} - {error_text}")
                        return None
                    
                    swap_data = await resp.json()
            
            # Deserialize and sign transaction
            swap_tx_base64 = swap_data.get('swapTransaction')
            if not swap_tx_base64:
                logger.error("No swapTransaction in response")
                return None
            
            raw_tx = VersionedTransaction.from_bytes(
                base64.b64decode(swap_tx_base64)
            )
            
            # Sign with wallet
            signed_tx = VersionedTransaction(
                raw_tx.message,
                [self.wallet]
            )
            
            # Send transaction
            opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=Confirmed
            )
            
            result = await self.client.send_raw_transaction(
                bytes(signed_tx),
                opts=opts
            )
            
            tx_id = json.loads(result.to_json())['result']
            
            logger.info(f"✅ Swap executed: {tx_id}")
            logger.info(f"   Explorer: https://solscan.io/tx/{tx_id}")
            
            self.swaps_executed += 1
            self.total_volume_sol += quote.input_amount
            
            trade_record = {
                'type': 'LIVE',
                'timestamp': time.time(),
                'tx_id': tx_id,
                'input': str(quote.input_amount),
                'output': str(quote.output_amount)
            }
            self.trade_history.append(trade_record)
            
            await self._send_alert(quote, tx_id)
            
            return tx_id
            
        except Exception as e:
            logger.error(f"❌ Swap failed: {e}")
            return None
    
    async def execute_limit_order(
        self,
        input_token: str,
        output_token: str,
        input_amount: Decimal,
        output_amount: Decimal
    ) -> Optional[str]:
        """Place a limit order via Jupiter"""
        if not self.jupiter or self.paper_trading:
            logger.info(f"🧪 PAPER LIMIT ORDER: {input_amount} {input_token} @ {output_amount} {output_token}")
            return f"paper_order_{int(time.time())}"
        
        try:
            order_data = await self.jupiter.open_order(
                input_mint=self.TOKENS.get(input_token),
                output_mint=self.TOKENS.get(output_token),
                in_amount=int(input_amount * Decimal(10**9)),
                out_amount=int(output_amount * Decimal(10**6))
            )
            
            logger.info(f"✅ Limit order placed")
            return order_data.get('signature')
            
        except Exception as e:
            logger.error(f"Limit order error: {e}")
            return None
    
    async def execute_dca(
        self,
        input_token: str,
        output_token: str,
        total_amount: Decimal,
        amount_per_cycle: Decimal,
        cycle_frequency: int = 3600  # seconds
    ) -> Optional[str]:
        """Create DCA (Dollar Cost Averaging) strategy"""
        if not self.jupiter or self.paper_trading:
            logger.info(f"🧪 PAPER DCA: {total_amount} {input_token} over {total_amount/amount_per_cycle} cycles")
            return f"paper_dca_{int(time.time())}"
        
        try:
            dca = Jupiter_DCA(
                async_client=self.client,
                keypair=self.wallet
            )
            
            result = await dca.create_dca(
                input_mint=Pubkey.from_string(self.TOKENS.get(input_token)),
                output_mint=Pubkey.from_string(self.TOKENS.get(output_token)),
                total_in_amount=int(total_amount * Decimal(10**9)),
                in_amount_per_cycle=int(amount_per_cycle * Decimal(10**9)),
                cycle_frequency=cycle_frequency,
                min_out_amount_per_cycle=0,
                max_out_amount_per_cycle=0,
                start=int(time.time())
            )
            
            logger.info(f"✅ DCA created: {result}")
            return result
            
        except Exception as e:
            logger.error(f"DCA error: {e}")
            return None
    
    async def _send_alert(self, quote: JupiterSwapQuote, tx_id: Optional[str] = None):
        """Send Telegram alert"""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            import aiohttp
            
            mode = "🧪 PAPER" if self.paper_trading else "💰 LIVE"
            status = f"✅ TX: {tx_id}" if tx_id else "📊 QUOTE"
            
            message = (
                f"{mode} JUPITER SWAP\n\n"
                f"🔄 {quote.input_amount} → {quote.output_amount}\n"
                f"📊 Impact: {float(quote.price_impact_pct):.4f}%\n"
                f"🛣 Route: {len(quote.route)} hops\n"
                f"{status}\n\n"
                f"🔗 https://solscan.io/tx/{tx_id}" if tx_id else ""
            )
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info("📨 Telegram alert sent")
                        
        except Exception as e:
            logger.debug(f"Alert error: {e}")
    
    async def get_stats(self) -> dict:
        """Get trading statistics"""
        return {
            'swaps_executed': self.swaps_executed,
            'total_volume_sol': float(self.total_volume_sol),
            'paper_trading': self.paper_trading,
            'wallet': str(self.wallet.pubkey()) if self.wallet else None,
            'trade_count': len(self.trade_history)
        }
    
    async def close(self):
        """Cleanup"""
        if self.client:
            await self.client.close()
        logger.info("🔌 Solana connector closed")


async def main():
    """Test the Solana connector"""
    connector = SolanaJupiterConnector(
        private_key=None,  # Add your base58 key for live trading
        paper_trading=True
    )
    
    try:
        await connector.initialize()
        
        # Get SOL balance
        balance = await connector.get_balance('SOL')
        logger.info(f"SOL Balance: {balance}")
        
        # Get quote
        quote = await connector.get_quote('SOL', 'USDC', Decimal('0.1'))
        if quote:
            logger.info(f"Quote: {quote.output_amount} USDC")
            
            # Execute paper swap
            tx = await connector.execute_swap(quote)
            logger.info(f"Paper tx: {tx}")
        
        stats = await connector.get_stats()
        logger.info(f"Stats: {stats}")
        
    except KeyboardInterrupt:
        logger.info("⛔ Stopped")
    finally:
        await connector.close()


if __name__ == '__main__':
    asyncio.run(main())
