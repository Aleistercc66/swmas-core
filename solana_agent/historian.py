#!/usr/bin/env python3
"""
Solana Historical Learning Engine
Μαθαίνει από το παρελθόν του Solana ecosystem.
Αναλύει: moon missions, rug pulls, seasonality, cycles, correlations.
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics


@dataclass
class HistoricalTokenProfile:
    """Πλήρες ιστορικό προφίλ ενός token."""
    address: str
    symbol: str
    launch_date: Optional[float] = None
    max_price: float = 0.0
    max_price_date: Optional[float] = None
    min_price_after_max: float = 0.0
    drawdown_from_max: float = 0.0
    
    # Lifecycle phases
    phases: List[Dict] = field(default_factory=list)
    
    # Performance metrics
    first_week_return: float = 0.0
    first_month_return: float = 0.0
    first_3month_return: float = 0.0
    max_return_from_launch: float = 0.0
    
    # Market context at launch
    sol_price_at_launch: float = 0.0
    market_sentiment_at_launch: str = "neutral"  # bear/bull/neutral
    
    # Category & tags
    category: str = "unknown"  # meme/defi/utility/gaming/nft
    tags: List[str] = field(default_factory=list)
    
    # Success indicators
    is_successful: bool = False  # >10x from launch
    is_moon_mission: bool = False  # >100x
    is_rug_pull: bool = False  # -90% from ATH quickly
    survived_1year: bool = False
    
    # What happened
    catalysts: List[str] = field(default_factory=list)  # exchange_listing, influencer_tweet, partnership
    death_reasons: List[str] = field(default_factory=list)  # dev_sold, liquidity_removed, hack
    
    # Pattern data
    volume_pattern: Dict[str, Any] = field(default_factory=dict)
    holder_pattern: Dict[str, Any] = field(default_factory=dict)
    social_pattern: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class MarketCycle:
    """Bear/Bull cycle στο Solana ecosystem."""
    start_date: float
    end_date: Optional[float] = None
    cycle_type: str = "bull"  # bull/bear/sideways
    sol_price_start: float = 0.0
    sol_price_end: Optional[float] = None
    sol_price_peak: float = 0.0
    sol_price_bottom: float = 0.0
    
    # What tokens did well
    top_performers: List[Dict] = field(default_factory=list)
    worst_performers: List[Dict] = field(default_factory=list)
    
    # Characteristics
    avg_meme_return: float = 0.0
    avg_defi_return: float = 0.0
    total_launches: int = 0
    rug_pull_rate: float = 0.0
    
    # Duration
    duration_days: float = 0.0
    
    def is_active(self) -> bool:
        return self.end_date is None


class SolanaHistorian:
    """
    Ιστορικός αναλυτής του Solana ecosystem.
    Μαθαίνει από το παρελθόν για να προβλέπει το μέλλον.
    """
    
    def __init__(self, storage_path: str = "solana_history.json"):
        self.storage_path = storage_path
        self.token_profiles: Dict[str, HistoricalTokenProfile] = {}
        self.market_cycles: List[MarketCycle] = []
        self.seasonal_patterns: Dict[str, Any] = {}
        self.category_performance: Dict[str, List[float]] = {
            "meme": [],
            "defi": [],
            "utility": [],
            "gaming": [],
            "nft": [],
        }
        
        # Famous historical patterns
        self.known_moon_missions: List[str] = [
            "BONK", "WIF", "BOME", "POPCAT", "SLERF", 
            "MYRO", "WEN", "SNOW", "SILLY", "NOS",
        ]
        
        self.known_rug_pulls: List[str] = [
            # Known rug patterns
        ]
        
        # Launch pad success rates
        self.launchpad_stats: Dict[str, Dict] = {
            "pump_fun": {"total": 0, "successes": 0, "avg_return": 0.0},
            "raydium": {"total": 0, "successes": 0, "avg_return": 0.0},
            "orca": {"total": 0, "successes": 0, "avg_return": 0.0},
        }
        
        # Time-based patterns
        self.hourly_success_rates: List[float] = [0.0] * 24
        self.daily_success_rates: List[float] = [0.0] * 7  # Monday=0
        self.monthly_success_rates: List[float] = [0.0] * 12
        
        self.load_history()
    
    def load_history(self):
        """Φόρτωση ιστορικών δεδομένων."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                
                for addr, profile_data in data.get("profiles", {}).items():
                    self.token_profiles[addr] = HistoricalTokenProfile(**profile_data)
                
                self.market_cycles = [MarketCycle(**c) for c in data.get("cycles", [])]
                self.seasonal_patterns = data.get("seasonal", {})
                self.category_performance = data.get("category_perf", self.category_performance)
                self.launchpad_stats = data.get("launchpad_stats", self.launchpad_stats)
                
                print(f"📜 Loaded history: {len(self.token_profiles)} profiles, {len(self.market_cycles)} cycles")
        except FileNotFoundError:
            print("📜 New historian created — will build from data")
    
    def save_history(self):
        """Αποθήκευση ιστορικών δεδομένων."""
        data = {
            "profiles": {
                addr: self._profile_to_dict(p) 
                for addr, p in self.token_profiles.items()
            },
            "cycles": [self._cycle_to_dict(c) for c in self.market_cycles],
            "seasonal": self.seasonal_patterns,
            "category_perf": self.category_performance,
            "launchpad_stats": self.launchpad_stats,
            "saved_at": time.time(),
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _profile_to_dict(self, p: HistoricalTokenProfile) -> Dict:
        return {
            "address": p.address,
            "symbol": p.symbol,
            "launch_date": p.launch_date,
            "max_price": p.max_price,
            "max_price_date": p.max_price_date,
            "min_price_after_max": p.min_price_after_max,
            "drawdown_from_max": p.drawdown_from_max,
            "phases": p.phases,
            "first_week_return": p.first_week_return,
            "first_month_return": p.first_month_return,
            "first_3month_return": p.first_3month_return,
            "max_return_from_launch": p.max_return_from_launch,
            "sol_price_at_launch": p.sol_price_at_launch,
            "market_sentiment_at_launch": p.market_sentiment_at_launch,
            "category": p.category,
            "tags": p.tags,
            "is_successful": p.is_successful,
            "is_moon_mission": p.is_moon_mission,
            "is_rug_pull": p.is_rug_pull,
            "survived_1year": p.survived_1year,
            "catalysts": p.catalysts,
            "death_reasons": p.death_reasons,
            "volume_pattern": p.volume_pattern,
            "holder_pattern": p.holder_pattern,
            "social_pattern": p.social_pattern,
        }
    
    def _cycle_to_dict(self, c: MarketCycle) -> Dict:
        return {
            "start_date": c.start_date,
            "end_date": c.end_date,
            "cycle_type": c.cycle_type,
            "sol_price_start": c.sol_price_start,
            "sol_price_end": c.sol_price_end,
            "sol_price_peak": c.sol_price_peak,
            "sol_price_bottom": c.sol_price_bottom,
            "top_performers": c.top_performers,
            "worst_performers": c.worst_performers,
            "avg_meme_return": c.avg_meme_return,
            "avg_defi_return": c.avg_defi_return,
            "total_launches": c.total_launches,
            "rug_pull_rate": c.rug_pull_rate,
            "duration_days": c.duration_days,
        }
    
    def analyze_token_lifecycle(self, address: str, symbol: str, 
                                price_history: List[Dict],
                                launch_price: float,
                                current_price: float,
                                category: str = "unknown") -> HistoricalTokenProfile:
        """Ανάλυση πλήρους lifecycle ενός token."""
        
        profile = HistoricalTokenProfile(
            address=address,
            symbol=symbol,
            category=category,
        )
        
        if not price_history:
            return profile
        
        # Find max price and when
        max_price_entry = max(price_history, key=lambda x: x.get("price", 0))
        profile.max_price = max_price_entry.get("price", 0)
        profile.max_price_date = max_price_entry.get("timestamp", time.time())
        
        # Find launch date
        profile.launch_date = price_history[0].get("timestamp", time.time())
        
        # Calculate returns
        if launch_price > 0:
            profile.max_return_from_launch = ((profile.max_price - launch_price) / launch_price) * 100
            profile.first_week_return = self._calc_return_in_period(price_history, 7, launch_price)
            profile.first_month_return = self._calc_return_in_period(price_history, 30, launch_price)
            profile.first_3month_return = self._calc_return_in_period(price_history, 90, launch_price)
        
        # Calculate drawdown
        if profile.max_price > 0:
            # Find lowest price after ATH
            after_ath = [p for p in price_history if p.get("timestamp", 0) >= profile.max_price_date]
            if after_ath:
                min_after = min(after_ath, key=lambda x: x.get("price", float('inf')))
                profile.min_price_after_max = min_after.get("price", 0)
                profile.drawdown_from_max = ((profile.min_price_after_max - profile.max_price) / profile.max_price) * 100
        
        # Classify
        profile.is_successful = profile.max_return_from_launch >= 1000  # 10x
        profile.is_moon_mission = profile.max_return_from_launch >= 10000  # 100x
        profile.is_rug_pull = profile.drawdown_from_max <= -90 and profile.max_return_from_launch < 500
        
        # Check survival
        if profile.launch_date:
            age_days = (time.time() - profile.launch_date) / 86400
            profile.survived_1year = age_days >= 365
        
        # Analyze phases
        profile.phases = self._identify_phases(price_history)
        
        # Volume pattern
        profile.volume_pattern = self._analyze_volume_pattern(price_history)
        
        # Store
        self.token_profiles[address] = profile
        
        # Update category performance
        if category in self.category_performance:
            self.category_performance[category].append(profile.max_return_from_launch)
        
        return profile
    
    def _calc_return_in_period(self, price_history: List[Dict], days: int, launch_price: float) -> float:
        """Υπολογισμός return σε συγκεκριμένη περίοδο από το launch."""
        if not price_history or launch_price <= 0:
            return 0.0
        
        launch_time = price_history[0].get("timestamp", time.time())
        cutoff = launch_time + (days * 86400)
        
        period_prices = [p for p in price_history if p.get("timestamp", 0) <= cutoff]
        if period_prices:
            max_in_period = max(p.get("price", 0) for p in period_prices)
            return ((max_in_period - launch_price) / launch_price) * 100
        
        return 0.0
    
    def _identify_phases(self, price_history: List[Dict]) -> List[Dict]:
        """Αναγνώριση phases (launch, pump, consolidation, dump, recovery)."""
        if len(price_history) < 5:
            return []
        
        phases = []
        prices = [p.get("price", 0) for p in price_history]
        
        # Simple phase detection based on price action
        for i in range(1, len(prices)):
            prev = prices[i-1]
            curr = prices[i]
            
            if prev > 0:
                change = ((curr - prev) / prev) * 100
                
                if change > 50:
                    phases.append({
                        "type": "pump",
                        "timestamp": price_history[i].get("timestamp", 0),
                        "change": change,
                    })
                elif change < -30:
                    phases.append({
                        "type": "dump",
                        "timestamp": price_history[i].get("timestamp", 0),
                        "change": change,
                    })
                elif abs(change) < 10:
                    phases.append({
                        "type": "consolidation",
                        "timestamp": price_history[i].get("timestamp", 0),
                        "change": change,
                    })
        
        return phases
    
    def _analyze_volume_pattern(self, price_history: List[Dict]) -> Dict:
        """Ανάλυση volume pattern."""
        volumes = [p.get("volume_24h", 0) for p in price_history if p.get("volume_24h", 0) > 0]
        
        if not volumes:
            return {}
        
        return {
            "avg_volume": statistics.mean(volumes),
            "max_volume": max(volumes),
            "volume_trend": "increasing" if volumes[-1] > statistics.mean(volumes[:len(volumes)//2]) else "decreasing",
            "volume_spikes": len([v for v in volumes if v > statistics.mean(volumes) * 3]),
        }
    
    def identify_current_cycle(self, sol_price_history: List[Dict]) -> MarketCycle:
        """Αναγνώριση current market cycle."""
        if not sol_price_history:
            # Create default cycle
            return MarketCycle(
                start_date=time.time() - 86400,
                cycle_type="unknown",
            )
        
        current_price = sol_price_history[-1].get("price", 0)
        
        # Find cycle characteristics
        prices = [p.get("price", 0) for p in sol_price_history]
        
        # Determine cycle type
        if len(prices) >= 30:
            recent_7d_avg = statistics.mean(prices[-7:]) if len(prices) >= 7 else current_price
            prev_7d_avg = statistics.mean(prices[-14:-7]) if len(prices) >= 14 else current_price
            
            if recent_7d_avg > prev_7d_avg * 1.1:
                cycle_type = "bull"
            elif recent_7d_avg < prev_7d_avg * 0.9:
                cycle_type = "bear"
            else:
                cycle_type = "sideways"
        else:
            cycle_type = "unknown"
        
        # Find or create cycle
        active_cycle = None
        for cycle in self.market_cycles:
            if cycle.is_active():
                active_cycle = cycle
                break
        
        if active_cycle is None:
            active_cycle = MarketCycle(
                start_date=time.time() - (len(sol_price_history) * 86400),
                cycle_type=cycle_type,
                sol_price_start=prices[0] if prices else current_price,
                sol_price_peak=max(prices) if prices else current_price,
                sol_price_bottom=min(prices) if prices else current_price,
            )
            self.market_cycles.append(active_cycle)
        
        # Update cycle
        active_cycle.sol_price_peak = max(active_cycle.sol_price_peak, max(prices) if prices else current_price)
        active_cycle.sol_price_bottom = min(active_cycle.sol_price_bottom, min(prices) if prices else current_price)
        
        return active_cycle
    
    def get_moon_mission_patterns(self) -> List[Dict]:
        """Εξαγωγή patterns από επιτυχημένα moon missions."""
        patterns = []
        
        for addr, profile in self.token_profiles.items():
            if profile.is_moon_mission:
                patterns.append({
                    "symbol": profile.symbol,
                    "category": profile.category,
                    "max_return": profile.max_return_from_launch,
                    "first_week": profile.first_week_return,
                    "first_month": profile.first_month_return,
                    "phases": profile.phases[:5],  # First 5 phases
                    "volume_pattern": profile.volume_pattern,
                    "catalysts": profile.catalysts,
                    "launchpad": self._detect_launchpad(profile),
                    "time_to_peak_days": (profile.max_price_date - profile.launch_date) / 86400 if profile.max_price_date and profile.launch_date else 0,
                })
        
        # Sort by max return
        patterns.sort(key=lambda x: x["max_return"], reverse=True)
        return patterns
    
    def _detect_launchpad(self, profile: HistoricalTokenProfile) -> str:
        """Detect which launchpad was used (based on patterns)."""
        # Simplified detection
        return "unknown"
    
    def get_success_prediction_features(self, token_data: Dict) -> Dict:
        """Υπολογισμός features για prediction αν ένα token θα πετύχει."""
        features = {
            "similar_successful_count": 0,
            "avg_similar_return": 0.0,
            "category_success_rate": 0.0,
            "launchpad_success_rate": 0.0,
            "time_of_day_score": 0.0,
            "day_of_week_score": 0.0,
            "market_cycle_score": 0.0,
            "volume_vs_history_avg": 0.0,
        }
        
        # Category success rate
        category = token_data.get("category", "unknown")
        if category in self.category_performance and self.category_performance[category]:
            returns = self.category_performance[category]
            features["category_success_rate"] = len([r for r in returns if r > 1000]) / len(returns)
            features["avg_similar_return"] = statistics.mean(returns)
        
        # Time-based patterns
        launch_time = token_data.get("launch_timestamp", time.time())
        dt = datetime.fromtimestamp(launch_time)
        
        hour = dt.hour
        day = dt.weekday()
        
        if self.hourly_success_rates[hour] > 0:
            features["time_of_day_score"] = self.hourly_success_rates[hour]
        if self.daily_success_rates[day] > 0:
            features["day_of_week_score"] = self.daily_success_rates[day]
        
        # Market cycle
        active_cycle = None
        for cycle in self.market_cycles:
            if cycle.is_active():
                active_cycle = cycle
                break
        
        if active_cycle:
            if active_cycle.cycle_type == "bull":
                features["market_cycle_score"] = 0.8
            elif active_cycle.cycle_type == "bear":
                features["market_cycle_score"] = 0.2
            else:
                features["market_cycle_score"] = 0.5
        
        return features
    
    def calculate_moon_probability(self, token_data: Dict) -> float:
        """Υπολογισμός πιθανότητας για moon mission (>10x)."""
        features = self.get_success_prediction_features(token_data)
        
        # Weighted scoring
        score = 0.0
        
        # Category matters a lot for memes
        if features["category_success_rate"] > 0:
            score += features["category_success_rate"] * 30  # Up to 30 points
        
        # Market cycle
        score += features["market_cycle_score"] * 25
        
        # Time patterns (less important)
        score += features["time_of_day_score"] * 10
        score += features["day_of_week_score"] * 10
        
        # Historical similarity
        if features["avg_similar_return"] > 1000:
            score += 15
        elif features["avg_similar_return"] > 500:
            score += 10
        
        # Volume anomaly
        if features["volume_vs_history_avg"] > 3:
            score += 10
        
        return max(0, min(100, score))
    
    def get_optimal_entry_timing(self, token_profile: HistoricalTokenProfile) -> Dict:
        """Βέλτιστο timing για entry βάσει ιστορικών patterns."""
        
        # Analyze what worked for similar tokens
        similar_tokens = [
            p for p in self.token_profiles.values()
            if p.category == token_profile.category and p.is_successful
        ]
        
        if not similar_tokens:
            return {
                "strategy": "early_entry",
                "reason": "No historical data for this category",
                "confidence": 0.5,
            }
        
        # Calculate average time to peak
        times_to_peak = []
        for p in similar_tokens:
            if p.max_price_date and p.launch_date:
                ttp = (p.max_price_date - p.launch_date) / 3600  # hours
                times_to_peak.append(ttp)
        
        if times_to_peak:
            avg_ttp = statistics.mean(times_to_peak)
            median_ttp = statistics.median(times_to_peak)
            
            return {
                "strategy": "timed_entry",
                "avg_hours_to_peak": avg_ttp,
                "median_hours_to_peak": median_ttp,
                "early_entry_window": f"0-{median_ttp * 0.3:.0f}h",
                "optimal_entry_window": f"{median_ttp * 0.3:.0f}-{median_ttp * 0.7:.0f}h",
                "late_entry_window": f"{median_ttp * 0.7:.0f}-{median_ttp * 1.5:.0f}h",
                "confidence": 0.7,
            }
        
        return {
            "strategy": "early_entry",
            "reason": "Insufficient timing data",
            "confidence": 0.3,
        }
    
    def get_lessons_from_failures(self) -> List[Dict]:
        """Μαθήματα από failed tokens."""
        lessons = []
        
        rug_pulls = [p for p in self.token_profiles.values() if p.is_rug_pull]
        
        if rug_pulls:
            # Analyze common patterns
            avg_time_to_rug = []
            for p in rug_pulls:
                if p.max_price_date and p.launch_date:
                    time_to_rug = (p.max_price_date - p.launch_date) / 3600
                    avg_time_to_rug.append(time_to_rug)
            
            if avg_time_to_rug:
                lessons.append({
                    "type": "rug_pull_timing",
                    "lesson": f"Rug pulls typically happen within {statistics.median(avg_time_to_rug):.0f}h of launch",
                    "action": "Take profits quickly, don't hold past first pump",
                })
        
        # Analyze death patterns
        dead_tokens = [p for p in self.token_profiles.values() 
                      if p.drawdown_from_max < -95]
        
        if dead_tokens:
            lessons.append({
                "type": "survival",
                "lesson": f"{len(dead_tokens)} tokens died completely (>95% drawdown)",
                "action": "Always use stop losses, never hold declining tokens",
            })
        
        return lessons
    
    def get_seasonal_insights(self) -> Dict:
        """Seasonal patterns (which months/days are best)."""
        return {
            "best_hours": sorted(range(24), key=lambda h: self.hourly_success_rates[h], reverse=True)[:5],
            "worst_hours": sorted(range(24), key=lambda h: self.hourly_success_rates[h])[:5],
            "best_days": sorted(range(7), key=lambda d: self.daily_success_rates[d], reverse=True)[:3],
            "worst_days": sorted(range(7), key=lambda d: self.daily_success_rates[d])[:3],
            "insights": self.seasonal_patterns.get("insights", []),
        }
    
    def generate_full_report(self) -> Dict:
        """Generate comprehensive historical analysis report."""
        
        total_profiles = len(self.token_profiles)
        successful = len([p for p in self.token_profiles.values() if p.is_successful])
        moon_missions = len([p for p in self.token_profiles.values() if p.is_moon_mission])
        rug_pulls = len([p for p in self.token_profiles.values() if p.is_rug_pull])
        
        report = {
            "summary": {
                "total_tokens_analyzed": total_profiles,
                "successful_10x_plus": successful,
                "moon_missions_100x_plus": moon_missions,
                "rug_pulls": rug_pulls,
                "success_rate": (successful / total_profiles * 100) if total_profiles > 0 else 0,
                "rug_rate": (rug_pulls / total_profiles * 100) if total_profiles > 0 else 0,
            },
            "moon_mission_patterns": self.get_moon_mission_patterns()[:10],
            "category_performance": {
                cat: {
                    "count": len(returns),
                    "avg_return": statistics.mean(returns) if returns else 0,
                    "max_return": max(returns) if returns else 0,
                    "success_rate": len([r for r in returns if r > 1000]) / len(returns) if returns else 0,
                }
                for cat, returns in self.category_performance.items()
            },
            "lessons_from_failures": self.get_lessons_from_failures(),
            "seasonal_insights": self.get_seasonal_insights(),
            "current_cycle": self._cycle_to_dict(self.market_cycles[-1]) if self.market_cycles else None,
            "optimal_strategies": self._derive_optimal_strategies(),
        }
        
        return report
    
    def assess_historical_setup(self, token: Dict) -> float:
        """
        Αξιολογεί ένα token setup με βάση ιστορικά patterns.
        Επιστρέφει score 0-100 — υψηλότερο = πιο ιστορικά ελκυστικό.
        """
        score = 50.0  # Baseline
        
        changes = token.get("priceChange", {})
        h1 = changes.get("h1", 0)
        h6 = changes.get("h6", 0)
        h24 = changes.get("h24", 0)
        
        volume = token.get("volume", {}).get("h24", 0)
        liquidity = token.get("liquidity", {}).get("usd", 0)
        symbol = token.get("baseToken", {}).get("symbol", "").lower()
        
        # Category detection
        meme_keywords = ["dog", "cat", "pepe", "frog", "wojak", "bonk", "shib", "elon", "moon", "rocket"]
        is_meme = any(k in symbol for k in meme_keywords)
        
        # Meme category bonus if historically profitable
        if is_meme:
            meme_returns = self.category_performance.get("meme", [])
            if meme_returns:
                avg_meme = statistics.mean(meme_returns)
                if avg_meme > 100:
                    score += 20
                elif avg_meme > 50:
                    score += 10
            else:
                score += 5  # Slight meme premium without data
        
        # Momentum pattern matching
        if h1 > 10 and h6 > 20:
            score += 15  # Strong short-term momentum
        elif h1 > 5 and h6 > 10:
            score += 10
        elif h1 < -5:
            score -= 10  # Negative momentum penalty
        
        # Volume pattern
        if volume > 100000:
            score += 10
        elif volume > 50000:
            score += 5
        elif volume < 5000:
            score -= 10
        
        # Liquidity sanity
        if liquidity > 200000:
            score += 5
        elif liquidity < 20000:
            score -= 15
        
        # 24h performance context
        if h24 > 50:
            score += 5  # Already moving but maybe not too late
        elif h24 > 200:
            score -= 10  # Too extended, risk of pullback
        
        # Historical cycle awareness
        successful_patterns = self.moon_mission_patterns if hasattr(self, 'moon_mission_patterns') else []
        if successful_patterns:
            score += 5  # Some historical learning exists
        
        return max(0, min(100, score))
    
    def _derive_optimal_strategies(self) -> List[Dict]:
        """Derive optimal strategies from historical data."""
        strategies = []
        
        # Strategy 1: Early meme entry
        meme_returns = self.category_performance.get("meme", [])
        if meme_returns and len([r for r in meme_returns if r > 1000]) / len(meme_returns) > 0.1:
            strategies.append({
                "name": "Early Meme Entry",
                "description": "Enter meme tokens within first 6 hours of launch",
                "expected_return": statistics.mean([r for r in meme_returns if r > 1000]) if any(r > 1000 for r in meme_returns) else 0,
                "win_rate": len([r for r in meme_returns if r > 1000]) / len(meme_returns) if meme_returns else 0,
                "risk_level": "high",
                "time_frame": "6-48 hours",
            })
        
        # Strategy 2: Momentum continuation
        strategies.append({
            "name": "Momentum Continuation",
            "description": "Enter tokens with strong 1h + 6h momentum",
            "expected_return": 50,
            "win_rate": 0.4,
            "risk_level": "medium",
            "time_frame": "2-24 hours",
        })
        
        # Strategy 3: Volume breakout
        strategies.append({
            "name": "Volume Breakout",
            "description": "Enter when volume spikes >3x average",
            "expected_return": 30,
            "win_rate": 0.35,
            "risk_level": "medium",
            "time_frame": "1-12 hours",
        })
        
        return strategies


if __name__ == "__main__":
    historian = SolanaHistorian()
    
    # Generate report
    report = historian.generate_full_report()
    print(json.dumps(report, indent=2))
    
    # Save
    historian.save_history()
    print("\n📜 History saved!")
