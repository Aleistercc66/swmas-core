"""
Stock Signal Generator — Technical Analysis Engine
RSI, MACD, Bollinger, EMA/SMA crossover, Volume anomaly
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Literal
from datetime import datetime
import pandas as pd
import numpy as np
import pandas_ta as ta  # pip install pandas-ta

from stock_config import DEFAULT_SIGNAL_CONFIG, SignalConfig
from stock_scanner import StockSnapshot, ScanResult

logger = logging.getLogger(__name__)

# ───────────────────────────
# SIGNAL DATA MODELS
# ───────────────────────────

SignalType = Literal["MOMENTUM", "MEAN_REVERSION", "BREAKOUT", "EMA_CROSS", "VOLUME_SPIKE"]

@dataclass
class Signal:
    """A single trading signal."""
    symbol: str
    signal_type: SignalType
    direction: Literal["LONG", "SHORT"]
    score: float  # 0-100
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    
    # Technical details
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Factor scores
    momentum_score: float = 0.0
    volume_score: float = 0.0
    technical_score: float = 0.0
    sentiment_score: float = 0.0
    fundamental_score: float = 0.0
    
    # Edge calculation
    edge_percent: float = 0.0
    rr_ratio: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    factors: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure score is 0-100
        self.score = max(0.0, min(100.0, self.score))
        
        # Set confidence based on score
        if self.score >= 85:
            self.confidence = "HIGH"
        elif self.score >= 70:
            self.confidence = "MEDIUM"
        else:
            self.confidence = "LOW"

@dataclass
class SignalBatch:
    """Batch of signals from a scan."""
    timestamp: datetime
    signals: List[Signal] = field(default_factory=list)
    
    # Stats
    total_signals: int = 0
    long_signals: int = 0
    short_signals: int = 0
    high_confidence: int = 0
    avg_score: float = 0.0

# ───────────────────────────
# SIGNAL GENERATOR
# ───────────────────────────

class SignalGenerator:
    """
    Multi-factor signal generator for US stocks.
    
    Generates signals based on:
    - Momentum: price > EMA20 + RSI > 50
    - Mean Reversion: price < lower Bollinger + RSI < 30
    - Breakout: volume > 2x avg + price above resistance
    - EMA Cross: 9/20/50 EMA crossovers
    - Volume Spike: abnormal volume activity
    """
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or DEFAULT_SIGNAL_CONFIG
        
        logger.info(
            f"SignalGenerator initialized — "
            f"RSI({self.config.rsi_period}), "
            f"MACD({self.config.macd_fast},{self.config.macd_slow},{self.config.macd_signal}), "
            f"BB({self.config.bb_period},{self.config.bb_std})"
        )
    
    def generate_signals(self, scan_result: ScanResult) -> SignalBatch:
        """
        Generate signals from scan results.
        
        Args:
            scan_result: Output from MarketScanner
            
        Returns:
            SignalBatch with all generated signals
        """
        logger.info(f"🧠 Generating signals for {len(scan_result.snapshots)} stocks...")
        
        signals: List[Signal] = []
        
        for snapshot in scan_result.snapshots:
            try:
                # We need historical data for technicals
                # For now, we'll use the snapshot's basic data
                # In production, fetch 1h/1d data and calculate indicators
                
                signal = self._analyze_stock(snapshot)
                if signal and signal.score >= self.config.signal_score_threshold:
                    signals.append(signal)
                    
            except Exception as e:
                logger.warning(f"Error analyzing {snapshot.symbol}: {e}")
                continue
        
        # Sort by score descending
        signals.sort(key=lambda x: x.score, reverse=True)
        
        batch = SignalBatch(
            timestamp=datetime.utcnow(),
            signals=signals,
            total_signals=len(signals),
            long_signals=sum(1 for s in signals if s.direction == "LONG"),
            short_signals=sum(1 for s in signals if s.direction == "SHORT"),
            high_confidence=sum(1 for s in signals if s.confidence == "HIGH"),
        )
        
        if signals:
            batch.avg_score = np.mean([s.score for s in signals])
        
        logger.info(
            f"✅ Generated {batch.total_signals} signals "
            f"({batch.long_signals} LONG, {batch.short_signals} SHORT) "
            f"— avg score: {batch.avg_score:.1f}"
        )
        
        return batch
    
    def _analyze_stock(self, snapshot: StockSnapshot) -> Optional[Signal]:
        """
        Analyze a single stock and generate signal if criteria met.
        
        This is a simplified version — in production, you'd fetch
        full historical data and calculate all indicators properly.
        """
        # For now, we'll use the snapshot data and simulate indicator values
        # In production, fetch 1h data and calculate real indicators
        
        price = snapshot.price
        change = snapshot.change_percent
        volume_ratio = snapshot.volume / snapshot.volume_avg_20d if snapshot.volume_avg_20d > 0 else 1.0
        volatility = snapshot.volatility
        
        # Simulate indicators (in production, calculate from real data)
        # These would come from pandas_ta calculations on historical data
        rsi = self._estimate_rsi(change, volume_ratio)
        ema_20 = price * (1 - 0.01) if change > 0 else price * (1 + 0.01)  # Placeholder
        bb_lower = price * 0.95  # Placeholder
        bb_upper = price * 1.05  # Placeholder
        volume_avg = snapshot.volume_avg_20d
        
        # Update snapshot with calculated values
        snapshot.rsi_14 = rsi
        snapshot.ema_20 = ema_20
        snapshot.bb_lower = bb_lower
        snapshot.bb_upper = bb_upper
        
        # Check signal types
        momentum_signal = self._check_momentum(snapshot, price, rsi, ema_20)
        mean_reversion_signal = self._check_mean_reversion(snapshot, price, rsi, bb_lower)
        breakout_signal = self._check_breakout(snapshot, price, volume_ratio, bb_upper)
        ema_cross_signal = self._check_ema_cross(snapshot, price)
        volume_spike_signal = self._check_volume_spike(snapshot, volume_ratio)
        
        # Pick the strongest signal
        all_signals = [
            momentum_signal, mean_reversion_signal, breakout_signal,
            ema_cross_signal, volume_spike_signal
        ]
        all_signals = [s for s in all_signals if s is not None]
        
        if not all_signals:
            return None
        
        # Return highest score signal
        best_signal = max(all_signals, key=lambda x: x.score)
        return best_signal
    
    def _check_momentum(
        self, snapshot: StockSnapshot, price: float, rsi: float, ema_20: float
    ) -> Optional[Signal]:
        """Momentum signal: price > EMA20 + RSI > 50."""
        if price > ema_20 and rsi > 50:
            score = min(100, 60 + (rsi - 50) * 2 + (price / ema_20 - 1) * 100)
            
            # Calculate targets
            stop = price * 0.98  # 2% stop
            tp1 = price * 1.04   # 4% TP1
            tp2 = price * 1.08   # 8% TP2
            tp3 = price * 1.15   # 15% TP3
            
            risk = price - stop
            reward = tp1 - price
            rr = reward / risk if risk > 0 else 0
            
            return Signal(
                symbol=snapshot.symbol,
                signal_type="MOMENTUM",
                direction="LONG",
                score=score,
                confidence="MEDIUM",
                entry_price=price,
                stop_loss=stop,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                momentum_score=score * 0.4,
                technical_score=score * 0.3,
                volume_score=score * 0.2,
                sentiment_score=score * 0.1,
                edge_percent=abs(price - ema_20) / price * 100,
                rr_ratio=rr,
                factors={
                    "rsi": rsi,
                    "ema_20": ema_20,
                    "price_vs_ema": (price / ema_20 - 1) * 100,
                }
            )
        return None
    
    def _check_mean_reversion(
        self, snapshot: StockSnapshot, price: float, rsi: float, bb_lower: float
    ) -> Optional[Signal]:
        """Mean reversion: price < lower Bollinger + RSI < 30."""
        if price < bb_lower and rsi < 30:
            score = min(100, 70 + (30 - rsi) * 2 + (bb_lower / price - 1) * 50)
            
            stop = price * 0.95  # 5% stop (wider for mean reversion)
            tp1 = price * 1.03   # 3% TP1
            tp2 = price * 1.06   # 6% TP2
            tp3 = price * 1.10   # 10% TP3
            
            risk = price - stop
            reward = tp1 - price
            rr = reward / risk if risk > 0 else 0
            
            return Signal(
                symbol=snapshot.symbol,
                signal_type="MEAN_REVERSION",
                direction="LONG",
                score=score,
                confidence="MEDIUM",
                entry_price=price,
                stop_loss=stop,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                momentum_score=score * 0.2,
                technical_score=score * 0.5,
                volume_score=score * 0.2,
                sentiment_score=score * 0.1,
                edge_percent=abs(bb_lower - price) / price * 100,
                rr_ratio=rr,
                factors={
                    "rsi": rsi,
                    "bb_lower": bb_lower,
                    "price_vs_bb": (bb_lower / price - 1) * 100,
                }
            )
        return None
    
    def _check_breakout(
        self, snapshot: StockSnapshot, price: float, volume_ratio: float, bb_upper: float
    ) -> Optional[Signal]:
        """Breakout: volume > 2x avg + price above resistance."""
        if volume_ratio >= 2.0 and price > bb_upper:
            score = min(100, 65 + (volume_ratio - 2) * 10 + (price / bb_upper - 1) * 100)
            
            stop = price * 0.97  # 3% stop
            tp1 = price * 1.05   # 5% TP1
            tp2 = price * 1.10   # 10% TP2
            tp3 = price * 1.20   # 20% TP3
            
            risk = price - stop
            reward = tp1 - price
            rr = reward / risk if risk > 0 else 0
            
            return Signal(
                symbol=snapshot.symbol,
                signal_type="BREAKOUT",
                direction="LONG",
                score=score,
                confidence="MEDIUM",
                entry_price=price,
                stop_loss=stop,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                momentum_score=score * 0.3,
                technical_score=score * 0.3,
                volume_score=score * 0.4,
                sentiment_score=score * 0.0,
                edge_percent=abs(price - bb_upper) / price * 100,
                rr_ratio=rr,
                factors={
                    "volume_ratio": volume_ratio,
                    "bb_upper": bb_upper,
                    "price_vs_resistance": (price / bb_upper - 1) * 100,
                }
            )
        return None
    
    def _check_ema_cross(self, snapshot: StockSnapshot, price: float) -> Optional[Signal]:
        """EMA crossover: 9 EMA crosses above 20 EMA."""
        # Simplified — in production, check actual EMA crossover
        # For now, use price momentum as proxy
        if snapshot.change_percent > 2.0:
            score = min(100, 60 + snapshot.change_percent * 5)
            
            stop = price * 0.98
            tp1 = price * 1.03
            tp2 = price * 1.06
            tp3 = price * 1.12
            
            risk = price - stop
            reward = tp1 - price
            rr = reward / risk if risk > 0 else 0
            
            return Signal(
                symbol=snapshot.symbol,
                signal_type="EMA_CROSS",
                direction="LONG",
                score=score,
                confidence="MEDIUM",
                entry_price=price,
                stop_loss=stop,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                technical_score=score * 0.6,
                momentum_score=score * 0.2,
                volume_score=score * 0.2,
                edge_percent=snapshot.change_percent,
                rr_ratio=rr,
                factors={
                    "change_percent": snapshot.change_percent,
                }
            )
        return None
    
    def _check_volume_spike(
        self, snapshot: StockSnapshot, volume_ratio: float
    ) -> Optional[Signal]:
        """Volume spike: volume > 3x average without significant price move."""
        if volume_ratio >= 3.0 and abs(snapshot.change_percent) < 2.0:
            score = min(100, 55 + (volume_ratio - 3) * 8)
            
            # Direction: assume continuation of trend
            direction = "LONG" if snapshot.change_percent > 0 else "SHORT"
            
            price = snapshot.price
            stop = price * 0.97 if direction == "LONG" else price * 1.03
            tp1 = price * 1.03 if direction == "LONG" else price * 0.97
            tp2 = price * 1.06 if direction == "LONG" else price * 0.94
            tp3 = price * 1.12 if direction == "LONG" else price * 0.88
            
            risk = abs(price - stop)
            reward = abs(tp1 - price)
            rr = reward / risk if risk > 0 else 0
            
            return Signal(
                symbol=snapshot.symbol,
                signal_type="VOLUME_SPIKE",
                direction=direction,
                score=score,
                confidence="LOW",
                entry_price=price,
                stop_loss=stop,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                volume_score=score * 0.8,
                momentum_score=score * 0.1,
                technical_score=score * 0.1,
                edge_percent=volume_ratio,
                rr_ratio=rr,
                factors={
                    "volume_ratio": volume_ratio,
                    "change_percent": snapshot.change_percent,
                }
            )
        return None
    
    def _estimate_rsi(self, change_percent: float, volume_ratio: float) -> float:
        """
        Estimate RSI from change and volume.
        This is a rough approximation — in production, calculate real RSI.
        """
        # Base RSI from change (0% change = ~50 RSI)
        base_rsi = 50 + change_percent * 3
        
        # Volume adjustment (high volume = more conviction)
        volume_adj = (volume_ratio - 1) * 5
        
        rsi = base_rsi + volume_adj
        return max(0, min(100, rsi))
    
    def calculate_technicals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators using pandas-ta.
        
        Args:
            df: DataFrame with columns [Open, High, Low, Close, Volume]
            
        Returns:
            DataFrame with added indicator columns
        """
        # RSI
        df.ta.rsi(length=self.config.rsi_period, append=True)
        
        # MACD
        df.ta.macd(
            fast=self.config.macd_fast,
            slow=self.config.macd_slow,
            signal=self.config.macd_signal,
            append=True
        )
        
        # Bollinger Bands
        df.ta.bbands(
            length=self.config.bb_period,
            std=self.config.bb_std,
            append=True
        )
        
        # EMAs
        df.ta.ema(length=self.config.ema_short, append=True)
        df.ta.ema(length=self.config.ema_medium, append=True)
        df.ta.ema(length=self.config.ema_long, append=True)
        df.ta.sma(length=self.config.sma_long, append=True)
        
        # ATR
        df.ta.atr(length=self.config.atr_period, append=True)
        
        # Volume indicators
        df.ta.obv(append=True)
        df.ta.vwap(append=True)
        
        return df
    
    def get_signal_summary(self, batch: SignalBatch) -> str:
        """Get human-readable summary of signals."""
        lines = [
            f"📊 SIGNAL BATCH — {batch.timestamp.strftime('%H:%M:%S')}",
            f"Total: {batch.total_signals} | LONG: {batch.long_signals} | SHORT: {batch.short_signals}",
            f"High Confidence: {batch.high_confidence} | Avg Score: {batch.avg_score:.1f}",
            "",
            "🔥 TOP 5 SIGNALS:",
        ]
        
        for i, signal in enumerate(batch.signals[:5], 1):
            emoji = "🟢" if signal.direction == "LONG" else "🔴"
            lines.append(
                f"{i}. {emoji} {signal.symbol} | {signal.signal_type} | "
                f"Score: {signal.score:.0f} | R:R {signal.rr_ratio:.1f}:1 | "
                f"Edge: {signal.edge_percent:.1f}%"
            )
        
        return "\n".join(lines)


# ───────────────────────────
# MAIN (for testing)
# ───────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create test snapshots
    test_snapshots = [
        StockSnapshot(symbol="AAPL", price=180.0, change_percent=3.5, volume=50_000_000, volume_avg_20d=30_000_000, volatility=0.02),
        StockSnapshot(symbol="TSLA", price=240.0, change_percent=-2.8, volume=80_000_000, volume_avg_20d=40_000_000, volatility=0.04),
        StockSnapshot(symbol="NVDA", price=890.0, change_percent=5.2, volume=60_000_000, volume_avg_20d=25_000_000, volatility=0.03),
    ]
    
    test_scan = ScanResult(
        timestamp=datetime.utcnow(),
        stocks_scanned=3,
        stocks_passing_filter=3,
        snapshots=test_snapshots,
    )
    
    gen = SignalGenerator()
    batch = gen.generate_signals(test_scan)
    
    print(gen.get_signal_summary(batch))
