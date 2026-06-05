#!/usr/bin/env python3
"""
Triangular Arbitrage Bot
Detects price loop inefficiencies within a single exchange.
Strategy: A → B → C → A where the product of exchange rates > 1
Example: USDT → BTC → ETH → USDT
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from itertools import permutations
import json

import ccxt.async_support as ccxt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/agents/logs/triangular_arbitrage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('triangular_arbitrage')


@dataclass
class TriangularOpportunity:
    """A triangular arbitrage opportunity"""
    exchange: str
    path: Tuple[str, str, str]  # (A, B, C) where A→B→C→A
    symbols: Tuple[str, str, str]  # (A/B, B/C, C/A)
    rate_product: Decimal  # Should be > 1 for profit
    profit_pct: Decimal
    profit_usd: Decimal
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            'exchange': self.exchange,
            'path': self.path,
            'symbols': self.symbols,
            'rate_product': float(self.rate_product),
            'profit_pct': float(self.profit_pct),
            'profit_usd': float(self.profit_usd),
            'timestamp': self.timestamp
        }


class TriangularArbitrageBot:
    """
    Triangular Arbitrage Bot for single exchange execution.
    
    Advantages:
    - No transfer risk (all on one exchange)
    - Instant execution (no blockchain delays)
    - Lower fees (only trading fees, no withdrawal)
    - No counterparty risk between exchanges
    
    Supports both paper and live trading.
    """
    
    def __init__(
        self,
        exchange_name: str = 'binance',
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_currency: str = 'USDT',
        trade_size_usd: Decimal = Decimal('100'),
        min_profit_pct: Decimal = Decimal('0.001'),  # 0.1%
        paper_trading: bool = True,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_currency = base_currency
        self.trade_size_usd = trade_size_usd
        self.min_profit_pct = min_profit_pct
        self.paper_trading = paper_trading
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Exchange client
        self.client: Optional[ccxt.Exchange] = None
        
        # Market data
        self.all_symbols: List[str] = []
        self.tickers: Dict[str, dict] = {}
        self.last_update: float = 0
        
        # Performance
        self.opportunities_found: int = 0
        self.trades_executed: int = 0
        self.total_pnl: Decimal = Decimal('0')
        self.trade_history: List[dict] = []
        
        # Common quote currencies for triangular paths
        self.quote_currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'USDC']
        
        logger.info(f"🔄 Triangular Arbitrage Bot initialized")
        logger.info(f"   Exchange: {exchange_name}")
        logger.info(f"   Base: {base_currency}")
        logger.info(f"   Min profit: {min_profit_pct}%")
    
    async def initialize(self):
        """Initialize exchange connection"""
        exchange_classes = {
            'binance': ccxt.binance,
            'bybit': ccxt.bybit,
            'okx': ccxt.okx,
            'kucoin': ccxt.kucoin,
            'gateio': ccxt.gateio,
        }
        
        exchange_class = exchange_classes.get(self.exchange_name.lower())
        if not exchange_class:
            raise ValueError(f"Exchange {self.exchange_name} not supported")
        
        kwargs = {'enableRateLimit': True}
        if self.api_key:
            kwargs['apiKey'] = self.api_key
        if self.api_secret:
            kwargs['secret'] = self.api_secret
        
        self.client = exchange_class(kwargs)
        
        # Load markets
        markets = await self.client.load_markets()
        self.all_symbols = list(markets.keys())
        
        logger.info(f"✅ Connected to {self.exchange_name}")
        logger.info(f"   Markets loaded: {len(self.all_symbols)}")
    
    async def fetch_tickers(self):
        """Fetch all tickers from the exchange"""
        try:
            tickers = await self.client.fetch_tickers()
            self.tickers = {
                symbol: {
                    'bid': Decimal(str(data.get('bid', 0))),
                    'ask': Decimal(str(data.get('ask', 0))),
                    'last': Decimal(str(data.get('last', 0))),
                    'volume': data.get('quoteVolume', 0) or data.get('volume', 0),
                    'baseVolume': data.get('baseVolume', 0)
                }
                for symbol, data in tickers.items()
                if data.get('bid', 0) and data.get('ask', 0)
            }
            self.last_update = time.time()
            logger.debug(f"📊 Fetched {len(self.tickers)} tickers")
        except Exception as e:
            logger.error(f"❌ Ticker fetch error: {e}")
    
    def build_triangular_paths(self) -> List[Tuple[str, str, str]]:
        """
        Build all valid triangular paths.
        A valid path: A/B, B/C, C/A
        Example: USDT→BTC→ETH→USDT means symbols: BTC/USDT, ETH/BTC, ETH/USDT
        """
        paths = []
        
        # Get all unique base currencies (excluding quote currencies)
        bases = set()
        for symbol in self.tickers.keys():
            if '/' in symbol:
                base, quote = symbol.split('/')
                if quote in self.quote_currencies:
                    bases.add(base)
        
        bases = sorted(bases)
        
        # Generate paths: base_currency → A → B → base_currency
        for a in bases:
            for b in bases:
                if a == b:
                    continue
                
                # Check if all 3 pairs exist
                pair1 = f"{a}/{self.base_currency}"  # USDT → A
                pair2 = f"{b}/{a}"                    # A → B
                pair3 = f"{b}/{self.base_currency}"  # B → USDT
                
                # Alternative orientations
                alt_pair1 = f"{self.base_currency}/{a}"
                alt_pair2 = f"{a}/{b}"
                alt_pair3 = f"{self.base_currency}/{b}"
                
                # Try both orientations
                if all(p in self.tickers for p in [pair1, pair2, pair3]):
                    paths.append((pair1, pair2, pair3))
                
                if all(p in self.tickers for p in [alt_pair1, alt_pair2, alt_pair3]):
                    paths.append((alt_pair1, alt_pair2, alt_pair3))
        
        return paths
    
    def calculate_triangular_profit(
        self,
        pair1: str,
        pair2: str,
        pair3: str,
        amount: Decimal
    ) -> Optional[TriangularOpportunity]:
        """
        Calculate if a triangular path is profitable.
        
        Path: Start with base currency, go through pairs, end with base currency.
        """
        try:
            ticker1 = self.tickers.get(pair1)
            ticker2 = self.tickers.get(pair2)
            ticker3 = self.tickers.get(pair3)
            
            if not all([ticker1, ticker2, ticker3]):
                return None
            
            # Determine the direction of each trade
            # We always use ASK when buying, BID when selling
            
            # Parse symbols to determine direction
            base1, quote1 = pair1.split('/')
            base2, quote2 = pair2.split('/')
            base3, quote3 = pair3.split('/')
            
            # Step 1: Start with base currency
            # If pair1 is A/BASE, we buy A (use ask)
            # If pair1 is BASE/A, we sell BASE (use bid) → get A
            
            if base1 == self.base_currency:
                # pair1 = BASE/A → Sell BASE, get A
                # rate = bid of pair1 (how much A we get per BASE)
                step1_rate = ticker1['bid']
                mid_currency1 = quote1
                after_step1 = amount * step1_rate
            else:
                # pair1 = A/BASE → Buy A with BASE
                # rate = 1/ask of pair1 (how much A we get per BASE spent)
                # Actually: amount_usd / ask = quantity of A
                step1_rate = Decimal('1') / ticker1['ask']
                mid_currency1 = base1
                after_step1 = amount * step1_rate
            
            # Step 2: A → B
            if base2 == mid_currency1:
                # pair2 = A/B → Sell A, get B
                step2_rate = ticker2['bid']
                mid_currency2 = quote2
                after_step2 = after_step1 * step2_rate
            else:
                # pair2 = B/A → Buy B with A
                step2_rate = Decimal('1') / ticker2['ask']
                mid_currency2 = base2
                after_step2 = after_step1 * step2_rate
            
            # Step 3: B → BASE
            if base3 == mid_currency2:
                # pair3 = B/BASE → Sell B, get BASE
                step3_rate = ticker3['bid']
                after_step3 = after_step2 * step3_rate
            else:
                # pair3 = BASE/B → Buy BASE with B
                step3_rate = Decimal('1') / ticker3['ask']
                after_step3 = after_step2 * step3_rate
            
            # Calculate profit
            if after_step3 <= 0:
                return None
            
            rate_product = after_step3 / amount
            profit_pct = (rate_product - Decimal('1')) * Decimal('100')
            profit_usd = after_step3 - amount
            
            if profit_pct < self.min_profit_pct:
                return None
            
            # Extract the currency path
            currencies = (self.base_currency, mid_currency1, mid_currency2)
            
            return TriangularOpportunity(
                exchange=self.exchange_name,
                path=currencies,
                symbols=(pair1, pair2, pair3),
                rate_product=rate_product,
                profit_pct=profit_pct,
                profit_usd=profit_usd
            )
            
        except Exception as e:
            logger.debug(f"Calculation error: {e}")
            return None
    
    async def scan_for_opportunities(self) -> List[TriangularOpportunity]:
        """Scan all triangular paths for profitable opportunities"""
        await self.fetch_tickers()
        
        paths = self.build_triangular_paths()
        logger.debug(f"🔍 Checking {len(paths)} triangular paths...")
        
        opportunities = []
        
        for pair1, pair2, pair3 in paths:
            opp = self.calculate_triangular_profit(
                pair1, pair2, pair3, self.trade_size_usd
            )
            if opp:
                opportunities.append(opp)
                self.opportunities_found += 1
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.profit_pct, reverse=True)
        return opportunities
    
    async def execute_triangular_arbitrage(self, opp: TriangularOpportunity) -> bool:
        """Execute triangular arbitrage sequence"""
        logger.info(f"🔺 TRIANGULAR ARBITRAGE!")
        logger.info(f"   Exchange: {opp.exchange}")
        logger.info(f"   Path: {' → '.join(opp.path)}")
        logger.info(f"   Pairs: {opp.symbols}")
        logger.info(f"   Rate product: {opp.rate_product:.6f}")
        logger.info(f"   Profit: {opp.profit_pct:.4f}% | ${opp.profit_usd:.2f}")
        
        if self.paper_trading:
            await self._paper_trade(opp)
            return True
        else:
            return await self._live_trade(opp)
    
    async def _paper_trade(self, opp: TriangularOpportunity):
        """Simulate triangular arbitrage"""
        trade_record = {
            'type': 'PAPER_TRIANGULAR',
            'timestamp': time.time(),
            'opportunity': opp.to_dict(),
            'status': 'SIMULATED',
            'pnl_usd': float(opp.profit_usd)
        }
        
        self.trades_executed += 1
        self.total_pnl += opp.profit_usd
        self.trade_history.append(trade_record)
        
        logger.info(f"📊 PAPER TRIANGULAR: +${opp.profit_usd:.2f}")
        logger.info(f"   Total: ${self.total_pnl:.2f} | Trades: {self.trades_executed}")
        
        await self._send_alert(opp)
    
    async def _live_trade(self, opp: TriangularOpportunity) -> bool:
        """Execute live triangular arbitrage"""
        try:
            # This requires precise order execution
            # In practice, triangular arb needs millisecond timing
            logger.warning("⚠️ Live triangular execution not implemented in this version")
            logger.warning("   Use cross-exchange or funding rate arbitrage for live trading")
            return False
            
        except Exception as e:
            logger.error(f"❌ Live trade failed: {e}")
            return False
    
    async def _send_alert(self, opp: TriangularOpportunity):
        """Send alert for opportunity"""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            import aiohttp
            
            mode = "🧪 PAPER" if self.paper_trading else "💰 LIVE"
            message = (
                f"{mode} TRIANGULAR ARBITRAGE\n\n"
                f"🏛 Exchange: {opp.exchange}\n"
                f"🔄 Path: {' → '.join(opp.path)}\n"
                f"📊 Rate: {opp.rate_product:.6f}\n"
                f"💵 Profit: {opp.profit_pct:.4f}% | ${opp.profit_usd:.2f}\n\n"
                f"📈 Pairs:\n"
                f"   1. {opp.symbols[0]}\n"
                f"   2. {opp.symbols[1]}\n"
                f"   3. {opp.symbols[2]}"
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
            logger.debug(f"Alert failed: {e}")
    
    async def run(self, interval_seconds: float = 10.0):
        """Main run loop"""
        logger.info("🔁 Starting triangular arbitrage scan loop...")
        
        while True:
            try:
                opportunities = await self.scan_for_opportunities()
                
                if opportunities:
                    top = opportunities[0]
                    logger.info(f"🔥 Top triangular: {' → '.join(top.path)} | "
                              f"{top.profit_pct:.4f}% | ${top.profit_usd:.2f}")
                    
                    await self.execute_triangular_arbitrage(top)
                    
                    if len(opportunities) > 1:
                        for opp in opportunities[1:5]:
                            logger.info(f"   📌 {' → '.join(opp.path)}: "
                                      f"{opp.profit_pct:.4f}%")
                else:
                    logger.debug("No triangular opportunities")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def close(self):
        """Cleanup"""
        if self.client:
            await self.client.close()
            logger.info("🔌 Disconnected")


async def main():
    """Run triangular arbitrage bot"""
    bot = TriangularArbitrageBot(
        exchange_name='binance',
        base_currency='USDT',
        trade_size_usd=Decimal('100'),
        min_profit_pct=Decimal('0.05'),  # 0.05%
        paper_trading=True
    )
    
    try:
        await bot.initialize()
        await bot.run(interval_seconds=15)
    except KeyboardInterrupt:
        logger.info("⛔ Stopped")
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
