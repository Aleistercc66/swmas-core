import asyncio
import aiohttp
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class YieldPosition:
    """Active yield farming position"""
    protocol: str
    pool: str
    token_a: str
    token_b: str
    deposit_amount: float
    current_value: float
    entry_apr: float
    current_apr: float
    impermanent_loss: float
    fees_earned: float
    rewards_earned: float
    entry_time: datetime = field(default_factory=datetime.now)
    last_harvest: datetime = field(default_factory=datetime.now)
    status: str = 'active'  # active, exited, harvesting

@dataclass
class YieldPool:
    """Yield pool opportunity"""
    protocol: str
    pool_address: str
    token_a: str
    token_b: str
    tvl: float
    apr: float
    fee_apr: float
    reward_apr: float
    total_apr: float
    volume_24h: float
    impermanent_loss_30d: float
    risk_score: float  # 0-1
    min_deposit: float
    lock_period: Optional[int] = None


class YieldFarmingOptimizer:
    """
    Autonomous Yield Farming Optimizer
    
    Optimizes capital allocation across yield farms based on:
    - Risk-adjusted returns (Sharpe-like)
    - Impermanent loss risk
    - Fee generation
    - Reward token value
    - Protocol safety score
    
    Strategies:
    1. Conservative: Stablecoin pairs, low IL, 5-15% APR
    2. Balanced: Major pairs, medium IL, 15-30% APR
    3. Aggressive: New pools, high IL, 30%+ APR
    4. Delta Neutral: Hedged positions, minimized directional risk
    
    Auto-harvests and compounds rewards.
    """
    
    def __init__(self, wallet_config: Dict, risk_profile: str = 'balanced'):
        self.wallet = wallet_config
        self.risk_profile = risk_profile
        self.positions: List[YieldPosition] = []
        self.pools: List[YieldPool] = []
        self.total_deposited = 0.0
        self.total_earned = 0.0
        self.active = False
        
        # Risk profile settings
        self.risk_settings = {
            'conservative': {
                'max_il_tolerance': 0.02,
                'min_tvl': 1000000,
                'max_pool_allocation': 0.40,
                'min_apr': 0.05,
                'harvest_frequency': 1,  # days
            },
            'balanced': {
                'max_il_tolerance': 0.05,
                'min_tvl': 500000,
                'max_pool_allocation': 0.30,
                'min_apr': 0.10,
                'harvest_frequency': 1,
            },
            'aggressive': {
                'max_il_tolerance': 0.15,
                'min_tvl': 100000,
                'max_pool_allocation': 0.25,
                'min_apr': 0.20,
                'harvest_frequency': 1,
            }
        }
        
        self.settings = self.risk_settings[risk_profile]
        
    async def start(self):
        """Start autonomous yield farming"""
        self.active = True
        logger.info(f"🌾 Yield Farming Optimizer STARTED ({self.risk_profile} mode)")
        
        tasks = [
            asyncio.create_task(self._discovery_loop()),
            asyncio.create_task(self._optimization_loop()),
            asyncio.create_task(self._harvest_loop()),
            asyncio.create_task(self._monitoring_loop()),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _discovery_loop(self):
        """Discover new yield pools"""
        while self.active:
            try:
                new_pools = await self._discover_pools()
                self.pools = new_pools  # Replace with fresh data
                
                logger.info(f"Discovered {len(new_pools)} yield pools")
                await asyncio.sleep(3600)  # Hourly refresh
                
            except Exception as e:
                logger.error(f"Pool discovery error: {e}")
                await asyncio.sleep(600)
                
    async def _optimization_loop(self):
        """Optimize portfolio allocation"""
        while self.active:
            try:
                # Calculate optimal allocation
                target = self._calculate_optimal_allocation()
                
                # Rebalance to target
                await self._rebalance_portfolio(target)
                
                await asyncio.sleep(86400)  # Daily rebalance
                
            except Exception as e:
                logger.error(f"Optimization error: {e}")
                await asyncio.sleep(3600)
                
    async def _harvest_loop(self):
        """Auto-harvest and compound rewards"""
        while self.active:
            try:
                for position in self.positions:
                    if position.status == 'active':
                        days_since_harvest = (datetime.now() - position.last_harvest).days
                        
                        if days_since_harvest >= self.settings['harvest_frequency']:
                            await self._harvest_position(position)
                            
                await asyncio.sleep(3600)  # Check hourly
                
            except Exception as e:
                logger.error(f"Harvest error: {e}")
                await asyncio.sleep(600)
                
    async def _monitoring_loop(self):
        """Monitor positions and exit if needed"""
        while self.active:
            try:
                for position in self.positions:
                    if position.status == 'active':
                        # Check if pool degraded
                        pool = next((p for p in self.pools if p.pool_address == position.pool), None)
                        
                        if pool:
                            # Exit if APR dropped too much
                            if pool.total_apr < position.entry_apr * 0.5:
                                logger.info(f"APR dropped significantly, exiting: {position.protocol}")
                                await self._exit_position(position)
                                
                            # Exit if IL exceeded tolerance
                            if position.impermanent_loss > self.settings['max_il_tolerance']:
                                logger.info(f"IL exceeded tolerance, exiting: {position.protocol}")
                                await self._exit_position(position)
                                
                await asyncio.sleep(300)  # 5-minute check
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)
                
    async def _discover_pools(self) -> List[YieldPool]:
        """Discover yield pools from protocols"""
        pools = []
        
        # Solana DEX pools
        solana_pools = [
            YieldPool(
                protocol='Raydium',
                pool_address='pool1',
                token_a='SOL',
                token_b='USDC',
                tvl=150000000,
                apr=0.12,
                fee_apr=0.08,
                reward_apr=0.04,
                total_apr=0.12,
                volume_24h=50000000,
                impermanent_loss_30d=0.02,
                risk_score=0.15,
                min_deposit=10
            ),
            YieldPool(
                protocol='Orca',
                pool_address='pool2',
                token_a='SOL',
                token_b='mSOL',
                tvl=80000000,
                apr=0.06,
                fee_apr=0.04,
                reward_apr=0.02,
                total_apr=0.06,
                volume_24h=20000000,
                impermanent_loss_30d=0.005,
                risk_score=0.05,
                min_deposit=5
            ),
            YieldPool(
                protocol='Raydium',
                pool_address='pool3',
                token_a='BONK',
                token_b='SOL',
                tvl=25000000,
                apr=0.45,
                fee_apr=0.30,
                reward_apr=0.15,
                total_apr=0.45,
                volume_24h=30000000,
                impermanent_loss_30d=0.08,
                risk_score=0.45,
                min_deposit=50
            ),
            YieldPool(
                protocol='Kamino',
                pool_address='pool4',
                token_a='USDC',
                token_b='SOL',
                tvl=45000000,
                apr=0.18,
                fee_apr=0.10,
                reward_apr=0.08,
                total_apr=0.18,
                volume_24h=15000000,
                impermanent_loss_30d=0.03,
                risk_score=0.20,
                min_deposit=20
            ),
            YieldPool(
                protocol='Marinade',
                pool_address='pool5',
                token_a='mSOL',
                token_b='SOL',
                tvl=120000000,
                apr=0.065,
                fee_apr=0.03,
                reward_apr=0.035,
                total_apr=0.065,
                volume_24h=10000000,
                impermanent_loss_30d=0.001,
                risk_score=0.05,
                min_deposit=1
            ),
            YieldPool(
                protocol='Jito',
                pool_address='pool6',
                token_a='JitoSOL',
                token_b='SOL',
                tvl=95000000,
                apr=0.08,
                fee_apr=0.04,
                reward_apr=0.04,
                total_apr=0.08,
                volume_24h=8000000,
                impermanent_loss_30d=0.002,
                risk_score=0.08,
                min_deposit=1
            ),
            YieldPool(
                protocol='Drift',
                pool_address='pool7',
                token_a='USDC',
                token_b='perp-SOL',
                tvl=30000000,
                apr=0.35,
                fee_apr=0.25,
                reward_apr=0.10,
                total_apr=0.35,
                volume_24h=40000000,
                impermanent_loss_30d=0.05,
                risk_score=0.55,
                min_deposit=100
            ),
            YieldPool(
                protocol='Meteora',
                pool_address='pool8',
                token_a='SOL',
                token_b='USDT',
                tvl=20000000,
                apr=0.22,
                fee_apr=0.14,
                reward_apr=0.08,
                total_apr=0.22,
                volume_24h=12000000,
                impermanent_loss_30d=0.04,
                risk_score=0.25,
                min_deposit=15
            ),
        ]
        
        pools.extend(solana_pools)
        
        # Filter by minimum TVL and risk
        filtered = [p for p in pools if p.tvl >= self.settings['min_tvl'] and p.risk_score <= self._max_risk_score()]
        
        return filtered
        
    def _max_risk_score(self) -> float:
        """Get maximum risk score based on profile"""
        risk_scores = {
            'conservative': 0.20,
            'balanced': 0.40,
            'aggressive': 0.70
        }
        return risk_scores[self.risk_profile]
        
    def _calculate_optimal_allocation(self) -> Dict[str, float]:
        """Calculate optimal allocation using risk-adjusted returns"""
        if not self.pools:
            return {}
            
        total_capital = self.wallet.get('balance', 0) * 0.8  # 80% deployable
        
        # Calculate risk-adjusted scores
        scores = []
        for pool in self.pools:
            # Sharpe-like ratio: APR / risk_score
            if pool.risk_score > 0:
                sharpe = pool.total_apr / pool.risk_score
            else:
                sharpe = pool.total_apr * 10  # Low risk bonus
                
            # IL penalty
            il_penalty = 1 - (pool.impermanent_loss_30d / self.settings['max_il_tolerance'])
            
            # Volume score (higher volume = more fees)
            volume_score = min(pool.volume_24h / pool.tvl, 2.0)  # Max 2x
            
            total_score = sharpe * max(il_penalty, 0.1) * (0.5 + volume_score * 0.5)
            scores.append((pool, total_score))
            
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Allocate top pools, respecting max allocation per pool
        allocation = {}
        remaining = total_capital
        
        for pool, score in scores[:5]:  # Top 5 pools
            if remaining <= 0:
                break
                
            max_alloc = min(
                total_capital * self.settings['max_pool_allocation'],
                remaining
            )
            
            # Scale by score (higher score = more allocation)
            weight = score / sum(s for _, s in scores[:5])
            alloc = min(max_alloc * weight, remaining)
            
            if alloc >= pool.min_deposit:
                allocation[pool.pool_address] = alloc
                remaining -= alloc
                
        return allocation
        
    async def _rebalance_portfolio(self, target: Dict[str, float]):
        """Rebalance portfolio to target allocation"""
        current_alloc = {p.pool: p.deposit_amount for p in self.positions if p.status == 'active'}
        
        # Exit positions that are overallocated or not in target
        for pool_addr in list(current_alloc.keys()):
            if pool_addr not in target or current_alloc[pool_addr] > target.get(pool_addr, 0) * 1.2:
                position = next((p for p in self.positions if p.pool == pool_addr), None)
                if position:
                    await self._exit_position(position)
                    
        # Enter new positions or add to existing
        for pool_addr, target_amount in target.items():
            current = current_alloc.get(pool_addr, 0)
            
            if current < target_amount * 0.8:  # If underallocated by 20%
                pool = next((p for p in self.pools if p.pool_address == pool_addr), None)
                if pool:
                    await self._enter_position(pool, target_amount - current)
                    
    async def _enter_position(self, pool: YieldPool, amount: float):
        """Enter a yield position"""
        logger.info(f"🌾 Entering: {pool.protocol} | {amount:.2f} SOL | {pool.total_apr:.1%} APR")
        
        position = YieldPosition(
            protocol=pool.protocol,
            pool=pool.pool_address,
            token_a=pool.token_a,
            token_b=pool.token_b,
            deposit_amount=amount,
            current_value=amount,
            entry_apr=pool.total_apr,
            current_apr=pool.total_apr,
            impermanent_loss=0.0,
            fees_earned=0.0,
            rewards_earned=0.0
        )
        
        self.positions.append(position)
        self.total_deposited += amount
        
    async def _exit_position(self, position: YieldPosition):
        """Exit a yield position"""
        logger.info(f"🌾 Exiting: {position.protocol} | IL: {position.impermanent_loss:.2%} | Fees: {position.fees_earned:.4f}")
        
        # Calculate P&L
        pnl = position.current_value - position.deposit_amount
        self.total_earned += pnl
        
        position.status = 'exited'
        self.total_deposited -= position.deposit_amount
        
    async def _harvest_position(self, position: YieldPosition):
        """Harvest rewards from position"""
        days_since = (datetime.now() - position.last_harvest).days
        
        # Calculate earned rewards
        daily_apr = position.current_apr / 365
        rewards = position.current_value * daily_apr * days_since
        
        position.rewards_earned += rewards
        position.last_harvest = datetime.now()
        
        logger.info(f"🌾 Harvested: {position.protocol} | +{rewards:.4f} SOL")
        
        # Auto-compound (reinvest rewards)
        if rewards > 0.01:  # Min 0.01 SOL to compound
            position.current_value += rewards
            self.total_earned += rewards
            
    def get_report(self) -> Dict:
        """Get yield farming report"""
        active = [p for p in self.positions if p.status == 'active']
        
        return {
            'total_deposited': self.total_deposited,
            'total_earned': self.total_earned,
            'active_positions': len(active),
            'current_apr_weighted': np.mean([p.current_apr for p in active]) if active else 0,
            'total_il': sum(p.impermanent_loss for p in active),
            'pools_tracked': len(self.pools),
            'risk_profile': self.risk_profile,
        }


# ─── MAIN ───
async def main():
    """Run yield farming optimizer"""
    wallet = {'address': 'dummy', 'balance': 10.0}
    optimizer = YieldFarmingOptimizer(wallet, 'balanced')
    await optimizer.start()


if __name__ == "__main__":
    asyncio.run(main())
