import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

from .execution_engine import ZeroLatencyExecutionEngine, ExecutionConfig
from .signal_composer import SignalComposer, MarketData, Signal
from .risk_manager import RiskManager, RiskProfile, Position
from .mev_protection import MEVProtection, MEVConfig

logger = logging.getLogger(__name__)

@dataclass
class SWMASSystemConfig:
    """Complete SWMAS system configuration"""
    # Execution
    rpc_endpoint: str = "https://mainnet.helius-rpc.com/"
    jupiter_api: str = "https://quote-api.jup.ag/v6"
    use_jito: bool = True
    
    # Risk
    max_position_pct: float = 0.05
    max_daily_risk_pct: float = 0.10
    stop_loss_pct: float = 0.15
    trailing_stop_pct: float = 0.10
    
    # Signal
    min_liquidity: float = 20000
    min_confidence: float = 60
    
    # Paper trading (default True for safety)
    paper_mode: bool = True
    
    # Bankroll
    initial_bankroll: float = 10.0


class SWMASTradingSystem:
    """
    SWMAS Quantitative Trading System — Main Orchestrator.
    
    Integrates:
    - SignalComposer: Multi-factor signal generation
    - ExecutionEngine: Zero-latency trade execution
    - RiskManager: Kelly sizing + multi-layer stops
    - MEVProtection: Jito bundle submission
    
    Pipeline:
    1. Market data ingestion (WebSocket/RPC)
    2. Signal composition (5-factor analysis)
    3. Risk validation (Kelly sizing + confluence)
    4. Execution (Jupiter + Jito bundles)
    5. Position monitoring (stops + profit tiers)
    """
    
    def __init__(self, config: SWMASSystemConfig):
        self.config = config
        self.initialized = False
        
        # Subsystems (initialized on start)
        self.signal_composer: Optional[SignalComposer] = None
        self.execution_engine: Optional[ZeroLatencyExecutionEngine] = None
        self.risk_manager: Optional[RiskManager] = None
        self.mev_protection: Optional[MEVProtection] = None
        
        # State
        self.active = False
        self.trading_task = None
        self.monitor_task = None
        
    async def initialize(self, wallet_keypair=None):
        """Initialize all subsystems"""
        logger.info("🔥 SWMAS Initializing...")
        
        # 1. Signal Composer
        self.signal_composer = SignalComposer(self.config.min_liquidity)
        logger.info("✅ Signal Composer ready")
        
        # 2. Risk Manager
        risk_profile = RiskProfile(
            max_position_pct=self.config.max_position_pct,
            max_daily_risk_pct=self.config.max_daily_risk_pct,
            stop_loss_pct=self.config.stop_loss_pct,
            trailing_stop_pct=self.config.trailing_stop_pct
        )
        self.risk_manager = RiskManager(risk_profile, self.config.initial_bankroll)
        logger.info("✅ Risk Manager ready")
        
        # 3. Execution Engine (if not paper mode)
        if not self.config.paper_mode and wallet_keypair:
            exec_config = ExecutionConfig(
                rpc_endpoint=self.config.rpc_endpoint,
                jupiter_api=self.config.jupiter_api,
                use_jito_bundles=self.config.use_jito
            )
            self.execution_engine = ZeroLatencyExecutionEngine(exec_config, wallet_keypair)
            await self.execution_engine.initialize()
            
            # 4. MEV Protection
            mev_config = MEVConfig(use_jito=self.config.use_jito)
            self.mev_protection = MEVProtection(mev_config, wallet_keypair)
            await self.mev_protection.initialize()
            
            logger.info("✅ Live Execution ready (Jupiter + Jito)")
        else:
            logger.info("📊 Paper Trading Mode — No live execution")
            
        self.initialized = True
        logger.info("🔥 SWMAS SYSTEM READY!")
        
    async def start(self):
        """Start the trading system"""
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
            
        self.active = True
        logger.info("🚀 SWMAS Trading STARTED!")
        
        # Start trading loop
        self.trading_task = asyncio.create_task(self._trading_loop())
        
        # Start monitoring loop
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop(self):
        """Stop the trading system"""
        self.active = False
        
        if self.trading_task:
            self.trading_task.cancel()
        if self.monitor_task:
            self.monitor_task.cancel()
            
        # Cleanup
        if self.execution_engine:
            await self.execution_engine.close()
        if self.mev_protection:
            await self.mev_protection.close()
            
        logger.info("⏹️ SWMAS Trading STOPPED")
        
    async def _trading_loop(self):
        """Main trading signal generation loop"""
        while self.active:
            try:
                # 1. Fetch market data (simulated for now)
                market_data = await self._fetch_market_data()
                
                # 2. Generate signals for all tokens
                signals = await self._generate_signals(market_data)
                
                # 3. Filter actionable signals
                actionable = [s for s in signals if s.confidence >= self.config.min_confidence]
                
                # 4. Execute trades
                for signal in actionable:
                    await self._execute_trade(signal)
                    
                # Wait before next scan
                await asyncio.sleep(5)  # 5-second scan interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
                
    async def _monitor_loop(self):
        """Position monitoring and stop-loss loop"""
        while self.active:
            try:
                # Monitor all open positions
                for mint, position in self.risk_manager.positions.items():
                    if position.status == 'OPEN':
                        exit_signal = await self.risk_manager.monitor_position(
                            mint, self._get_price
                        )
                        
                        if exit_signal:
                            if self.config.paper_mode:
                                logger.info(f"📊 PAPER EXIT: {exit_signal}")
                            else:
                                await self._execute_exit(exit_signal)
                                
                await asyncio.sleep(1)  # 1-second monitoring
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)
                
    async def _fetch_market_data(self) -> List[MarketData]:
        """Fetch market data from Jupiter/Raydium"""
        # TODO: Implement real WebSocket data fetching
        # For now, return empty list
        return []
        
    async def _generate_signals(self, market_data: List[MarketData]) -> List[Signal]:
        """Generate signals for all tokens"""
        if not market_data:
            return []
            
        return await self.signal_composer.batch_compose(market_data)
        
    async def _execute_trade(self, signal: Signal):
        """Execute a trade signal"""
        # Check risk limits
        allowed, reason = self.risk_manager.check_entry_permission(signal.target_mint)
        if not allowed:
            logger.warning(f"Trade rejected: {reason}")
            return
            
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            win_rate=0.45,  # From backtest
            avg_win=0.35,
            avg_loss=0.15,
            signal_confidence=signal.confidence
        )
        
        if position_size <= 0:
            logger.warning("Position size zero — skipped")
            return
            
        # Paper mode
        if self.config.paper_mode:
            # Record paper trade
            position = self.risk_manager.open_position(
                signal.target_mint,
                signal.entry_price,
                position_size,
                'LONG' if signal.direction == 'BUY' else 'SHORT'
            )
            logger.info(f"📊 PAPER TRADE: {signal.target_mint} | {position_size:.4f} SOL | {signal.direction}")
            return
            
        # Live execution
        exec_signal = {
            'mint': signal.target_mint,
            'direction': signal.direction,
            'size': position_size,
            'slippage_bps': 50
        }
        
        result = await self.execution_engine.execute_trade(exec_signal)
        
        if result['status'] == 'SUCCESS':
            # Record position
            position = self.risk_manager.open_position(
                signal.target_mint,
                signal.entry_price,
                position_size,
                'LONG' if signal.direction == 'BUY' else 'SHORT'
            )
            logger.info(f"✅ LIVE TRADE: {signal.target_mint} | {result['tx_id']} | {result['latency_ms']:.0f}ms")
        else:
            logger.error(f"❌ Trade failed: {result['error']}")
            
    async def _execute_exit(self, exit_signal: Dict):
        """Execute an exit signal"""
        if exit_signal['action'] == 'EXIT':
            # Full exit
            exec_signal = {
                'mint': exit_signal['mint'],
                'direction': 'SELL' if exit_signal['reason'] != 'HARD_STOP' else 'SELL',
                'size': self.risk_manager.positions[exit_signal['mint']].remaining_size,
                'slippage_bps': 100  # Wider slippage for exit
            }
            
            result = await self.execution_engine.execute_trade(exec_signal)
            
            if result['status'] == 'SUCCESS':
                logger.info(f"✅ EXIT: {exit_signal['mint']} | {exit_signal['reason']} | {result['tx_id']}")
            else:
                logger.error(f"❌ Exit failed: {result['error']}")
                
        elif exit_signal['action'] == 'PARTIAL_EXIT':
            # Partial profit taking
            exec_signal = {
                'mint': exit_signal['mint'],
                'direction': 'SELL',
                'size': exit_signal['exit_size'],
                'slippage_bps': 75
            }
            
            result = await self.execution_engine.execute_trade(exec_signal)
            
            if result['status'] == 'SUCCESS':
                logger.info(f"✅ PARTIAL EXIT: {exit_signal['mint']} | {exit_signal['reason']} | {exit_signal['exit_size']:.4f} SOL")
                
    async def _get_price(self, mint: str) -> Optional[float]:
        """Get current price for a token"""
        # TODO: Implement real price fetching
        # For now, return mock price
        return 0.001
        
    def get_status(self) -> Dict:
        """Get system status"""
        risk_stats = self.risk_manager.get_stats() if self.risk_manager else {}
        
        return {
            'status': 'ACTIVE' if self.active else 'INACTIVE',
            'mode': 'PAPER' if self.config.paper_mode else 'LIVE',
            'initialized': self.initialized,
            'bankroll': self.config.initial_bankroll,
            'risk_stats': risk_stats,
            'open_positions': len([p for p in self.risk_manager.positions.values() if p.status == 'OPEN']) if self.risk_manager else 0
        }


# ─── MAIN ENTRY POINT ───
async def main():
    """Run SWMAS trading system"""
    config = SWMASSystemConfig(paper_mode=True)
    system = SWMASTradingSystem(config)
    
    await system.initialize()
    await system.start()
    
    # Run for 60 seconds (demo)
    await asyncio.sleep(60)
    
    status = system.get_status()
    print(f"Final status: {status}")
    
    await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
