#!/usr/bin/env python3
"""
Unified Arbitrage Orchestrator
Runs multiple arbitrage strategies simultaneously:
- Cross-Exchange Arbitrage
- Triangular Arbitrage  
- Funding Rate Arbitrage
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional
import json
import sys
import os

sys.path.insert(0, '/root/.openclaw/workspace/agents')

from cross_exchange_arbitrage import CrossExchangeArbitrageBot, ExchangeConfig
from triangular_arbitrage import TriangularArbitrageBot
from funding_rate_arbitrage import FundingRateArbitrageBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/agents/logs/arbitrage_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('arbitrage_orchestrator')


@dataclass
class ArbitrageConfig:
    """Configuration for all arbitrage strategies"""
    # Cross-Exchange
    cross_exchanges: List[ExchangeConfig]
    cross_min_spread: Decimal = Decimal('0.003')
    cross_trade_size: Decimal = Decimal('500')
    
    # Triangular
    triangular_exchange: str = 'binance'
    triangular_base: str = 'USDT'
    triangular_trade_size: Decimal = Decimal('100')
    triangular_min_profit: Decimal = Decimal('0.05')
    
    # Funding Rate
    funding_exchanges: List[str] = None
    funding_min_diff: Decimal = Decimal('0.0001')
    funding_position_size: Decimal = Decimal('1000')
    
    # Global
    paper_trading: bool = True
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    def __post_init__(self):
        if self.funding_exchanges is None:
            self.funding_exchanges = ['binance', 'bybit', 'okx']


class UnifiedArbitrageOrchestrator:
    """
    Master orchestrator that runs all arbitrage strategies in parallel.
    
    Architecture:
    ┌─────────────────────────────────────────┐
    │      UnifiedArbitrageOrchestrator       │
    │  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
    │  │ Cross-  │ │ Tri-    │ │ Funding  │  │
    │  │ Exchange│ │ angular │ │ Rate     │  │
    │  │ Bot     │ │ Bot     │ │ Bot      │  │
    │  └────┬────┘ └────┬────┘ └────┬─────┘  │
    │       │           │           │         │
    │       └───────────┴───────────┘         │
    │                │                        │
    │         ┌──────┴──────┐                 │
    │         │  Telegram   │                 │
    │         │   Alerts    │                 │
    │         └─────────────┘                 │
    └─────────────────────────────────────────┘
    """
    
    def __init__(self, config: ArbitrageConfig):
        self.config = config
        self.bots: Dict[str, object] = {}
        self.stats = {
            'started_at': time.time(),
            'strategies_active': 0,
            'total_opportunities': 0,
            'total_trades': 0,
            'total_pnl': Decimal('0')
        }
        self.running = False
        
        logger.info("🎯 Unified Arbitrage Orchestrator initialized")
    
    async def initialize(self):
        """Initialize all arbitrage bots"""
        # Cross-Exchange Bot
        if self.config.cross_exchanges:
            self.bots['cross_exchange'] = CrossExchangeArbitrageBot(
                exchanges=self.config.cross_exchanges,
                min_spread_pct=self.config.cross_min_spread,
                trade_size_usd=self.config.cross_trade_size,
                paper_trading=self.config.paper_trading,
                telegram_token=self.config.telegram_token,
                telegram_chat_id=self.config.telegram_chat_id
            )
            await self.bots['cross_exchange'].initialize_exchanges()
            logger.info("✅ Cross-Exchange Bot initialized")
        
        # Triangular Bot
        self.bots['triangular'] = TriangularArbitrageBot(
            exchange_name=self.config.triangular_exchange,
            base_currency=self.config.triangular_base,
            trade_size_usd=self.config.triangular_trade_size,
            min_profit_pct=self.config.triangular_min_profit,
            paper_trading=self.config.paper_trading,
            telegram_token=self.config.telegram_token,
            telegram_chat_id=self.config.telegram_chat_id
        )
        await self.bots['triangular'].initialize()
        logger.info("✅ Triangular Bot initialized")
        
        # Funding Rate Bot
        self.bots['funding'] = FundingRateArbitrageBot(
            exchanges=self.config.funding_exchanges,
            min_funding_diff=self.config.funding_min_diff,
            position_size_usd=self.config.funding_position_size,
            paper_trading=self.config.paper_trading,
            telegram_token=self.config.telegram_token,
            telegram_chat_id=self.config.telegram_chat_id
        )
        await self.bots['funding'].initialize()
        logger.info("✅ Funding Rate Bot initialized")
        
        self.stats['strategies_active'] = len(self.bots)
    
    async def run_all(self):
        """Run all strategies in parallel"""
        self.running = True
        logger.info("🚀 ALL ARBITRAGE STRATEGIES STARTING!")
        logger.info("=" * 60)
        
        tasks = []
        
        # Cross-Exchange (every 10 seconds)
        if 'cross_exchange' in self.bots:
            tasks.append(self._run_cross_exchange())
        
        # Triangular (every 15 seconds)
        if 'triangular' in self.bots:
            tasks.append(self._run_triangular())
        
        # Funding Rate (every 60 seconds)
        if 'funding' in self.bots:
            tasks.append(self._run_funding())
        
        # Stats reporter (every 5 minutes)
        tasks.append(self._stats_reporter())
        
        await asyncio.gather(*tasks)
    
    async def _run_cross_exchange(self):
        """Run cross-exchange arbitrage loop"""
        bot = self.bots['cross_exchange']
        logger.info("🔁 Cross-Exchange loop starting...")
        
        while self.running:
            try:
                await bot.fetch_tickers()
                opportunities = bot.detect_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"🔥 [CROSS] {top.symbol}: "
                              f"{top.spread_pct:.3f}% | "
                              f"${top.profit_usd:.2f} | "
                              f"{top.buy_exchange}→{top.sell_exchange}")
                    
                    await bot.execute_arbitrage(top)
                    self.stats['total_trades'] += 1
                
                self.stats['total_opportunities'] += len(opportunities)
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Cross-exchange error: {e}")
                await asyncio.sleep(10)
    
    async def _run_triangular(self):
        """Run triangular arbitrage loop"""
        bot = self.bots['triangular']
        logger.info("🔁 Triangular loop starting...")
        
        while self.running:
            try:
                opportunities = await bot.scan_for_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"🔺 [TRIANGULAR] {' → '.join(top.path)}: "
                              f"{top.profit_pct:.4f}% | ${top.profit_usd:.2f}")
                    
                    await bot.execute_triangular_arbitrage(top)
                    self.stats['total_trades'] += 1
                
                self.stats['total_opportunities'] += len(opportunities)
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"❌ Triangular error: {e}")
                await asyncio.sleep(15)
    
    async def _run_funding(self):
        """Run funding rate arbitrage loop"""
        bot = self.bots['funding']
        logger.info("🔁 Funding Rate loop starting...")
        
        while self.running:
            try:
                await bot.fetch_funding_rates()
                opportunities = bot.detect_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"💸 [FUNDING] {top.symbol}: "
                              f"{top.annualized_return:.1f}% annual | "
                              f"{top.long_exchange}↔{top.short_exchange}")
                    
                    await bot.execute_funding_arbitrage(top)
                    self.stats['total_trades'] += 1
                
                self.stats['total_opportunities'] += len(opportunities)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Funding error: {e}")
                await asyncio.sleep(60)
    
    async def _stats_reporter(self):
        """Periodic stats report"""
        while self.running:
            await asyncio.sleep(300)  # 5 minutes
            
            uptime = time.time() - self.stats['started_at']
            hours = uptime / 3600
            
            report = f"""
╔══════════════════════════════════════════════╗
║       ARBITRAGE ORCHESTRATOR STATS           ║
╠══════════════════════════════════════════════╣
║  Uptime:        {hours:.1f} hours                     ║
║  Strategies:    {self.stats['strategies_active']} active                  ║
║  Opportunities: {self.stats['total_opportunities']} detected            ║
║  Trades:        {self.stats['total_trades']} executed                 ║
║  Mode:          {'🧪 PAPER' if self.config.paper_trading else '💰 LIVE'}              ║
╚══════════════════════════════════════════════╝
            """
            logger.info(report)
    
    def get_dashboard_data(self) -> dict:
        """Get data for dashboard/telegraf"""
        return {
            'timestamp': time.time(),
            'uptime_seconds': time.time() - self.stats['started_at'],
            'strategies_active': self.stats['strategies_active'],
            'total_opportunities': self.stats['total_opportunities'],
            'total_trades': self.stats['total_trades'],
            'paper_trading': self.config.paper_trading,
            'bots': {
                name: {
                    'opportunities': getattr(bot, 'opportunities_found', 0),
                    'trades': getattr(bot, 'trades_executed', 0),
                    'pnl': float(getattr(bot, 'total_pnl', Decimal('0')))
                }
                for name, bot in self.bots.items()
            }
        }
    
    async def stop(self):
        """Stop all bots"""
        logger.info("⛔ Stopping all arbitrage strategies...")
        self.running = False
        
        for name, bot in self.bots.items():
            try:
                await bot.close()
                logger.info(f"   ✅ {name} stopped")
            except Exception as e:
                logger.error(f"   ❌ Error stopping {name}: {e}")
        
        # Save final stats
        self._save_stats()
    
    def _save_stats(self):
        """Save final statistics"""
        filepath = '/root/.openclaw/workspace/agents/logs/arbitrage_final_stats.json'
        with open(filepath, 'w') as f:
            json.dump({
                'config': {
                    'paper_trading': self.config.paper_trading,
                    'strategies': list(self.bots.keys())
                },
                'stats': {
                    'started_at': self.stats['started_at'],
                    'stopped_at': time.time(),
                    'total_opportunities': self.stats['total_opportunities'],
                    'total_trades': self.stats['total_trades']
                }
            }, f, indent=2)
        logger.info(f"💾 Stats saved to {filepath}")


async def main():
    """Main entry point"""
    config = ArbitrageConfig(
        cross_exchanges=[
            ExchangeConfig('binance', trading_fee=Decimal('0.001')),
            ExchangeConfig('bybit', trading_fee=Decimal('0.001')),
            ExchangeConfig('okx', trading_fee=Decimal('0.001')),
            ExchangeConfig('kucoin', trading_fee=Decimal('0.001')),
        ],
        cross_min_spread=Decimal('0.003'),
        cross_trade_size=Decimal('500'),
        
        triangular_exchange='binance',
        triangular_base='USDT',
        triangular_trade_size=Decimal('100'),
        triangular_min_profit=Decimal('0.05'),
        
        funding_exchanges=['binance', 'bybit', 'okx'],
        funding_min_diff=Decimal('0.0001'),
        funding_position_size=Decimal('1000'),
        
        paper_trading=True
    )
    
    orchestrator = UnifiedArbitrageOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        await orchestrator.run_all()
    except KeyboardInterrupt:
        logger.info("⛔ Interrupted by user")
    finally:
        await orchestrator.stop()


if __name__ == '__main__':
    asyncio.run(main())
