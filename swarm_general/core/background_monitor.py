#!/usr/bin/env python3
"""
👁️ BACKGROUND MONITORING SYSTEM
Whale tracking, mempool monitoring, health checks.
Τρέχει συνεχώς στο background.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('BackgroundMonitor')

class BackgroundMonitor:
    """
    Background monitoring για whale activity, mempool, system health.
    """
    
    def __init__(self):
        self.is_running = False
        self.monitored_wallets: Dict[str, Dict] = {}
        self.health_status = {
            'last_check': 0,
            'status': 'unknown',
            'checks_passed': 0,
            'checks_failed': 0
        }
        self.alerts_sent = 0
        
    async def start(self):
        """Ξεκινάει όλα τα monitoring loops"""
        self.is_running = True
        
        logger.info("👁️ Background Monitor started")
        
        # Start monitoring loops
        tasks = [
            asyncio.create_task(self._whale_monitor_loop()),
            asyncio.create_task(self._system_health_loop()),
            asyncio.create_task(self._mempool_simulation_loop()),
            asyncio.create_task(self._metrics_collection_loop())
        ]
        
        await asyncio.gather(*tasks)
    
    async def _whale_monitor_loop(self):
        """Monitor whale wallets"""
        logger.info("🐋 Whale monitoring started")
        
        # Add demo whales
        self.monitored_wallets = {
            '7nY7HGrT5z7xY7Z9': {'label': 'Smart_Whale_1', 'tier': 'S'},
            '9xYzAbc123Def456': {'label': 'Early_Adopter', 'tier': 'A'},
            '3mNoPqr789Stu012': {'label': 'Degen_King', 'tier': 'B'}
        }
        
        while self.is_running:
            try:
                for wallet, info in self.monitored_wallets.items():
                    # Simulate whale activity detection
                    if self._detect_whale_activity(wallet):
                        logger.info(
                            f"🐋 WHALE ALERT: {info['label']} ({info['tier']}) | "
                            f"Wallet: {wallet[:15]}..."
                        )
                        self.alerts_sent += 1
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Whale monitor error: {e}")
                await asyncio.sleep(10)
    
    def _detect_whale_activity(self, wallet: str) -> bool:
        """Simulate whale detection"""
        import random
        # 10% chance of activity per check
        return random.random() < 0.1
    
    async def _system_health_loop(self):
        """Monitor system health"""
        logger.info("🏥 System health monitoring started")
        
        while self.is_running:
            try:
                # Check memory
                try:
                    with open('/proc/meminfo', 'r') as f:
                        mem_info = f.read()
                        
                    # Parse memory info
                    mem_total = self._parse_mem_value(mem_info, 'MemTotal')
                    mem_available = self._parse_mem_value(mem_info, 'MemAvailable')
                    
                    if mem_total > 0:
                        mem_usage = (mem_total - mem_available) / mem_total * 100
                        
                        if mem_usage > 90:
                            logger.warning(f"🔴 HIGH MEMORY USAGE: {mem_usage:.1f}%")
                        elif mem_usage > 80:
                            logger.info(f"🟡 Memory usage: {mem_usage:.1f}%")
                        else:
                            logger.info(f"🟢 Memory healthy: {mem_usage:.1f}%")
                            
                except Exception as e:
                    logger.error(f"Memory check error: {e}")
                
                # Check disk
                try:
                    import shutil
                    disk = shutil.disk_usage('/')
                    disk_usage = disk.used / disk.total * 100
                    
                    if disk_usage > 90:
                        logger.warning(f"🔴 HIGH DISK USAGE: {disk_usage:.1f}%")
                    else:
                        logger.info(f"💽 Disk: {disk_usage:.1f}% used")
                        
                except Exception as e:
                    logger.error(f"Disk check error: {e}")
                
                # Update health status
                self.health_status['last_check'] = time.time()
                self.health_status['status'] = 'healthy'
                self.health_status['checks_passed'] += 1
                
                await asyncio.sleep(60)  # Every minute
                
            except Exception as e:
                self.health_status['checks_failed'] += 1
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)
    
    def _parse_mem_value(self, mem_info: str, key: str) -> int:
        """Parse memory value from /proc/meminfo"""
        for line in mem_info.split('\n'):
            if key in line:
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) * 1024  # Convert from KB to bytes
        return 0
    
    async def _mempool_simulation_loop(self):
        """Simulate mempool monitoring"""
        logger.info("📦 Mempool monitoring started (simulated)")
        
        while self.is_running:
            try:
                # Simulate mempool stats
                import random
                
                pending_tx = random.randint(0, 500)
                gas_price = random.uniform(0.001, 0.1)
                
                if pending_tx > 200:
                    logger.info(f"📦 Mempool: {pending_tx} pending | Gas: {gas_price:.4f} SOL")
                
                # Simulate transaction detection
                if random.random() < 0.05:  # 5% chance
                    tx_size = random.uniform(10, 1000)
                    logger.info(f"🔍 Large transaction detected: {tx_size:.2f} SOL")
                
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"Mempool error: {e}")
                await asyncio.sleep(10)
    
    async def _metrics_collection_loop(self):
        """Collect and log metrics"""
        logger.info("📊 Metrics collection started")
        
        while self.is_running:
            try:
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'wallets_monitored': len(self.monitored_wallets),
                    'alerts_sent': self.alerts_sent,
                    'health_status': self.health_status['status'],
                    'checks_passed': self.health_status['checks_passed'],
                    'checks_failed': self.health_status['checks_failed']
                }
                
                logger.info(
                    f"📊 METRICS | Wallets: {metrics['wallets_monitored']} | "
                    f"Alerts: {metrics['alerts_sent']} | "
                    f"Health: {metrics['health_status']}"
                )
                
                # Write to file
                self._write_metrics(metrics)
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Metrics error: {e}")
                await asyncio.sleep(60)
    
    def _write_metrics(self, metrics: Dict):
        """Write metrics to file"""
        try:
            import json
            with open('/root/.openclaw/workspace/swarm_general/data/metrics.jsonl', 'a') as f:
                f.write(json.dumps(metrics) + '\n')
        except Exception as e:
            logger.error(f"Error writing metrics: {e}")
    
    def add_wallet(self, address: str, label: str, tier: str = 'B'):
        """Add wallet to monitoring"""
        self.monitored_wallets[address] = {
            'label': label,
            'tier': tier,
            'added_at': time.time()
        }
        logger.info(f"👁️ Added wallet: {label} ({tier})")
    
    def get_stats(self) -> Dict:
        """Get monitoring stats"""
        return {
            'wallets_monitored': len(self.monitored_wallets),
            'alerts_sent': self.alerts_sent,
            'health': self.health_status,
            'is_running': self.is_running
        }
    
    async def stop(self):
        """Stop monitoring"""
        self.is_running = False
        logger.info("🛑 Background Monitor stopped")


async def main():
    """Main entry"""
    monitor = BackgroundMonitor()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        await monitor.stop()

if __name__ == '__main__':
    asyncio.run(main())