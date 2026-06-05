"""
Stock Market Scanner — US Equities (S&P 500, NASDAQ-100)
Real-time scanning for momentum, volume, and volatility.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

import yfinance as yf  # For data fetching (free tier)

from stock_config import (
    US_STOCK_UNIVERSE, SCAN_INTERVAL_MINUTES,
    DEFAULT_SIGNAL_CONFIG, DEFAULT_RISK_CONFIG
)

logger = logging.getLogger(__name__)

# ───────────────────────────
# DATA MODELS
# ───────────────────────────

@dataclass
class StockSnapshot:
    """Single snapshot of a stock's current state."""
    symbol: str
    price: float
    change_percent: float
    volume: int
    volume_avg_20d: float
    volatility: float  # ATR-based
    market_cap: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Technical values (populated by signal generator)
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    rsi_14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    atr_14: Optional[float] = None

@dataclass
class ScanResult:
    """Result of a market scan."""
    timestamp: datetime
    stocks_scanned: int
    stocks_passing_filter: int
    snapshots: List[StockSnapshot] = field(default_factory=list)
    
    # Stats
    avg_volume: float = 0.0
    avg_volatility: float = 0.0
    top_movers: List[Tuple[str, float]] = field(default_factory=list)  # (symbol, change%)
    volume_leaders: List[Tuple[str, float]] = field(default_factory=list)  # (symbol, volume_ratio)

# ───────────────────────────
# MARKET SCANNER
# ───────────────────────────

class MarketScanner:
    """
    US Stock Market Scanner.
    
    Fetches real-time data for S&P 500 + NASDAQ-100 universe,
    applies filters for volume, price, and volatility.
    """
    
    def __init__(
        self,
        universe: List[str] = None,
        min_volume: int = 1_000_000,  # 1M shares minimum
        min_price: float = 5.0,  # No penny stocks
        max_price: float = 5000.0,
        min_volatility: float = 0.01,  # 1% ATR minimum
        max_volatility: float = 0.10,  # 10% ATR max (avoid chaos)
        volume_anomaly_threshold: float = 2.0,
        data_provider: str = "yfinance",
    ):
        self.universe = universe or US_STOCK_UNIVERSE
        self.min_volume = min_volume
        self.min_price = min_price
        self.max_price = max_price
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        self.volume_anomaly_threshold = volume_anomaly_threshold
        self.data_provider = data_provider
        
        self._cache: Dict[str, Dict] = {}  # Cache for recent data
        self._cache_ttl_seconds: int = 60
        
        logger.info(f"MarketScanner initialized — {len(self.universe)} stocks")
    
    async def scan(self) -> ScanResult:
        """
        Run a full market scan.
        
        Returns:
            ScanResult with all stocks passing filters.
        """
        logger.info("🔍 Starting market scan...")
        start_time = datetime.utcnow()
        
        snapshots: List[StockSnapshot] = []
        
        # Fetch data in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(self.universe), batch_size):
            batch = self.universe[i:i + batch_size]
            batch_data = await self._fetch_batch(batch)
            
            for symbol, data in batch_data.items():
                if data is None:
                    continue
                    
                snapshot = self._create_snapshot(symbol, data)
                
                if self._passes_filter(snapshot):
                    snapshots.append(snapshot)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        # Calculate stats
        scan_result = ScanResult(
            timestamp=datetime.utcnow(),
            stocks_scanned=len(self.universe),
            stocks_passing_filter=len(snapshots),
            snapshots=snapshots,
        )
        
        if snapshots:
            scan_result.avg_volume = np.mean([s.volume for s in snapshots])
            scan_result.avg_volatility = np.mean([s.volatility for s in snapshots])
            
            # Top movers
            sorted_by_change = sorted(
                snapshots, key=lambda x: abs(x.change_percent), reverse=True
            )[:10]
            scan_result.top_movers = [
                (s.symbol, s.change_percent) for s in sorted_by_change
            ]
            
            # Volume leaders
            sorted_by_volume = sorted(
                snapshots, key=lambda x: x.volume / x.volume_avg_20d if x.volume_avg_20d > 0 else 0,
                reverse=True,
            )[:10]
            scan_result.volume_leaders = [
                (s.symbol, s.volume / s.volume_avg_20d if s.volume_avg_20d > 0 else 0)
                for s in sorted_by_volume
            ]
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"✅ Scan complete — {len(snapshots)} stocks passed filter "
            f"({scan_result.stocks_scanned} scanned) in {elapsed:.1f}s"
        )
        
        return scan_result
    
    async def _fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[pd.DataFrame]]:
        """Fetch historical data for a batch of symbols."""
        result = {}
        
        for symbol in symbols:
            try:
                # Check cache first
                cache_key = f"{symbol}_{datetime.utcnow().strftime('%Y%m%d%H%M')}"
                if cache_key in self._cache:
                    result[symbol] = self._cache[cache_key]
                    continue
                
                # Fetch via yfinance (free, no API key needed)
                ticker = yf.Ticker(symbol)
                
                # Get 1h data for last 5 days (for intraday signals)
                hist_1h = ticker.history(period="5d", interval="1h")
                
                # Get daily data for 20-day averages
                hist_daily = ticker.history(period="1mo", interval="1d")
                
                if hist_1h.empty or hist_daily.empty:
                    result[symbol] = None
                    continue
                
                # Combine data
                data = {
                    "hist_1h": hist_1h,
                    "hist_daily": hist_daily,
                    "info": ticker.info,
                }
                
                self._cache[cache_key] = data
                result[symbol] = data
                
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
                result[symbol] = None
        
        return result
    
    def _create_snapshot(self, symbol: str, data: Dict) -> StockSnapshot:
        """Create a StockSnapshot from fetched data."""
        hist_1h = data["hist_1h"]
        hist_daily = data["hist_daily"]
        info = data.get("info", {})
        
        # Current price and change
        current_price = hist_1h["Close"].iloc[-1]
        prev_close = hist_daily["Close"].iloc[-2] if len(hist_daily) > 1 else hist_1h["Close"].iloc[0]
        change_percent = ((current_price - prev_close) / prev_close) * 100
        
        # Volume
        volume = int(hist_1h["Volume"].iloc[-1])
        volume_avg_20d = hist_daily["Volume"].tail(20).mean()
        
        # Volatility (ATR-based)
        atr = self._calculate_atr(hist_daily)
        volatility = atr / current_price if current_price > 0 else 0
        
        # Market cap
        market_cap = info.get("marketCap")
        
        snapshot = StockSnapshot(
            symbol=symbol,
            price=current_price,
            change_percent=change_percent,
            volume=volume,
            volume_avg_20d=volume_avg_20d,
            volatility=volatility,
            market_cap=market_cap,
        )
        
        return snapshot
    
    def _passes_filter(self, snapshot: StockSnapshot) -> bool:
        """Check if a stock passes all scan filters."""
        # Price filter
        if not (self.min_price <= snapshot.price <= self.max_price):
            return False
        
        # Volume filter
        if snapshot.volume < self.min_volume:
            return False
        
        # Volatility filter
        if not (self.min_volatility <= snapshot.volatility <= self.max_volatility):
            return False
        
        # Volume anomaly (optional — include even if not anomaly, but flag it)
        return True
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr
    
    def get_volume_anomalies(self, scan_result: ScanResult) -> List[StockSnapshot]:
        """Return stocks with volume > 2x average."""
        return [
            s for s in scan_result.snapshots
            if s.volume_avg_20d > 0 and s.volume / s.volume_avg_20d >= self.volume_anomaly_threshold
        ]
    
    def get_high_momentum(self, scan_result: ScanResult, min_change: float = 3.0) -> List[StockSnapshot]:
        """Return stocks with >3% change (up or down)."""
        return [
            s for s in scan_result.snapshots
            if abs(s.change_percent) >= min_change
        ]
    
    def get_high_volatility(self, scan_result: ScanResult, min_vol: float = 0.05) -> List[StockSnapshot]:
        """Return stocks with >5% volatility."""
        return [s for s in scan_result.snapshots if s.volatility >= min_vol]
    
    async def run_continuous(self, callback=None):
        """Run continuous scanning loop."""
        logger.info("🔄 Continuous scan started")
        
        while True:
            try:
                result = await self.scan()
                
                if callback:
                    await callback(result)
                
                # Wait until next scan
                await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(60)  # Wait 1 min on error


# ───────────────────────────
# UTILS
# ───────────────────────────

def is_market_open() -> bool:
    """Check if US market is currently open (ET)."""
    now = datetime.now()
    et_time = now  # Simplified — assume server is ET or use pytz
    
    # Market open 9:30-16:00 ET, Mon-Fri
    if et_time.weekday() >= 5:  # Weekend
        return False
    
    market_open = et_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= et_time <= market_close


# ───────────────────────────
# MAIN (for testing)
# ───────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        scanner = MarketScanner()
        result = await scanner.scan()
        
        print(f"\n📊 SCAN RESULTS")
        print(f"Stocks scanned: {result.stocks_scanned}")
        print(f"Stocks passing: {result.stocks_passing_filter}")
        print(f"\n🔥 Top Movers:")
        for symbol, change in result.top_movers[:5]:
            print(f"  {symbol}: {change:+.2f}%")
        
        print(f"\n📈 Volume Anomalies:")
        anomalies = scanner.get_volume_anomalies(result)
        for s in anomalies[:5]:
            ratio = s.volume / s.volume_avg_20d
            print(f"  {s.symbol}: {ratio:.1f}x avg volume")
    
    asyncio.run(test())
