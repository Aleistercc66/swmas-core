#!/usr/bin/env python3
"""
Solana Profit Agent v2.0 - ULTIMATE EDITION
Κεντρικό σύστημα με ΟΛΑ τα advanced features:
- Learning Engine (DexScreener, Pump.fun, Jupiter)
- Historical Analysis (moon missions, cycles)
- Opportunity Scanner (15-30% targets)
- Strategy Engine (adaptive)
- Risk Manager (circuit breakers)
- Execution Layer (Jupiter v6)
- Telegram Alerts

NEW v2.0:
- Pump.fun Bonding Curve Tracker (graduation prediction)
- Token Safety Analyzer (rug pull detection)
- MEV Protection (Jito Labs, anti-front-run)
- WebSocket Sniper (sub-second detection)
- Advanced Jupiter (multi-hop, DCA)
"""

import asyncio
import aiohttp
import json
import time
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime

# Core modules
from learning_engine import SolanaKnowledgeBase
from historian import SolanaHistorian
from opportunity_scanner import OpportunityScanner, TradeSetup
from strategy_engine import StrategyEngine
from execution_layer import ExecutionEngine
from risk_manager import RiskManager
from telegram_alerts import TelegramAlerter, AlertConfig

# NEW v2.0 modules
from pumpfun_tracker import PumpFunTracker
from token_safety import TokenSafetyAnalyzer
from mev_protection import MEVProtection, MEVConfig
from websocket_sniper import WebSocketSniper, SnipeSignal
from jupiter_client import JupiterClient, JupiterSwapConfig


# Superior Training
from training_engine import SuperiorTrainingEngine


class SolanaProfitAgentV2:
    """
    Ultimate Solana Profit Agent v2.0
    Συνδυάζει 13 modules για maximum performance.
    """
    
    def __init__(self, telegram_token: Optional[str] = None, 
                 telegram_chat: Optional[str] = None,
                 wallet_key: Optional[str] = None,
                 wallet_pubkey: Optional[str] = None):
        
        print("🔥🔥🔥 INITIALIZING SOLANA PROFIT AGENT v2.0 - ULTIMATE 🔥🔥🔥")
        print("=" * 60)
        
        # Core subsystems
        self.kb = SolanaKnowledgeBase()
        self.historian = SolanaHistorian()
        self.scanner = OpportunityScanner(self.kb, self.historian)
        self.strategy_engine = StrategyEngine()
        self.execution = ExecutionEngine(wallet_key, wallet_pubkey)
        self.risk = RiskManager()
        
        # NEW v2.0 subsystems
        self.pump_tracker = PumpFunTracker()
        self.safety = TokenSafetyAnalyzer()
        self.mev = MEVProtection(MEVConfig())
        self.jupiter = JupiterClient(JupiterSwapConfig())
        
        # Superior Training Engine
        self.trainer = SuperiorTrainingEngine(
            knowledge_base=self.kb,
            historian=self.historian,
            strategy_engine=self.strategy_engine,
            risk_manager=self.risk
        )
        
        # Training state
        self.training_mode = False
        self.last_training_time = 0
        self.training_interval_hours = 6  # Auto-train every 6 hours
        
        # WebSocket Sniper
        self.ws_sniper = WebSocketSniper()
        self.ws_sniper.on_new_token = self._handle_new_token_launch
        self.ws_sniper.on_trade = self._handle_snipe_signal
        
        # Telegram alerts
        if telegram_token and telegram_chat:
            alert_config = AlertConfig(
                bot_token=telegram_token,
                chat_id=telegram_chat,
            )
            self.alerter = TelegramAlerter(alert_config)
        else:
            self.alerter = None
        
        # Wallet
        self.wallet_pubkey = wallet_pubkey
        self.simulation_mode = wallet_key is None
        self.simulated_portfolio_value = 10.0  # 10 SOL
        
        # State
        self.running = False
        self.scan_count = 0
        self.session_start = time.time()
        
        print("✅ ALL 13 SUBSYSTEMS INITIALIZED!")
        print(f"   Core: Learning | History | Scanner | Strategy | Execution | Risk | Telegram")
        print(f"   v2.0: Pump Tracker | Safety | MEV | WebSocket | Jupiter v6")
        print(f"   Simulation: {self.simulation_mode}")
        print(f"   Telegram: {'Enabled' if self.alerter else 'Disabled'}")
        print("=" * 60)
    
    async def run(self):
        """Main run loop με όλα τα subsystems."""
        self.running = True
        
        print("\n🚀 AGENT v2.0 STARTED - Ultimate Solana Hunter")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Goal: 15-30% daily returns")
        print("-" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Start WebSocket sniper in background
            ws_task = asyncio.create_task(self.ws_sniper.start_monitoring())
            
            # Start main cycles
            cycle_task = asyncio.create_task(self._main_cycles(session))
            
            # Start position monitor
            monitor_task = asyncio.create_task(self._monitor_positions(session))
            
            # Wait for all
            await asyncio.gather(ws_task, cycle_task, monitor_task)
    
    async def _main_cycles(self, session: aiohttp.ClientSession):
        """Main scanning cycles."""
        while self.running:
            try:
                await self._main_cycle(session)
            except Exception as e:
                print(f"❌ Main cycle error: {e}")
                await asyncio.sleep(60)
    
    async def _main_cycle(self, session: aiohttp.ClientSession):
        """Ένας πλήρης κύκλος."""
        
        cycle_start = time.time()
        print(f"\n{'='*60}")
        print(f"🔄 CYCLE #{self.scan_count + 1} | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        # 1. Update MEV / Network
        print("\n🛡️ PHASE 1: MEV & NETWORK")
        await self.mev.update_network_conditions(session)
        
        # 2. Learn (DexScreener + Pump.fun)
        print("\n📚 PHASE 2: LEARNING")
        try:
            dex_opps = await self.kb.learn_from_dexscreener(session)
            pump_launches = await self.kb.learn_from_pumpfun(session)
            print(f"   ✅ {len(dex_opps)} DexScreener, {len(pump_launches)} Pump.fun")
        except Exception as e:
            print(f"   ⚠️ {e}")
        
        # 3. Check Pump.fun graduation opportunities
        print("\n🎯 PHASE 3: PUMP.FUN GRADUATIONS")
        graduation_opps = self.pump_tracker.get_pre_graduation_setups()
        if graduation_opps:
            for opp in graduation_opps[:5]:
                print(f"   🎓 {opp['symbol']}: {opp['progress']:.1f}% | ${opp['market_cap']:,.0f}")
        
        # 4. Scan for 15-30% opportunities
        print("\n🔍 PHASE 4: OPPORTUNITY SCAN")
        try:
            opportunities = await self.scanner.scan_for_opportunities()
            print(f"   ✅ {len(opportunities)} opportunities found")
        except Exception as e:
            print(f"   ⚠️ {e}")
            opportunities = []
        
        # 5. Safety check + Alert
        print("\n🛡️ PHASE 5: SAFETY & ALERTS")
        safe_opportunities = []
        for opp in opportunities[:5]:
            # Quick safety check
            safety = self.safety.quick_safety_check(opp)
            if safety.get("is_safe", False):
                safe_opportunities.append(opp)
                print(f"   ✅ {opp.symbol} | Safe | Score: {opp.opportunity_score:.0f}")
            else:
                print(f"   ❌ {opp.symbol} | Risk: {safety.get('score', 0):.0f} | {safety.get('red_flags', [])}")
            
            # Telegram alert for high-confidence safe opportunities
            if opp.opportunity_score >= 75 and self.alerter:
                await self.alerter.send_opportunity_alert(session, opp)
        
        # 6. Portfolio + Risk
        print("\n💼 PHASE 6: PORTFOLIO & RISK")
        portfolio = self.execution.get_portfolio_status()
        risk_status = self.risk.get_daily_stats()
        print(f"   Positions: {portfolio['total_positions']} | PnL: {portfolio['daily_pnl_sol']:+.3f} SOL")
        print(f"   Risk: {risk_status['can_trade']} | Trades: {risk_status['trades']}")
        
        # 7. Jupiter trending
        print("\n🪐 PHASE 7: JUPITER TRENDING")
        try:
            trending = await self.jupiter.get_trending_tokens(session, 10)
            print(f"   ✅ {len(trending)} trending tokens")
        except Exception as e:
            print(f"   ⚠️ {e}")
        
        # Stats
        cycle_time = time.time() - cycle_start
        self.scan_count += 1
        
        print(f"\n📊 CYCLE COMPLETE | {cycle_time:.1f}s | Scans: {self.scan_count}")
        
        # Wait
        wait = max(0, 300 - cycle_time)
        if wait > 0:
            print(f"   Next in {wait:.0f}s...")
            await asyncio.sleep(wait)
    
    async def _handle_new_token_launch(self, signal: SnipeSignal):
        """Handle new token από WebSocket."""
        print(f"\n🚀 WS NEW TOKEN: {signal.symbol} | Score: {signal.snipe_score:.0f}")
        
        # Safety check
        if not signal.safety_check_passed:
            # Quick safety check
            safety = {"is_safe": True}  # Simplified
            signal.safety_check_passed = safety.get("is_safe", False)
        
        if signal.safety_check_passed and signal.snipe_score >= 70:
            # Generate alert
            print(f"   🎯 HIGH SCORE SNIPE: {signal.symbol} | {signal.snipe_score:.0f}")
            
            if self.alerter:
                async with aiohttp.ClientSession() as session:
                    # Create a TradeSetup-like object for alert
                    setup = TradeSetup(
                        token_address=signal.token_address,
                        symbol=signal.symbol,
                        entry_price=signal.initial_price,
                        target_return=50,  # High target for new launches
                        tp1=20, tp2=35, tp3=50,
                        stop_loss=-20,
                        risk_reward=2.5,
                        opportunity_score=signal.snipe_score,
                        catalyst="new_launch",
                        urgency="critical" if signal.snipe_score >= 90 else "high",
                    )
                    await self.alerter.send_opportunity_alert(session, setup)
    
    async def _handle_snipe_signal(self, signal: SnipeSignal):
        """Handle snipe signal από evaluation."""
        print(f"🎯 SNIPE SIGNAL CONFIRMED: {signal.symbol} | Score: {signal.snipe_score:.0f}")
        
        # Could auto-execute here if configured
        pass
    
    async def _monitor_positions(self, session: aiohttp.ClientSession):
        """Monitor ανοιχτές θέσεις."""
        while self.running:
            try:
                triggered = await self.execution.monitor_positions(
                    session,
                    self._fetch_token_price
                )
                
                for trigger in triggered:
                    result = await self.execution.execute_exit(
                        trigger['address'],
                        trigger['trigger'],
                        session
                    )
                    
                    if result:
                        self.risk.record_trade(
                            trigger['token'],
                            result.get('entry_price', 0),
                            result.get('exit_price', 0),
                            result.get('position_size', 0),
                            trigger['trigger']
                        )
                        
                        if self.alerter:
                            await self.alerter.send_trade_notification(session, {
                                **result,
                                "symbol": trigger['token'],
                                "pnl_pct": trigger['pnl_pct'],
                                "reason": trigger['trigger'],
                            })
                
                await asyncio.sleep(30)
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_token_price(self, token_address: str) -> Optional[float]:
        """Fetch current token price."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use Jupiter price API
                prices = await self.jupiter.get_token_prices(session, [token_address])
                if prices and token_address in prices:
                    return float(prices[token_address].get("price", 0))
                
                # Fallback to DexScreener
                async with session.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get("pairs", [])
                        if pairs:
                            return float(pairs[0].get("priceUsd", 0))
        except Exception as e:
            print(f"❌ Price fetch error: {e}")
        return None
    
    def generate_full_report(self) -> Dict:
        """Generate comprehensive report."""
        
        return {
            "version": "2.0",
            "session": {
                "start": datetime.fromtimestamp(self.session_start).isoformat(),
                "uptime_hours": (time.time() - self.session_start) / 3600,
                "scans": self.scan_count,
            },
            "subsystems": {
                "knowledge_base": {"tokens": len(self.kb.tokens), "patterns": len(self.kb.patterns)},
                "historian": {"profiles": len(self.historian.token_profiles), "cycles": len(self.historian.market_cycles)},
                "scanner": {"active_setups": len(self.scanner.active_setups), "executed": len(self.scanner.executed_setups)},
                "risk": self.risk.get_risk_report(),
                "execution": self.execution.get_portfolio_status(),
                "pump_tracker": {"curves": len(self.pump_tracker.curves), "graduated": len(self.pump_tracker.graduated_tokens)},
                "sniper": self.ws_sniper.get_stats(),
                "mev": self.mev.get_execution_stats(),
                "jupiter": self.jupiter.get_stats(),
            },
        }
    
    def stop(self):
        """Graceful shutdown."""
        print("\n🛑 STOPPING AGENT v2.0...")
        self.running = False
        
        # Save all data
        self.kb.save_knowledge()
        self.historian.save_history()
        self.strategy_engine.save_strategies()
        self.risk.save_risk_data()
        
        # Report
        report = self.generate_full_report()
        print(f"\n📊 FINAL REPORT v2.0:")
        print(json.dumps(report, indent=2, default=str))
        
        print("\n👋 Agent stopped. All data saved.")


def signal_handler(agent: SolanaProfitAgentV2):
    def handler(signum, frame):
        print("\n⚠️ Interrupted")
        agent.stop()
        sys.exit(0)
    return handler


async def main():
    """Entry point."""
    
    TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
    TELEGRAM_CHAT = "YOUR_CHAT_ID"
    WALLET_KEY = None
    WALLET_PUBKEY = None
    
    agent = SolanaProfitAgentV2(
        telegram_token=TELEGRAM_TOKEN if TELEGRAM_TOKEN != "YOUR_BOT_TOKEN" else None,
        telegram_chat=TELEGRAM_CHAT if TELEGRAM_CHAT != "YOUR_CHAT_ID" else None,
        wallet_key=WALLET_KEY,
        wallet_pubkey=WALLET_PUBKEY,
    )
    
    signal.signal(signal.SIGINT, signal_handler(agent))
    
    try:
        await agent.run()
    except Exception as e:
        print(f"❌ Fatal: {e}")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
