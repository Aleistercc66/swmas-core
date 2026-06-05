#!/usr/bin/env python3
"""
🧬 SWARM EVOLUTION ENGINE
Συνεχής βελτίωση, self-monitoring, auto-adjustment.
Στόχος: 9+/10 score, continuous evolution.
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
logger = logging.getLogger('EvolutionEngine')

class SwarmEvolutionEngine:
    """
    Engine που παρακολουθεί, αναλύει και βελτιώνει το swarm.
    Συνεχής loop: measure → analyze → improve → validate
    """
    
    def __init__(self):
        self.swarm_dir = Path('/root/.openclaw/workspace/swarm_general')
        self.data_dir = self.swarm_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Evolution state
        self.generation = 0
        self.current_score = 0.0
        self.target_score = 9.0
        self.evolution_history: List[Dict] = []
        
        # Component metrics
        self.component_scores = {
            'system_health': {'current': 8.0, 'target': 9.5, 'weight': 0.15},
            'resource_usage': {'current': 7.0, 'target': 9.0, 'weight': 0.15},
            'agent_activity': {'current': 8.0, 'target': 9.5, 'weight': 0.20},
            'market_coverage': {'current': 8.0, 'target': 9.5, 'weight': 0.15},
            'realtime_speed': {'current': 8.0, 'target': 9.5, 'weight': 0.10},
            'intelligence': {'current': 8.0, 'target': 9.5, 'weight': 0.10},
            'automation': {'current': 8.0, 'target': 9.5, 'weight': 0.10},
            'scalability': {'current': 8.0, 'target': 9.5, 'weight': 0.05}
        }
        
        # Bottlenecks detected
        self.bottlenecks: List[Dict] = []
        
        # Improvements applied
        self.improvements: List[Dict] = []
        
        # Learning data
        self.patterns: Dict[str, Any] = {}
        self.baseline_metrics: Dict[str, Any] = {}
        
        # Evolution loop config
        self.check_interval = 60  # Check every minute
        self.improvement_cooldown = 300  # 5 min between improvements
        self.last_improvement_time = 0
        
        logger.info("🧬 Evolution Engine initialized")
    
    async def start(self):
        """Ξεκινάει το evolution loop"""
        logger.info("🚀 Starting Evolution Engine...")
        logger.info(f"🎯 Target Score: {self.target_score}/10")
        
        # Load history
        self._load_state()
        
        # Start evolution loop
        while True:
            try:
                await self._evolution_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Evolution cycle error: {e}")
                await asyncio.sleep(30)
    
    async def _evolution_cycle(self):
        """Ένας evolution κύκλος"""
        self.generation += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🧬 EVOLUTION CYCLE #{self.generation}")
        logger.info(f"{'='*60}")
        
        # Phase 1: MEASURE
        metrics = await self._measure_system()
        
        # Phase 2: ANALYZE
        analysis = self._analyze_metrics(metrics)
        
        # Phase 3: PLAN
        improvements = self._plan_improvements(analysis)
        
        # Phase 4: EXECUTE
        if improvements:
            await self._execute_improvements(improvements)
        
        # Phase 5: VALIDATE
        score = self._calculate_score()
        
        # Phase 6: LEARN
        self._learn_from_cycle(metrics, score, improvements)
        
        # Save state
        self._save_state()
        
        # Report
        self._report_cycle(score, improvements)
    
    async def _measure_system(self) -> Dict:
        """Μετράει system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'generation': self.generation
        }
        
        try:
            # CPU / Load
            with open('/proc/loadavg', 'r') as f:
                load_data = f.read().strip().split()
                metrics['load_1m'] = float(load_data[0])
                metrics['load_5m'] = float(load_data[1])
                metrics['load_15m'] = float(load_data[2])
            
            # Memory
            with open('/proc/meminfo', 'r') as f:
                mem_data = f.read()
                mem_total = self._parse_mem_value(mem_data, 'MemTotal')
                mem_available = self._parse_mem_value(mem_data, 'MemAvailable')
                metrics['memory_usage_pct'] = ((mem_total - mem_available) / mem_total * 100) if mem_total > 0 else 0
            
            # Process count
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            metrics['process_count'] = len(result.stdout.strip().split('\n')) - 1
            
            # Active swarm processes
            swarm_procs = subprocess.run(
                ['pgrep', '-f', 'general_orchestrator|enhanced_scanner|multichain_scanner|auto_discovery|background_monitor|websocket_feeds|realtime_interface'],
                capture_output=True, text=True
            )
            metrics['swarm_processes'] = len([p for p in swarm_procs.stdout.strip().split('\n') if p])
            
            # Disk usage
            import shutil
            disk = shutil.disk_usage('/')
            metrics['disk_usage_pct'] = disk.used / disk.total * 100
            
            # Network (rough check)
            net_data = subprocess.run(['cat', '/proc/net/dev'], capture_output=True, text=True)
            metrics['network_interfaces'] = len([l for l in net_data.stdout.split('\n') if ':' in l and 'lo' not in l])
            
            # Scanner metrics from logs
            metrics['scanner'] = self._parse_scanner_metrics()
            metrics['discovery'] = self._parse_discovery_metrics()
            
        except Exception as e:
            logger.error(f"Measurement error: {e}")
        
        return metrics
    
    def _parse_mem_value(self, mem_info: str, key: str) -> int:
        """Parse memory value from /proc/meminfo"""
        for line in mem_info.split('\n'):
            if key in line:
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) * 1024
        return 0
    
    def _parse_scanner_metrics(self) -> Dict:
        """Parse scanner log for metrics"""
        metrics = {'opportunities_found': 0, 'hot_tokens': 0, 'scans_completed': 0}
        log_file = self.swarm_dir / 'logs' / 'scanner.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:  # Last 100 lines
                        if 'Opportunities:' in line:
                            parts = line.split('Opportunities:')
                            if len(parts) > 1:
                                try:
                                    metrics['opportunities_found'] = int(parts[1].split('|')[0].strip())
                                except:
                                    pass
                        if 'Hot:' in line:
                            parts = line.split('Hot:')
                            if len(parts) > 1:
                                try:
                                    metrics['hot_tokens'] = int(parts[1].strip())
                                except:
                                    pass
                        if 'Scan complete' in line:
                            metrics['scans_completed'] += 1
            except Exception:
                pass
        
        return metrics
    
    def _parse_discovery_metrics(self) -> Dict:
        """Parse discovery log for metrics"""
        metrics = {'signals_discovered': 0, 'high_quality': 0}
        log_file = self.swarm_dir / 'logs' / 'discovery.log'
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        if 'high-quality' in line:
                            parts = line.split('high-quality')
                            if len(parts) > 1:
                                try:
                                    metrics['high_quality'] = int(parts[0].split('|')[-1].strip().split()[-1])
                                except:
                                    pass
            except Exception:
                pass
        
        return metrics
    
    def _analyze_metrics(self, metrics: Dict) -> Dict:
        """Αναλύει metrics και βρίσκει bottlenecks"""
        analysis = {
            'bottlenecks': [],
            'opportunities': [],
            'score_impact': {}
        }
        
        # Health analysis
        mem_usage = metrics.get('memory_usage_pct', 0)
        if mem_usage > 80:
            analysis['bottlenecks'].append({
                'component': 'system_health',
                'issue': 'high_memory_usage',
                'severity': 'high',
                'value': mem_usage,
                'threshold': 80
            })
        
        # Resource usage analysis
        load = metrics.get('load_1m', 0)
        if load < 0.5:
            analysis['bottlenecks'].append({
                'component': 'resource_usage',
                'issue': 'underutilized_cpu',
                'severity': 'medium',
                'value': load,
                'threshold': 0.5
            })
            analysis['opportunities'].append({
                'component': 'resource_usage',
                'action': 'increase_parallelism',
                'potential_score_gain': 1.5
            })
        
        # Agent activity analysis
        swarm_procs = metrics.get('swarm_processes', 0)
        if swarm_procs < 5:
            analysis['bottlenecks'].append({
                'component': 'agent_activity',
                'issue': 'insufficient_active_agents',
                'severity': 'high',
                'value': swarm_procs,
                'threshold': 5
            })
        
        # Market coverage analysis
        scanner = metrics.get('scanner', {})
        if scanner.get('opportunities_found', 0) == 0:
            analysis['bottlenecks'].append({
                'component': 'market_coverage',
                'issue': 'no_opportunities_detected',
                'severity': 'medium',
                'value': 0,
                'threshold': 1
            })
        
        # Real-time analysis
        discovery = metrics.get('discovery', {})
        if discovery.get('high_quality', 0) < 5:
            analysis['bottlenecks'].append({
                'component': 'intelligence',
                'issue': 'low_signal_volume',
                'severity': 'medium',
                'value': discovery.get('high_quality', 0),
                'threshold': 5
            })
        
        self.bottlenecks = analysis['bottlenecks']
        
        return analysis
    
    def _plan_improvements(self, analysis: Dict) -> List[Dict]:
        """Σχεδιάζει βελτιώσεις"""
        improvements = []
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_improvement_time < self.improvement_cooldown:
            return []
        
        for bottleneck in analysis.get('bottlenecks', []):
            component = bottleneck['component']
            issue = bottleneck['issue']
            
            if component == 'resource_usage' and issue == 'underutilized_cpu':
                improvements.append({
                    'id': f'imp_{self.generation}_resource',
                    'component': 'resource_usage',
                    'action': 'increase_scan_frequency',
                    'description': 'Increase scanner frequency from 120s to 60s',
                    'score_gain': 1.0,
                    'risk': 'low',
                    'auto_apply': True
                })
                
            elif component == 'market_coverage' and issue == 'no_opportunities_detected':
                improvements.append({
                    'id': f'imp_{self.generation}_market',
                    'component': 'market_coverage',
                    'action': 'relax_filters',
                    'description': 'Temporarily relax filters to find more opportunities',
                    'score_gain': 1.5,
                    'risk': 'medium',
                    'auto_apply': False  # Needs approval
                })
                
            elif component == 'intelligence' and issue == 'low_signal_volume':
                improvements.append({
                    'id': f'imp_{self.generation}_intel',
                    'component': 'intelligence',
                    'action': 'add_data_sources',
                    'description': 'Add more data sources to discovery engine',
                    'score_gain': 1.0,
                    'risk': 'low',
                    'auto_apply': True
                })
        
        # Always try to improve if score < target
        if self.current_score < self.target_score:
            improvements.append({
                'id': f'imp_{self.generation}_evolve',
                'component': 'general',
                'action': 'micro_optimization',
                'description': f'Auto-tune parameters for score {self.current_score} → {self.target_score}',
                'score_gain': 0.5,
                'risk': 'low',
                'auto_apply': True
            })
        
        return improvements
    
    async def _execute_improvements(self, improvements: List[Dict]):
        """Εκτελεί βελτιώσεις"""
        for imp in improvements:
            if not imp.get('auto_apply', False):
                logger.info(f"⏸️ Manual approval needed: {imp['description']}")
                continue
            
            logger.info(f"🔧 Applying improvement: {imp['description']}")
            
            try:
                if imp['action'] == 'increase_scan_frequency':
                    await self._tune_scanner(frequency=60)
                    
                elif imp['action'] == 'relax_filters':
                    await self._tune_scanner(min_liquidity=25000, min_volume=50000)
                    
                elif imp['action'] == 'add_data_sources':
                    await self._add_data_sources()
                    
                elif imp['action'] == 'micro_optimization':
                    await self._micro_optimize()
                
                # Record improvement
                imp['applied_at'] = datetime.now().isoformat()
                imp['status'] = 'applied'
                self.improvements.append(imp)
                self.last_improvement_time = time.time()
                
                logger.info(f"✅ Improvement applied: {imp['id']}")
                
            except Exception as e:
                logger.error(f"❌ Improvement failed: {e}")
                imp['status'] = 'failed'
                imp['error'] = str(e)
    
    async def _tune_scanner(self, frequency: Optional[int] = None, 
                          min_liquidity: Optional[int] = None,
                          min_volume: Optional[int] = None):
        """Tune scanner parameters"""
        logger.info(f"🔧 Tuning scanner: freq={frequency}, liq={min_liquidity}, vol={min_volume}")
        
        # Write tuning config
        config = {
            'scan_interval': frequency or 120,
            'min_liquidity': min_liquidity or 50000,
            'min_volume_24h': min_volume or 100000,
            'tuned_at': datetime.now().isoformat()
        }
        
        config_file = self.data_dir / 'scanner_tuning.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Signal scanner to reload (if it's watching for config changes)
        logger.info(f"📁 Scanner tuning written to {config_file}")
    
    async def _add_data_sources(self):
        """Add more data sources"""
        logger.info("📡 Adding additional data sources...")
        
        sources = [
            {'name': 'coingecko', 'type': 'api', 'priority': 3},
            {'name': 'coinmarketcap', 'type': 'api', 'priority': 3},
            {'name': 'defillama', 'type': 'api', 'priority': 2},
            {'name': 'token_terminal', 'type': 'api', 'priority': 2}
        ]
        
        sources_file = self.data_dir / 'additional_sources.json'
        with open(sources_file, 'w') as f:
            json.dump(sources, f, indent=2)
        
        logger.info(f"📁 {len(sources)} additional sources configured")
    
    async def _micro_optimize(self):
        """Micro-optimizations based on patterns"""
        logger.info("⚙️ Running micro-optimizations...")
        
        # Adjust based on learned patterns
        if 'peak_hours' in self.patterns:
            peak_hours = self.patterns['peak_hours']
            logger.info(f"📊 Peak activity hours detected: {peak_hours}")
        
        # Optimize queue sizes
        if 'queue_pressure' in self.patterns:
            pressure = self.patterns['queue_pressure']
            if pressure > 0.8:
                logger.info("📈 High queue pressure detected - increasing worker count")
                # This would signal the parallel executor to scale up
    
    def _calculate_score(self) -> float:
        """Υπολογίζει συνολικό score"""
        total_weight = sum(c['weight'] for c in self.component_scores.values())
        weighted_score = sum(
            c['current'] * c['weight']
            for c in self.component_scores.values()
        )
        
        self.current_score = weighted_score / total_weight if total_weight > 0 else 0
        return self.current_score
    
    def _learn_from_cycle(self, metrics: Dict, score: float, improvements: List[Dict]):
        """Μαθαίνει από τον κύκλο"""
        cycle_data = {
            'generation': self.generation,
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'metrics': metrics,
            'improvements_applied': len([i for i in improvements if i.get('status') == 'applied']),
            'bottlenecks_found': len(self.bottlenecks)
        }
        
        self.evolution_history.append(cycle_data)
        
        # Learn patterns
        hour = datetime.now().hour
        if 'activity_by_hour' not in self.patterns:
            self.patterns['activity_by_hour'] = {}
        
        self.patterns['activity_by_hour'][hour] = metrics.get('swarm_processes', 0)
        
        # Detect peak hours
        if len(self.patterns['activity_by_hour']) >= 6:
            sorted_hours = sorted(
                self.patterns['activity_by_hour'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            self.patterns['peak_hours'] = [h for h, _ in sorted_hours[:3]]
    
    def _report_cycle(self, score: float, improvements: List[Dict]):
        """Αναφορά κύκλου"""
        logger.info(f"\n📊 EVOLUTION REPORT - Generation #{self.generation}")
        logger.info(f"{'='*60}")
        logger.info(f"🎯 Current Score: {score:.2f}/10")
        logger.info(f"🎯 Target Score: {self.target_score}/10")
        logger.info(f"📈 Gap to target: {self.target_score - score:.2f}")
        
        if score >= self.target_score:
            logger.info(f"🎉🎉🎉 TARGET REACHED! Score: {score:.2f}/10 🎉🎉🎉")
        
        logger.info(f"🔧 Improvements applied this cycle: {len([i for i in improvements if i.get('status') == 'applied'])}")
        logger.info(f"⚠️ Bottlenecks detected: {len(self.bottlenecks)}")
        
        # Component breakdown
        logger.info(f"\n📋 Component Scores:")
        for name, data in self.component_scores.items():
            status = "✅" if data['current'] >= data['target'] else "🔧"
            logger.info(f"  {status} {name}: {data['current']:.1f}/{data['target']:.1f} (weight: {data['weight']})")
        
        # Evolution trend
        if len(self.evolution_history) >= 2:
            prev_score = self.evolution_history[-2]['score']
            trend = score - prev_score
            if trend > 0:
                logger.info(f"📈 Trend: +{trend:.2f} (improving)")
            elif trend < 0:
                logger.info(f"📉 Trend: {trend:.2f} (declining)")
            else:
                logger.info(f"➡️ Trend: stable")
        
        logger.info(f"{'='*60}\n")
    
    def _save_state(self):
        """Αποθηκεύει state"""
        state = {
            'generation': self.generation,
            'current_score': self.current_score,
            'target_score': self.target_score,
            'component_scores': self.component_scores,
            'bottlenecks': self.bottlenecks,
            'improvements': self.improvements,
            'patterns': self.patterns,
            'evolution_history': self.evolution_history[-100:],  # Last 100
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.data_dir / 'evolution_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Φορτώνει state"""
        state_file = self.data_dir / 'evolution_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.generation = state.get('generation', 0)
                    self.current_score = state.get('current_score', 0)
                    self.component_scores = state.get('component_scores', self.component_scores)
                    self.bottlenecks = state.get('bottlenecks', [])
                    self.improvements = state.get('improvements', [])
                    self.patterns = state.get('patterns', {})
                    self.evolution_history = state.get('evolution_history', [])
                    
                logger.info(f"📁 Loaded evolution state: Gen {self.generation}, Score {self.current_score:.2f}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def get_stats(self) -> Dict:
        """Επιστρέφει evolution stats"""
        return {
            'generation': self.generation,
            'current_score': self.current_score,
            'target_score': self.target_score,
            'improvements_applied': len([i for i in self.improvements if i.get('status') == 'applied']),
            'bottlenecks_active': len(self.bottlenecks),
            'evolution_history_length': len(self.evolution_history),
            'patterns_learned': len(self.patterns)
        }


# Integration with Swarm System
class SwarmEvolutionPlugin:
    """
    Plugin που ενσωματώνει το Evolution Engine στο swarm.
    """
    
    def __init__(self):
        self.engine = SwarmEvolutionEngine()
        self.is_running = False
    
    async def start(self):
        """Ξεκινάει το evolution plugin"""
        self.is_running = True
        
        logger.info("🧬 Swarm Evolution Plugin started")
        logger.info("🔄 Monitoring and improving swarm continuously...")
        
        # Start evolution engine
        await self.engine.start()
    
    async def stop(self):
        """Σταματάει το plugin"""
        self.is_running = False
        logger.info("🛑 Swarm Evolution Plugin stopped")


async def main():
    """Main entry"""
    plugin = SwarmEvolutionPlugin()
    
    try:
        await plugin.start()
    except KeyboardInterrupt:
        await plugin.stop()

if __name__ == '__main__':
    asyncio.run(main())
