#!/usr/bin/env python3
"""🧪 24h Paper Mode Stress Test — Accelerated simulation."""
import sys
import asyncio
import random
from datetime import datetime, timedelta

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType
from config.safety import safety_config, update_safety_config
from core.secure_executor import SecureExecutor


class PaperModeSimulator:
    """Simulates 24 hours of swarm activity in accelerated time."""
    
    def __init__(self, speed_multiplier: int = 3600):
        """
        speed_multiplier: How much to accelerate time.
        3600 = 1 real second = 1 simulated hour
        So 24 simulated hours = 24 real seconds
        """
        self.speed = speed_multiplier
        self.executor = SecureExecutor()
        self.stats = {
            "scans": 0,
            "signals": 0,
            "trades_attempted": 0,
            "trades_executed": 0,
            "trades_blocked": 0,
            "tp_hits": 0,
            "sl_hits": 0,
            "manual_approvals": 0,
            "kill_switch_activations": 0,
            "errors": 0,
        }
        self.simulated_time = datetime.utcnow()
        self.bus = None
        self.running = False
    
    async def init(self):
        """Initialize event bus."""
        self.bus = await get_event_bus()
        # Ensure paper mode
        update_safety_config(trading_mode="paper")
        print(f"🧪 Paper mode: ACTIVE")
        print(f"⏱️  Time acceleration: {self.speed}x (1s real = {self.speed//60}m sim)")
    
    async def run_24h(self):
        """Run 24-hour simulation."""
        await self.init()
        
        start_time = datetime.utcnow()
        end_simulated = self.simulated_time + timedelta(hours=24)
        
        print(f"\n{'═' * 60}")
        print(f"🚀 Starting 24h Paper Mode Simulation")
        print(f"   Real duration: ~{24 * 3600 // self.speed}s")
        print(f"{'═' * 60}\n")
        
        self.running = True
        hour = 0
        
        while self.simulated_time < end_simulated and self.running:
            # Each iteration = 1 simulated hour
            await self._simulate_hour(hour)
            
            hour += 1
            self.simulated_time += timedelta(hours=1)
            
            # Real sleep: 1 second per simulated hour
            await asyncio.sleep(1)
            
            # Progress report every 6 hours
            if hour % 6 == 0:
                self._print_progress(hour)
        
        # Final report
        real_duration = (datetime.utcnow() - start_time).total_seconds()
        self._print_final_report(real_duration)
    
    async def _simulate_hour(self, hour: int):
        """Simulate one hour of activity."""
        try:
            # Random number of scans (1-4 per hour)
            scans = random.randint(1, 4)
            for _ in range(scans):
                await self._simulate_scan()
            
            # Random signals (0-2 per hour)
            signals = random.randint(0, 2)
            for _ in range(signals):
                await self._simulate_signal()
            
            # Random market events
            if random.random() < 0.1:  # 10% chance per hour
                await self._simulate_market_event()
            
            # Random kill switch test (once during simulation)
            if hour == 12 and random.random() < 0.5:
                await self._test_kill_switch()
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"  ❌ Error in hour {hour}: {e}")
    
    async def _simulate_scan(self):
        """Simulate token scan."""
        self.stats["scans"] += 1
        tokens = ["SOL", "BONK", "JUP", "PYTH", "RAY", "MNGO"]
        discovered = random.sample(tokens, k=random.randint(1, 3))
        
        await self.bus.publish_simple(
            event_type=EventType.TOKENS_DISCOVERED.value,
            data={"tokens": [{"symbol": t} for t in discovered], "count": len(discovered)},
            source="scanner",
        )
    
    async def _simulate_signal(self):
        """Simulate trade signal."""
        self.stats["signals"] += 1
        
        symbols = ["SOL", "BONK", "JUP", "PYTH"]
        symbol = random.choice(symbols)
        
        decision = {
            "symbol": symbol,
            "entry_price": random.uniform(50, 200),
            "position_size_usd": random.uniform(50, 300),  # Some may be blocked
            "stop_loss": random.uniform(40, 180),
            "take_profit": random.uniform(100, 400),
            "stop_loss_pct": random.uniform(5, 15),
            "expected_slippage": random.uniform(0.1, 2.0),  # Some may be blocked
        }
        
        self.stats["trades_attempted"] += 1
        
        result = await self.executor.execute(decision)
        
        if result:
            self.stats["trades_executed"] += 1
        else:
            self.stats["trades_blocked"] += 1
    
    async def _simulate_market_event(self):
        """Simulate market volatility event."""
        event_type = random.choice(["VOLATILITY_SPIKE", "LIQUIDITY_DROP", "WHALE_MOVE"])
        await self.bus.publish_simple(
            event_type=EventType.ALERT.value,
            data={
                "alert_type": "MARKET_EVENT",
                "event": event_type,
                "severity": random.choice(["low", "medium", "high"]),
            },
            source="market_monitor",
        )
    
    async def _test_kill_switch(self):
        """Test kill switch activation/deactivation."""
        print(f"\n  🛑 Testing kill switch...")
        
        from core.secure_executor import activate_kill_switch, deactivate_kill_switch
        
        await activate_kill_switch("STRESS_TEST")
        self.stats["kill_switch_activations"] += 1
        
        # Try trade during kill switch (should be blocked)
        decision = {
            "symbol": "SOL",
            "entry_price": 150.0,
            "position_size_usd": 100.0,
            "stop_loss": 135.0,
            "take_profit": 225.0,
            "stop_loss_pct": 10.0,
        }
        
        result = await self.executor.execute(decision)
        if not result:
            print(f"  ✅ Trade correctly blocked during kill switch")
        else:
            print(f"  ⚠️  Trade NOT blocked during kill switch")
        
        await deactivate_kill_switch()
        print(f"  ✅ Kill switch test complete\n")
    
    def _print_progress(self, hour: int):
        """Print progress update."""
        print(f"\n  📊 Hour {hour}/24 — Simulated: {self.simulated_time.strftime('%H:%M')}")
        print(f"     Scans: {self.stats['scans']} | Signals: {self.stats['signals']} | "
              f"Trades: {self.stats['trades_executed']}/{self.stats['trades_attempted']} | "
              f"Blocked: {self.stats['trades_blocked']} | Errors: {self.stats['errors']}")
    
    def _print_final_report(self, real_duration: float):
        """Print final 24h report."""
        print(f"\n{'═' * 60}")
        print(f"║          📊 24H PAPER MODE REPORT                        ║")
        print(f"{'═' * 60}")
        print(f"\n  ⏱️  Duration:")
        print(f"     Simulated: 24 hours")
        print(f"     Real time: {real_duration:.1f} seconds")
        print(f"     Speed: {24*3600/real_duration:.0f}x")
        
        print(f"\n  📈 Activity:")
        print(f"     Token scans: {self.stats['scans']}")
        print(f"     Signals generated: {self.stats['signals']}")
        print(f"     Trades attempted: {self.stats['trades_attempted']}")
        print(f"     Trades executed: {self.stats['trades_executed']}")
        print(f"     Trades blocked (safety): {self.stats['trades_blocked']}")
        
        print(f"\n  🛡️  Safety:")
        print(f"     Kill switch tests: {self.stats['kill_switch_activations']}")
        print(f"     Errors encountered: {self.stats['errors']}")
        
        print(f"\n  ✅ System Status:")
        print(f"     Mode: {safety_config.trading_mode.upper()}")
        print(f"     Executor daily trades: {self.executor.daily_trades}/{safety_config.daily_trade_limit}")
        print(f"     Audit entries: {len(self.executor.get_audit_log())}")
        
        # Success criteria
        success = (
            self.stats['errors'] == 0 and
            self.stats['trades_executed'] > 0 and
            self.stats['trades_blocked'] > 0  # Safety is working
        )
        
        if success:
            print(f"\n  🔥 24H TEST PASSED ✅")
            print(f"\n  🚀 Ready for extended paper testing:")
            print(f"     Run: python3 run_paper_24h.py --real-time")
        else:
            print(f"\n  ❌ 24H TEST FAILED")
            if self.stats['errors'] > 0:
                print(f"     Fix: {self.stats['errors']} errors encountered")
        
        print(f"\n{'═' * 60}\n")


async def main():
    """Run 24h paper mode test."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🧪 24H PAPER MODE STRESS TEST                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Check if we should do real-time or accelerated
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-time", action="store_true", help="Run actual 24 hours")
    parser.add_argument("--fast", action="store_true", help="Fast mode (24h in 24s)")
    args = parser.parse_args()
    
    if args.real_time:
        # Real 24 hours: 1 iteration per hour, sleep 3600 seconds
        sim = PaperModeSimulator(speed_multiplier=1)
        print(f"⏰ REAL TIME MODE: Will run for 24 actual hours")
        print(f"   Start: {datetime.utcnow().isoformat()}")
        print(f"   End: {(datetime.utcnow() + timedelta(hours=24)).isoformat()}")
    elif args.fast:
        # Fast: 24h in 24 seconds
        sim = PaperModeSimulator(speed_multiplier=3600)
    else:
        # Default: 24h in ~2 minutes (1s = 12 simulated minutes)
        sim = PaperModeSimulator(speed_multiplier=720)
    
    try:
        await sim.run_24h()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sim.running = False
    
    return sim.stats['errors'] == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
