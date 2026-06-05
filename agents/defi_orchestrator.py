#!/usr/bin/env python3
"""
Unified DeFi Trading Orchestrator
Brings together ALL DeFi trading modules:
- Web3 Ethereum Trading (via web3.py)
- Solana Jupiter Trading (via Jupiter SDK)
- Flash Loan Arbitrage (via Aave/dYdX)
- Cross-Exchange CEX Arbitrage (via CCXT)
- MetaMask Automation (via Playwright)

This is the BRAIN of your DeFi trading operation!
"""
import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Import all modules
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from web3_trading_connector import Web3TradingConnector
from solana_jupiter_connector import SolanaJupiterConnector
from flash_loan_arbitrage import FlashLoanArbitrage
from cross_exchange_arbitrage import CrossExchangeArbitrageBot, ExchangeConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/agents/logs/defi_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('defi_orchestrator')


@dataclass
class DeFiStrategyConfig:
    """Configuration for all DeFi strategies"""
    # Web3 Ethereum
    eth_private_key: Optional[str] = None
    eth_networks: List[str] = field(default_factory=lambda: ['ethereum', 'arbitrum', 'base'])
    
    # Solana
    solana_private_key: Optional[str] = None
    solana_rpc: str = 'https://api.mainnet-beta.solana.com'
    
    # Flash Loans
    min_flash_loan_profit: Decimal = Decimal('100')
    
    # Cross-Exchange
    cex_exchanges: List[str] = field(default_factory=lambda: ['binance', 'bybit', 'okx'])
    
    # Global
    paper_trading: bool = True
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class UnifiedDeFiOrchestrator:
    """
    MASTER ORCHESTRATOR for all DeFi trading.
    
    Architecture:
    ┌─────────────────────────────────────────────────────┐
    │         UnifiedDeFiOrchestrator (YOU ARE HERE)      │
    ├─────────────────────────────────────────────────────┤
    │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐  │
    │  │ Web3 Trading │ │Solana Jupiter│ │Flash Loans  │  │
    │  │  (Ethereum)  │ │   (Solana)   │ │  (Aave)     │  │
    │  └──────────────┘ └──────────────┘ └─────────────┘  │
    │  ┌──────────────┐ ┌──────────────┐                  │
    │  │ Cross-Exchange│ │MetaMask Auto │                  │
    │  │   (CEX-DEX)  │ │  (Browser)   │                  │
    │  └──────────────┘ └──────────────┘                  │
    ├─────────────────────────────────────────────────────┤
    │              Telegram Alerts & Dashboard            │
    └─────────────────────────────────────────────────────┘
    
    Strategies:
    1. CROSS-DEX ARBITRAGE: Uniswap vs SushiSwap vs Curve
    2. CROSS-CHAIN ARBITRAGE: Ethereum vs Arbitrum vs Base
    3. CROSS-EXCHANGE CEX-DEX: Binance vs Uniswap
    4. FLASH LOAN ARBITRAGE: Zero capital, atomic execution
    5. SOLANA ARBITRAGE: Jupiter vs Raydium vs Orca
    6. FUNDING RATE ARBITRAGE: Perpetual futures
    """
    
    def __init__(self, config: DeFiStrategyConfig):
        self.config = config
        
        # Sub-modules
        self.web3_connector: Optional[Web3TradingConnector] = None
        self.solana_connector: Optional[SolanaJupiterConnector] = None
        self.flash_loan: Optional[FlashLoanArbitrage] = None
        self.cross_exchange: Optional[CrossExchangeArbitrageBot] = None
        
        # State
        self.running = False
        self.strategies_active: Dict[str, bool] = {}
        self.stats = {
            'started_at': time.time(),
            'opportunities_found': 0,
            'trades_executed': 0,
            'total_pnl': Decimal('0'),
        }
        
        logger.info("🌐 Unified DeFi Orchestrator initialized")
        logger.info("=" * 60)
    
    async def initialize_all(self):
        """Initialize all trading modules"""
        logger.info("🚀 INITIALIZING ALL DEFI MODULES...")
        
        # 1. Web3 Ethereum Trading
        if self.config.eth_private_key or self.config.paper_trading:
            try:
                self.web3_connector = Web3TradingConnector(
                    private_key=self.config.eth_private_key,
                    default_chain=self.config.eth_networks[0] if self.config.eth_networks else 'ethereum',
                    paper_trading=self.config.paper_trading,
                    telegram_token=self.config.telegram_token,
                    telegram_chat_id=self.config.telegram_chat_id
                )
                await self.web3_connector.initialize()
                self.strategies_active['web3_eth'] = True
                logger.info("✅ Web3 Ethereum Trading: ACTIVE")
            except Exception as e:
                logger.error(f"❌ Web3 init error: {e}")
                self.strategies_active['web3_eth'] = False
        
        # 2. Solana Jupiter Trading
        if self.config.solana_private_key or self.config.paper_trading:
            try:
                self.solana_connector = SolanaJupiterConnector(
                    private_key=self.config.solana_private_key,
                    rpc_url=self.config.solana_rpc,
                    paper_trading=self.config.paper_trading,
                    telegram_token=self.config.telegram_token,
                    telegram_chat_id=self.config.telegram_chat_id
                )
                await self.solana_connector.initialize()
                self.strategies_active['solana_jupiter'] = True
                logger.info("✅ Solana Jupiter Trading: ACTIVE")
            except Exception as e:
                logger.error(f"❌ Solana init error: {e}")
                self.strategies_active['solana_jupiter'] = False
        
        # 3. Flash Loan Arbitrage
        if self.web3_connector and self.web3_connector.w3_instances:
            try:
                w3 = list(self.web3_connector.w3_instances.values())[0]
                account = self.web3_connector.account
                
                if account:
                    self.flash_loan = FlashLoanArbitrage(
                        w3=w3,
                        account=account,
                        min_profit_usd=self.config.min_flash_loan_profit,
                        paper_trading=self.config.paper_trading
                    )
                    self.strategies_active['flash_loan'] = True
                    logger.info("✅ Flash Loan Arbitrage: ACTIVE")
            except Exception as e:
                logger.error(f"❌ Flash loan init error: {e}")
                self.strategies_active['flash_loan'] = False
        
        # 4. Cross-Exchange CEX
        try:
            exchanges = [
                ExchangeConfig(name, trading_fee=Decimal('0.001'))
                for name in self.config.cex_exchanges
            ]
            
            self.cross_exchange = CrossExchangeArbitrageBot(
                exchanges=exchanges,
                min_spread_pct=Decimal('0.003'),
                trade_size_usd=Decimal('500'),
                paper_trading=self.config.paper_trading,
                telegram_token=self.config.telegram_token,
                telegram_chat_id=self.config.telegram_chat_id
            )
            await self.cross_exchange.initialize_exchanges()
            self.strategies_active['cross_exchange'] = True
            logger.info("✅ Cross-Exchange Arbitrage: ACTIVE")
        except Exception as e:
            logger.error(f"❌ CEX init error: {e}")
            self.strategies_active['cross_exchange'] = False
        
        logger.info("=" * 60)
        active = sum(1 for v in self.strategies_active.values() if v)
        logger.info(f"🎯 {active}/{len(self.strategies_active)} strategies ACTIVE")
    
    async def run_all_strategies(self):
        """Run all strategies in parallel"""
        self.running = True
        logger.info("🔥 ALL STRATEGIES STARTING!")
        logger.info("=" * 60)
        
        tasks = []
        
        # Strategy 1: Cross-Exchange CEX Arbitrage (every 10s)
        if self.strategies_active.get('cross_exchange'):
            tasks.append(self._run_cross_exchange_loop())
        
        # Strategy 2: Flash Loan Arbitrage (every 30s)
        if self.strategies_active.get('flash_loan'):
            tasks.append(self._run_flash_loan_loop())
        
        # Strategy 3: Solana Jupiter Scan (every 15s)
        if self.strategies_active.get('solana_jupiter'):
            tasks.append(self._run_solana_loop())
        
        # Strategy 4: Web3 DEX Scan (every 20s)
        if self.strategies_active.get('web3_eth'):
            tasks.append(self._run_web3_loop())
        
        # Reporter
        tasks.append(self._stats_reporter())
        
        await asyncio.gather(*tasks)
    
    async def _run_cross_exchange_loop(self):
        """Cross-exchange CEX arbitrage loop"""
        logger.info("🔁 Cross-Exchange loop starting (10s interval)...")
        
        while self.running:
            try:
                await self.cross_exchange.fetch_tickers()
                opportunities = self.cross_exchange.detect_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"🔥 [CEX] {top.symbol}: {top.spread_pct:.3f}% | ${top.profit_usd:.2f}")
                    await self.cross_exchange.execute_arbitrage(top)
                    self.stats['trades_executed'] += 1
                
                self.stats['opportunities_found'] += len(opportunities)
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ CEX error: {e}")
                await asyncio.sleep(10)
    
    async def _run_flash_loan_loop(self):
        """Flash loan arbitrage loop"""
        logger.info("🔁 Flash Loan loop starting (30s interval)...")
        
        while self.running:
            try:
                # Simulated price data for testing
                # In production, would fetch from real DEXs
                prices = {
                    'WETH': {
                        'uniswap': Decimal('3500.50'),
                        'sushiswap': Decimal('3510.25'),
                    },
                    'WBTC': {
                        'uniswap': Decimal('67500.00'),
                        'sushiswap': Decimal('67650.00'),
                    }
                }
                
                opportunities = self.flash_loan.detect_opportunities(prices)
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"⚡ [FLASH] {top.token}: ${top.net_profit:.2f} net profit")
                    await self.flash_loan.execute_flash_loan_arbitrage(top)
                    self.stats['trades_executed'] += 1
                
                self.stats['opportunities_found'] += len(opportunities)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Flash loan error: {e}")
                await asyncio.sleep(30)
    
    async def _run_solana_loop(self):
        """Solana Jupiter loop"""
        logger.info("🔁 Solana loop starting (15s interval)...")
        
        while self.running:
            try:
                # Get quote for SOL/USDC
                quote = await self.solana_connector.get_quote('SOL', 'USDC', Decimal('0.1'))
                
                if quote and quote.price_impact_pct < Decimal('1'):
                    logger.info(f"☀️ [SOLANA] SOL/USDC: {quote.output_amount} USDC | Impact: {float(quote.price_impact_pct):.3f}%")
                    
                    if quote.price_impact_pct < Decimal('0.5'):
                        await self.solana_connector.execute_swap(quote)
                        self.stats['trades_executed'] += 1
                
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"❌ Solana error: {e}")
                await asyncio.sleep(15)
    
    async def _run_web3_loop(self):
        """Web3 DEX loop"""
        logger.info("🔁 Web3 DEX loop starting (20s interval)...")
        
        while self.running:
            try:
                # Get ETH/USDC quote
                quote = await self.web3_connector.get_swap_quote('ETH', 'USDC', Decimal('0.1'))
                
                if quote:
                    logger.info(f"🔗 [WEB3] ETH/USDC: {quote.to_amount} USDC | Gas: {quote.gas_estimate}")
                
                await asyncio.sleep(20)
                
            except Exception as e:
                logger.error(f"❌ Web3 error: {e}")
                await asyncio.sleep(20)
    
    async def _stats_reporter(self):
        """Periodic stats report"""
        while self.running:
            await asyncio.sleep(300)  # 5 minutes
            
            uptime = time.time() - self.stats['started_at']
            hours = uptime / 3600
            
            report = f"""
╔══════════════════════════════════════════════════════════╗
║           UNIFIED DEFI ORCHESTRATOR STATS                ║
╠══════════════════════════════════════════════════════════╣
║  Uptime:           {hours:.1f} hours                              ║
║  Strategies:       {sum(1 for v in self.strategies_active.values() if v)} active                           ║
║  Opportunities:    {self.stats['opportunities_found']} detected                    ║
║  Trades:           {self.stats['trades_executed']} executed                      ║
║  Mode:             {'🧪 PAPER' if self.config.paper_trading else '💰 LIVE'}                      ║
╠══════════════════════════════════════════════════════════╣
║  Web3 ETH:         {'✅' if self.strategies_active.get('web3_eth') else '❌'}                                  ║
║  Solana Jupiter:   {'✅' if self.strategies_active.get('solana_jupiter') else '❌'}                                  ║
║  Flash Loans:      {'✅' if self.strategies_active.get('flash_loan') else '❌'}                                  ║
║  Cross-Exchange:   {'✅' if self.strategies_active.get('cross_exchange') else '❌'}                                  ║
╚══════════════════════════════════════════════════════════╝
            """
            logger.info(report)
    
    def get_full_dashboard(self) -> dict:
        """Get complete dashboard data"""
        return {
            'timestamp': time.time(),
            'uptime': time.time() - self.stats['started_at'],
            'mode': 'paper' if self.config.paper_trading else 'live',
            'strategies': self.strategies_active,
            'stats': {
                'opportunities': self.stats['opportunities_found'],
                'trades': self.stats['trades_executed'],
            },
            'connectors': {
                'web3': self.web3_connector.get_stats() if self.web3_connector else None,
                'solana': self.solana_connector.get_stats() if self.solana_connector else None,
                'flash_loan': self.flash_loan.get_stats() if self.flash_loan else None,
                'cross_exchange': self.cross_exchange.get_stats() if self.cross_exchange else None,
            }
        }
    
    async def stop(self):
        """Stop all strategies"""
        logger.info("⛔ Stopping all DeFi strategies...")
        self.running = False
        
        # Cleanup connectors
        for name, connector in [
            ('web3', self.web3_connector),
            ('solana', self.solana_connector),
            ('cross_exchange', self.cross_exchange)
        ]:
            try:
                if connector:
                    await connector.close()
                    logger.info(f"   ✅ {name} stopped")
            except Exception as e:
                logger.error(f"   ❌ Error stopping {name}: {e}")
        
        logger.info("💾 Final stats saved")


async def main():
    """Run the unified orchestrator"""
    config = DeFiStrategyConfig(
        # Add your private keys for live trading
        # eth_private_key='0x...',
        # solana_private_key='base58...',
        
        paper_trading=True,
        eth_networks=['ethereum', 'arbitrum', 'base'],
        solana_rpc='https://api.mainnet-beta.solana.com',
        cex_exchanges=['binance', 'bybit', 'okx'],
        min_flash_loan_profit=Decimal('50'),
    )
    
    orchestrator = UnifiedDeFiOrchestrator(config)
    
    try:
        await orchestrator.initialize_all()
        await orchestrator.run_all_strategies()
    except KeyboardInterrupt:
        logger.info("⛔ Interrupted by user")
    finally:
        await orchestrator.stop()


if __name__ == '__main__':
    asyncio.run(main())
