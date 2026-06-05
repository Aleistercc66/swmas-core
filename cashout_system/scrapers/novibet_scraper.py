#!/usr/bin/env python3
"""
Novibet Live Odds Scraper
Scrapes live betting odds from novibet.gr for cash-out analysis
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("novibet_scraper")


@dataclass
class NovibetMatch:
    match_id: str
    home_team: str
    away_team: str
    league: str
    sport: str
    match_time: str
    current_score: str
    home_odds: float
    draw_odds: float
    away_odds: float
    over_25_odds: float
    under_25_odds: float
    btts_yes_odds: float
    btts_no_odds: float
    last_updated: str
    cash_out_available: bool = False
    cash_out_value: float = 0.0


class NovibetScraper:
    """Scraper for Novibet live odds"""
    
    BASE_URL = "https://www.novibet.gr"
    API_URL = "https://www.novibet.gr/api/v1/live/events"
    
    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session or aiohttp.ClientSession()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
            "Referer": "https://www.novibet.gr/live/",
        }
        self.matches: Dict[str, NovibetMatch] = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, *args):
        await self.session.close()
    
    async def fetch_live_matches(self) -> List[NovibetMatch]:
        """Fetch all live matches with odds"""
        try:
            async with self.session.get(
                self.API_URL, 
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status}")
                    return []
                
                data = await response.json()
                matches = self._parse_matches(data)
                
                for match in matches:
                    self.matches[match.match_id] = match
                
                logger.info(f"Fetched {len(matches)} live matches from Novibet")
                return matches
                
        except Exception as e:
            logger.error(f"Error fetching Novibet: {e}")
            return []
    
    def _parse_matches(self, data: Dict) -> List[NovibetMatch]:
        """Parse API response"""
        matches = []
        events = data.get("events", []) or data.get("data", []) or []
        
        for event in events:
            try:
                match = NovibetMatch(
                    match_id=str(event.get("id", "")),
                    home_team=event.get("home", "Unknown"),
                    away_team=event.get("away", "Unknown"),
                    league=event.get("league", "Unknown"),
                    sport=event.get("sport", "Football"),
                    match_time=event.get("time", "LIVE"),
                    current_score=event.get("score", "0-0"),
                    home_odds=self._extract_odds(event, "1"),
                    draw_odds=self._extract_odds(event, "X"),
                    away_odds=self._extract_odds(event, "2"),
                    over_25_odds=self._extract_odds(event, "Over 2.5"),
                    under_25_odds=self._extract_odds(event, "Under 2.5"),
                    btts_yes_odds=self._extract_odds(event, "BTTS Yes"),
                    btts_no_odds=self._extract_odds(event, "BTTS No"),
                    last_updated=datetime.now().isoformat(),
                    cash_out_available=event.get("cashOut", False),
                    cash_out_value=event.get("cashOutValue", 0.0)
                )
                matches.append(match)
            except Exception as e:
                logger.warning(f"Parse error: {e}")
                continue
        
        return matches
    
    def _extract_odds(self, event: Dict, market_type: str) -> float:
        """Extract odds for specific market"""
        markets = event.get("markets", [])
        for market in markets:
            if market.get("name") == market_type or market.get("type") == market_type:
                selections = market.get("selections", [])
                if selections:
                    return float(selections[0].get("price", 0))
        return 0.0
    
    async def get_match_by_teams(self, home: str, away: str) -> Optional[NovibetMatch]:
        """Find match by team names"""
        matches = await self.fetch_live_matches()
        for match in matches:
            if home.lower() in match.home_team.lower() and away.lower() in match.away_team.lower():
                return match
        return None
    
    def save_to_file(self, filepath: str = None):
        """Save matches to JSON"""
        filepath = filepath or "/root/.openclaw/workspace/cashout_system/data/novibet_live.json"
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "matches": [asdict(m) for m in self.matches.values()]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.matches)} matches to {filepath}")


async def main():
    """Test scraper"""
    async with NovibetScraper() as scraper:
        matches = await scraper.fetch_live_matches()
        for match in matches[:5]:
            print(f"{match.home_team} vs {match.away_team}: {match.current_score}")
            print(f"  1: {match.home_odds} | X: {match.draw_odds} | 2: {match.away_odds}")
            print(f"  CashOut: {match.cash_out_available} | Value: {match.cash_out_value}")
            print()


if __name__ == "__main__":
    asyncio.run(main())