#!/usr/bin/env python3
"""
Football OSINT Intelligence Module
=================================
Open Source Intelligence for football betting

Sources integrated:
- Transfermarkt (team news, injuries, squad info)
- Flashscore (live scores, match data)
- Twitter/X (betting sentiment, sharp money signals)
- Oddschecker (odds comparison)
- News APIs (injury reports, lineup announcements)

Usage: Free APIs and public data scraping
"""

import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import re

logger = logging.getLogger("FootballOSINT")


class IntelligenceType(Enum):
    INJURY = "injury"
    LINEUP = "lineup"
    FORM = "form"
    SENTIMENT = "sentiment"
    ODDS_MOVEMENT = "odds_movement"
    WEATHER = "weather"
    REFEREE = "referee"
    DERBY = "derby"


@dataclass
class IntelligenceReport:
    """Structured intelligence report"""
    type: IntelligenceType
    match_id: str
    match_name: str
    source: str
    confidence: int  # 0-100
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TransfermarktScraper:
    """
    Transfermarkt scraper for squad info and injuries
    Uses public web scraping (respect robots.txt)
    """
    
    BASE_URL = "https://www.transfermarkt.com"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _init_session(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.session = aiohttp.ClientSession(headers=headers)
    
    async def get_team_injuries(self, team_name: str) -> List[Dict]:
        """
        Get current injuries for a team
        Note: In production, use real API or web scraping
        """
        # Demo data for major teams
        demo_injuries = {
            "olympiacos": [
                {"player": "M. Camara", "injury": "Hamstring", "return": "1-2 weeks", "severity": "medium"},
            ],
            "paok": [
                {"player": "T. Tzolis", "injury": "Ankle", "return": "Doubtful", "severity": "low"},
            ],
            "aek": [
                {"player": "L. Garcia", "injury": "Groin", "return": "3-5 days", "severity": "low"},
            ],
            "panathinaikos": [
                {"player": "F. Ioannidis", "injury": "Knee", "return": "1 week", "severity": "medium"},
            ],
            "arsenal": [
                {"player": "B. Saka", "injury": "Hamstring", "return": "Doubtful", "severity": "high"},
            ],
            "chelsea": [
                {"player": "R. James", "injury": "Thigh", "return": "2 weeks", "severity": "medium"},
            ]
        }
        
        team_key = team_name.lower().replace(" ", "")
        return demo_injuries.get(team_key, [])
    
    async def get_team_form(self, team_name: str, last_n: int = 5) -> Dict:
        """
        Get recent form (last N matches)
        """
        demo_form = {
            "olympiacos": {"w": 4, "d": 0, "l": 1, "goals_for": 12, "goals_against": 4, "last_5": ["W", "W", "W", "L", "W"]},
            "paok": {"w": 3, "d": 1, "l": 1, "goals_for": 9, "goals_against": 5, "last_5": ["W", "D", "W", "L", "W"]},
            "aek": {"w": 3, "d": 2, "l": 0, "goals_for": 10, "goals_against": 6, "last_5": ["W", "D", "W", "D", "W"]},
            "panathinaikos": {"w": 2, "d": 1, "l": 2, "goals_for": 7, "goals_against": 8, "last_5": ["L", "W", "D", "L", "W"]},
            "arsenal": {"w": 4, "d": 1, "l": 0, "goals_for": 15, "goals_against": 5, "last_5": ["W", "W", "D", "W", "W"]},
            "chelsea": {"w": 2, "d": 2, "l": 1, "goals_for": 8, "goals_against": 7, "last_5": ["W", "D", "L", "D", "W"]},
        }
        
        team_key = team_name.lower().replace(" ", "")
        return demo_form.get(team_key, {"w": 0, "d": 0, "l": 0, "last_5": []})
    
    async def close(self):
        if self.session:
            await self.session.close()


class FlashscoreAPI:
    """
    Flashscore API integration
    Uses their public API for live scores and match data
    """
    
    BASE_URL = "https://flashscore.com/api"
    
    def __init__(self):
        self.session = None
    
    async def _init_session(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
    
    async def get_match_info(self, match_id: str) -> Dict:
        """Get match information"""
        # In production: Use real Flashscore API
        return {}
    
    async def get_live_matches(self) -> List[Dict]:
        """Get currently live matches"""
        return []
    
    async def get_head_to_head(self, team1: str, team2: str) -> Dict:
        """Get head-to-head statistics"""
        demo_h2h = {
            "olympiacos_paok": {"total": 25, "team1_wins": 15, "draws": 5, "team2_wins": 5, "avg_goals": 2.8},
            "aek_panathinaikos": {"total": 30, "team1_wins": 12, "draws": 8, "team2_wins": 10, "avg_goals": 2.4},
            "arsenal_chelsea": {"total": 60, "team1_wins": 25, "draws": 15, "team2_wins": 20, "avg_goals": 2.6},
        }
        
        key1 = f"{team1.lower()}_{team2.lower()}"
        key2 = f"{team2.lower()}_{team1.lower()}"
        
        return demo_h2h.get(key1, demo_h2h.get(key2, {"total": 0, "avg_goals": 2.5}))


class BettingSentimentAnalyzer:
    """
    Analyze betting sentiment from social media and forums
    """
    
    def __init__(self):
        self.sentiment_cache: Dict[str, Dict] = {}
    
    def analyze_match_sentiment(self, match_name: str, home_team: str, away_team: str) -> Dict:
        """
        Analyze sentiment for a match
        Returns: {home_bias, away_bias, sharp_money_direction, confidence}
        """
        # In production: Scrape Twitter/X, Reddit, betting forums
        # For now, return demo data based on team names
        
        sentiment_map = {
            "olympiacos": {"favorability": 0.65, "sharp_bias": "home"},
            "paok": {"favorability": 0.55, "sharp_bias": "away"},
            "aek": {"favorability": 0.60, "sharp_bias": "home"},
            "panathinaikos": {"favorability": 0.58, "sharp_bias": "away"},
            "arsenal": {"favorability": 0.62, "sharp_bias": "home"},
            "chelsea": {"favorability": 0.48, "sharp_bias": "away"},
        }
        
        home_sentiment = sentiment_map.get(home_team.lower(), {"favorability": 0.50, "sharp_bias": "neutral"})
        away_sentiment = sentiment_map.get(away_team.lower(), {"favorability": 0.50, "sharp_bias": "neutral"})
        
        # Determine sharp money direction
        if home_sentiment["sharp_bias"] == "home" and away_sentiment["sharp_bias"] != "home":
            sharp_direction = "home"
        elif away_sentiment["sharp_bias"] == "away" and home_sentiment["sharp_bias"] != "away":
            sharp_direction = "away"
        else:
            sharp_direction = "neutral"
        
        return {
            "home_favorability": home_sentiment["favorability"],
            "away_favorability": away_sentiment["favorability"],
            "sharp_money_direction": sharp_direction,
            "public_bias": "home" if home_sentiment["favorability"] > away_sentiment["favorability"] else "away",
            "confidence": 65
        }


class OddscheckerAPI:
    """
    Oddschecker odds comparison
    Shows best odds across all bookmakers
    """
    
    def __init__(self):
        self.base_url = "https://www.oddschecker.com"
    
    def get_best_odds(self, match_name: str, market: str = "1x2") -> Dict:
        """
        Get best odds across bookmakers
        Returns: {best_home, best_draw, best_away, bookmaker}
        """
        # Demo data
        best_odds = {
            "olympiacos vs paok": {
                "home": {"odds": 2.30, "bookmaker": "Bet365"},
                "draw": {"odds": 3.40, "bookmaker": "Stoiximan"},
                "away": {"odds": 3.50, "bookmaker": "Pinnacle"}
            },
            "aek athens vs panathinaikos": {
                "home": {"odds": 1.90, "bookmaker": "Stoiximan"},
                "draw": {"odds": 3.50, "bookmaker": "Bet365"},
                "away": {"odds": 5.75, "bookmaker": "Pinnacle"}
            },
            "arsenal vs chelsea": {
                "home": {"odds": 2.10, "bookmaker": "Bet365"},
                "draw": {"odds": 3.80, "bookmaker": "Stoiximan"},
                "away": {"odds": 3.50, "bookmaker": "Pinnacle"}
            }
        }
        
        return best_odds.get(match_name.lower(), {})


class FootballOSINT:
    """
    Main OSINT Orchestrator
    Combines all intelligence sources into actionable reports
    """
    
    def __init__(self):
        self.transfermarkt = TransfermarktScraper()
        self.flashscore = FlashscoreAPI()
        self.sentiment = BettingSentimentAnalyzer()
        self.oddschecker = OddscheckerAPI()
    
    async def analyze_match(self, match_id: str, home_team: str, away_team: str, 
                           league: str, kickoff: datetime) -> List[IntelligenceReport]:
        """
        Full OSINT analysis for a match
        Returns list of intelligence reports
        """
        reports = []
        match_name = f"{home_team} vs {away_team}"
        
        # 1. Injury report
        home_injuries = await self.transfermarkt.get_team_injuries(home_team)
        away_injuries = await self.transfermarkt.get_team_injuries(away_team)
        
        if home_injuries or away_injuries:
            injury_summary = []
            if home_injuries:
                injury_summary.append(f"{home_team}: {', '.join([i['player'] for i in home_injuries])}")
            if away_injuries:
                injury_summary.append(f"{away_team}: {', '.join([i['player'] for i in away_injuries])}")
            
            reports.append(IntelligenceReport(
                type=IntelligenceType.INJURY,
                match_id=match_id,
                match_name=match_name,
                source="Transfermarkt",
                confidence=75,
                summary="; ".join(injury_summary),
                details={"home": home_injuries, "away": away_injuries}
            ))
        
        # 2. Form analysis
        home_form = await self.transfermarkt.get_team_form(home_team)
        away_form = await self.transfermarkt.get_team_form(away_team)
        
        reports.append(IntelligenceReport(
            type=IntelligenceType.FORM,
            match_id=match_id,
            match_name=match_name,
            source="Transfermarkt",
            confidence=80,
            summary=f"{home_team}: {home_form['w']}W-{home_form['d']}D-{home_form['l']}L | "
                    f"{away_team}: {away_form['w']}W-{away_form['d']}D-{away_form['l']}L",
            details={"home_form": home_form, "away_form": away_form}
        ))
        
        # 3. Head-to-head
        h2h = await self.flashscore.get_head_to_head(home_team, away_team)
        
        reports.append(IntelligenceReport(
            type=IntelligenceType.FORM,
            match_id=match_id,
            match_name=match_name,
            source="Flashscore",
            confidence=85,
            summary=f"H2H: {h2h['total']} matches, avg {h2h['avg_goals']} goals",
            details=h2h
        ))
        
        # 4. Sentiment analysis
        sentiment = self.sentiment.analyze_match_sentiment(match_name, home_team, away_team)
        
        reports.append(IntelligenceReport(
            type=IntelligenceType.SENTIMENT,
            match_id=match_id,
            match_name=match_name,
            source="Social Media/OSINT",
            confidence=sentiment["confidence"],
            summary=f"Sharp money: {sentiment['sharp_money_direction']}, "
                    f"Public bias: {sentiment['public_bias']}",
            details=sentiment
        ))
        
        # 5. Best odds
        best_odds = self.oddschecker.get_best_odds(match_name)
        
        if best_odds:
            reports.append(IntelligenceReport(
                type=IntelligenceType.ODDS_MOVEMENT,
                match_id=match_id,
                match_name=match_name,
                source="Oddschecker",
                confidence=90,
                summary=f"Best: Home {best_odds['home']['odds']}@{best_odds['home']['bookmaker']} | "
                        f"Away {best_odds['away']['odds']}@{best_odds['away']['bookmaker']}",
                details=best_odds
            ))
        
        return reports
    
    async def close(self):
        await self.transfermarkt.close()
        if self.flashscore.session:
            await self.flashscore.session.close()


if __name__ == "__main__":
    async def test():
        osint = FootballOSINT()
        
        print("🔍 Testing Football OSINT...")
        
        reports = await osint.analyze_match(
            "match_001",
            "Olympiacos",
            "PAOK",
            "Super League Greece",
            datetime.now() + timedelta(hours=2)
        )
        
        print(f"\n📊 Generated {len(reports)} intelligence reports:")
        for report in reports:
            print(f"\n[{report.type.value.upper()}] {report.source} (confidence: {report.confidence}%)")
            print(f"  {report.summary}")
        
        await osint.close()
    
    asyncio.run(test())
