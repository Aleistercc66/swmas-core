import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
import os

from .zero_to_revenue import ZeroToRevenueEngine, ZeroOpportunity
from .live_wallet import LiveWalletConnector
from .hyperclaw_orchestrator import HyperClawOrchestrator

logger = logging.getLogger(__name__)


class ZeroRevenueLauncher:
    """
    Zero-to-Revenue Launcher
    
    Starts the full pipeline:
    1. Initialize live wallet (if available)
    2. Initialize HyperClaw orchestrator
    3. Discover 20+ zero-capital opportunities
    4. Execute all zero-capital tasks
    5. Transition to growth phase when capital > $10
    6. Scale to full revenue engine
    """
    
    def __init__(self, wallet_address: Optional[str] = None, use_live_wallet: bool = False):
        self.wallet_address = wallet_address
        self.use_live_wallet = use_live_wallet
        self.live_wallet: Optional[LiveWalletConnector] = None
        self.orchestrator: Optional[HyperClawOrchestrator] = None
        self.revenue_engine: Optional[ZeroToRevenueEngine] = None
        self.active = False
        
    async def start(self):
        """Start the zero-to-revenue pipeline"""
        self.active = True
        logger.info("🚀 ZERO-TO-REVENUE LAUNCHER STARTING...")
        
        # 1. Initialize live wallet (if configured)
        if self.use_live_wallet:
            await self._init_wallet()
            
        # 2. Initialize HyperClaw orchestrator
        await self._init_orchestrator()
        
        # 3. Initialize revenue engine
        await self._init_revenue_engine()
        
        # 4. Start the main loop
        await self._main_loop()
        
    async def _init_wallet(self):
        """Initialize live wallet connection"""
        try:
            self.live_wallet = LiveWalletConnector.from_env()
            await self.live_wallet.initialize()
            
            balance = await self.live_wallet.get_balance()
            logger.info(f"🔑 Live wallet connected: {self.live_wallet.keypair.pubkey()}")
            logger.info(f"💰 Balance: {balance:.6f} SOL")
            
            # Update wallet address
            self.wallet_address = str(self.live_wallet.keypair.pubkey())
            
        except Exception as e:
            logger.warning(f"⚠️ Live wallet not available: {e}")
            logger.info("📊 Continuing in paper mode")
            
    async def _init_orchestrator(self):
        """Initialize HyperClaw orchestrator"""
        try:
            self.orchestrator = HyperClawOrchestrator()
            await self.orchestrator.initialize()
            logger.info("✅ HyperClaw orchestrator ready")
        except Exception as e:
            logger.warning(f"⚠️ HyperClaw init failed: {e}")
            
    async def _init_revenue_engine(self):
        """Initialize revenue engine"""
        initial_capital = 0.0
        
        if self.live_wallet:
            balance = await self.live_wallet.get_balance()
            initial_capital = balance * 20  # Approximate USD value (SOL ~$20)
            
        self.revenue_engine = ZeroToRevenueEngine(
            self.wallet_address or "paper_wallet",
            initial_capital
        )
        
        logger.info(f"🎯 Revenue engine initialized | Capital: ${initial_capital:.2f}")
        
    async def _main_loop(self):
        """Main execution loop"""
        while self.active:
            try:
                # Phase 1: Zero-capital opportunities
                if self.revenue_engine.phase == 1:
                    logger.info("🎯 PHASE 1: Zero-Capital Survival Mode")
                    await self._execute_zero_capital_tasks()
                    
                # Phase 2: Growth with minimal capital
                elif self.revenue_engine.phase == 2:
                    logger.info("📈 PHASE 2: Growth Mode")
                    await self._execute_growth_tasks()
                    
                # Phase 3: Full scale
                elif self.revenue_engine.phase == 3:
                    logger.info("🔥 PHASE 3: Scale Mode")
                    await self._execute_scale_tasks()
                    
                # Check phase transition
                await self.revenue_engine._check_phase_transition()
                
                # Report status
                report = self.revenue_engine.get_report()
                logger.info(f"📊 Status: {report}")
                
                # Save progress
                await self._save_progress()
                
                await asyncio.sleep(60)  # 1-minute cycles
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(30)
                
    async def _execute_zero_capital_tasks(self):
        """Execute all zero-capital tasks"""
        # Discover opportunities
        opps = await self.revenue_engine._discover_zero_capital_opportunities()
        
        # Filter to zero-capital only
        zero_capital = [o for o in opps if o.capital_required == 0 and o.status == 'pending']
        
        logger.info(f"🎯 Found {len(zero_capital)} zero-capital tasks to execute")
        
        # Execute each with HyperClaw validation
        for opp in zero_capital[:10]:  # Max 10 per cycle
            try:
                # Validate with HyperClaw if available
                if self.orchestrator:
                    decision = await self.orchestrator.propose_action('revenue', {
                        'protocol': opp.protocol,
                        'type': opp.type,
                        'expected_value': opp.expected_value,
                        'time_required': opp.time_required,
                        'capital_required': opp.capital_required
                    })
                    
                    if decision.hermes_status != 'approved':
                        logger.warning(f"⛔ Task rejected by Hermes: {opp.name}")
                        continue
                        
                # Execute task
                await self.revenue_engine._execute_opportunity(opp)
                
                # Update wallet if live
                if self.live_wallet and opp.earnings > 0:
                    # In real scenario, this would be actual token transfer
                    logger.info(f"💰 Earned: ${opp.earnings:.2f} (paper)")
                    
            except Exception as e:
                logger.error(f"Task execution error: {e}")
                
    async def _execute_growth_tasks(self):
        """Execute growth-phase tasks with minimal capital"""
        opps = await self.revenue_engine._discover_minimal_capital_opportunities()
        
        for opp in opps:
            if opp.capital_required <= self.revenue_engine.capital * 0.3:
                try:
                    await self.revenue_engine._execute_opportunity(opp)
                except Exception as e:
                    logger.error(f"Growth task error: {e}")
                    
    async def _execute_scale_tasks(self):
        """Execute full-scale revenue engine"""
        # Start autonomous revenue engine
        from .autonomous_revenue import AutonomousRevenueEngine
        
        wallet = {
            'address': self.wallet_address,
            'balance': self.revenue_engine.capital
        }
        config = {'risk_level': 'medium'}
        
        engine = AutonomousRevenueEngine(wallet, config)
        await engine.start()
        
    async def _save_progress(self):
        """Save progress to file"""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'wallet': self.wallet_address,
            'phase': self.revenue_engine.phase if self.revenue_engine else 1,
            'capital': self.revenue_engine.capital if self.revenue_engine else 0,
            'total_earned': self.revenue_engine.total_earned if self.revenue_engine else 0,
            'completed_tasks': len(self.revenue_engine.completed) if self.revenue_engine else 0,
        }
        
        # Save to workspace
        progress_file = '/root/.openclaw/workspace/zero_revenue_progress.json'
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
            
    async def stop(self):
        """Stop the launcher"""
        self.active = False
        
        if self.live_wallet:
            await self.live_wallet.close()
            
        logger.info("⏹️ Zero-to-Revenue launcher stopped")


# ─── MAIN ───
async def main():
    """Run zero-to-revenue launcher"""
    
    # Check for live wallet
    use_live = os.environ.get('USE_LIVE_WALLET', 'false').lower() == 'true'
    
    launcher = ZeroRevenueLauncher(
        wallet_address=None,
        use_live_wallet=use_live
    )
    
    try:
        await launcher.start()
    except KeyboardInterrupt:
        await launcher.stop()
        
    # Final report
    if launcher.revenue_engine:
        report = launcher.revenue_engine.get_report()
        print(f"\n🔥 FINAL REPORT: {report}")


if __name__ == "__main__":
    asyncio.run(main())
