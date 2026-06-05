#!/usr/bin/env python3
"""
💰 SWARM PROFIT ENGINE
Ενσωματώνει AI scoring, prediction και profit pipeline.
Στόχος: Μετατροπή signals σε actionable trading alerts.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('ProfitEngine')

class SwarmProfitEngine:
    """
    Engine που μετατρέπει raw signals σε profit opportunities.
    Ενσωματώνει AI scoring, prediction, και risk management.
    """
    
    def __init__(self):
        self.swarm_dir = Path('/root/.openclaw/workspace/swarm_general')
        self.data_dir = self.swarm_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Profit tracking
        self.signals_processed = 0
        self.opportunities_found = 0
        self.alerts_sent = 0
        self.paper_trades: List[Dict] = []
        self.profit_predictions: Dict[str, Any] = {}
        
        # AI Scoring weights
        self.scoring_weights = {
            'momentum': 0.25,
            'liquidity': 0.20,
            'volume': 0.20,
            'social': 0.15,
            'technical': 0.10,
            'onchain': 0.10
        }
        
        # Risk parameters
        self.max_position_size = 1000  # $USD
        self.stop_loss_pct = 15
        self.take_profit_levels = [1.5, 2.5, 4.0]  # 50%, 150%, 300%
        
        # Signal quality thresholds
        self.min_score = 45  # Lowered from 60 to generate more alerts
        self.min_profit_potential = 25  # 25% expected profit
        
        logger.info("💰 Profit Engine initialized")
        logger.info("🎯 Target: Convert signals → Alerts → Profit")
    
    async def start(self):
        """Ξεκινάει το profit pipeline"""
        logger.info("🚀 Starting Profit Pipeline...")
        
        # Load state
        self._load_state()
        
        # Main loop
        while True:
            try:
                await self._profit_cycle()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Profit cycle error: {e}")
                await asyncio.sleep(10)
    
    async def _profit_cycle(self):
        """Ένας profit cycle"""
        logger.info(f"\n💰 PROFIT CYCLE #{self.signals_processed + 1}")
        
        # Phase 1: COLLECT signals
        signals = self._collect_signals()
        
        # Phase 2: AI SCORE
        scored = self._ai_score_signals(signals)
        
        # Phase 3: PREDICT profit
        opportunities = self._predict_profit(scored)
        
        # Phase 4: GENERATE alerts
        alerts = self._generate_alerts(opportunities)
        
        # Phase 5: SEND alerts
        sent = await self._send_alerts(alerts)
        
        # Phase 6: TRACK performance
        self._track_performance(sent)
        
        # Phase 7: ADAPT scoring
        self._adapt_scoring()
        
        # Report
        self._report_cycle(signals, scored, opportunities, sent)
    
    def _collect_signals(self) -> List[Dict]:
        """Συλλέγει signals από όλες τις πηγές"""
        signals = []
        
        # Source 1: Auto-Discovery
        signals.extend(self._read_discovery_signals())
        
        # Source 2: Scanner
        signals.extend(self._read_scanner_signals())
        
        # Source 3: WebSocket feeds
        signals.extend(self._read_websocket_signals())
        
        # Source 4: Multi-chain
        signals.extend(self._read_multichain_signals())
        
        logger.info(f"📡 Collected {len(signals)} raw signals")
        return signals
    
    def _read_discovery_signals(self) -> List[Dict]:
        """Διαβάζει signals από auto-discovery"""
        signals = []
        log_file = self.swarm_dir / 'logs' / 'discovery.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:  # Last 100 lines
                        if 'AUTO-DISCOVERED' in line:
                            # Parse: "🚨 AUTO-DISCOVERED: new_token | Score: 60 | Address: xxx"
                            parts = line.split('|')
                            if len(parts) >= 3:
                                try:
                                    score = int(parts[1].split(':')[1].strip())
                                    address = parts[2].split(':')[1].strip()
                                    
                                    signals.append({
                                        'source': 'auto_discovery',
                                        'token': 'new_token',
                                        'address': address,
                                        'score': score,
                                        'timestamp': datetime.now().isoformat(),
                                        'chain': 'solana',
                                        'raw_data': line.strip()
                                    })
                                except Exception:
                                    pass
            except Exception as e:
                logger.warning(f"Error reading discovery: {e}")
        
        return signals
    
    def _read_scanner_signals(self) -> List[Dict]:
        """Διαβάζει signals από scanner"""
        signals = []
        log_file = self.swarm_dir / 'logs' / 'scanner.log'
        
        # For now, scanner logs don't have individual token data
        # This would need enhancement
        
        return signals
    
    def _read_websocket_signals(self) -> List[Dict]:
        """Διαβάζει signals από websocket feeds"""
        signals = []
        log_file = self.swarm_dir / 'logs' / 'websocket.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        if 'NEW TOKEN' in line:
                            try:
                                # Extract address
                                addr_start = line.find(': ')
                                if addr_start > 0:
                                    address = line[addr_start+2:addr_start+2+44].strip()
                                    
                                    signals.append({
                                        'source': 'websocket',
                                        'token': 'new_token',
                                        'address': address,
                                        'score': 50,
                                        'timestamp': datetime.now().isoformat(),
                                        'chain': 'solana'
                                    })
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"Error reading websocket: {e}")
        
        return signals
    
    def _read_multichain_signals(self) -> List[Dict]:
        """Διαβάζει signals από multichain scanner"""
        signals = []
        log_file = self.swarm_dir / 'logs' / 'multichain.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        if 'tokens found' in line:
                            # Parse chain info
                            try:
                                chain = line.split(':')[1].split()[0].strip()
                                count = int(line.split(':')[2].split()[0].strip())
                                
                                if count > 0:
                                    signals.append({
                                        'source': 'multichain',
                                        'token': f'{chain}_scan',
                                        'address': f'chain_{chain}',
                                        'score': min(50 + count, 80),
                                        'timestamp': datetime.now().isoformat(),
                                        'chain': chain,
                                        'count': count
                                    })
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"Error reading multichain: {e}")
        
        return signals
    
    def _ai_score_signals(self, signals: List[Dict]) -> List[Dict]:
        """AI scoring για κάθε signal"""
        scored = []
        
        for signal in signals:
            # Base score
            base_score = signal.get('score', 50)
            
            # Calculate component scores
            momentum_score = self._calculate_momentum(signal)
            liquidity_score = self._calculate_liquidity(signal)
            volume_score = self._calculate_volume(signal)
            social_score = self._calculate_social(signal)
            technical_score = self._calculate_technical(signal)
            onchain_score = self._calculate_onchain(signal)
            
            # Weighted AI score
            ai_score = (
                momentum_score * self.scoring_weights['momentum'] +
                liquidity_score * self.scoring_weights['liquidity'] +
                volume_score * self.scoring_weights['volume'] +
                social_score * self.scoring_weights['social'] +
                technical_score * self.scoring_weights['technical'] +
                onchain_score * self.scoring_weights['onchain']
            )
            
            # Quality multiplier based on source
            source_multiplier = {
                'auto_discovery': 1.0,
                'websocket': 1.2,  # Real-time = higher quality
                'multichain': 0.9,
                'scanner': 1.1
            }.get(signal.get('source', ''), 1.0)
            
            final_score = min(ai_score * source_multiplier, 100)
            
            signal['ai_score'] = round(final_score, 1)
            signal['component_scores'] = {
                'momentum': round(momentum_score, 1),
                'liquidity': round(liquidity_score, 1),
                'volume': round(volume_score, 1),
                'social': round(social_score, 1),
                'technical': round(technical_score, 1),
                'onchain': round(onchain_score, 1)
            }
            
            scored.append(signal)
        
        # Sort by AI score
        scored.sort(key=lambda x: x['ai_score'], reverse=True)
        
        logger.info(f"🧠 AI Scored {len(scored)} signals")
        if scored:
            top = scored[0]
            logger.info(f"   Top signal: {top.get('token', 'unknown')} | Score: {top['ai_score']}/100")
        
        return scored
    
    def _calculate_momentum(self, signal: Dict) -> float:
        """Calculate momentum score"""
        base = signal.get('score', 50)
        # Higher base score = more momentum
        return min(base * 1.2, 100)
    
    def _calculate_liquidity(self, signal: Dict) -> float:
        """Calculate liquidity score"""
        # Default moderate liquidity
        return 55.0
    
    def _calculate_volume(self, signal: Dict) -> float:
        """Calculate volume score"""
        # Higher for real-time sources
        if signal.get('source') == 'websocket':
            return 70.0
        return 50.0
    
    def _calculate_social(self, signal: Dict) -> float:
        """Calculate social sentiment score"""
        # New tokens have higher social buzz
        if signal.get('source') in ['websocket', 'auto_discovery']:
            return 65.0
        return 45.0
    
    def _calculate_technical(self, signal: Dict) -> float:
        """Calculate technical score"""
        return 50.0
    
    def _calculate_onchain(self, signal: Dict) -> float:
        """Calculate on-chain score"""
        return 55.0
    
    def _predict_profit(self, scored: List[Dict]) -> List[Dict]:
        """Predict profit potential"""
        opportunities = []
        
        for signal in scored:
            ai_score = signal.get('ai_score', 0)
            
            # Only consider high-quality signals
            if ai_score < self.min_score:
                continue
            
            # Predict profit based on AI score
            # Higher score = higher expected profit
            profit_potential = self._estimate_profit(ai_score)
            
            # Risk-adjusted profit
            risk_score = self._calculate_risk(signal)
            risk_adjusted_profit = profit_potential * (1 - risk_score / 100)
            
            signal['profit_potential'] = round(profit_potential, 1)
            signal['risk_score'] = round(risk_score, 1)
            signal['risk_adjusted_profit'] = round(risk_adjusted_profit, 1)
            signal['confidence'] = self._calculate_confidence(ai_score, risk_score)
            
            # Add trading parameters
            signal['entry_price'] = self._estimate_entry(signal)
            signal['stop_loss'] = self._calculate_stop_loss(signal)
            signal['take_profit_1'] = self._calculate_tp1(signal)
            signal['take_profit_2'] = self._calculate_tp2(signal)
            signal['take_profit_3'] = self._calculate_tp3(signal)
            signal['position_size'] = self._calculate_position_size(signal)
            
            opportunities.append(signal)
        
        # Sort by risk-adjusted profit
        opportunities.sort(key=lambda x: x['risk_adjusted_profit'], reverse=True)
        
        self.opportunities_found += len(opportunities)
        logger.info(f"💎 Found {len(opportunities)} profit opportunities")
        
        if opportunities:
            top = opportunities[0]
            logger.info(f"   Best: {top.get('token', 'unknown')} | Profit: +{top['profit_potential']}% | Risk: {top['risk_score']}/100")
        
        return opportunities
    
    def _estimate_profit(self, ai_score: float) -> float:
        """Estimate profit percentage"""
        # Non-linear scaling: higher scores = exponentially higher profits
        if ai_score >= 90:
            return 200.0  # 200% potential
        elif ai_score >= 80:
            return 100.0  # 100% potential
        elif ai_score >= 70:
            return 60.0
        elif ai_score >= 60:
            return 35.0
        else:
            return 20.0
    
    def _calculate_risk(self, signal: Dict) -> float:
        """Calculate risk score 0-100"""
        base_risk = 30  # Base risk for new tokens
        
        # Adjust based on source
        source_risk = {
            'auto_discovery': 10,
            'websocket': 15,
            'multichain': 20,
            'scanner': 10
        }.get(signal.get('source', ''), 10)
        
        # Adjust based on score
        score_adjustment = (100 - signal.get('ai_score', 50)) * 0.3
        
        return min(base_risk + source_risk + score_adjustment, 100)
    
    def _calculate_confidence(self, ai_score: float, risk_score: float) -> str:
        """Calculate confidence level"""
        score = ai_score * (1 - risk_score / 200)  # Risk reduces confidence
        
        if score >= 75:
            return "🔥 HIGH"
        elif score >= 60:
            return "🟢 MEDIUM"
        elif score >= 40:
            return "🟡 LOW"
        else:
            return "🔴 SPECULATIVE"
    
    def _estimate_entry(self, signal: Dict) -> float:
        """Estimate entry price"""
        return 0.0001  # Placeholder
    
    def _calculate_stop_loss(self, signal: Dict) -> float:
        """Calculate stop loss"""
        entry = signal.get('entry_price', 0.0001)
        return entry * (1 - self.stop_loss_pct / 100)
    
    def _calculate_tp1(self, signal: Dict) -> float:
        """Calculate TP1"""
        entry = signal.get('entry_price', 0.0001)
        return entry * self.take_profit_levels[0]
    
    def _calculate_tp2(self, signal: Dict) -> float:
        """Calculate TP2"""
        entry = signal.get('entry_price', 0.0001)
        return entry * self.take_profit_levels[1]
    
    def _calculate_tp3(self, signal: Dict) -> float:
        """Calculate TP3"""
        entry = signal.get('entry_price', 0.0001)
        return entry * self.take_profit_levels[2]
    
    def _calculate_position_size(self, signal: Dict) -> float:
        """Calculate position size"""
        ai_score = signal.get('ai_score', 50)
        risk_score = signal.get('risk_score', 50)
        
        # Higher score = larger position
        # Higher risk = smaller position
        size_pct = (ai_score / 100) * (1 - risk_score / 200)
        return round(self.max_position_size * size_pct, 2)
    
    def _generate_alerts(self, opportunities: List[Dict]) -> List[Dict]:
        """Generate trading alerts"""
        alerts = []
        
        for opp in opportunities:
            # Send alerts for all opportunities above threshold
            ai_score = opp.get('ai_score', 0)
            if ai_score >= self.min_score:
                alert = {
                    'type': 'profit_opportunity',
                    'token': opp.get('token', 'unknown'),
                    'address': opp.get('address', ''),
                    'chain': opp.get('chain', 'unknown'),
                    'ai_score': opp.get('ai_score', 0),
                    'profit_potential': opp.get('profit_potential', 0),
                    'risk_score': opp.get('risk_score', 0),
                    'risk_adjusted_profit': opp.get('risk_adjusted_profit', 0),
                    'confidence': opp.get('confidence', ''),
                    'entry': opp.get('entry_price', 0),
                    'stop_loss': opp.get('stop_loss', 0),
                    'take_profit_1': opp.get('take_profit_1', 0),
                    'take_profit_2': opp.get('take_profit_2', 0),
                    'take_profit_3': opp.get('take_profit_3', 0),
                    'position_size': opp.get('position_size', 0),
                    'source': opp.get('source', ''),
                    'timestamp': datetime.now().isoformat(),
                    'message': self._format_alert_message(opp)
                }
                
                alerts.append(alert)
        
        logger.info(f"🚨 Generated {len(alerts)} trading alerts")
        return alerts
    
    def _format_alert_message(self, opp: Dict) -> str:
        """Format alert message for Telegram"""
        token = opp.get('token', 'Unknown')
        ai_score = opp.get('ai_score', 0)
        profit = opp.get('profit_potential', 0)
        risk = opp.get('risk_score', 0)
        confidence = opp.get('confidence', '')
        address = opp.get('address', '')
        
        message = f"""
💰 **PROFIT OPPORTUNITY**

🏷️ Token: `{token}`
🔗 Address: `{address[:20]}...`
📊 AI Score: {ai_score}/100
📈 Profit Potential: +{profit}%
⚠️ Risk Score: {risk}/100
🎯 Confidence: {confidence}

📍 Entry: {opp.get('entry_price', 0)}
🛑 Stop Loss: {opp.get('stop_loss', 0)} (-{self.stop_loss_pct}%)
✅ TP1: {opp.get('take_profit_1', 0)} (+50%)
✅ TP2: {opp.get('take_profit_2', 0)} (+150%)
✅ TP3: {opp.get('take_profit_3', 0)} (+300%)

💵 Position Size: ${opp.get('position_size', 0)}
🔗 Chain: {opp.get('chain', 'unknown')}
📡 Source: {opp.get('source', 'unknown')}

🔥 **Act fast! This is a {confidence.split()[1] if len(confidence.split()) > 1 else 'unknown'} confidence signal.**
        """.strip()
        
        return message
    
    async def _send_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """Send alerts to Telegram and log"""
        sent = []
        
        for alert in alerts:
            try:
                # Log alert
                self._log_alert(alert)
                
                # Write to alert file for Telegram integration
                self._write_alert_file(alert)
                
                sent.append(alert)
                self.alerts_sent += 1
                
                logger.info(f"📤 Alert sent for {alert['token']} | Score: {alert['ai_score']}")
                
            except Exception as e:
                logger.error(f"Error sending alert: {e}")
        
        return sent
    
    def _log_alert(self, alert: Dict):
        """Log alert to file"""
        alert_log = self.data_dir / 'alerts.jsonl'
        with open(alert_log, 'a') as f:
            f.write(json.dumps(alert) + '\n')
    
    def _write_alert_file(self, alert: Dict):
        """Write alert for Telegram bot to read"""
        alert_file = self.data_dir / 'latest_alert.json'
        with open(alert_file, 'w') as f:
            json.dump(alert, f, indent=2)
    
    def _track_performance(self, sent: List[Dict]):
        """Track alert performance"""
        for alert in sent:
            # Track for learning
            tracking = {
                'alert_id': f"alert_{self.alerts_sent}",
                'token': alert['token'],
                'ai_score': alert['ai_score'],
                'profit_potential': alert['profit_potential'],
                'timestamp': alert['timestamp'],
                'status': 'active'
            }
            
            self.paper_trades.append(tracking)
    
    def _adapt_scoring(self):
        """Adapt scoring based on performance"""
        # If no opportunities found, lower thresholds slightly
        if self.opportunities_found == 0 and self.signals_processed > 10:
            self.min_score = max(self.min_score - 2, 40)
            logger.info(f"📉 Lowered min score to {self.min_score} (no opportunities found)")
        
        # If too many opportunities, raise thresholds
        if self.opportunities_found > 20:
            self.min_score = min(self.min_score + 2, 80)
            logger.info(f"📈 Raised min score to {self.min_score} (too many opportunities)")
    
    def _report_cycle(self, signals: List[Dict], scored: List[Dict], 
                     opportunities: List[Dict], sent: List[Dict]):
        """Report cycle results"""
        self.signals_processed += len(signals)
        
        logger.info(f"\n📊 PROFIT PIPELINE REPORT")
        logger.info(f"{'='*50}")
        logger.info(f"📡 Raw Signals: {len(signals)}")
        logger.info(f"🧠 AI Scored: {len(scored)}")
        logger.info(f"💎 Opportunities: {len(opportunities)}")
        logger.info(f"🚨 Alerts Sent: {len(sent)}")
        logger.info(f"📈 Total Alerts: {self.alerts_sent}")
        logger.info(f"📊 Min Score Threshold: {self.min_score}")
        
        if sent:
            top = sent[0]
            logger.info(f"\n🔥 TOP ALERT:")
            logger.info(f"   Token: {top['token']}")
            logger.info(f"   AI Score: {top['ai_score']}/100")
            logger.info(f"   Profit: +{top['profit_potential']}%")
            logger.info(f"   Risk: {top['risk_score']}/100")
            logger.info(f"   Position: ${top['position_size']}")
        
        logger.info(f"{'='*50}\n")
    
    def _save_state(self):
        """Αποθηκεύει state"""
        state = {
            'signals_processed': self.signals_processed,
            'opportunities_found': self.opportunities_found,
            'alerts_sent': self.alerts_sent,
            'min_score': self.min_score,
            'scoring_weights': self.scoring_weights,
            'paper_trades': self.paper_trades[-100:],  # Last 100
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.data_dir / 'profit_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Φορτώνει state"""
        state_file = self.data_dir / 'profit_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.signals_processed = state.get('signals_processed', 0)
                    self.opportunities_found = state.get('opportunities_found', 0)
                    self.alerts_sent = state.get('alerts_sent', 0)
                    self.min_score = state.get('min_score', 60)
                    self.scoring_weights = state.get('scoring_weights', self.scoring_weights)
                    self.paper_trades = state.get('paper_trades', [])
                
                logger.info(f"📁 Loaded profit state: {self.alerts_sent} alerts sent")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def get_stats(self) -> Dict:
        """Επιστρέφει profit stats"""
        return {
            'signals_processed': self.signals_processed,
            'opportunities_found': self.opportunities_found,
            'alerts_sent': self.alerts_sent,
            'min_score': self.min_score,
            'paper_trades_active': len([t for t in self.paper_trades if t['status'] == 'active'])
        }


async def main():
    """Main entry"""
    engine = SwarmProfitEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("🛑 Profit Engine stopped")
        engine._save_state()

if __name__ == '__main__':
    asyncio.run(main())
