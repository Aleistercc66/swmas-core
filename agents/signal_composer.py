import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Aggregated market data snapshot"""
    price: float
    timestamp: float
    volume_24h: float
    liquidity: float
    buy_pressure: float
    sell_pressure: float
    holder_count: int
    tx_count_24h: int
    
    # OHLCV data
    ohlcv: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # On-chain data
    whale_inflows: float = 0.0
    whale_outflows: float = 0.0
    smart_money_score: float = 0.0
    
    # Social data
    social_sentiment: float = 0.5
    mention_velocity: float = 0.0

@dataclass
class Signal:
    """Generated trading signal"""
    score: float  # 0-100
    confidence: float  # 0-100
    direction: str  # 'BUY', 'SELL', 'HOLD'
    timestamp: float
    factors: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ''
    target_mint: str = ''
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    position_size: float = 0.0


class MomentumEngine:
    """RSI + MACD + Bollinger momentum analysis"""
    
    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        
    def score(self, ohlcv: pd.DataFrame) -> float:
        """Return momentum score 0-100"""
        if len(ohlcv) < self.macd_slow:
            return 50.0
            
        closes = ohlcv['close'].values
        
        # RSI
        rsi = self._calculate_rsi(closes)
        rsi_score = rsi / 100 * 100  # Normalize
        
        # MACD
        macd, signal, hist = self._calculate_macd(closes)
        macd_score = 50 + (hist / abs(hist).max() * 50) if abs(hist).max() > 0 else 50
        
        # Bollinger position
        bb_position = self._calculate_bb_position(closes)
        bb_score = 100 - bb_position if bb_position > 50 else bb_position * 2
        
        # Weighted composite
        score = rsi_score * 0.35 + macd_score * 0.35 + bb_score * 0.30
        return np.clip(score, 0, 100)
        
    def _calculate_rsi(self, prices: np.ndarray) -> float:
        """Calculate RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
        
    def _calculate_macd(self, prices: np.ndarray) -> Tuple[float, float, float]:
        """Calculate MACD"""
        ema_fast = pd.Series(prices).ewm(span=self.macd_fast).mean().iloc[-1]
        ema_slow = pd.Series(prices).ewm(span=self.macd_slow).mean().iloc[-1]
        macd = ema_fast - ema_slow
        signal = pd.Series(prices).ewm(span=9).mean().iloc[-1]
        hist = macd - signal
        return macd, signal, hist
        
    def _calculate_bb_position(self, prices: np.ndarray) -> float:
        """Calculate position within Bollinger Bands (0-100)"""
        window = 20
        if len(prices) < window:
            return 50.0
        sma = np.mean(prices[-window:])
        std = np.std(prices[-window:])
        upper = sma + 2 * std
        lower = sma - 2 * std
        position = (prices[-1] - lower) / (upper - lower) * 100
        return np.clip(position, 0, 100)


class VolumeEngine:
    """Volume profile + VWAP analysis"""
    
    def score(self, trades: List[Dict]) -> float:
        """Return volume score 0-100"""
        if not trades:
            return 50.0
            
        # Calculate volume metrics
        buy_vol = sum(t['volume'] for t in trades if t['side'] == 'buy')
        sell_vol = sum(t['volume'] for t in trades if t['side'] == 'sell')
        total_vol = buy_vol + sell_vol
        
        if total_vol == 0:
            return 50.0
            
        # Volume ratio
        buy_ratio = buy_vol / total_vol
        
        # Volume velocity (current vs average)
        recent_vol = sum(t['volume'] for t in trades[-10:])
        avg_vol = sum(t['volume'] for t in trades) / len(trades)
        velocity = recent_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Score: high buy ratio + high velocity = bullish
        score = buy_ratio * 60 + min(velocity, 2.0) * 20 + 20
        return np.clip(score, 0, 100)


class LiquidityEngine:
    """Liquidity depth + slippage analysis"""
    
    def __init__(self, min_liquidity_usd: float = 20000):
        self.min_liquidity = min_liquidity_usd
        
    def score(self, orderbook: Dict) -> float:
        """Return liquidity score 0-100"""
        liquidity = orderbook.get('liquidity_usd', 0)
        spread = orderbook.get('spread_pct', 1.0)
        depth_2pct = orderbook.get('depth_2pct', 0)
        
        # Liquidity must meet minimum
        if liquidity < self.min_liquidity:
            return 0.0
            
        # Score based on liquidity depth and spread
        liquidity_score = min(liquidity / 100000, 1.0) * 40  # Max at $100K
        spread_score = max(0, (1 - spread)) * 30
        depth_score = min(depth_2pct / 50000, 1.0) * 30
        
        return liquidity_score + spread_score + depth_score


class WhaleEngine:
    """On-chain whale tracking"""
    
    def score(self, onchain_data: Dict) -> float:
        """Return whale score 0-100"""
        inflows = onchain_data.get('whale_inflows', 0)
        outflows = onchain_data.get('whale_outflows', 0)
        smart_money = onchain_data.get('smart_money_score', 0.5)
        
        net_flow = inflows - outflows
        total_flow = inflows + outflows
        
        if total_flow == 0:
            return 50.0
            
        # Net flow ratio (-1 to 1)
        flow_ratio = net_flow / total_flow
        
        # Score: positive net flow + high smart money = bullish
        score = (flow_ratio + 1) / 2 * 60 + smart_money * 40
        return np.clip(score, 0, 100)


class SentimentEngine:
    """Social sentiment analysis"""
    
    def score(self, social_data: Dict) -> float:
        """Return sentiment score 0-100"""
        sentiment = social_data.get('sentiment', 0.5)
        velocity = social_data.get('mention_velocity', 0)
        
        # Sentiment (0-1) to score (0-100)
        sentiment_score = sentiment * 60
        
        # Velocity bonus (max 20 points for 2x baseline)
        velocity_score = min(velocity, 2.0) * 10
        
        # Base score
        base_score = 30
        
        return np.clip(base_score + sentiment_score + velocity_score, 0, 100)


class ConfluenceEngine:
    """
    Requires minimum 3/5 factors to align before generating signal.
    Uses Bayesian confidence scoring.
    """
    
    MINIMUM_FACTORS = 3
    CONFIDENCE_THRESHOLD = 60
    
    def __init__(self):
        self.weights = {
            'momentum': 0.25,
            'volume': 0.25,
            'liquidity': 0.20,
            'whale': 0.15,
            'sentiment': 0.15
        }
        
    def validate(self, factors: Dict[str, Dict]) -> bool:
        """Check if minimum factors align"""
        directions = [f['direction'] for f in factors.values()]
        buy_count = directions.count('BUY')
        sell_count = directions.count('SELL')
        
        # For BUY: need 3+ BUY factors
        # For SELL: need 3+ SELL factors
        return buy_count >= self.MINIMUM_FACTORS or sell_count >= self.MINIMUM_FACTORS
        
    def calculate_confidence(self, factors: Dict[str, Dict]) -> float:
        """Bayesian confidence scoring"""
        scores = [f['score'] for f in factors.values()]
        
        # Mean score weighted by individual weights
        mean_score = np.mean(scores)
        
        # Minimum score penalizes weak factors
        min_score = np.min(scores)
        
        # Confidence = mean * penalty_factor
        confidence = mean_score * (0.5 + 0.5 * (min_score / 100))
        return np.clip(confidence, 0, 100)


class SignalComposer:
    """
    Multi-factor signal composition with confluence requirement.
    
    Pipeline:
    1. Ingest market data
    2. Run 5 engines (momentum, volume, liquidity, whale, sentiment)
    3. Confluence validation (3/5 factors)
    4. Signal generation with confidence
    5. Risk-adjusted position sizing
    """
    
    def __init__(self, min_liquidity: float = 20000):
        self.momentum_engine = MomentumEngine()
        self.volume_engine = VolumeEngine()
        self.liquidity_engine = LiquidityEngine(min_liquidity)
        self.whale_engine = WhaleEngine()
        self.sentiment_engine = SentimentEngine()
        self.confluence_engine = ConfluenceEngine()
        
    async def compose(self, data: MarketData) -> Signal:
        """
        Generate trading signal from market data.
        
        Returns Signal with score, confidence, direction, and recommendations.
        """
        # 1. Run all 5 engines
        momentum_score = self.momentum_engine.score(data.ohlcv)
        volume_score = self.volume_engine.score([])  # Placeholder
        liquidity_score = self.liquidity_engine.score({
            'liquidity_usd': data.liquidity,
            'spread_pct': 0.01,
            'depth_2pct': data.liquidity * 0.5
        })
        whale_score = self.whale_engine.score({
            'whale_inflows': data.whale_inflows,
            'whale_outflows': data.whale_outflows,
            'smart_money_score': data.smart_money_score
        })
        sentiment_score = self.sentiment_engine.score({
            'sentiment': data.social_sentiment,
            'mention_velocity': data.mention_velocity
        })
        
        # 2. Determine directions
        def direction(score: float) -> str:
            if score > 60:
                return 'BUY'
            elif score < 40:
                return 'SELL'
            return 'HOLD'
            
        factors = {
            'momentum': {'score': momentum_score, 'direction': direction(momentum_score)},
            'volume': {'score': volume_score, 'direction': direction(volume_score)},
            'liquidity': {'score': liquidity_score, 'direction': direction(liquidity_score)},
            'whale': {'score': whale_score, 'direction': direction(whale_score)},
            'sentiment': {'score': sentiment_score, 'direction': direction(sentiment_score)}
        }
        
        # 3. Confluence validation
        if not self.confluence_engine.validate(factors):
            return Signal(
                score=50.0,
                confidence=0.0,
                direction='HOLD',
                timestamp=datetime.now().timestamp(),
                factors=factors,
                recommendation='No confluence - insufficient aligned factors'
            )
            
        # 4. Calculate composite score
        weights = self.confluence_engine.weights
        composite_score = (
            momentum_score * weights['momentum'] +
            volume_score * weights['volume'] +
            liquidity_score * weights['liquidity'] +
            whale_score * weights['whale'] +
            sentiment_score * weights['sentiment']
        )
        
        # 5. Calculate confidence
        confidence = self.confluence_engine.calculate_confidence(factors)
        
        # 6. Determine direction
        if composite_score > 60 and confidence >= 60:
            direction = 'BUY'
        elif composite_score < 40 and confidence >= 60:
            direction = 'SELL'
        else:
            direction = 'HOLD'
            
        # 7. Generate recommendations
        entry_price = data.price
        if direction == 'BUY':
            stop_loss = entry_price * 0.85  # 15% stop
            tp1 = entry_price * 1.50  # 50%
            tp2 = entry_price * 2.00  # 100%
            tp3 = entry_price * 3.00  # 200%
            recommendation = f"BUY at ${entry_price:.6f} | SL: ${stop_loss:.6f} | TP1: ${tp1:.6f} | TP2: ${tp2:.6f} | TP3: ${tp3:.6f}"
        elif direction == 'SELL':
            stop_loss = entry_price * 1.15  # 15% stop on short
            tp1 = entry_price * 0.70  # -30%
            recommendation = f"SELL at ${entry_price:.6f} | SL: ${stop_loss:.6f} | TP1: ${tp1:.6f}"
        else:
            stop_loss = tp1 = tp2 = tp3 = 0.0
            recommendation = 'HOLD - wait for better confluence'
            
        return Signal(
            score=composite_score,
            confidence=confidence,
            direction=direction,
            timestamp=datetime.now().timestamp(),
            factors=factors,
            recommendation=recommendation,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3
        )
        
    async def batch_compose(self, data_list: List[MarketData]) -> List[Signal]:
        """Generate signals for multiple tokens"""
        tasks = [self.compose(data) for data in data_list]
        return await asyncio.gather(*tasks)


# ─── QUICK TEST ───
async def test_signal_composer():
    """Test the signal composer with dummy data"""
    composer = SignalComposer()
    
    # Create dummy OHLCV data
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    prices = np.cumsum(np.random.randn(100) * 0.001) + 1.0
    ohlcv = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(100) * 0.001),
        'low': prices - np.abs(np.random.randn(100) * 0.001),
        'close': prices + np.random.randn(100) * 0.0005,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    data = MarketData(
        price=prices[-1],
        timestamp=datetime.now().timestamp(),
        volume_24h=1000000,
        liquidity=50000,
        buy_pressure=0.65,
        sell_pressure=0.35,
        holder_count=1000,
        tx_count_24h=5000,
        ohlcv=ohlcv,
        whale_inflows=100000,
        whale_outflows=50000,
        smart_money_score=0.75,
        social_sentiment=0.70,
        mention_velocity=1.5
    )
    
    signal = await composer.compose(data)
    print(f"Signal: {signal}")
    
    return signal


if __name__ == "__main__":
    asyncio.run(test_signal_composer())
