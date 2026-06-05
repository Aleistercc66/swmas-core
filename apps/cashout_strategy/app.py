#!/usr/bin/env python3
"""
Stoiximan Cashout Strategy - Desktop Application
==============================================
Production-grade desktop app with real-time dashboard for 
implementing the Two-Step Cashout strategy.

Strategy: Monitor Pinnacle dropping odds → Find Stoiximan lag → 
Pre-match cashout during Golden Hour (60-90 min before kickoff)
"""

import os
import sys
import json
import sqlite3
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import requests

# Add integrations to path
sys.path.insert(0, str(Path(__file__).parent / "integrations"))
sys.path.insert(0, str(Path(__file__).parent / "osint"))

from pinnacle_api import PinnacleAPI, PinnacleDemoAPI, PinnacleMatch
from stoiximan_api import StoiximanAPI, StoiximanDemoAPI, StoiximanOdds
from football_osint import FootballOSINT, IntelligenceType, IntelligenceReport
from telegram_alerts import TelegramAlerter

# Setup paths
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
LOGS_DIR = APP_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"cashout_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CashoutApp")


class OpportunityStatus(Enum):
    DETECTED = "detected"
    TRACKING = "tracking"
    EXPIRED = "expired"
    CASHOUT_READY = "cashout_ready"
    EXECUTED = "executed"
    MISSED = "missed"


@dataclass
class OddsMovement:
    """Tracks odds movement for a specific market"""
    match_id: str
    match_name: str
    league: str
    kickoff: datetime
    market: str  # "1X2", "OVER_UNDER", etc.
    selection: str  # "Home", "Away", "Over 2.5", etc.
    
    # Pinnacle (sharp book)
    pinnacle_open: float
    pinnacle_current: float
    pinnacle_drop_pct: float
    pinnacle_last_update: datetime
    
    # Stoiximan (soft book)
    stoiximan_odds: float
    stoiximan_last_update: datetime
    
    # Opportunity metrics
    value_edge: float  # % edge vs fair odds
    confidence: int  # 0-100
    golden_hour: bool  # Within 60-90 min window
    
    # Status
    status: OpportunityStatus
    detected_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict:
        return {
            **asdict(self),
            'kickoff': self.kickoff.isoformat(),
            'pinnacle_last_update': self.pinnacle_last_update.isoformat(),
            'stoiximan_last_update': self.stoiximan_last_update.isoformat(),
            'detected_at': self.detected_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'status': self.status.value
        }


class Database:
    """SQLite database for tracking opportunities and performance"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_DIR / "cashout_tracker.db")
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT,
                    match_name TEXT,
                    league TEXT,
                    kickoff TIMESTAMP,
                    market TEXT,
                    selection TEXT,
                    pinnacle_open REAL,
                    pinnacle_current REAL,
                    pinnacle_drop_pct REAL,
                    stoiximan_odds REAL,
                    value_edge REAL,
                    confidence INTEGER,
                    golden_hour BOOLEAN,
                    status TEXT,
                    detected_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    cashed_out_at TIMESTAMP,
                    profit_pct REAL,
                    notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    opportunities_found INTEGER,
                    opportunities_executed INTEGER,
                    avg_profit_pct REAL,
                    total_profit_pct REAL,
                    win_rate REAL,
                    bankroll REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            conn.commit()
    
    def save_opportunity(self, opp: OddsMovement) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO opportunities (
                    match_id, match_name, league, kickoff, market, selection,
                    pinnacle_open, pinnacle_current, pinnacle_drop_pct,
                    stoiximan_odds, value_edge, confidence, golden_hour,
                    status, detected_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """, (
                opp.match_id, opp.match_name, opp.league, opp.kickoff,
                opp.market, opp.selection, opp.pinnacle_open,
                opp.pinnacle_current, opp.pinnacle_drop_pct,
                opp.stoiximan_odds, opp.value_edge, opp.confidence,
                opp.golden_hour, opp.status.value, opp.detected_at,
                opp.updated_at
            ))
            conn.commit()
            return cursor.lastrowid
    
    def update_opportunity(self, match_id: str, updates: dict):
        with sqlite3.connect(self.db_path) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [match_id]
            conn.execute(f"""
                UPDATE opportunities 
                SET {set_clause}, updated_at = ?
                WHERE match_id = ?
            """, values + [datetime.now(), match_id])
            conn.commit()
    
    def get_opportunities(self, status: str = None, limit: int = 50) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT * FROM opportunities WHERE status = ? ORDER BY detected_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM opportunities ORDER BY detected_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
    
    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            total = conn.execute("SELECT COUNT(*) as count FROM opportunities").fetchone()["count"]
            executed = conn.execute(
                "SELECT COUNT(*) as count FROM opportunities WHERE status = 'executed'"
            ).fetchone()["count"]
            
            avg_profit = conn.execute(
                "SELECT AVG(profit_pct) as avg FROM opportunities WHERE profit_pct IS NOT NULL"
            ).fetchone()["avg"] or 0
            
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) as count FROM opportunities WHERE date(detected_at) = ?",
                (today,)
            ).fetchone()["count"]
            
            return {
                "total_opportunities": total,
                "executed": executed,
                "avg_profit_pct": round(avg_profit, 2),
                "today_opportunities": today_count,
                "win_rate": round((executed / max(total, 1)) * 100, 1)
            }


class PinnacleMonitor:
    """Monitor Pinnacle for dropping odds (sharp money indicators)"""
    
    def __init__(self):
        self.api_base = "https://api.pinnacle.com/v2"
        self.session = None
        self.odds_cache: Dict[str, dict] = {}
        
    async def init_session(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
    
    async def fetch_odds(self, sport: str = "Soccer") -> List[dict]:
        """Fetch current odds from Pinnacle"""
        try:
            # In production, use real Pinnacle API or scrape
            # For now, simulate with realistic data structure
            return await self._fetch_simulated(sport)
        except Exception as e:
            logger.error(f"Pinnacle fetch error: {e}")
            return []
    
    async def _fetch_simulated(self, sport: str) -> List[dict]:
        """Simulated data for development - shows realistic opportunities"""
        from datetime import datetime, timedelta
        import random
        
        # Demo matches for visualization
        demo_matches = [
            {
                "id": "match_001",
                "name": "Olympiacos vs PAOK",
                "league": "Super League Greece",
                "kickoff": (datetime.now() + timedelta(hours=1, minutes=30)).isoformat(),
                "1": 2.10, "2": 3.40, "X": 3.20,
                "market": "1", "selection": "Home",
                "old_odds": 2.45, "new_odds": 2.10, "drop_pct": 14.3
            },
            {
                "id": "match_002",
                "name": "AEK Athens vs Panathinaikos",
                "league": "Super League Greece",
                "kickoff": (datetime.now() + timedelta(hours=2, minutes=15)).isoformat(),
                "1": 1.85, "2": 4.20, "X": 3.50,
                "market": "2", "selection": "Away",
                "old_odds": 5.10, "new_odds": 4.20, "drop_pct": 17.6
            },
            {
                "id": "match_003",
                "name": "Arsenal vs Chelsea",
                "league": "Premier League",
                "kickoff": (datetime.now() + timedelta(hours=3)).isoformat(),
                "1": 1.95, "2": 3.60, "X": 3.80,
                "market": "over_2_5", "selection": "Over 2.5",
                "old_odds": 2.15, "new_odds": 1.95, "drop_pct": 9.3
            }
        ]
        
        return demo_matches
    
    def detect_dropping_odds(self, current_odds: List[dict]) -> List[dict]:
        """Detect significant odds drops (sharp money)"""
        drops = []
        for match in current_odds:
            match_id = match.get("id") or match.get("match_id")
            # For demo, use the pre-calculated drop data
            if "drop_pct" in match and match["drop_pct"] > 5:
                drops.append({
                    "match_id": match_id,
                    "match_name": match.get("name") or match.get("match_name", "Unknown"),
                    "market": match.get("market", "1"),
                    "selection": match.get("selection", "Home"),
                    "old_odds": match.get("old_odds", match.get("pinnacle_open", 0)),
                    "new_odds": match.get("new_odds", match.get("pinnacle_current", 0)),
                    "drop_pct": match["drop_pct"],
                    "timestamp": datetime.now().isoformat(),
                    "kickoff": match.get("kickoff", (datetime.now() + timedelta(hours=2)).isoformat())
                })
            
            self.odds_cache[match_id] = match
        
        return drops


class StoiximanMonitor:
    """Monitor Stoiximan for odds that haven't adjusted yet"""
    
    def __init__(self):
        self.api_base = "https://www.stoiximan.gr/api"
        self.session = None
        
    async def init_session(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
        )
    
    async def fetch_odds(self, match_ids: List[str]) -> Dict[str, float]:
        """Fetch current Stoiximan odds for specific matches"""
        try:
            # Demo data - in production replace with real Stoiximan API
            demo_odds = {
                "match_001": 2.25,  # Olympiacos vs PAOK - Home still high
                "match_002": 5.50,  # AEK vs Panathinaikos - Away still high
                "match_003": 2.05,  # Arsenal vs Chelsea - Over 2.5
            }
            return {mid: demo_odds.get(mid, 0.0) for mid in match_ids}
        except Exception as e:
            logger.error(f"Stoiximan fetch error: {e}")
            return {}
    
    def is_golden_hour(self, kickoff: datetime) -> bool:
        """Check if within Golden Hour window (60-90 min before kickoff)"""
        now = datetime.now()
        # Handle timezone-aware datetime
        if kickoff.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=kickoff.tzinfo)
        elif kickoff.tzinfo is None and now.tzinfo is not None:
            kickoff = kickoff.replace(tzinfo=now.tzinfo)
        
        time_to_kickoff = kickoff - now
        minutes = time_to_kickoff.total_seconds() / 60
        return 60 <= minutes <= 90


class OpportunityEngine:
    """
    Two-Step Cashout Engine
    =======================
    Step 1: Detect Pinnacle dropping odds (sharp money)
    Step 2: Check if Stoiximan hasn't adjusted yet
    Step 3: Calculate value edge and confidence
    Step 4: Flag for pre-match cashout during Golden Hour
    """
    
    def __init__(self, db: Database, pinnacle: PinnacleMonitor, stoiximan: StoiximanMonitor):
        self.db = db
        self.pinnacle = pinnacle
        self.stoiximan = stoiximan
        self.active_opportunities: Dict[str, OddsMovement] = {}
        
    async def scan(self) -> List[OddsMovement]:
        """Full scan cycle - detect opportunities"""
        opportunities = []
        
        # Step 1: Get Pinnacle odds and detect drops
        pinnacle_odds = await self.pinnacle.fetch_odds()
        drops = self.pinnacle.detect_dropping_odds(pinnacle_odds)
        
        # Step 2: For each drop, check Stoiximan
        if drops:
            match_ids = [d["match_id"] for d in drops]
            stoiximan_odds = await self.stoiximan.fetch_odds(match_ids)
            
            for drop in drops:
                match_id = drop["match_id"]
                stoix_odds = stoiximan_odds.get(match_id, 0.0)
                
                if stoix_odds > 0 and stoix_odds > drop["new_odds"]:
                    # Calculate value edge
                    fair_odds = drop["new_odds"]  # Pinnacle = fair odds
                    value_edge = ((stoix_odds - fair_odds) / fair_odds) * 100
                    
                    # Parse kickoff
                    kickoff_str = drop.get("kickoff", (datetime.now() + timedelta(hours=2)).isoformat())
                    if isinstance(kickoff_str, str):
                        kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                    else:
                        kickoff = kickoff_str
                    
                    # Confidence scoring
                    is_golden = self.stoiximan.is_golden_hour(kickoff)
                    confidence = min(100, int(
                        30 +  # Base
                        drop["drop_pct"] * 2 +  # Drop magnitude
                        value_edge * 3 +  # Value edge
                        (20 if is_golden else 0)  # Golden hour bonus
                    ))
                    
                    opp = OddsMovement(
                        match_id=match_id,
                        match_name=drop["match_name"],
                        league="Super League Greece" if any(x in drop["match_name"] for x in ["Olympiacos", "PAOK", "AEK", "Panathinaikos"]) else "Premier League",
                        kickoff=kickoff,
                        market="1X2" if drop["market"] in ["1", "2", "X"] else "OVER_UNDER",
                        selection=drop["selection"],
                        pinnacle_open=drop["old_odds"],
                        pinnacle_current=drop["new_odds"],
                        pinnacle_drop_pct=drop["drop_pct"],
                        stoiximan_odds=stoix_odds,
                        stoiximan_last_update=datetime.now(),
                        value_edge=value_edge,
                        confidence=confidence,
                        golden_hour=is_golden,
                        status=OpportunityStatus.DETECTED,
                        detected_at=datetime.now(),
                        pinnacle_last_update=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    opportunities.append(opp)
                    self.active_opportunities[match_id] = opp
                    self.db.save_opportunity(opp)
                    
                    logger.info(
                        f"🎯 OPPORTUNITY: {opp.match_name} | "
                        f"Drop: {opp.pinnacle_drop_pct:.1f}% | "
                        f"Edge: {opp.value_edge:.1f}% | "
                        f"Confidence: {opp.confidence}/100"
                    )
        
        return opportunities
    
    async def update_tracking(self):
        """Update tracked opportunities - check if still valid"""
        for match_id, opp in list(self.active_opportunities.items()):
            now = datetime.now()
            
            # Check if kickoff passed
            if now > opp.kickoff:
                opp.status = OpportunityStatus.EXPIRED
                self.db.update_opportunity(match_id, {"status": "expired"})
                del self.active_opportunities[match_id]
                logger.info(f"⏰ Expired: {opp.match_name}")
                continue
            
            # Check if still in Golden Hour
            if self.stoiximan.is_golden_hour(opp.kickoff) and opp.status == OpportunityStatus.DETECTED:
                opp.status = OpportunityStatus.CASHOUT_READY
                opp.golden_hour = True
                self.db.update_opportunity(match_id, {
                    "status": "cashout_ready",
                    "golden_hour": True
                })
                logger.info(f"🔥 GOLDEN HOUR: {opp.match_name} - CASHOUT NOW!")


class CashoutApp:
    """Main application controller with real API integrations"""
    
    def __init__(self, use_demo: bool = True):
        self.db = Database()
        self.use_demo = use_demo
        
        # Use demo APIs by default (no credentials needed)
        # In production, switch to real APIs with credentials
        if use_demo:
            self.pinnacle = PinnacleDemoAPI()
            self.stoiximan = StoiximanDemoAPI()
        else:
            self.pinnacle = PinnacleAPI()
            self.stoiximan = StoiximanAPI()
        
        self.osint = FootballOSINT()
        self.alerter = TelegramAlerter()  # Telegram alerts
        self.engine = OpportunityEngine(self.db, self.pinnacle, self.stoiximan)
        self.running = False
        self.scan_interval = 120  # 2 minutes
        self.osint_reports: Dict[str, List[dict]] = {}
        self._telegram_enabled = True
        
    async def start(self):
        """Start the application"""
        logger.info("🚀 Starting Cashout Strategy App [Real API Mode]" if not self.use_demo else "🚀 Starting Cashout Strategy App [Demo Mode]")
        self.running = True
        
        await self.pinnacle._init_session()
        await self.stoiximan._init_session()
        
        # Main loop
        while self.running:
            try:
                # Step 1: Find opportunities
                opportunities = await self.engine.scan()
                await self.engine.update_tracking()
                
                # Step 2: Run OSINT and send alerts for each opportunity
                if opportunities:
                    logger.info(f"✅ Found {len(opportunities)} opportunities")
                    for opp in opportunities:
                        # Send Telegram alert for new opportunity
                        if self._telegram_enabled:
                            try:
                                await self.alerter.alert_new_opportunity(opp.to_dict())
                            except Exception as e:
                                logger.error(f"Telegram alert error: {e}")
                        
                        await self._run_osint(opp)
                
                # Check for golden hour transitions and alert
                for opp in self.engine.active_opportunities.values():
                    if opp.status == OpportunityStatus.CASHOUT_READY and self._telegram_enabled:
                        try:
                            await self.alerter.alert_golden_hour({
                                "match_id": opp.match_id,
                                "match_name": opp.match_name,
                                "kickoff": opp.kickoff.isoformat(),
                                "value_edge": opp.value_edge,
                                "confidence": opp.confidence,
                                "market": opp.market,
                                "selection": opp.selection
                            })
                        except Exception as e:
                            logger.error(f"Golden hour alert error: {e}")
                
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(30)
    
    async def _run_osint(self, opp: OddsMovement):
        """Run OSINT analysis for an opportunity"""
        try:
            # Parse teams from match name
            teams = opp.match_name.split(" vs ")
            if len(teams) == 2:
                home_team, away_team = teams[0].strip(), teams[1].strip()
                
                reports = await self.osint.analyze_match(
                    opp.match_id, home_team, away_team, 
                    opp.league, opp.kickoff
                )
                
                self.osint_reports[opp.match_id] = [
                    {
                        "type": r.type.value,
                        "source": r.source,
                        "confidence": r.confidence,
                        "summary": r.summary,
                        "details": r.details
                    }
                    for r in reports
                ]
                
                logger.info(f"🔍 OSINT: {len(reports)} reports for {opp.match_name}")
                
                # Send Telegram alerts for high-confidence OSINT
                if self._telegram_enabled and reports:
                    for report in reports:
                        if report.confidence >= 70:  # Only alert on high confidence
                            try:
                                await self.alerter.alert_osint(opp.match_name, {
                                    "type": report.type.value,
                                    "source": report.source,
                                    "confidence": report.confidence,
                                    "summary": report.summary
                                })
                            except Exception as e:
                                logger.error(f"OSINT alert error: {e}")
        except Exception as e:
            logger.error(f"OSINT error for {opp.match_name}: {e}")
    
    def stop(self):
        """Stop the application"""
        self.running = False
        logger.info("🛑 App stopped")
        
        # Close sessions
        asyncio.create_task(self._close_sessions())
    
    async def _close_sessions(self):
        """Close API sessions"""
        try:
            await self.pinnacle.close()
        except:
            pass
        try:
            await self.stoiximan.close()
        except:
            pass
        try:
            await self.osint.close()
        except:
            pass
        try:
            await self.alerter.close()
        except:
            pass
    
    def get_dashboard_data(self) -> dict:
        """Get data for dashboard with OSINT integration"""
        return {
            "stats": self.db.get_stats(),
            "opportunities": self.db.get_opportunities(limit=20),
            "active_count": len(self.engine.active_opportunities),
            "running": self.running,
            "last_scan": datetime.now().isoformat(),
            "osint_reports": self.osint_reports,
            "mode": "demo" if self.use_demo else "live"
        }


if __name__ == "__main__":
    app = CashoutApp(use_demo=True)  # Set to False for real APIs with credentials
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        app.stop()
