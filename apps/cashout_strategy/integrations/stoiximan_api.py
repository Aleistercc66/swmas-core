#!/usr/bin/env python3
"""
Stoiximan API Integration
========================
Real-time odds data from Stoiximan Greece

Stoiximan uses a public API that can be accessed without authentication
for viewing odds. This module provides structured access to their data.

Note: This is for informational purposes. Respect their ToS.
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger("StoiximanAPI")


@dataclass
class StoiximanOdds:
    """Stoiximan odds data structure"""
    match_id: str
    match_name: str
    league: str
    kickoff: datetime
    
    # 1X2 odds
    home_odds: float
    draw_odds: Optional[float]
    away_odds: float
    
    # Totals
    over_25: Optional[float] = None
    under_25: Optional[float] = None
    
    # Both Teams to Score
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None
    
    # Cashout availability
    cashout_available: bool = True
    
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class StoiximanAPI:
    """
    Stoiximan API Client
    ===================
    Access Stoiximan public odds API
    """
    
    BASE_URL = "https://www.stoiximan.gr/api"
    WEB_URL = "https://www.stoiximan.gr"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._odds_cache: Dict[str, StoiximanOdds] = {}
        self._last_request_time = None
        self._rate_limit_delay = 2.0  # Be respectful with requests
        
    async def _init_session(self):
        """Initialize session with realistic browser headers"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.stoiximan.gr/",
            "Origin": "https://www.stoiximan.gr",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        self.session = aiohttp.ClientSession(headers=headers)
    
    async def _rate_limited_request(self, endpoint: str, **kwargs) -> dict:
        """Make rate-limited request"""
        if self.session is None:
            await self._init_session()
        
        # Rate limiting
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - elapsed)
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with self.session.get(url, **kwargs, timeout=aiohttp.ClientTimeout(total=10)) as response:
                self._last_request_time = datetime.now()
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    logger.warning("Stoiximan API: Access denied (403)")
                    return {"error": "access_denied"}
                elif response.status == 429:
                    logger.warning("Stoiximan API: Rate limited")
                    await asyncio.sleep(10)
                    return await self._rate_limited_request(endpoint, **kwargs)
                else:
                    logger.error(f"Stoiximan API error: {response.status}")
                    return {"error": f"http_{response.status}"}
                    
        except aiohttp.ClientError as e:
            logger.error(f"Stoiximan request failed: {e}")
            return {"error": str(e)}
        except asyncio.TimeoutError:
            logger.error("Stoiximan request timed out")
            return {"error": "timeout"}
    
    async def get_sports(self) -> List[dict]:
        """Get available sports"""
        data = await self._rate_limited_request("sports")
        return data.get("sports", [])
    
    async def get_leagues(self, sport_id: str = "1") -> List[dict]:
        """Get leagues for a sport (default: Soccer = 1)"""
        data = await self._rate_limited_request(f"leagues?sportId={sport_id}")
        return data.get("leagues", [])
    
    async def get_matches(self, league_ids: List[str] = None, 
                          sport_id: str = "1",
                          hours_ahead: int = 24) -> List[dict]:
        """
        Get upcoming matches
        
        Args:
            league_ids: Filter by specific leagues
            sport_id: Sport ID (1 = Soccer)
            hours_ahead: How many hours ahead to look
        """
        now = datetime.now()
        end_time = now + timedelta(hours=hours_ahead)
        
        params = {
            "sportId": sport_id,
            "from": now.isoformat(),
            "to": end_time.isoformat()
        }
        
        if league_ids:
            params["leagueIds"] = ",".join(league_ids)
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        data = await self._rate_limited_request(f"matches?{query}")
        return data.get("matches", [])
    
    async def get_match_odds(self, match_id: str) -> Optional[StoiximanOdds]:
        """
        Get detailed odds for a specific match
        """
        data = await self._rate_limited_request(f"matches/{match_id}/odds")
        
        if "error" in data:
            return None
        
        match_info = data.get("match", {})
        markets = data.get("markets", [])
        
        # Extract 1X2 odds
        home_odds = 0.0
        draw_odds = None
        away_odds = 0.0
        
        for market in markets:
            if market.get("name") == "1X2" or market.get("id") == "1":
                selections = market.get("selections", [])
                for sel in selections:
                    name = sel.get("name", "").lower()
                    if "1" in name or "home" in name:
                        home_odds = sel.get("odds", 0)
                    elif "x" in name or "draw" in name:
                        draw_odds = sel.get("odds")
                    elif "2" in name or "away" in name:
                        away_odds = sel.get("odds", 0)
        
        # Extract totals
        over_25 = None
        under_25 = None
        
        for market in markets:
            if "over/under" in market.get("name", "").lower() or "totals" in market.get("name", "").lower():
                selections = market.get("selections", [])
                for sel in selections:
                    name = sel.get("name", "").lower()
                    if "over" in name and "2.5" in name:
                        over_25 = sel.get("odds")
                    elif "under" in name and "2.5" in name:
                        under_25 = sel.get("odds")
        
        return StoiximanOdds(
            match_id=match_id,
            match_name=f"{match_info.get('home', '')} vs {match_info.get('away', '')}",
            league=match_info.get("league", {}).get("name", ""),
            kickoff=datetime.fromisoformat(match_info.get("startTime", datetime.now().isoformat())),
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            over_25=over_25,
            under_25=under_25,
            cashout_available=match_info.get("cashout", True)
        )
    
    async def get_all_odds(self, league_ids: List[str] = None) -> Dict[str, StoiximanOdds]:
        """
        Get all current odds for specified leagues
        """
        matches = await self.get_matches(league_ids=league_ids)
        odds_map = {}
        
        for match in matches:
            match_id = str(match.get("id", ""))
            odds = await self.get_match_odds(match_id)
            if odds:
                odds_map[match_id] = odds
                self._odds_cache[match_id] = odds
        
        return odds_map
    
    def is_golden_hour(self, kickoff: datetime) -> bool:
        """Check if within Golden Hour (60-90 min before kickoff)"""
        now = datetime.now()
        if kickoff.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=kickoff.tzinfo)
        elif kickoff.tzinfo is None and now.tzinfo is not None:
            kickoff = kickoff.replace(tzinfo=now.tzinfo)
        
        minutes = (kickoff - now).total_seconds() / 60
        return 60 <= minutes <= 90
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None


# Demo mode
class StoiximanDemoAPI(StoiximanAPI):
    """Demo Stoiximan API - Returns simulated data"""
    
    def __init__(self):
        super().__init__()
    
    async def _rate_limited_request(self, endpoint: str, **kwargs) -> dict:
        """Return demo data"""
        await asyncio.sleep(0.2)
        
        if "matches" in endpoint and "odds" not in endpoint:
            return self._demo_matches()
        elif "matches/" in endpoint and "odds" in endpoint:
            match_id = endpoint.split("/")[-2]
            return self._demo_match_odds(match_id)
        else:
            return {"sports": [{"id": "1", "name": "Soccer"}]}
    
    def _demo_matches(self) -> dict:
        """Generate demo matches"""
        now = datetime.now()
        matches = [
            {
                "id": "1001",
                "home": "Olympiacos",
                "away": "PAOK",
                "league": {"name": "Super League Greece", "id": "101"},
                "startTime": (now + timedelta(hours=1, minutes=30)).isoformat(),
                "cashout": True
            },
            {
                "id": "1002",
                "home": "AEK Athens",
                "away": "Panathinaikos",
                "league": {"name": "Super League Greece", "id": "101"},
                "startTime": (now + timedelta(hours=2, minutes=15)).isoformat(),
                "cashout": True
            },
            {
                "id": "1003",
                "home": "Arsenal",
                "away": "Chelsea",
                "league": {"name": "Premier League", "id": "201"},
                "startTime": (now + timedelta(hours=3)).isoformat(),
                "cashout": True
            }
        ]
        return {"matches": matches}
    
    def _demo_match_odds(self, match_id: str) -> dict:
        """Generate demo odds - Stoiximan has HIGHER odds than Pinnacle (value opportunity)"""
        odds_map = {
            "1001": {  # Olympiacos vs PAOK - Pinnacle dropped to 2.10, Stoiximan still at 2.25
                "home": 2.25, "draw": 3.30, "away": 3.30,
                "over_25": 1.95, "under_25": 1.85
            },
            "1002": {  # AEK vs Panathinaikos - Pinnacle dropped to 4.20, Stoiximan still at 5.50
                "home": 1.80, "draw": 3.40, "away": 5.50,
                "over_25": 2.10, "under_25": 1.70
            },
            "1003": {  # Arsenal vs Chelsea - Pinnacle dropped to 1.95, Stoiximan still at 2.05
                "home": 2.05, "draw": 3.70, "away": 3.40,
                "over_25": 1.95, "under_25": 1.85
            }
        }
        
        odds = odds_map.get(match_id, {})
        match_data = {
            "1001": {"home": "Olympiacos", "away": "PAOK", "league": "Super League Greece"},
            "1002": {"home": "AEK Athens", "away": "Panathinaikos", "league": "Super League Greece"},
            "1003": {"home": "Arsenal", "away": "Chelsea", "league": "Premier League"}
        }
        
        m = match_data.get(match_id, {})
        now = datetime.now()
        
        return {
            "match": {
                "id": match_id,
                "home": m.get("home", ""),
                "away": m.get("away", ""),
                "league": {"name": m.get("league", "")},
                "startTime": (now + timedelta(hours=int(match_id) - 1000)).isoformat(),
                "cashout": True
            },
            "markets": [
                {
                    "name": "1X2",
                    "selections": [
                        {"name": "1", "odds": odds.get("home", 0)},
                        {"name": "X", "odds": odds.get("draw", 0)},
                        {"name": "2", "odds": odds.get("away", 0)}
                    ]
                },
                {
                    "name": "Over/Under 2.5",
                    "selections": [
                        {"name": "Over 2.5", "odds": odds.get("over_25", 0)},
                        {"name": "Under 2.5", "odds": odds.get("under_25", 0)}
                    ]
                }
            ]
        }


if __name__ == "__main__":
    async def test():
        api = StoiximanDemoAPI()
        
        print("🔍 Testing Stoiximan Demo API...")
        
        odds = await api.get_all_odds()
        print(f"\n📊 Found {len(odds)} matches with odds:")
        
        for match_id, match_odds in odds.items():
            print(f"\n⚽ {match_odds.match_name}")
            print(f"   League: {match_odds.league}")
            print(f"   1: {match_odds.home_odds} | X: {match_odds.draw_odds} | 2: {match_odds.away_odds}")
            print(f"   Cashout: {'✅' if match_odds.cashout_available else '❌'}")
        
        await api.close()
    
    asyncio.run(test())
