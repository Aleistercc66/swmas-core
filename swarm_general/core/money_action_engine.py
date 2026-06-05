#!/usr/bin/env python3
"""
💰 MONEY ACTION ENGINE
Μαθαίνει για χρήμα και το μαζεύει αυτόνομα.
Εκτελεί actionable profit strategies.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('MoneyActionEngine')

class MoneyActionEngine:
    """
    Engine που:
    1. Μαθαίνει για χρήμα (money mastery)
    2. Βρίσκει ευκαιρίες
    3. Τις μετατρέπει σε actionable alerts
    4. Παρακολουθεί performance
    """
    
    def __init__(self):
        self.swarm_dir = Path('/root/.openclaw/workspace/swarm_general')
        self.data_dir = self.swarm_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Money mastery knowledge
        self.money_knowledge = self._load_money_mastery()
        
        # Action tracking
        self.actions_taken = 0
        self.opportunities_found = 0
        self.paper_trades = []
        self.real_trades = []
        self.profit_history = []
        
        # Strategy state
        self.strategies = {
            'scanning': {'active': True, 'weight': 0.25},
            'arbitrage': {'active': True, 'weight': 0.20},
            'yield_farming': {'active': True, 'weight': 0.15},
            'sniper': {'active': True, 'weight': 0.20},
            'social_signals': {'active': True, 'weight': 0.20}
        }
        
        # Learning state
        self.learned_patterns = {}
        self.success_rate = {}
        
        logger.info("💰 Money Action Engine initialized")
        logger.info("🎯 Mission: Learn money → Find opportunities → Take action → Profit")
    
    def _load_money_mastery(self) -> dict:
        """Φορτώνει money mastery knowledge"""
        mastery_file = self.swarm_dir / 'core' / 'money_mastery.py'
        
        knowledge = {
            'principles': [
                "Money is a claim on wealth, not wealth itself",
                "Speed + Information + Execution = Profit",
                "Cut losses short, let winners run",
                "Compound interest is the 8th wonder",
                "The house edge is in information"
            ],
            'strategies': {
                'scanning': {
                    'description': 'Find new tokens before anyone else',
                    'speed': 'minutes',
                    'risk': 'HIGH',
                    'tools': ['DexScreener', 'DEXTools', 'Telegram monitors']
                },
                'arbitrage': {
                    'description': 'Exploit price differences across exchanges',
                    'speed': 'seconds',
                    'risk': 'LOW',
                    'tools': ['Cross-exchange monitors', 'flash loans']
                },
                'yield_farming': {
                    'description': 'Earn interest + token rewards',
                    'speed': 'days',
                    'risk': 'MEDIUM',
                    'tools': ['DeFiLlama', 'APY calculators']
                },
                'sniper': {
                    'description': 'Buy new launches before price pumps',
                    'speed': 'seconds',
                    'risk': 'VERY HIGH',
                    'tools': ['pump.fun monitor', 'custom sniper']
                },
                'social_signals': {
                    'description': 'Trade on social media trends',
                    'speed': 'minutes',
                    'risk': 'MEDIUM',
                    'tools': ['TweetScout', 'LunarCrush']
                }
            },
            'risk_rules': [
                "Never risk more than you can lose",
                "Stop losses at -15% MANDATORY",
                "Take profits in stages: 50%, 150%, 300%",
                "Position size: 1-2% of capital max",
                "Diversify across multiple tokens",
                "Paper trade first, real money second"
            ]
        }
        
        logger.info("📚 Loaded Money Mastery curriculum")
        return knowledge
    
    async def start(self):
        """Ξεκινάει το money action loop"""
        logger.info("🚀 Starting Money Action Engine...")
        logger.info("📖 Phase 1: Learning (continuous)")
        logger.info("🎯 Phase 2: Action (immediate)")
        logger.info("💰 Phase 3: Profit (ongoing)")
        
        # Load state
        self._load_state()
        
        cycle = 0
        while True:
            cycle += 1
            try:
                await self._money_cycle(cycle)
                await asyncio.sleep(45)  # Every 45 seconds
            except Exception as e:
                logger.error(f"Money cycle error: {e}")
                await asyncio.sleep(10)
    
    async def _money_cycle(self, cycle: int):
        """Ένας money cycle"""
        logger.info(f"\n{'='*60}")
        logger.info(f"💰 MONEY CYCLE #{cycle}")
        logger.info(f"{'='*60}")
        
        # Step 1: LEARN (continuous)
        await self._learn_phase()
        
        # Step 2: SCAN (find opportunities)
        opportunities = await self._scan_phase()
        
        # Step 3: ANALYZE (AI scoring + risk)
        analyzed = self._analyze_opportunities(opportunities)
        
        # Step 4: ACTION (generate alerts)
        actions = self._generate_actions(analyzed)
        
        # Step 5: EXECUTE (send alerts)
        executed = await self._execute_actions(actions)
        
        # Step 6: LEARN FROM RESULTS
        self._learn_from_actions(executed)
        
        # Step 7: REPORT
        self._report_cycle(cycle, opportunities, analyzed, executed)
    
    async def _learn_phase(self):
        """Continuous learning phase"""
        # Analyze recent performance
        if self.profit_history:
            recent_profits = self.profit_history[-10:]
            avg_profit = sum(recent_profits) / len(recent_profits)
            
            # Adjust strategies based on performance
            if avg_profit > 0:
                logger.info(f"📈 Recent avg profit: +{avg_profit:.2f}% — scaling winning strategies")
            else:
                logger.info(f"📉 Recent avg profit: {avg_profit:.2f}% — adjusting approach")
        
        # Learn new patterns from market data
        self._update_patterns()
    
    async def _scan_phase(self) -> List[Dict]:
        """Scan for money-making opportunities"""
        opportunities = []
        
        # Strategy 1: SCANNING (new tokens)
        if self.strategies['scanning']['active']:
            scan_opp = self._scan_for_new_tokens()
            opportunities.extend(scan_opp)
        
        # Strategy 2: ARBITRAGE (price differences)
        if self.strategies['arbitrage']['active']:
            arb_opp = self._scan_for_arbitrage()
            opportunities.extend(arb_opp)
        
        # Strategy 3: YIELD (farming opportunities)
        if self.strategies['yield_farming']['active']:
            yield_opp = self._scan_for_yield()
            opportunities.extend(yield_opp)
        
        # Strategy 4: SNIPER (new launches)
        if self.strategies['sniper']['active']:
            snipe_opp = self._scan_for_snipes()
            opportunities.extend(snipe_opp)
        
        # Strategy 5: SOCIAL (trending tokens)
        if self.strategies['social_signals']['active']:
            social_opp = self._scan_for_social()
            opportunities.extend(social_opp)
        
        self.opportunities_found += len(opportunities)
        logger.info(f"🔍 Found {len(opportunities)} money opportunities")
        
        return opportunities
    
    def _scan_for_new_tokens(self) -> List[Dict]:
        """Scan for newly launched tokens"""
        opps = []
        
        # Read from discovery log
        log_file = self.swarm_dir / 'logs' / 'discovery.log'
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        if 'AUTO-DISCOVERED' in line:
                            try:
                                # Parse: 🚨 AUTO-DISCOVERED: new_token | Score: 60 | Address: XXX
                                score = 50
                                address = ''
                                token_name = 'new_token'
                                
                                # Extract score - find "Score: XX" in line
                                if 'Score:' in line:
                                    score_part = line.split('Score:')[1].strip()
                                    score_str = score_part.split('|')[0].split()[0]
                                    score = int(score_str)
                                
                                # Extract address - find "Address: XXX" in line
                                if 'Address:' in line:
                                    addr_part = line.split('Address:')[1].strip()
                                    address = addr_part.split()[0]
                                
                                # Extract token name
                                if 'AUTO-DISCOVERED:' in line:
                                    name_part = line.split('AUTO-DISCOVERED:')[1].strip()
                                    token_name = name_part.split('|')[0].strip()
                                
                                if address and len(address) > 10:
                                    opps.append({
                                        'type': 'new_token',
                                        'strategy': 'scanning',
                                        'token': token_name,
                                        'address': address,
                                        'score': score,
                                        'timestamp': datetime.now().isoformat(),
                                        'chain': 'solana',
                                        'profit_potential': self._estimate_new_token_profit(score),
                                        'risk': 'HIGH',
                                        'action': 'research_then_paper_trade'
                                    })
                            except Exception:
                                pass
            except Exception:
                pass
        
        if opps:
            logger.info(f"🔍 Found {len(opps)} new tokens from discovery log")
        return opps
    
    def _scan_for_arbitrage(self) -> List[Dict]:
        """Scan for arbitrage opportunities"""
        # Placeholder: would need real price data from multiple exchanges
        # For now, return empty but log that we're checking
        return []
    
    def _scan_for_yield(self) -> List[Dict]:
        """Scan for yield farming opportunities"""
        # Placeholder: would need DeFiLlama API
        return []
    
    def _scan_for_snipes(self) -> List[Dict]:
        """Scan for sniper opportunities (new launches)"""
        # Read from websocket log (new tokens)
        opps = []
        log_file = self.swarm_dir / 'logs' / 'websocket.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:
                        if 'NEW TOKEN' in line:
                            try:
                                addr_start = line.find(': ')
                                if addr_start > 0:
                                    address = line[addr_start+2:addr_start+2+44].strip()
                                    
                                    opps.append({
                                        'type': 'snipe',
                                        'strategy': 'sniper',
                                        'token': 'new_launch',
                                        'address': address,
                                        'score': 70,
                                        'timestamp': datetime.now().isoformat(),
                                        'chain': 'solana',
                                        'profit_potential': 200.0,
                                        'risk': 'VERY HIGH',
                                        'action': 'quick_research_then_paper_trade'
                                    })
                            except Exception:
                                pass
            except Exception:
                pass
        
        return opps
    
    def _scan_for_social(self) -> List[Dict]:
        """Scan for social signal opportunities"""
        # Placeholder: would need Twitter/Telegram monitoring
        return []
    
    def _estimate_new_token_profit(self, score: int) -> float:
        """Estimate profit for new token based on score"""
        if score >= 80:
            return 150.0
        elif score >= 70:
            return 100.0
        elif score >= 60:
            return 50.0
        else:
            return 25.0
    
    def _analyze_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Analyze opportunities with AI scoring"""
        analyzed = []
        
        for opp in opportunities:
            # Calculate composite score
            base_score = opp.get('score', 50)
            
            # Strategy multiplier
            strategy_mult = {
                'scanning': 1.0,
                'arbitrage': 1.3,
                'yield_farming': 0.9,
                'sniper': 1.5,
                'social_signals': 1.1
            }.get(opp.get('strategy', ''), 1.0)
            
            # Risk adjustment
            risk_penalty = {
                'LOW': 0,
                'MEDIUM': 5,
                'HIGH': 5,
                'VERY HIGH': 10
            }.get(opp.get('risk', 'MEDIUM'), 10)
            
            final_score = min(base_score * strategy_mult - risk_penalty, 100)
            
            opp['ai_score'] = round(final_score, 1)
            opp['confidence'] = self._score_to_confidence(final_score)
            opp['recommended_action'] = self._get_action_recommendation(opp)
            opp['position_size'] = self._calculate_position_size(final_score, opp.get('risk', 'MEDIUM'))
            
            analyzed.append(opp)
        
        # Sort by AI score
        analyzed.sort(key=lambda x: x['ai_score'], reverse=True)
        
        logger.info(f"🧠 AI Analyzed {len(analyzed)} opportunities")
        if analyzed:
            top = analyzed[0]
            logger.info(f"   Best: {top['type']} | Score: {top['ai_score']}/100 | Action: {top['recommended_action']}")
        
        return analyzed
    
    def _score_to_confidence(self, score: float) -> str:
        """Convert score to confidence level"""
        if score >= 80:
            return "🔥 HIGH"
        elif score >= 65:
            return "🟢 MEDIUM"
        elif score >= 50:
            return "🟡 LOW"
        else:
            return "🔴 SPECULATIVE"
    
    def _get_action_recommendation(self, opp: Dict) -> str:
        """Get recommended action"""
        score = opp.get('ai_score', 0)
        risk = opp.get('risk', 'MEDIUM')
        
        if score >= 65 and risk in ['LOW', 'MEDIUM']:
            return "paper_trade_now"
        elif score >= 50:
            return "research_then_paper_trade"
        else:
            return "watch_only"
    
    def _calculate_position_size(self, score: float, risk: str) -> float:
        """Calculate position size based on score and risk"""
        base_size = 50  # $50 base
        
        # Score multiplier
        if score >= 80:
            size_mult = 2.0
        elif score >= 70:
            size_mult = 1.5
        elif score >= 60:
            size_mult = 1.0
        else:
            size_mult = 0.5
        
        # Risk reduction
        risk_mult = {
            'LOW': 1.0,
            'MEDIUM': 0.8,
            'HIGH': 0.5,
            'VERY HIGH': 0.25
        }.get(risk, 0.5)
        
        return round(base_size * size_mult * risk_mult, 2)
    
    def _generate_actions(self, analyzed: List[Dict]) -> List[Dict]:
        """Generate actionable alerts"""
        actions = []
        
        for opp in analyzed:
            if opp.get('recommended_action') == 'watch_only':
                continue
            
            # Create action
            action = {
                'type': opp.get('type', 'unknown'),
                'strategy': opp.get('strategy', 'unknown'),
                'token': opp.get('token', 'unknown'),
                'address': opp.get('address', ''),
                'chain': opp.get('chain', 'unknown'),
                'ai_score': opp.get('ai_score', 0),
                'confidence': opp.get('confidence', ''),
                'profit_potential': opp.get('profit_potential', 0),
                'risk': opp.get('risk', 'MEDIUM'),
                'position_size': opp.get('position_size', 0),
                'recommended_action': opp.get('recommended_action', ''),
                'timestamp': datetime.now().isoformat(),
                'message': self._format_money_alert(opp)
            }
            
            actions.append(action)
        
        logger.info(f"🎯 Generated {len(actions)} actionable alerts")
        return actions
    
    def _format_money_alert(self, opp: Dict) -> str:
        """Format money-making alert"""
        token = opp.get('token', 'Unknown')
        score = opp.get('ai_score', 0)
        profit = opp.get('profit_potential', 0)
        risk = opp.get('risk', 'MEDIUM')
        confidence = opp.get('confidence', '')
        action = opp.get('recommended_action', '')
        size = opp.get('position_size', 0)
        strategy = opp.get('strategy', 'unknown')
        
        action_emoji = {
            'paper_trade_now': '🚀 PAPER TRADE NOW',
            'research_then_paper_trade': '🔍 RESEARCH → PAPER TRADE',
            'watch_only': '👁️ WATCH ONLY'
        }.get(action, action)
        
        strategy_emoji = {
            'scanning': '🔍 SCAN',
            'arbitrage': '⚡ ARBITRAGE',
            'yield_farming': '🌾 YIELD',
            'sniper': '🎯 SNIPER',
            'social_signals': '📱 SOCIAL'
        }.get(strategy, strategy)
        
        message = f"""
💰💰💰 **MONEY OPPORTUNITY** 💰💰💰

🏷️ Token: `{token}`
🔗 Address: `{opp.get('address', 'N/A')[:20]}...`
🎯 Strategy: {strategy_emoji}
📊 AI Score: {score}/100
{confidence}

📈 Profit Potential: +{profit}%
⚠️ Risk Level: {risk}
💵 Position Size: ${size}
🎬 Action: {action_emoji}

📚 **What I Learned:**
• This is a {strategy} opportunity
• Risk is {risk} — manage accordingly
• Target profit: +{profit}%
• Use stop loss at -15%

🧠 **Swarm Intelligence:**
"{self._get_wisdom_quote()}"

🔗 Chain: {opp.get('chain', 'unknown')}
⏰ Time: {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        return message
    
    def _get_wisdom_quote(self) -> str:
        """Get a money wisdom quote"""
        quotes = [
            "Money flows to where it's treated best",
            "Speed + Information + Execution = Profit",
            "Cut losses short, let winners run",
            "The house edge is in information",
            "Consistency beats intensity",
            "Small wins compound into big profits"
        ]
        import random
        return random.choice(quotes)
    
    async def _execute_actions(self, actions: List[Dict]) -> List[Dict]:
        """Execute actions (send alerts)"""
        executed = []
        
        for action in actions:
            try:
                # Write to alert file
                self._write_alert(action)
                
                # Log action
                self._log_action(action)
                
                executed.append(action)
                self.actions_taken += 1
                
                logger.info(f"💰 Action executed: {action['type']} | Score: {action['ai_score']}")
                
            except Exception as e:
                logger.error(f"Error executing action: {e}")
        
        return executed
    
    def _write_alert(self, action: Dict):
        """Write alert for Telegram"""
        alert_file = self.data_dir / 'money_alert.json'
        with open(alert_file, 'w') as f:
            json.dump(action, f, indent=2)
    
    def _log_action(self, action: Dict):
        """Log action to history"""
        history_file = self.data_dir / 'money_actions.jsonl'
        with open(history_file, 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'action': action
            }) + '\n')
    
    def _learn_from_actions(self, executed: List[Dict]):
        """Learn from executed actions"""
        for action in executed:
            strategy = action.get('strategy', 'unknown')
            score = action.get('ai_score', 0)
            
            # Track strategy performance
            if strategy not in self.success_rate:
                self.success_rate[strategy] = {'total': 0, 'high_score': 0}
            
            self.success_rate[strategy]['total'] += 1
            if score > self.success_rate[strategy]['high_score']:
                self.success_rate[strategy]['high_score'] = score
        
        # Adjust strategy weights based on performance
        self._adjust_strategies()
    
    def _adjust_strategies(self):
        """Adjust strategy weights based on learning"""
        for strategy, stats in self.success_rate.items():
            if stats['total'] > 5:
                high_score_pct = stats['high_score'] / 100
                
                # Increase weight for high-performing strategies
                if high_score_pct > 0.7:
                    self.strategies[strategy]['weight'] = min(
                        self.strategies[strategy]['weight'] * 1.1,
                        0.35
                    )
                    logger.info(f"📈 Increased {strategy} weight to {self.strategies[strategy]['weight']:.2f}")
    
    def _update_patterns(self):
        """Update learned patterns"""
        # Learn from recent data
        pass  # Placeholder for pattern learning
    
    def _report_cycle(self, cycle: int, opportunities: List[Dict], 
                     analyzed: List[Dict], executed: List[Dict]):
        """Report cycle results"""
        logger.info(f"\n{'='*60}")
        logger.info(f"💰 MONEY CYCLE #{cycle} COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"📊 Opportunities Found: {len(opportunities)}")
        logger.info(f"🧠 AI Analyzed: {len(analyzed)}")
        logger.info(f"🎯 Actions Taken: {len(executed)}")
        logger.info(f"📈 Total Actions: {self.actions_taken}")
        logger.info(f"🧠 Strategies Active: {sum(1 for s in self.strategies.values() if s['active'])}")
        
        if executed:
            top = executed[0]
            logger.info(f"\n🔥 TOP OPPORTUNITY:")
            logger.info(f"   Type: {top['type']}")
            logger.info(f"   Score: {top['ai_score']}/100")
            logger.info(f"   Profit: +{top['profit_potential']}%")
            logger.info(f"   Action: {top['recommended_action']}")
        
        logger.info(f"{'='*60}\n")
    
    def _save_state(self):
        """Save state"""
        state = {
            'actions_taken': self.actions_taken,
            'opportunities_found': self.opportunities_found,
            'strategies': self.strategies,
            'success_rate': self.success_rate,
            'learned_patterns': self.learned_patterns,
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.data_dir / 'money_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Load state"""
        state_file = self.data_dir / 'money_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                self.actions_taken = state.get('actions_taken', 0)
                self.opportunities_found = state.get('opportunities_found', 0)
                self.strategies = state.get('strategies', self.strategies)
                self.success_rate = state.get('success_rate', {})
                self.learned_patterns = state.get('learned_patterns', {})
                logger.info(f"📁 Loaded money state: {self.actions_taken} actions taken")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def get_stats(self) -> Dict:
        """Get stats"""
        return {
            'actions_taken': self.actions_taken,
            'opportunities_found': self.opportunities_found,
            'strategies_active': sum(1 for s in self.strategies.values() if s['active']),
            'learned_patterns': len(self.learned_patterns),
            'success_rate': self.success_rate
        }


async def main():
    engine = MoneyActionEngine()
    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("🛑 Money Action Engine stopped")
        engine._save_state()

if __name__ == '__main__':
    asyncio.run(main())
