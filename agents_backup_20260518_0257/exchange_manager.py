"""
Multi-Exchange Master Integration
Connects to top exchanges: Binance, Bybit, OKX, Jupiter, Raydium
"""

import asyncio
import aiohttp
import json
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from collections import defaultdict

class ExchangeType(Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    JUPITER = "jupiter"
    RAYDIUM = "raydium"
    ORCA = "orca"

@dataclass
class OrderBook:
    exchange: str
    symbol: str
    bids: List[tuple]  # (price, amount)
    asks: List[tuple]
    timestamp: datetime
    
    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 0
    
    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid
    
    @property
    def spread_pct(self) -> float:
        mid = (self.best_bid + self.best_ask) / 2
        return (self.spread / mid * 100) if mid > 0 else 0

@dataclass
class MarketData:
    symbol: str
    price: float
    volume_24h: float
    high_24h: float
    low_24h: float
    change_24h: float
    change_24h_pct: float
    open_interest: float = 0
    funding_rate: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Trade:
    symbol: str
    side: str  # buy/sell
    amount: float
    price: float
    timestamp: datetime
    exchange: str
    fee: float = 0
    pnl: float = 0

class ExchangeConnector:
    """Base exchange connector"""
    
    def __init__(self, name: str, api_key: str = None, api_secret: str = None):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_remaining = 1200
        self.rate_limit_reset = 60
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, params: Dict) -> str:
        """Generate API signature"""
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def get_orderbook(self, symbol: str) -> OrderBook:
        raise NotImplementedError
    
    async def get_market_data(self, symbol: str) -> MarketData:
        raise NotImplementedError
    
    async def get_balance(self) -> Dict[str, float]:
        raise NotImplementedError
    
    async def place_order(self, symbol: str, side: str, amount: float, price: float = None, order_type: str = 'market'):
        raise NotImplementedError

class BinanceConnector(ExchangeConnector):
    """Binance exchange connector"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__("binance", api_key, api_secret)
        self.base_url = "https://api.binance.com"
        self.futures_url = "https://fapi.binance.com"
    
    async def get_orderbook(self, symbol: str) -> OrderBook:
        url = f"{self.base_url}/api/v3/depth"
        params = {"symbol": symbol.upper(), "limit": 20}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            
            return OrderBook(
                exchange="binance",
                symbol=symbol,
                bids=[(float(b[0]), float(b[1])) for b in data.get('bids', [])],
                asks=[(float(a[0]), float(a[1])) for a in data.get('asks', [])],
                timestamp=datetime.now()
            )
    
    async def get_market_data(self, symbol: str) -> MarketData:
        url = f"{self.base_url}/api/v3/ticker/24hr"
        params = {"symbol": symbol.upper()}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            
            return MarketData(
                symbol=symbol,
                price=float(data.get('lastPrice', 0)),
                volume_24h=float(data.get('volume', 0)),
                high_24h=float(data.get('highPrice', 0)),
                low_24h=float(data.get('lowPrice', 0)),
                change_24h=float(data.get('priceChange', 0)),
                change_24h_pct=float(data.get('priceChangePercent', 0)),
                timestamp=datetime.now()
            )
    
    async def get_futures_data(self, symbol: str) -> MarketData:
        """Get futures market data with funding rate"""
        url = f"{self.futures_url}/fapi/v1/ticker/24hr"
        params = {"symbol": symbol.upper()}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            
            # Get funding rate
            funding_url = f"{self.futures_url}/fapi/v1/premiumIndex"
            async with self.session.get(funding_url, params=params, timeout=10) as funding_resp:
                funding_data = await funding_resp.json()
                funding_rate = float(funding_data.get('lastFundingRate', 0))
                open_interest = float(funding_data.get('openInterest', 0))
            
            return MarketData(
                symbol=symbol,
                price=float(data.get('lastPrice', 0)),
                volume_24h=float(data.get('volume', 0)),
                high_24h=float(data.get('highPrice', 0)),
                low_24h=float(data.get('lowPrice', 0)),
                change_24h=float(data.get('priceChange', 0)),
                change_24h_pct=float(data.get('priceChangePercent', 0)),
                open_interest=open_interest,
                funding_rate=funding_rate,
                timestamp=datetime.now()
            )
    
    async def get_balance(self) -> Dict[str, float]:
        if not self.api_key or not self.api_secret:
            return {}
        
        timestamp = int(datetime.now().timestamp() * 1000)
        params = {"timestamp": timestamp}
        params['signature'] = self._generate_signature(params)
        
        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.base_url}/api/v3/account"
        
        async with self.session.get(url, params=params, headers=headers, timeout=10) as resp:
            data = await resp.json()
            balances = {}
            for b in data.get('balances', []):
                free = float(b.get('free', 0))
                locked = float(b.get('locked', 0))
                if free + locked > 0:
                    balances[b['asset']] = free + locked
            return balances

class BybitConnector(ExchangeConnector):
    """Bybit exchange connector"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__("bybit", api_key, api_secret)
        self.base_url = "https://api.bybit.com"
    
    async def get_orderbook(self, symbol: str) -> OrderBook:
        url = f"{self.base_url}/v5/market/orderbook"
        params = {"category": "spot", "symbol": symbol.upper(), "limit": 20}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            result = data.get('result', {})
            
            return OrderBook(
                exchange="bybit",
                symbol=symbol,
                bids=[(float(b[0]), float(b[1])) for b in result.get('b', [])],
                asks=[(float(a[0]), float(a[1])) for a in result.get('a', [])],
                timestamp=datetime.now()
            )
    
    async def get_market_data(self, symbol: str) -> MarketData:
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": "spot", "symbol": symbol.upper()}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            result = data.get('result', {}).get('list', [{}])[0]
            
            return MarketData(
                symbol=symbol,
                price=float(result.get('lastPrice', 0)),
                volume_24h=float(result.get('volume24h', 0)),
                high_24h=float(result.get('highPrice24h', 0)),
                low_24h=float(result.get('lowPrice24h', 0)),
                change_24h=float(result.get('price24hPcnt', 0)) * float(result.get('lastPrice', 0)),
                change_24h_pct=float(result.get('price24hPcnt', 0)) * 100,
                timestamp=datetime.now()
            )

class OKXConnector(ExchangeConnector):
    """OKX exchange connector"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, passphrase: str = None):
        super().__init__("okx", api_key, api_secret)
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com"
    
    async def get_orderbook(self, symbol: str) -> OrderBook:
        url = f"{self.base_url}/api/v5/market/books"
        params = {"instId": symbol.upper().replace("/", "-"), "sz": 20}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            result = data.get('data', [{}])[0]
            
            return OrderBook(
                exchange="okx",
                symbol=symbol,
                bids=[(float(b[0]), float(b[1])) for b in result.get('bids', [])],
                asks=[(float(a[0]), float(a[1])) for a in result.get('asks', [])],
                timestamp=datetime.now()
            )
    
    async def get_market_data(self, symbol: str) -> MarketData:
        url = f"{self.base_url}/api/v5/market/ticker"
        params = {"instId": symbol.upper().replace("/", "-")}
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            result = data.get('data', [{}])[0]
            
            return MarketData(
                symbol=symbol,
                price=float(result.get('last', 0)),
                volume_24h=float(result.get('vol24h', 0)),
                high_24h=float(result.get('high24h', 0)),
                low_24h=float(result.get('low24h', 0)),
                change_24h=float(result.get('last', 0)) - float(result.get('open24h', 0)),
                change_24h_pct=float(result.get('change24h', 0)),
                timestamp=datetime.now()
            )

class JupiterConnector(ExchangeConnector):
    """Jupiter DEX aggregator (Solana)"""
    
    def __init__(self):
        super().__init__("jupiter")
        self.base_url = "https://quote-api.jup.ag/v6"
    
    async def get_quote(self, input_mint: str, output_mint: str, amount: float) -> Dict:
        """Get swap quote from Jupiter"""
        url = f"{self.base_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": int(amount * 1e9),  # Convert to lamports
            "slippageBps": 50  # 0.5% slippage
        }
        
        async with self.session.get(url, params=params, timeout=10) as resp:
            return await resp.json()
    
    async def get_price(self, token_address: str) -> float:
        """Get token price from Jupiter"""
        # Use USDC as reference
        quote = await self.get_quote(
            token_address,
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            1.0
        )
        
        if 'outAmount' in quote:
            return float(quote['outAmount']) / 1e6  # USDC has 6 decimals
        return 0
    
    async def get_orderbook(self, symbol: str) -> OrderBook:
        """Jupiter doesn't have traditional orderbook, return estimated"""
        # Get routes for estimation
        base, quote = symbol.split('/')
        
        # This is simplified - would need proper token mint mapping
        return OrderBook(
            exchange="jupiter",
            symbol=symbol,
            bids=[],
            asks=[],
            timestamp=datetime.now()
        )

class MultiExchangeManager:
    """Manage multiple exchanges simultaneously"""
    
    def __init__(self):
        self.exchanges: Dict[str, ExchangeConnector] = {}
        self.price_cache: Dict[str, Dict[str, float]] = {}  # symbol -> exchange -> price
        self.arbitrage_opportunities: List[Dict] = []
        
    def add_exchange(self, name: str, connector: ExchangeConnector):
        self.exchanges[name] = connector
    
    async def get_best_price(self, symbol: str, side: str = 'buy') -> tuple:
        """Get best price across all exchanges"""
        prices = []
        
        for name, exchange in self.exchanges.items():
            try:
                data = await exchange.get_market_data(symbol)
                prices.append((name, data.price))
            except:
                continue
        
        if not prices:
            return None, 0
        
        if side == 'buy':
            # Best ask (lowest)
            return min(prices, key=lambda x: x[1])
        else:
            # Best bid (highest)
            return max(prices, key=lambda x: x[1])
    
    async def find_arbitrage(self, symbol: str, min_profit_pct: float = 0.5) -> Optional[Dict]:
        """Find arbitrage opportunities across exchanges"""
        orderbooks = {}
        
        for name, exchange in self.exchanges.items():
            try:
                ob = await exchange.get_orderbook(symbol)
                orderbooks[name] = ob
            except:
                continue
        
        if len(orderbooks) < 2:
            return None
        
        # Find best bid and ask
        best_bid = None
        best_ask = None
        
        for name, ob in orderbooks.items():
            if not best_bid or ob.best_bid > best_bid[1]:
                best_bid = (name, ob.best_bid)
            if not best_ask or ob.best_ask < best_ask[1]:
                best_ask = (name, ob.best_ask)
        
        if not best_bid or not best_ask or best_bid[0] == best_ask[0]:
            return None
        
        profit_pct = (best_bid[1] - best_ask[1]) / best_ask[1] * 100
        
        if profit_pct >= min_profit_pct:
            return {
                'symbol': symbol,
                'buy_exchange': best_ask[0],
                'sell_exchange': best_bid[0],
                'buy_price': best_ask[1],
                'sell_price': best_bid[1],
                'profit_pct': profit_pct,
                'timestamp': datetime.now()
            }
        
        return None
    
    async def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """Get balances from all exchanges"""
        balances = {}
        
        for name, exchange in self.exchanges.items():
            try:
                balances[name] = await exchange.get_balance()
            except:
                balances[name] = {}
        
        return balances
    
    async def execute_arbitrage(self, opportunity: Dict, amount: float) -> bool:
        """Execute arbitrage trade"""
        buy_exchange = self.exchanges.get(opportunity['buy_exchange'])
        sell_exchange = self.exchanges.get(opportunity['sell_exchange'])
        
        if not buy_exchange or not sell_exchange:
            return False
        
        try:
            # Buy on cheaper exchange
            await buy_exchange.place_order(
                opportunity['symbol'],
                'buy',
                amount,
                opportunity['buy_price']
            )
            
            # Sell on expensive exchange
            await sell_exchange.place_order(
                opportunity['symbol'],
                'sell',
                amount,
                opportunity['sell_price']
            )
            
            return True
        except:
            return False
    
    async def get_portfolio_value(self) -> Dict:
        """Get total portfolio value across all exchanges"""
        balances = await self.get_all_balances()
        total_value = 0
        exchange_values = {}
        
        for exchange_name, balance in balances.items():
            exchange_value = 0
            
            for asset, amount in balance.items():
                if asset == 'USDT' or asset == 'USDC':
                    exchange_value += amount
                else:
                    # Get price and calculate value
                    try:
                        symbol = f"{asset}USDT"
                        data = await self.exchanges[exchange_name].get_market_data(symbol)
                        exchange_value += amount * data.price
                    except:
                        pass
            
            exchange_values[exchange_name] = exchange_value
            total_value += exchange_value
        
        return {
            'total_value_usd': total_value,
            'by_exchange': exchange_values,
            'timestamp': datetime.now()
        }


class StrategyLearner:
    """Learn and adapt trading strategies from market data"""
    
    def __init__(self):
        self.strategies = {
            'momentum': self._momentum_strategy,
            'mean_reversion': self._mean_reversion_strategy,
            'breakout': self._breakout_strategy,
            'scalping': self._scalping_strategy,
            'trend_following': self._trend_following_strategy
        }
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        self.best_strategy = None
        self.market_regime = 'neutral'
    
    def analyze_market_regime(self, data: List[MarketData]) -> str:
        """Determine current market regime"""
        if len(data) < 20:
            return 'neutral'
        
        prices = [d.price for d in data]
        returns = np.diff(prices) / prices[:-1]
        
        # Trend detection
        sma_short = np.mean(prices[-10:])
        sma_long = np.mean(prices[-20:])
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(365)
        
        # Momentum
        momentum = (prices[-1] - prices[-10]) / prices[-10]
        
        if sma_short > sma_long * 1.02 and momentum > 0.05:
            return 'strong_uptrend'
        elif sma_short > sma_long:
            return 'uptrend'
        elif sma_short < sma_long * 0.98 and momentum < -0.05:
            return 'strong_downtrend'
        elif sma_short < sma_long:
            return 'downtrend'
        elif volatility > 0.8:
            return 'volatile'
        else:
            return 'ranging'
    
    def select_best_strategy(self, regime: str) -> str:
        """Select best strategy for current regime"""
        strategy_map = {
            'strong_uptrend': 'momentum',
            'uptrend': 'trend_following',
            'strong_downtrend': 'mean_reversion',
            'downtrend': 'mean_reversion',
            'volatile': 'scalping',
            'ranging': 'mean_reversion',
            'neutral': 'breakout'
        }
        
        return strategy_map.get(regime, 'breakout')
    
    def _momentum_strategy(self, data: List[MarketData]) -> Dict:
        """Momentum-based strategy"""
        if len(data) < 10:
            return {'signal': 'hold', 'confidence': 0, 'reason': 'Need more data'}
        
        prices = [d.price for d in data]
        volumes = [d.volume_24h for d in data]
        
        # Price momentum
        price_change_1h = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        price_change_24h = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        
        # Volume momentum
        avg_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else np.mean(volumes)
        recent_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
        volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Combined signal
        if price_change_1h > 0.02 and volume_surge > 1.5 and price_change_24h > 0:
            return {
                'signal': 'buy',
                'confidence': min(100, (price_change_1h * 100 + volume_surge * 20)),
                'reason': f"Momentum: +{price_change_1h*100:.1f}% with {volume_surge:.1f}x volume"
            }
        elif price_change_1h < -0.02 and volume_surge > 1.5:
            return {
                'signal': 'sell',
                'confidence': min(100, (abs(price_change_1h) * 100 + volume_surge * 20)),
                'reason': f"Negative momentum: {price_change_1h*100:.1f}% with {volume_surge:.1f}x volume"
            }
        
        return {'signal': 'hold', 'confidence': 0, 'reason': 'No clear momentum'}
    
    def _mean_reversion_strategy(self, data: List[MarketData]) -> Dict:
        """Mean reversion strategy"""
        if len(data) < 20:
            return {'signal': 'hold', 'confidence': 0, 'reason': 'Need more data'}
        
        prices = [d.price for d in data]
        sma = np.mean(prices)
        std = np.std(prices)
        
        current_price = prices[-1]
        z_score = (current_price - sma) / std if std > 0 else 0
        
        if z_score > 2.0:
            return {
                'signal': 'sell',
                'confidence': min(100, abs(z_score) * 25),
                'reason': f"Overbought (Z: {z_score:.2f})"
            }
        elif z_score < -2.0:
            return {
                'signal': 'buy',
                'confidence': min(100, abs(z_score) * 25),
                'reason': f"Oversold (Z: {z_score:.2f})"
            }
        
        return {'signal': 'hold', 'confidence': 0, 'reason': f'Price near mean (Z: {z_score:.2f})'}
    
    def _breakout_strategy(self, data: List[MarketData]) -> Dict:
        """Breakout strategy"""
        if len(data) < 20:
            return {'signal': 'hold', 'confidence': 0, 'reason': 'Need more data'}
        
        prices = [d.price for d in data]
        highs = [d.high_24h for d in data]
        lows = [d.low_24h for d in data]
        
        resistance = max(highs[-20:])
        support = min(lows[-20:])
        current = prices[-1]
        
        if current > resistance * 1.01:
            return {
                'signal': 'buy',
                'confidence': min(100, (current / resistance - 1) * 1000),
                'reason': f"Breakout above ${resistance:.4f}"
            }
        elif current < support * 0.99:
            return {
                'signal': 'sell',
                'confidence': min(100, (1 - current / support) * 1000),
                'reason': f"Breakdown below ${support:.4f}"
            }
        
        return {'signal': 'hold', 'confidence': 0, 'reason': f'In range ${support:.4f}-${resistance:.4f}'}
    
    def _scalping_strategy(self, data: List[MarketData]) -> Dict:
        """Scalping strategy for volatile markets"""
        if len(data) < 5:
            return {'signal': 'hold', 'confidence': 0, 'reason': 'Need more data'}
        
        prices = [d.price for d in data]
        
        # Short-term RSI
        gains = []
        losses = []
        for i in range(1, min(15, len(prices))):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0.001
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi < 30:
            return {'signal': 'buy', 'confidence': 100 - rsi, 'reason': f"RSI oversold ({rsi:.1f})"}
        elif rsi > 70:
            return {'signal': 'sell', 'confidence': rsi, 'reason': f"RSI overbought ({rsi:.1f})"}
        
        return {'signal': 'hold', 'confidence': 0, 'reason': f'RSI neutral ({rsi:.1f})'}
    
    def _trend_following_strategy(self, data: List[MarketData]) -> Dict:
        """Trend following with moving averages"""
        if len(data) < 50:
            return {'signal': 'hold', 'confidence': 0, 'reason': 'Need more data'}
        
        prices = [d.price for d in data]
        
        ema_9 = np.mean(prices[-9:])
        ema_21 = np.mean(prices[-21:])
        ema_50 = np.mean(prices[-50:])
        
        if ema_9 > ema_21 > ema_50:
            return {
                'signal': 'buy',
                'confidence': min(100, (ema_9 / ema_50 - 1) * 500),
                'reason': f"Uptrend: EMA9 > EMA21 > EMA50"
            }
        elif ema_9 < ema_21 < ema_50:
            return {
                'signal': 'sell',
                'confidence': min(100, (1 - ema_9 / ema_50) * 500),
                'reason': f"Downtrend: EMA9 < EMA21 < EMA50"
            }
        
        return {'signal': 'hold', 'confidence': 0, 'reason': 'Mixed signals'}
    
    def generate_signal(self, data: List[MarketData]) -> Dict:
        """Generate trading signal based on best strategy"""
        regime = self.analyze_market_regime(data)
        self.market_regime = regime
        
        best_strategy_name = self.select_best_strategy(regime)
        self.best_strategy = best_strategy_name
        
        strategy_fn = self.strategies.get(best_strategy_name, self._breakout_strategy)
        signal = strategy_fn(data)
        
        signal['strategy'] = best_strategy_name
        signal['regime'] = regime
        
        return signal
    
    def update_performance(self, strategy: str, pnl: float):
        """Update strategy performance tracking"""
        self.performance_history[strategy].append(pnl)
        
        # Keep last 100 trades
        if len(self.performance_history[strategy]) > 100:
            self.performance_history[strategy] = self.performance_history[strategy][-100:]
    
    def get_strategy_performance(self) -> Dict[str, Dict]:
        """Get performance metrics for all strategies"""
        performance = {}
        
        for strategy, pnls in self.performance_history.items():
            if not pnls:
                continue
            
            wins = sum(1 for p in pnls if p > 0)
            total = len(pnls)
            
            performance[strategy] = {
                'total_trades': total,
                'win_rate': wins / total * 100 if total > 0 else 0,
                'avg_pnl': np.mean(pnls),
                'total_pnl': sum(pnls),
                'max_drawdown': min(pnls),
                'best_trade': max(pnls),
                'sharpe': np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0
            }
        
        return performance


# Usage example
async def main():
    # Initialize multi-exchange manager
    manager = MultiExchangeManager()
    
    # Add exchanges (with your API keys)
    # manager.add_exchange("binance", BinanceConnector("api_key", "api_secret"))
    # manager.add_exchange("bybit", BybitConnector("api_key", "api_secret"))
    
    # Initialize strategy learner
    learner = StrategyLearner()
    
    # Example: Get market data and generate signal
    # market_data = [...]  # List of MarketData objects
    # signal = learner.generate_signal(market_data)
    # print(f"Signal: {signal['signal']} ({signal['confidence']:.0f}% confidence)")
    # print(f"Strategy: {signal['strategy']}")
    # print(f"Reason: {signal['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
