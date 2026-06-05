#!/usr/bin/env python3
"""
Pinnacle API Integration
========================
Real-time odds data from Pinnacle (sharp bookmaker)

Requires: Pinnacle API key (available at https://www.pinnacle.com/en/api)
Free tier: 100 requests/day
Paid tier: 10,000+ requests/day

Documentation: https://github.com/pinnacleapi/pinnacleapi-documentation
"""

import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("PinnacleAPI")


@dataclass
class PinnacleMatch:
    """Pinnacle match data structure"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    sport: str
    
    # Odds
    moneyline_home: float
    moneyline_away: float
    moneyline_draw: Optional[float]
    
    # Spreads / Totals
    spread_home: Optional[float] = None
    spread_away: Optional[float] = None
    total_over: Optional[float] = None
    total_under: Optional[float] = None
    total_line: Optional[float] = None
    
    # Metadata
    last_updated: datetime = None
    is_live: bool = False
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class PinnacleAPI:
    """
    Pinnacle API Client
    ===================
    Authenticated API client for Pinnacle Sports API v3
    """
    
    BASE_URL = "https://api.pinnacle.com/v3"
    
    def __init__(self, api_key: str = None, username: str = None, password: str = None):
        self.api_key = api_key or os.getenv("PINNACLE_API_KEY")
        self.username = username or os.getenv("PINNACLE_USERNAME")
        self.password = password or os.getenv("PINNACLE_PASSWORD")
        self.session: Optional[aiohttp.ClientSession] = None
        self._odds_cache: Dict[str, dict] = {}
        self._last_request_time = None
        self._rate_limit_delay = 1.0  # seconds between requests
        
    async def _init_session(self):
        """Initialize aiohttp session with auth headers"""
        headers = {
            "Authorization": f"Basic {self._encode_auth()}",
            "Content-Type": "application/json",
            "User-Agent": "CashoutPro/1.0"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        
    def _encode_auth(self) -> str:
        """Encode username:password for Basic Auth"""
        import base64
        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def _rate_limited_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make rate-limited API request"""
        if self.session is None:
            await self._init_session()
        
        # Rate limiting
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - elapsed)
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                self._last_request_time = datetime.now()
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error("Pinnacle API: Unauthorized - check credentials")
                    return {"error": "unauthorized"}
                elif response.status == 429:
                    logger.warning("Pinnacle API: Rate limited")
                    await asyncio.sleep(5)
                    return await self._rate_limited_request(method, endpoint, **kwargs)
                else:
                    logger.error(f"Pinnacle API error: {response.status}")
                    return {"error": f"http_{response.status}"}
                    
        except aiohttp.ClientError as e:
            logger.error(f"Pinnacle API request failed: {e}")
            return {"error": str(e)}
    
    async def get_sports(self) -> List[dict]:
        """Get list of available sports"""
        data = await self._rate_limited_request("GET", "sports")
        return data.get("sports", [])
    
    async def get_leagues(self, sport_id: int) -> List[dict]:
        """Get leagues for a sport"""
        data = await self._rate_limited_request("GET", f"leagues?sportId={sport_id}")
        return data.get("leagues", [])
    
    async def get_fixtures(self, sport_id: int, league_ids: List[int] = None) -> List[dict]:
        """Get upcoming fixtures"""
        params = f"sportId={sport_id}"
        if league_ids:
            params += f"&leagueIds={','.join(map(str, league_ids))}"
        
        data = await self._rate_limited_request("GET", f"fixtures?{params}")
        return data.get("fixtures", [])
    
    async def get_odds(self, sport_id: int, league_ids: List[int] = None, 
                       fixture_ids: List[int] = None, is_live: bool = False) -> List[dict]:
        """
        Get odds for fixtures
        
        Args:
            sport_id: Sport ID (e.g., 29 for Soccer)
            league_ids: Filter by league IDs
            fixture_ids: Filter by specific fixtures
            is_live: Get live odds instead of pre-match
        """
        params = f"sportId={sport_id}"
        if league_ids:
            params += f"&leagueIds={','.join(map(str, league_ids))}"
        if fixture_ids:
            params += f"&fixtureIds={','.join(map(str, fixture_ids))}"
        if is_live:
            params += "&isLive=1"
        
        data = await self._rate_limited_request("GET", f"odds?{params}")
        return data.get("odds", [])
    
    def parse_odds_data(self, odds_data: List[dict]) -> List[PinnacleMatch]:
        """Parse raw odds data into structured objects"""
        matches = []
        
        for fixture in odds_data:
            fixture_id = str(fixture.get("id", ""))
            
            # Extract moneyline odds
            moneyline = fixture.get("moneyline", {})
            home_odds = moneyline.get("home", 0)
            away_odds = moneyline.get("away", 0)
            draw_odds = moneyline.get("draw")
            
            # Extract totals
            totals = fixture.get("totals", [])
            total_over = None
            total_under = None
            total_line = None
            if totals:
                first_total = totals[0]
                total_over = first_total.get("over", 0)
                total_under = first_total.get("under", 0)
                total_line = first_total.get("points", 0)
            
            match = PinnacleMatch(
                match_id=fixture_id,
                home_team=fixture.get("home", ""),
                away_team=fixture.get("away", ""),
                league=fixture.get("league", {}).get("name", ""),
                kickoff=datetime.fromisoformat(fixture.get("starts", datetime.now().isoformat())),
                sport=fixture.get("sport", {}).get("name", ""),
                moneyline_home=home_odds,
                moneyline_away=away_odds,
                moneyline_draw=draw_odds,
                total_over=total_over,
                total_under=total_under,
                total_line=total_line,
                is_live=fixture.get("liveStatus", 0) == 1
            )
            matches.append(match)
        
        return matches
    
    async def get_soccer_odds(self) -> List[PinnacleMatch]:
        """Convenience method: Get all soccer odds"""
        # Soccer sport ID is typically 29
        odds_data = await self.get_odds(sport_id=29)
        return self.parse_odds_data(odds_data)
    
    def detect_odds_drops(self, current_matches: List[PinnacleMatch], 
                          threshold_pct: float = 5.0) -> List[dict]:
        """
        Detect significant odds drops from cache
        
        Returns list of matches with dropping odds
        """
        drops = []
        
        for match in current_matches:
            match_id = match.match_id
            
            if match_id in self._odds_cache:
                old = self._odds_cache[match_id]
                
                # Check moneyline home
                if old.get("home", 0) > 0 and match.moneyline_home > 0:
                    drop_pct = ((old["home"] - match.moneyline_home) / old["home"]) * 100
                    if drop_pct >= threshold_pct:
                        drops.append({
                            "match_id": match_id,
                            "match_name": f"{match.home_team} vs {match.away_team}",
                            "league": match.league,
                            "market": "1",
                            "selection": match.home_team,
                            "old_odds": old["home"],
                            "new_odds": match.moneyline_home,
                            "drop_pct": round(drop_pct, 2),
                            "timestamp": datetime.now().isoformat(),
                            "kickoff": match.kickoff.isoformat()
                        })
                
                # Check moneyline away
                if old.get("away", 0) > 0 and match.moneyline_away > 0:
                    drop_pct = ((old["away"] - match.moneyline_away) / old["away"]) * 100
                    if drop_pct >= threshold_pct:
                        drops.append({
                            "match_id": match_id,
                            "match_name": f"{match.home_team} vs {match.away_team}",
                            "league": match.league,
                            "market": "2",
                            "selection": match.away_team,
                            "old_odds": old["away"],
                            "new_odds": match.moneyline_away,
                            "drop_pct": round(drop_pct, 2),
                            "timestamp": datetime.now().isoformat(),
                            "kickoff": match.kickoff.isoformat()
                        })
            
            # Update cache
            self._odds_cache[match_id] = {
                "home": match.moneyline_home,
                "away": match.moneyline_away,
                "draw": match.moneyline_draw,
                "over": match.total_over,
                "under": match.total_under,
                "timestamp": datetime.now().isoformat()
            }
        
        return drops
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None


# Demo mode for testing without API keys
class PinnacleDemoAPI(PinnacleAPI):
    """
    Demo Pinnacle API - Returns simulated data
    Use this for testing without real API credentials
    """
    
    def __init__(self):
        super().__init__(api_key="demo", username="demo", password="demo")
    
    async def _rate_limited_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Return demo data instead of making real API calls"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if "fixtures" in endpoint:
            return self._demo_fixtures()
        elif "odds" in endpoint:
            return self._demo_odds()
        else:
            return {"sports": [{"id": 29, "name": "Soccer"}]}
    
    def _demo_fixtures(self) -> dict:
        """Generate demo fixtures"""
        from datetime import datetime, timedelta
        now = datetime.now()
        
        fixtures = [
            {
                "id": 1001,
                "home": "Olympiacos",
                "away": "PAOK",
                "league": {"name": "Super League Greece", "id": 101},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (now + timedelta(hours=1, minutes=30)).isoformat(),
                "liveStatus": 0
            },
            {
                "id": 1002,
                "home": "AEK Athens",
                "away": "Panathinaikos",
                "league": {"name": "Super League Greece", "id": 101},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (now + timedelta(hours=2, minutes=15)).isoformat(),
                "liveStatus": 0
            },
            {
                "id": 1003,
                "home": "Arsenal",
                "away": "Chelsea",
                "league": {"name": "Premier League", "id": 201},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (now + timedelta(hours=3)).isoformat(),
                "liveStatus": 0
            }
        ]
        
        return {"fixtures": fixtures}
    
    def _demo_odds(self) -> dict:
        """Generate demo odds with realistic drops"""
        odds = [
            {
                "id": 1001,
                "home": "Olympiacos",
                "away": "PAOK",
                "league": {"name": "Super League Greece", "id": 101},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (datetime.now() + timedelta(hours=1, minutes=30)).isoformat(),
                "liveStatus": 0,
                "moneyline": {"home": 2.10, "away": 3.40, "draw": 3.20},
                "totals": [{"over": 1.95, "under": 1.85, "points": 2.5}]
            },
            {
                "id": 1002,
                "home": "AEK Athens",
                "away": "Panathinaikos",
                "league": {"name": "Super League Greece", "id": 101},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (datetime.now() + timedelta(hours=2, minutes=15)).isoformat(),
                "liveStatus": 0,
                "moneyline": {"home": 1.85, "away": 4.20, "draw": 3.50},
                "totals": [{"over": 2.05, "under": 1.75, "points": 2.5}]
            },
            {
                "id": 1003,
                "home": "Arsenal",
                "away": "Chelsea",
                "league": {"name": "Premier League", "id": 201},
                "sport": {"name": "Soccer", "id": 29},
                "starts": (datetime.now() + timedelta(hours=3)).isoformat(),
                "liveStatus": 0,
                "moneyline": {"home": 1.95, "away": 3.60, "draw": 3.80},
                "totals": [{"over": 1.95, "under": 1.85, "points": 2.5}]
            }
        ]
        
        return {"odds": odds}


if __name__ == "__main__":
    # Test the demo API
    async def test():
        api = PinnacleDemoAPI()
        
        print("🔍 Testing Pinnacle Demo API...")
        
        # Get soccer odds
        matches = await api.get_soccer_odds()
        print(f"\n📊 Found {len(matches)} matches:")
        
        for match in matches:
            print(f"\n⚽ {match.home_team} vs {match.away_team}")
            print(f"   League: {match.league}")
            print(f"   Kickoff: {match.kickoff}")
            print(f"   Home: {match.moneyline_home} | Draw: {match.moneyline_draw} | Away: {match.moneyline_away}")
        
        # Detect drops (second call will show drops)
        drops = api.detect_odds_drops(matches, threshold_pct=5.0)
        print(f"\n📉 Detected {len(drops)} odds drops")
        
        for drop in drops:
            print(f"   🔻 {drop['match_name']}: {drop['drop_pct']:.1f}% drop on {drop['selection']}")
        
        await api.close()
    
    asyncio.run(test())
