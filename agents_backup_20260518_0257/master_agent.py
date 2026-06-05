"""
Master Blockchain Trading Agent
Autonomous intelligence that learns, adapts, and executes
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from blockchain_analyzer import BlockchainAnalyzer, PatternRecognizer
from exchange_manager import (
    MultiExchangeManager, StrategyLearner,
    BinanceConnector, BybitConnector, OKXConnector, JupiterConnector
)
from risk_portfolio import RiskManager, PortfolioOptimizer, RiskLevel, Position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MasterAgent')

@dataclass
class AgentState:
    """Current agent state"""
    mode: str = 'learning'  # learning, trading, paused
    confidence: float = 0
    last_trade: Optional[datetime] = None
    daily_trades: int = 0
    learning_cycles: int = 0
    strategy_performance: Dict = None
    market_regime: str = 'neutral'
    
    def __post_init__(self):
        if self.strategy_performance is None:
            self.strategy_performance = {}

class MasterTradingAgent:
    """
    Master Blockchain Trading Agent
    
    Capabilities:
    - Deep on-chain analysis (Solana, Ethereum)
    - Multi-exchange integration (Binance, Bybit, OKX, Jupiter, Raydium)
    - Adaptive strategy learning
    - Advanced risk management
    - Real-time opportunity detection
    - Autonomous execution
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.state = AgentState()
        
        # Initialize components
        self.blockchain = None
        self.exchanges = None
        self.strategies = None
        self.risk = None
        self.optimizer = None
        self.patterns = None
        
        # Learning system
        self.knowledge_base: Dict = {
            'successful_patterns': [],
            'failed_patterns': [],
            'market_regimes': {},
            'optimal_strategies': {},
            'token_behaviors': {}
        }
        
        # Execution tracking
        self.active_signals: List[Dict] = []
        self.pending_orders: List[Dict] = []
        self.alert_history: List[Dict] = []
        
        # Settings
        self.scan_interval = 300  # 5 minutes
        self.learning_interval = 3600  # 1 hour
        self.max_daily_trades = 10
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🔥 Initializing Master Trading Agent...")
        
        # Blockchain analyzer
        self.blockchain = await BlockchainAnalyzer().__aenter__()
        
        # Exchange manager
        self.exchanges = MultiExchangeManager()
        
        # Add exchanges if API keys provided
        if self.config.get('binance_api_key'):
            self.exchanges.add_exchange(
                'binance',
                BinanceConnector(
                    self.config['binance_api_key'],
                    self.config['binance_api_secret']
                )
            )
        
        if self.config.get('bybit_api_key'):
            self.exchanges.add_exchange(
                'bybit',
                BybitConnector(
                    self.config['bybit_api_key'],
                    self.config['bybit_api_secret']
                )
            )
        
        if self.config.get('okx_api_key'):
            self.exchanges.add_exchange(
                'okx',
                OKXConnector(
                    self.config['okx_api_key'],
                    self.config['okx_api_secret'],
                    self.config.get('okx_passphrase')
                )
            )
        
        # Always add Jupiter (no API key needed)
        self.exchanges.add_exchange('jupiter', JupiterConnector())
        
        # Strategy learner
        self.strategies = StrategyLearner()
        
        # Risk manager
        risk_level = RiskLevel(self.config.get('risk_level', 'moderate'))
        self.risk = RiskManager(risk_level)
        
        # Portfolio optimizer
        self.optimizer = PortfolioOptimizer()
        
        # Pattern recognizer
        self.patterns = PatternRecognizer()
        
        logger.info("✅ All components initialized!")
        
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Master Agent...")
        if self.blockchain:
            await self.blockchain.__aexit__(None, None, None)
    
    async def learn_market(self, hours: int = 24):
        """
        Learning phase: Analyze market patterns without trading
        """
        logger.info(f"📚 Starting learning phase ({hours}h)...")
        self.state.mode = 'learning'
        
        # 1. Scan top tokens
        opportunities = await self.blockchain.scan_opportunities()
        
        for opp in opportunities[:20]:
            token = opp['token']
            
            # Analyze token behavior
            await self._analyze_token_behavior(token.address, hours)
            
            # Record patterns
            patterns = self.patterns.analyze(
                await self._get_token_history(token.address, hours)
            )
            
            # Store in knowledge base
            self.knowledge_base['token_behaviors'][token.symbol] = {
                'patterns': patterns,
                'metrics': token,
                'timestamp': datetime.now()
            }
            
            logger.info(f"📊 Learned: {token.symbol} - Risk: {token.contract_risk_score}/100")
        
        # 2. Learn from historical data
        await self._learn_from_history()
        
        # 3. Optimize strategies
        await self._optimize_strategies()
        
        self.state.learning_cycles += 1
        logger.info(f"✅ Learning complete! Cycles: {self.state.learning_cycles}")
        
    async def _analyze_token_behavior(self, token_address: str, hours: int):
        """Analyze token behavior patterns"""
        # Get on-chain data
        metrics = await self.blockchain.analyze_token(token_address)
        
        # Classify behavior
        behaviors = []
        
        if metrics.whale_transactions_24h > 10:
            behaviors.append('whale_driven')
        
        if metrics.smart_money_inflows > metrics.smart_money_outflows * 2:
            behaviors.append('smart_money_accumulating')
        
        if metrics.holder_growth_24h > 50:
            behaviors.append('viral_growth')
        
        if metrics.volume_24h > metrics.liquidity * 3:
            behaviors.append('high_velocity')
        
        return behaviors
    
    async def _get_token_history(self, token_address: str, hours: int) -> List[Dict]:
        """Get token price history"""
        # Would fetch from API
        # Placeholder implementation
        return []
    
    async def _learn_from_history(self):
        """Learn from historical trade data"""
        logger.info("🧠 Learning from historical patterns...")
        
        # Analyze what worked and what didn't
        for symbol, behavior in self.knowledge_base['token_behaviors'].items():
            patterns = behavior.get('patterns', {})
            
            # Record successful patterns
            if patterns.get('accumulation') and not patterns.get('rugpull_warning'):
                self.knowledge_base['successful_patterns'].append({
                    'symbol': symbol,
                    'pattern': 'accumulation',
                    'timestamp': datetime.now()
                })
            
            # Record failed patterns
            if patterns.get('rugpull_warning'):
                self.knowledge_base['failed_patterns'].append({
                    'symbol': symbol,
                    'pattern': 'rugpull',
                    'timestamp': datetime.now()
                })
    
    async def _optimize_strategies(self):
        """Optimize strategy selection based on market regime"""
        logger.info("🎯 Optimizing strategies...")
        
        # Determine current market regime
        # This would analyze overall market data
        
        # Map regimes to strategies
        self.knowledge_base['optimal_strategies'] = {
            'strong_uptrend': 'momentum',
            'uptrend': 'trend_following',
            'downtrend': 'mean_reversion',
            'volatile': 'scalping',
            'ranging': 'mean_reversion',
            'neutral': 'breakout'
        }
    
    async def scan_opportunities(self) -> List[Dict]:
        """
        Scan for trading opportunities
        """
        logger.info("🔍 Scanning for opportunities...")
        
        opportunities = []
        
        # 1. On-chain opportunities
        chain_opps = await self.blockchain.scan_opportunities()
        
        for opp in chain_opps:
            token = opp['token']
            
            # Check if we know this token's behavior
            behavior = self.knowledge_base['token_behaviors'].get(token.symbol, {})
            
            # Score adjustment based on learning
            learning_boost = 0
            if behavior:
                patterns = behavior.get('patterns', {})
                if patterns.get('accumulation') and patterns.get('smart_money_front_run'):
                    learning_boost = 15
            
            adjusted_score = opp['score'] + learning_boost
            
            if adjusted_score >= 65:
                opportunities.append({
                    **opp,
                    'adjusted_score': adjusted_score,
                    'behavior': behavior,
                    'source': 'on_chain'
                })
        
        # 2. Cross-exchange arbitrage
        if self.exchanges:
            for opp in opportunities:
                symbol = opp['token'].symbol
                arb = await self.exchanges.find_arbitrage(f"{symbol}USDT")
                if arb:
                    opp['arbitrage'] = arb
                    opp['adjusted_score'] += 10
        
        # Sort by adjusted score
        opportunities.sort(key=lambda x: x['adjusted_score'], reverse=True)
        
        logger.info(f"✅ Found {len(opportunities)} opportunities")
        return opportunities[:10]
    
    async def generate_signals(self, opportunities: List[Dict]) -> List[Dict]:
        """
        Generate trading signals from opportunities
        """
        signals = []
        
        for opp in opportunities:
            token = opp['token']
            
            # Get market data for strategy
            market_data = await self._get_market_data(token.symbol)
            
            if len(market_data) < 10:
                continue
            
            # Generate strategy signal
            strategy_signal = self.strategies.generate_signal(market_data)
            
            # Combine with on-chain signal
            combined_confidence = min(100, (opp['adjusted_score'] + strategy_signal['confidence']) / 2)
            
            if strategy_signal['signal'] in ['buy', 'sell'] and combined_confidence >= 60:
                # Calculate position size
                sizing = self.risk.calculate_position_size(
                    symbol=token.symbol,
                    entry_price=token.price,
                    stop_loss=token.price * 0.95,  # 5% stop
                    portfolio_value=self.risk.portfolio.total_equity,
                    confidence=combined_confidence
                )
                
                # Set stop levels
                stops = self.risk.set_stop_levels(token.price, 'long' if strategy_signal['signal'] == 'buy' else 'short')
                
                signal = {
                    'symbol': token.symbol,
                    'address': token.address,
                    'signal': strategy_signal['signal'],
                    'confidence': combined_confidence,
                    'strategy': strategy_signal['strategy'],
                    'regime': strategy_signal['regime'],
                    'entry_price': token.price,
                    'position_size': sizing,
                    'stop_loss': stops['stop_loss'],
                    'take_profit_1': stops['take_profit_1'],
                    'take_profit_2': stops['take_profit_2'],
                    'take_profit_3': stops['take_profit_3'],
                    'trailing_stop': stops['trailing_distance'],
                    'reason': strategy_signal['reason'],
                    'on_chain_signals': opp['signals'],
                    'risk_level': opp['risk_level'],
                    'timestamp': datetime.now()
                }
                
                signals.append(signal)
        
        logger.info(f"🎯 Generated {len(signals)} signals")
        return signals
    
    async def _get_market_data(self, symbol: str) -> List[Any]:
        """Get market data from exchanges"""
        data = []
        
        # Try multiple exchanges
        for name, exchange in self.exchanges.exchanges.items():
            try:
                market_data = await exchange.get_market_data(f"{symbol}USDT")
                data.append(market_data)
            except:
                continue
        
        return data
    
    async def execute_signal(self, signal: Dict) -> Dict:
        """
        Execute a trading signal
        """
        if self.state.daily_trades >= self.max_daily_trades:
            return {'error': 'Daily trade limit reached'}
        
        # Check risk limits
        can_trade, reason = self.risk.check_portfolio_limits(
            signal['position_size']['position_value']
        )
        
        if not can_trade:
            return {'error': f'Risk limit: {reason}'}
        
        # Select best exchange
        best_exchange = await self._select_exchange(signal['symbol'])
        
        if not best_exchange:
            return {'error': 'No suitable exchange'}
        
        # Execute order
        try:
            order = await best_exchange.place_order(
                symbol=f"{signal['symbol']}USDT",
                side=signal['signal'],
                amount=signal['position_size']['quantity'],
                price=signal['entry_price']
            )
            
            # Create position
            position = Position(
                symbol=signal['symbol'],
                entry_price=signal['entry_price'],
                current_price=signal['entry_price'],
                quantity=signal['position_size']['quantity'],
                side='long' if signal['signal'] == 'buy' else 'short',
                entry_time=datetime.now(),
                stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'],
                take_profit_2=signal['take_profit_2'],
                take_profit_3=signal['take_profit_3'],
                trailing_distance=signal['trailing_stop']
            )
            
            self.risk.update_portfolio(position)
            
            self.state.daily_trades += 1
            self.state.last_trade = datetime.now()
            
            return {
                'success': True,
                'order': order,
                'position': position,
                'signal': signal
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _select_exchange(self, symbol: str) -> Optional[Any]:
        """Select best exchange for execution"""
        best = None
        best_liquidity = 0
        
        for name, exchange in self.exchanges.exchanges.items():
            try:
                if name == 'jupiter':
                    continue  # Jupiter doesn't have traditional orderbook
                
                ob = await exchange.get_orderbook(f"{symbol}USDT")
                liquidity = sum(b[1] for b in ob.bids[:5]) + sum(a[1] for a in ob.asks[:5])
                
                if liquidity > best_liquidity:
                    best_liquidity = liquidity
                    best = exchange
            except:
                continue
        
        return best
    
    async def monitor_positions(self):
        """
        Monitor open positions and manage exits
        """
        for symbol, position in list(self.risk.portfolio.positions.items()):
            # Update current price
            market_data = await self._get_market_data(symbol)
            if market_data:
                position.current_price = market_data[-1].price
            
            # Update trailing stop
            position.update_trailing_stop()
            
            # Check exit conditions
            should_exit, reason = position.should_exit
            
            if should_exit:
                logger.info(f"🚨 Exit signal for {symbol}: {reason}")
                
                # Close position
                result = self.risk.close_position(symbol, position.current_price, reason)
                
                # Update strategy performance
                self.strategies.update_performance(
                    self.strategies.best_strategy or 'unknown',
                    result['pnl']
                )
                
                # Log the trade
                logger.info(f"💰 Closed {symbol}: P&L ${result['pnl']:,.2f} ({result['pnl_pct']:.2f}%)")
    
    async def get_status_report(self) -> Dict:
        """
        Get comprehensive agent status report
        """
        portfolio_stats = self.risk.get_portfolio_stats()
        strategy_perf = self.strategies.get_strategy_performance()
        
        return {
            'agent_state': {
                'mode': self.state.mode,
                'confidence': self.state.confidence,
                'daily_trades': self.state.daily_trades,
                'learning_cycles': self.state.learning_cycles,
                'market_regime': self.state.market_regime
            },
            'portfolio': {
                'total_equity': self.risk.portfolio.total_equity,
                'total_pnl': self.risk.portfolio.total_pnl,
                'exposure_pct': self.risk.portfolio.margin_used_pct,
                'open_positions': self.risk.portfolio.position_count,
                'available_cash': self.risk.portfolio.available_cash
            },
            'performance': portfolio_stats,
            'strategies': strategy_perf,
            'knowledge': {
                'tokens_learned': len(self.knowledge_base['token_behaviors']),
                'successful_patterns': len(self.knowledge_base['successful_patterns']),
                'failed_patterns': len(self.knowledge_base['failed_patterns'])
            }
        }
    
    async def run(self):
        """
        Main agent loop
        """
        logger.info("🚀 Starting Master Trading Agent...")
        
        # Initialize
        await self.initialize()
        
        try:
            while True:
                # 1. Learning phase (every hour)
                if self.state.learning_cycles == 0 or (datetime.now() - self.state.last_trade).seconds > self.learning_interval:
                    await self.learn_market(hours=24)
                
                # 2. Scan opportunities
                opportunities = await self.scan_opportunities()
                
                # 3. Generate signals
                signals = await self.generate_signals(opportunities)
                
                # 4. Execute high-confidence signals
                for signal in signals:
                    if signal['confidence'] >= 75:
                        result = await self.execute_signal(signal)
                        if result.get('success'):
                            logger.info(f"✅ Executed: {signal['symbol']} {signal['signal']} @ ${signal['entry_price']}")
                
                # 5. Monitor positions
                await self.monitor_positions()
                
                # 6. Log status
                if len(self.risk.portfolio.positions) > 0:
                    status = await self.get_status_report()
                    logger.info(f"📊 Portfolio: ${status['portfolio']['total_equity']:,.2f} | P&L: ${status['portfolio']['total_pnl']:,.2f}")
                
                # Wait for next cycle
                await asyncio.sleep(self.scan_interval)
                
        except Exception as e:
            logger.error(f"Agent error: {e}")
        finally:
            await self.shutdown()


# Telegram Alert System
class AlertSystem:
    """Send alerts to Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_signal_alert(self, signal: Dict):
        """Send trade signal alert"""
        message = f"""
🎯 *TRADING SIGNAL*

*Symbol:* {signal['symbol']}
*Signal:* {'🟢 BUY' if signal['signal'] == 'buy' else '🔴 SELL'}
*Confidence:* {signal['confidence']:.0f}%
*Strategy:* {signal['strategy']}

*Entry:* ${signal['entry_price']:.4f}
*Stop Loss:* ${signal['stop_loss']:.4f}
*TP1:* ${signal['take_profit_1']:.4f}
*TP2:* ${signal['take_profit_2']:.4f}
*TP3:* ${signal['take_profit_3']:.4f}

*Position Size:* {signal['position_size']['quantity']:.4f}
*Risk:* {signal['position_size']['risk_pct']:.2f}%

*Reason:* {signal['reason']}
"""
        
        await self._send_message(message)
    
    async def send_opportunity_alert(self, opportunity: Dict):
        """Send opportunity alert"""
        token = opportunity['token']
        
        message = f"""
🔥 *HIGH POTENTIAL OPPORTUNITY*

*Token:* {token.symbol}
*Score:* {opportunity['adjusted_score']:.0f}/100
*Risk:* {opportunity['risk_level']}

*Price:* ${token.price:.6f}
*Market Cap:* ${token.market_cap:,.0f}
*Liquidity:* ${token.liquidity:,.0f}
*Volume 24h:* ${token.volume_24h:,.0f}

*Signals:*
"""
        
        for signal in opportunity['signals']:
            message += f"  • {signal}\n"
        
        if opportunity.get('arbitrage'):
            arb = opportunity['arbitrage']
            message += f"\n*Arbitrage:* {arb['profit_pct']:.2f}% ({arb['buy_exchange']} → {arb['sell_exchange']})"
        
        await self._send_message(message)
    
    async def send_portfolio_update(self, report: Dict):
        """Send portfolio update"""
        portfolio = report['portfolio']
        perf = report['performance']
        
        message = f"""
📊 *PORTFOLIO UPDATE*

*Equity:* ${portfolio['total_equity']:,.2f}
*P&L:* ${portfolio['total_pnl']:+,.2f}
*Exposure:* {portfolio['exposure_pct']:.1f}%
*Open Positions:* {portfolio['open_positions']}

*Performance:*
Win Rate: {perf.get('win_rate', 0):.1f}%
Profit Factor: {perf.get('profit_factor', 0):.2f}
Sharpe: {perf.get('sharpe_ratio', 0):.2f}
Max DD: {perf.get('max_drawdown', 0):.1f}%

*Trades Today:* {report['agent_state']['daily_trades']}
"""
        
        await self._send_message(message)
    
    async def _send_message(self, message: str):
        """Send message via Telegram"""
        import aiohttp
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return resp.status == 200


# Main entry point
async def main():
    """Run the master agent"""
    
    # Configuration
    config = {
        'risk_level': 'aggressive',
        # Add your API keys here:
        # 'binance_api_key': 'your_key',
        # 'binance_api_secret': 'your_secret',
        # 'bybit_api_key': 'your_key',
        # 'bybit_api_secret': 'your_secret',
    }
    
    # Create and run agent
    agent = MasterTradingAgent(config)
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
