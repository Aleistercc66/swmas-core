#!/usr/bin/env python3
"""
Wallet Trading Bridge
Connects WalletManager to Web3TradingConnector for live trading.
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal

from core.wallet_manager import WalletManager

# Import trading connectors
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from web3_trading_connector import Web3TradingConnector, SwapQuote
from solana_jupiter_connector import SolanaJupiterConnector, JupiterSwapQuote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('wallet_trading_bridge')


class WalletTradingBridge:
    """
    Bridge between WalletManager and trading connectors.
    Enables real trading through connected MetaMask wallets.
    """
    
    def __init__(self, wallet_manager: WalletManager):
        self.wallet_manager = wallet_manager
        self.evm_connector: Optional[Web3TradingConnector] = None
        self.solana_connector: Optional[SolanaJupiterConnector] = None
        
    async def initialize_evm(self, wallet_name: str = 'MetaMask Main'):
        """Initialize EVM trading (Ethereum, Arbitrum, Base, etc.)"""
        wallet = await self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            raise ValueError(f"Wallet '{wallet_name}' not found")
        
        # Get decrypted private key
        private_key = await self.wallet_manager.get_private_key(wallet_name)
        if not private_key:
            raise ValueError("Failed to decrypt private key")
        
        # Initialize connector
        self.evm_connector = Web3TradingConnector(
            private_key=private_key,
            default_chain=wallet.chain,
            paper_trading=False,  # LIVE TRADING!
        )
        await self.evm_connector.initialize()
        
        logger.info(f"🔗 EVM bridge initialized: {wallet.address[:10]}... on {wallet.chain}")
        
    async def initialize_solana(self, wallet_name: str = 'MetaMask Main'):
        """Initialize Solana trading via Jupiter"""
        wallet = await self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            raise ValueError(f"Wallet '{wallet_name}' not found")
        
        private_key = await self.wallet_manager.get_private_key(wallet_name)
        if not private_key:
            raise ValueError("Failed to decrypt private key")
        
        self.solana_connector = SolanaJupiterConnector(private_key=private_key, paper_trading=False)
        await self.solana_connector.initialize()
        
        logger.info(f"⚡ Solana bridge initialized: {wallet.address[:10]}...")
        logger.info(f"   Paper trading: {self.solana_connector.paper_trading}")
        
    async def get_swap_quote(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        chain: Optional[str] = None,
        wallet_name: str = 'MetaMask Main'
    ) -> Dict:
        """Get swap quote"""
        wallet = await self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            return {'error': 'Wallet not found'}
        
        try:
            if wallet.chain == 'solana':
                if not self.solana_connector:
                    await self.initialize_solana(wallet_name)
                    
                quote = await self.solana_connector.get_quote(
                    from_token, to_token, amount
                )
                return {
                    'from': from_token,
                    'to': to_token,
                    'amount': amount,
                    'quote': str(quote),
                    'chain': 'solana'
                }
            else:
                # EVM chains
                if not self.evm_connector:
                    await self.initialize_evm(wallet_name)
                    
                quote = await self.evm_connector.get_swap_quote(
                    from_token, to_token, Decimal(str(amount))
                )
                return {
                    'from': from_token,
                    'to': to_token,
                    'amount': amount,
                    'quote': str(quote),
                    'chain': wallet.chain
                }
        except Exception as e:
            logger.error(f"❌ Quote failed: {e}")
            return {'error': str(e)}
            
    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        wallet_name: str = 'MetaMask Main'
    ) -> Dict:
        """
        Execute a token swap!
        ⚠️ REAL TRANSACTION - USE WITH CAUTION
        """
        wallet = await self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            return {'error': 'Wallet not found'}
        
        logger.warning(f"🚨 EXECUTING REAL SWAP: {amount} {from_token} -> {to_token}")
        
        try:
            if wallet.chain == 'solana':
                if not self.solana_connector:
                    await self.initialize_solana(wallet_name)
                    
                # Get quote first
                quote = await self.solana_connector.get_quote(
                    from_token, to_token, amount
                )
                
                # Execute
                tx_id = await self.solana_connector.execute_swap(quote)
                
                return {
                    'status': 'success',
                    'tx_id': tx_id,
                    'explorer': f'https://solscan.io/tx/{tx_id}',
                    'from': from_token,
                    'to': to_token,
                    'amount': amount
                }
            else:
                # EVM
                if not self.evm_connector:
                    await self.initialize_evm(wallet_name)
                    
                quote = await self.evm_connector.get_swap_quote(
                    from_token, to_token, Decimal(str(amount))
                )
                
                tx_hash = await self.evm_connector.execute_swap(quote)
                
                return {
                    'status': 'success',
                    'tx_hash': tx_hash,
                    'explorer': f'{self.evm_connector.CHAINS[wallet.chain].explorer}/tx/{tx_hash}',
                    'from': from_token,
                    'to': to_token,
                    'amount': amount
                }
                
        except Exception as e:
            logger.error(f"❌ Swap failed: {e}")
            return {'error': str(e)}
            
    async def get_portfolio(self, wallet_name: str = 'MetaMask Main') -> Dict:
        """Get complete portfolio for wallet"""
        wallet = await self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            return {'error': 'Wallet not found'}
        
        # Get native balance
        balance = await self.wallet_manager.get_balance(wallet_name, wallet.chain)
        
        return {
            'wallet': wallet.address,
            'chain': wallet.chain,
            'native_balance': balance.get('native_balance', 0),
            'symbol': balance.get('symbol', 'ETH'),
            'tokens': []  # Would need token balance fetching
        }


# ============== FACTORY ==============

_bridge: Optional[WalletTradingBridge] = None

async def get_trading_bridge(wallet_manager: WalletManager) -> WalletTradingBridge:
    """Get or create trading bridge"""
    global _bridge
    if _bridge is None:
        _bridge = WalletTradingBridge(wallet_manager)
    return _bridge
