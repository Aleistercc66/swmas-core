#!/usr/bin/env python3
"""
Funding Rate Arbitrage Bot
Captures funding rate differentials across perpetual futures exchanges.
Strategy: Go long on exchange with negative/low funding, short on exchange with positive/high funding.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json

import ccxt.async_support as ccxt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/agents/logs/funding_arbitrage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('funding_arbitrage')


@dataclass
class FundingOpportunity:
    """Funding rate arbitrage opportunity"""
    symbol: str
    long_exchange: str      # Exchange to go LONG (lower/negative funding)
    short_exchange: str     # Exchange to go SHORT (higher/positive funding)
    long_funding: Decimal   # Funding rate on long exchange
    short_funding: Decimal  # Funding rate on short exchange
    funding_diff: Decimal   # Difference (positive = profit)
    annualized_return: Decimal
    next_funding_time: int  # Unix timestamp
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'long_exchange': self.long_exchange,
            'short_exchange': self.short_exchange,
            'long_funding': float(self.long_funding),
            'short_funding': float(self.short_funding),
            'funding_diff': float(self.funding_diff),
            'annualized_return': float(self.annualized_return),
            'next_funding_time': self.next_funding_time,
            'timestamp': self.timestamp
        }


class FundingRateArbitrageBot:
    """
    Funding Rate Arbitrage Bot.
    
    This is one of the most CONSISTENT arbitrage strategies:
    - Market neutral (no directional risk)
    - Captures funding rate differential every 8 hours
    - Works across Binance, Bybit, OKX, dYdX, etc.
    
    Strategy:
    1. Find coin with largest funding rate spread across exchanges
    2. Go LONG on exchange with lower (or negative) funding
    3. Go SHORT on exchange with higher (positive) funding
    4. Collect funding differential every 8h
    5. Close when spread narrows
    
    Example:
    - BTC funding on Binance: +0.01% (paying)
    - BTC funding on Bybit: -0.005% (receiving)
    - Spread: 0.015% per 8h = ~16.4% annualized
    """
    
    def __init__(
        self,
        exchanges: List[str] = None,
        min_funding_diff: Decimal = Decimal('0.0001'),  # 0.01%
        position_size_usd: Decimal = Decimal('1000'),
        paper_trading: bool = True,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        self.exchanges = exchanges or ['binance', 'bybit', 'okx', 'gateio']
        self.min_funding_diff = min_funding_diff
        self.position_size_usd = position_size_usd
        self.paper_trading = paper_trading
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Exchange clients
        self.clients: Dict[str, ccxt.Exchange] = {}
        
        # Data storage
        self.funding_rates: Dict[str, Dict[str, Decimal]] = {}  # symbol -> {exchange: rate}
        self.mark_prices: Dict[str, Dict[str, Decimal]] = {}    # symbol -> {exchange: price}
        
        # Performance
        self.opportunities_found: int = 0
        self.positions_opened: int = 0
        self.total_pnl: Decimal = Decimal('0')
        
        # Active positions
        self.active_positions: Dict[str, dict] = {}  # symbol -> position info
        
        logger.info(f"💰 Funding Rate Arbitrage Bot initialized")
        logger.info(f"   Exchanges: {self.exchanges}")
        logger.info(f"   Min diff: {min_funding_diff * 100}%")
        logger.info(f"   Position size: ${position_size_usd}")
    
    async def initialize(self):
        """Connect to all exchanges"""
        exchange_classes = {
            'binance': ccxt.binance,
            'bybit': ccxt.bybit,
            'okx': ccxt.okx,
            'gateio': ccxt.gateio,
            'kucoin': ccxt.kucoin,
            'mexc': ccxt.mexc,
            'bitget': ccxt.bitget,
            'deribit': ccxt.deribit,
        }
        
        for name in self.exchanges:
            try:
                exchange_class = exchange_classes.get(name.lower())
                if not exchange_class:
                    continue
                
                self.clients[name] = exchange_class({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'swap'}  # Perpetual futures
                })
                
                # Test connection
                await self.clients[name].fetch_time()
                logger.info(f"✅ Connected to {name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect {name}: {e}")
    
    async def fetch_funding_rates(self):
        """Fetch funding rates from all exchanges"""
        tasks = []
        for name, client in self.clients.items():
            task = self._fetch_exchange_funding(name, client)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results
        for name, result in zip(self.clients.keys(), results):
            if isinstance(result, Exception):
                logger.debug(f"Funding fetch error {name}: {result}")
                continue
            
            for symbol, data in result.items():
                if symbol not in self.funding_rates:
                    self.funding_rates[symbol] = {}
                self.funding_rates[symbol][name] = data
    
    async def _fetch_exchange_funding(
        self,
        name: str,
        client: ccxt.Exchange
    ) -> Dict[str, dict]:
        """Fetch funding rates for a single exchange"""
        try:
            rates = await client.fetch_funding_rates()
            
            result = {}
            for symbol, data in rates.items():
                # Only perpetual swaps
                if ':USDT' in symbol or '-USDT' in symbol or 'PERP' in symbol:
                    funding_rate = Decimal(str(data.get('fundingRate', 0)))
                    mark_price = Decimal(str(data.get('markPrice', 0)))
                    next_time = data.get('fundingTimestamp', 0)
                    
                    # Normalize symbol
                    clean_symbol = symbol.replace(':USDT', '/USDT:USDT')
                    
                    result[clean_symbol] = {
                        'funding_rate': funding_rate,
                        'mark_price': mark_price,
                        'next_funding_time': next_time
                    }
            
            return result
            
        except Exception as e:
            logger.debug(f"Error fetching funding from {name}: {e}")
            return {}
    
    def detect_opportunities(self) -> List[FundingOpportunity]:
        """Detect funding rate arbitrage opportunities"""
        opportunities = []
        
        for symbol, exchange_data in self.funding_rates.items():
            if len(exchange_data) < 2:
                continue
            
            # Find best long and short exchanges
            # Long: most negative (or least positive) funding
            # Short: most positive funding
            
            sorted_by_rate = sorted(
                exchange_data.items(),
                key=lambda x: x[1]['funding_rate']
            )
            
            long_ex = sorted_by_rate[0]   # Lowest/negative funding
            short_ex = sorted_by_rate[-1]  # Highest funding
            
            long_rate = long_ex[1]['funding_rate']
            short_rate = short_ex[1]['funding_rate']
            
            # Calculate spread
            funding_diff = short_rate - long_rate
            
            # Must be greater than threshold
            if funding_diff < self.min_funding_diff:
                continue
            
            # Annualized return (funding paid every 8 hours = 3x per day)
            # 365 days * 3 = 1095 payments per year
            annualized = funding_diff * Decimal('3') * Decimal('365') * Decimal('100')
            
            # Skip if annualized is too low (< 5%)
            if annualized < Decimal('5'):
                continue
            
            # Get next funding time
            next_times = [
                d['next_funding_time'] 
                for d in exchange_data.values()
                if d.get('next_funding_time')
            ]
            next_funding = min(next_times) if next_times else 0
            
            opp = FundingOpportunity(
                symbol=symbol,
                long_exchange=long_ex[0],
                short_exchange=short_ex[0],
                long_funding=long_rate,
                short_funding=short_rate,
                funding_diff=funding_diff,
                annualized_return=annualized,
                next_funding_time=next_funding
            )
            
            opportunities.append(opp)
            self.opportunities_found += 1
        
        # Sort by annualized return
        opportunities.sort(key=lambda x: x.annualized_return, reverse=True)
        return opportunities
    
    async def execute_funding_arbitrage(self, opp: FundingOpportunity) -> bool:
        """Execute funding rate arbitrage position"""
        logger.info(f"💸 FUNDING ARBITRAGE!")
        logger.info(f"   {opp.symbol}")
        logger.info(f"   📉 LONG on {opp.long_exchange}: {opp.long_funding * 100:.4f}%")
        logger.info(f"   📈 SHORT on {opp.short_exchange}: {opp.short_funding * 100:.4f}%")
        logger.info(f"   📊 Spread: {opp.funding_diff * 100:.4f}% per 8h")
        logger.info(f"   🎯 Annualized: {opp.annualized_return:.1f}%")
        
        if self.paper_trading:
            await self._paper_position(opp)
            return True
        else:
            return await self._live_position(opp)
    
    async def _paper_position(self, opp: FundingOpportunity):
        """Simulate opening funding arbitrage position"""
        # Calculate 8h profit
        profit_8h = self.position_size_usd * opp.funding_diff
        
        position = {
            'type': 'PAPER_FUNDING_ARB',
            'symbol': opp.symbol,
            'timestamp': time.time(),
            'opportunity': opp.to_dict(),
            'position_size': float(self.position_size_usd),
            'estimated_8h_profit': float(profit_8h),
            'status': 'OPEN'
        }
        
        self.active_positions[opp.symbol] = position
        self.positions_opened += 1
        
        logger.info(f"📊 PAPER POSITION OPENED")
        logger.info(f"   Est. 8h profit: ${profit_8h:.2f}")
        logger.info(f"   Est. daily: ${profit_8h * 3:.2f}")
        logger.info(f"   Positions open: {len(self.active_positions)}")
        
        await self._send_alert(opp)
    
    async def _live_position(self, opp: FundingOpportunity) -> bool:
        """Open live funding arbitrage position"""
        try:
            long_client = self.clients.get(opp.long_exchange)
            short_client = self.clients.get(opp.short_exchange)
            
            if not long_client or not short_client:
                logger.error("Exchange clients not available")
                return False
            
            # Open LONG position
            long_order = await long_client.create_market_buy_order(
                opp.symbol, float(self.position_size_usd)
            )
            logger.info(f"✅ LONG opened on {opp.long_exchange}: {long_order['id']}")
            
            # Open SHORT position
            short_order = await short_client.create_market_sell_order(
                opp.symbol, float(self.position_size_usd)
            )
            logger.info(f"✅ SHORT opened on {opp.short_exchange}: {short_order['id']}")
            
            position = {
                'type': 'LIVE_FUNDING_ARB',
                'symbol': opp.symbol,
                'timestamp': time.time(),
                'opportunity': opp.to_dict(),
                'long_order': long_order,
                'short_order': short_order,
                'status': 'OPEN'
            }
            
            self.active_positions[opp.symbol] = position
            self.positions_opened += 1
            
            await self._send_alert(opp)
            return True
            
        except Exception as e:
            logger.error(f"❌ Live position failed: {e}")
            return False
    
    async def monitor_positions(self):
        """Monitor and report on open positions"""
        if not self.active_positions:
            return
        
        logger.info(f"📋 Monitoring {len(self.active_positions)} positions...")
        
        for symbol, position in list(self.active_positions.items()):
            hours_open = (time.time() - position['timestamp']) / 3600
            
            # Calculate accumulated funding
            opp = position.get('opportunity', {})
            funding_diff = Decimal(str(opp.get('funding_diff', 0)))
            periods = int(hours_open / 8)
            accumulated = self.position_size_usd * funding_diff * periods
            
            logger.info(f"   {symbol}: Open {hours_open:.1f}h | "
                      f"Periods: {periods} | Accumulated: ${accumulated:.2f}")
    
    async def _send_alert(self, opp: FundingOpportunity):
        """Send Telegram alert"""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            import aiohttp
            
            hours_to_funding = (opp.next_funding_time / 1000 - time.time()) / 3600
            
            mode = "🧪 PAPER" if self.paper_trading else "💰 LIVE"
            message = (
                f"{mode} FUNDING ARBITRAGE\n\n"
                f"🪙 {opp.symbol}\n"
                f"📉 LONG: {opp.long_exchange} ({opp.long_funding * 100:.4f}%)\n"
                f"📈 SHORT: {opp.short_exchange} ({opp.short_funding * 100:.4f}%)\n"
                f"📊 Spread: {opp.funding_diff * 100:.4f}% / 8h\n"
                f"🎯 Annualized: {opp.annualized_return:.1f}%\n"
                f"⏰ Next funding: {hours_to_funding:.1f}h\n\n"
                f"💵 Position: ${self.position_size_usd}\n"
                f"💰 Est. 8h profit: ${float(self.position_size_usd * opp.funding_diff):.2f}"
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
                        logger.info("📨 Alert sent")
                        
        except Exception as e:
            logger.debug(f"Alert error: {e}")
    
    async def run(self, scan_interval: float = 60.0, monitor_interval: float = 300.0):
        """Main run loop"""
        logger.info("🔁 Starting funding rate arbitrage bot...")
        
        scan_task = asyncio.create_task(self._scan_loop(scan_interval))
        monitor_task = asyncio.create_task(self._monitor_loop(monitor_interval))
        
        await asyncio.gather(scan_task, monitor_task)
    
    async def _scan_loop(self, interval: float):
        """Continuous scan loop"""
        while True:
            try:
                await self.fetch_funding_rates()
                opportunities = self.detect_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"🔥 Top funding arb: {top.symbol} | "
                              f"{top.annualized_return:.1f}% annualized | "
                              f"{top.long_exchange}↔{top.short_exchange}")
                    
                    # Only open if not already in position
                    if top.symbol not in self.active_positions:
                        await self.execute_funding_arbitrage(top)
                    
                    for opp in opportunities[1:5]:
                        logger.info(f"   📌 {opp.symbol}: {opp.annualized_return:.1f}% | "
                                  f"{opp.funding_diff * 100:.4f}% spread")
                else:
                    logger.debug("No funding opportunities")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(interval)
    
    async def _monitor_loop(self, interval: float):
        """Position monitoring loop"""
        while True:
            try:
                await self.monitor_positions()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)
    
    async def close(self):
        """Cleanup"""
        for name, client in self.clients.items():
            try:
                await client.close()
                logger.info(f"🔌 Disconnected from {name}")
            except:
                pass


async def main():
    """Run funding rate arbitrage bot"""
    bot = FundingRateArbitrageBot(
        exchanges=['binance', 'bybit', 'okx'],
        min_funding_diff=Decimal('0.0001'),  # 0.01%
        position_size_usd=Decimal('500'),
        paper_trading=True
    )
    
    try:
        await bot.initialize()
        await bot.run(scan_interval=60, monitor_interval=300)
    except KeyboardInterrupt:
        logger.info("⛔ Stopped")
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
