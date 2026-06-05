#!/usr/bin/env python3
"""
CashOut System - Main Orchestrator
Monitors live odds, calculates EV, sends alerts
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import aiohttp

# Import our modules
from scrapers.stoiximan_scraper import StoiximanScraper
from scrapers.novibet_scraper import NovibetScraper
from core.cashout_calculator import CashOutCalculator, CashOutAnalysis
from alerts.telegram_alerts import TelegramCashOutAlerts, DesktopNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cashout_orchestrator")


class CashOutOrchestrator:
    """Main orchestrator for cash-out system"""
    
    def __init__(self):
        self.stoiximan = StoiximanScraper()
        self.novibet = NovibetScraper()
        self.calculator = CashOutCalculator()
        self.desktop = DesktopNotifier()
        
        # Telegram alerts
        self.bot_token = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
        self.chat_id = "158923136"
        self.telegram: Optional[TelegramCashOutAlerts] = None
        
        # Tracking
        self.tracked_bets: Dict[str, Dict] = {}
        self.active_matches: Dict[str, Dict] = {}
        self.running = False
        self.check_interval = 30  # seconds
        
        # Data directory
        self.data_dir = Path("/root/.openclaw/workspace/cashout_system/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def __aenter__(self):
        self.telegram = TelegramCashOutAlerts(self.bot_token, self.chat_id)
        await self.telegram.__aenter__()
        return self
        
    async def __aexit__(self, *args):
        self.running = False
        if self.telegram:
            await self.telegram.__aexit__(*args)
        await self.stoiximan.__aexit__()
        await self.novibet.__aexit__()
    
    def add_tracked_bet(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        bookmaker: str,
        original_odds: float,
        stake: float,
        bet_type: str = "1X2"
    ):
        """Add a bet to track for cash-out"""
        self.tracked_bets[match_id] = {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "bookmaker": bookmaker,
            "original_odds": original_odds,
            "stake": stake,
            "bet_type": bet_type,
            "added_at": datetime.now().isoformat()
        }
        logger.info(f"Added tracked bet: {home_team} vs {away_team} @ {bookmaker}")
        
    async def monitor_live_matches(self):
        """Main monitoring loop"""
        self.running = True
        
        logger.info("🚀 CashOut System STARTED!")
        logger.info(f"📊 Checking every {self.check_interval} seconds")
        logger.info(f"💰 Tracking {len(self.tracked_bets)} bets")
        
        while self.running:
            try:
                await self._check_all_matches()
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_matches(self):
        """Check all bookmakers and bets"""
        logger.info("🔍 Checking live matches...")
        
        # Fetch from Stoiximan
        try:
            stoiximan_matches = await self.stoiximan.fetch_live_matches()
            await self._process_matches(stoiximan_matches, "Stoiximan")
        except Exception as e:
            logger.error(f"Stoiximan error: {e}")
        
        # Fetch from Novibet
        try:
            novibet_matches = await self.novibet.fetch_live_matches()
            await self._process_matches(novibet_matches, "Novibet")
        except Exception as e:
            logger.error(f"Novibet error: {e}")
        
        # Save state
        self._save_state()
    
    async def _process_matches(self, matches: List, bookmaker: str):
        """Process matches and check for cash-out opportunities"""
        
        for match in matches:
            match_id = match.match_id
            
            # Check if this is a tracked bet
            tracked = self.tracked_bets.get(match_id)
            if not tracked:
                continue
            
            # Get current odds based on bet type
            if tracked["bet_type"] == "1X2":
                # For simplicity, assume bet on home win
                current_odds = match.home_odds
            else:
                current_odds = match.home_odds
            
            # Calculate cash-out value (if available from bookmaker)
            cash_out_value = match.cash_out_value if match.cash_out_available else 0
            
            # If no cash-out value, estimate it
            if cash_out_value == 0:
                cash_out_value = self._estimate_cash_out_value(
                    tracked["stake"],
                    tracked["original_odds"],
                    current_odds
                )
            
            # Calculate analysis
            analysis = self.calculator.calculate_cash_out(
                match_id=match_id,
                home_team=match.home_team,
                away_team=match.away_team,
                current_score=match.current_score,
                original_odds=tracked["original_odds"],
                current_odds=current_odds,
                stake=tracked["stake"],
                cash_out_value=cash_out_value
            )
            
            # Log analysis
            logger.info(f"📊 {match.home_team} vs {match.away_team}: {analysis.cash_out_roi:+.1f}%")
            
            # Check for alerts
            await self._check_alerts(analysis, bookmaker)
            
            # Update active matches
            self.active_matches[match_id] = {
                "match": match,
                "analysis": analysis,
                "bookmaker": bookmaker,
                "last_check": datetime.now().isoformat()
            }
    
    def _estimate_cash_out_value(self, stake: float, original_odds: float, current_odds: float) -> float:
        """Estimate cash-out value when not available from API"""
        if current_odds <= 1.01:
            return 0
        
        # Simple estimation: (original_odds / current_odds) * stake * 0.95
        estimated = (original_odds / current_odds) * stake * 0.95
        return max(0, estimated)
    
    async def _check_alerts(self, analysis: CashOutAnalysis, bookmaker: str):
        """Check if we need to send alerts"""
        
        # Check for optimal cash-out
        if analysis.optimal_cash_out and analysis.confidence > 70:
            logger.info(f"🔥 OPTIMAL CASH-OUT: {analysis.home_team} vs {analysis.away_team}")
            
            # Send Telegram alert
            await self.telegram.send_optimal_cash_out_alert(
                match_id=analysis.match_id,
                home_team=analysis.home_team,
                away_team=analysis.away_team,
                current_score=analysis.current_score,
                cash_out_value=analysis.cash_out_value,
                stake=analysis.stake,
                roi=analysis.cash_out_roi,
                confidence=analysis.confidence
            )
            
            # Desktop notification
            self.desktop.notify_optimal_cash_out(
                analysis.home_team,
                analysis.away_team,
                analysis.cash_out_value
            )
        
        # Check for good cash-out opportunity
        elif analysis.cash_out_roi > 20 and analysis.confidence > 50:
            logger.info(f"🟢 GOOD CASH-OUT: {analysis.home_team} vs {analysis.away_team}")
            
            await self.telegram.send_cash_out_opportunity(
                match_id=analysis.match_id,
                home_team=analysis.home_team,
                away_team=analysis.away_team,
                current_score=analysis.current_score,
                original_odds=analysis.original_odds,
                current_odds=analysis.current_odds,
                stake=analysis.stake,
                cash_out_value=analysis.cash_out_value,
                roi=analysis.cash_out_roi,
                recommendation=analysis.recommendation,
                bookmaker=bookmaker
            )
            
            self.desktop.notify_cash_out_opportunity(
                analysis.home_team,
                analysis.away_team,
                analysis.cash_out_roi
            )
        
        # Check for significant price drift
        elif abs(analysis.price_drift_pct) > 15:
            logger.info(f"📊 PRICE DRIFT: {analysis.home_team} vs {analysis.away_team}")
            
            await self.telegram.send_price_drift_alert(
                match_id=analysis.match_id,
                home_team=analysis.home_team,
                away_team=analysis.away_team,
                drift_pct=analysis.price_drift_pct,
                current_odds=analysis.current_odds,
                recommendation=analysis.recommendation
            )
    
    def _save_state(self):
        """Save current state to file"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "tracked_bets": self.tracked_bets,
            "active_matches": {
                k: {
                    "match": {
                        "match_id": v["match"].match_id,
                        "home_team": v["match"].home_team,
                        "away_team": v["match"].away_team,
                        "current_score": v["match"].current_score,
                        "home_odds": v["match"].home_odds,
                        "away_odds": v["match"].away_odds,
                    },
                    "bookmaker": v["bookmaker"],
                    "last_check": v["last_check"]
                }
                for k, v in self.active_matches.items()
            }
        }
        
        with open(self.data_dir / "state.json", 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def load_state(self):
        """Load state from file"""
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.tracked_bets = state.get("tracked_bets", {})
                logger.info(f"Loaded {len(self.tracked_bets)} tracked bets")
    
    def get_status(self) -> str:
        """Get system status"""
        return f"""
🚀 **CASHOUT SYSTEM STATUS** 🚀

📊 **Tracking**
Tracked Bets: {len(self.tracked_bets)}
Active Matches: {len(self.active_matches)}

⚙️ **Config**
Check Interval: {self.check_interval}s
Status: {'🟢 RUNNING' if self.running else '🔴 STOPPED'}

📈 **Last Check**
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    async def run_once(self):
        """Run one monitoring cycle"""
        await self._check_all_matches()
        return self.get_status()


# Example usage
async def main():
    """Run the cash-out system"""
    async with CashOutOrchestrator() as orchestrator:
        # Load previous state
        orchestrator.load_state()
        
        # Add example tracked bets (in real usage, these come from user input)
        orchestrator.add_tracked_bet(
            match_id="demo_1",
            home_team="Olympiacos",
            away_team="PAOK",
            bookmaker="Stoiximan",
            original_odds=2.50,
            stake=100.0
        )
        
        # Run one check
        print("Running initial check...")
        await orchestrator.run_once()
        
        # Start continuous monitoring
        print("Starting continuous monitoring...")
        await orchestrator.monitor_live_matches()


if __name__ == "__main__":
    asyncio.run(main())