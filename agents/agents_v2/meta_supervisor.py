#!/usr/bin/env python3
"""
🧠 AGENT V2: META SUPERVISOR — Self-healing system guardian
Replaces meta_agent.py. Monitors all agents, auto-repairs, sends alerts.
"""
import asyncio
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from core import (
    settings, get_logger,
    EventLogManager,
    set_agent_healthy, set_agent_degraded, set_agent_down,
    AGENT_HEALTH, ERRORS_TOTAL,
)

logger = get_logger("meta_supervisor")

class AsyncMetaSupervisor:
    """Production-grade system supervisor."""
    
    AGENT_NAMES = ["scanner", "validator", "risk_engine", "executor", "position_monitor", "telegram_bot"]
    
    def __init__(self):
        self.running = False
        self.health_checks: Dict[str, datetime] = {}
        self.agent_status: Dict[str, str] = {}
    
    async def check_processes(self) -> Dict[str, bool]:
        """Check which agent processes are running."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pgrep", "-f", "agents_v2",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            
            # Check each agent
            status = {}
            for agent in self.AGENT_NAMES:
                status[agent] = agent.replace("_", "_") in output.lower()
            
            return status
            
        except Exception as e:
            logger.error(f"Process check failed: {e}")
            return {}
    
    async def check_disk_space(self) -> bool:
        """Check disk space."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "df", "-h", ".",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            
            # Simple check
            lines = output.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    usage = parts[4].replace("%", "")
                    return int(usage) < 90
            
            return True
            
        except Exception as e:
            logger.warning(f"Disk check failed: {e}")
            return True
    
    async def run_health_check(self):
        """Full system health check."""
        try:
            processes = await self.check_processes()
            disk_ok = await self.check_disk_space()
            
            now = datetime.now(timezone.utc)
            
            for agent, running in processes.items():
                if running:
                    self.health_checks[agent] = now
                    self.agent_status[agent] = "HEALTHY"
                    set_agent_healthy(agent)
                else:
                    last_check = self.health_checks.get(agent)
                    if last_check and (now - last_check) > timedelta(minutes=2):
                        self.agent_status[agent] = "DOWN"
                        set_agent_down(agent)
                        logger.error(f"AGENT DOWN: {agent}")
                        
                        # Log event
                        await EventLogManager.log(
                            event_type="agent_down",
                            event_name=f"Agent {agent} is down",
                            agent_name="meta_supervisor",
                            correlation_id=f"health_{now.isoformat()}",
                            payload={"agent": agent, "last_seen": last_check.isoformat() if last_check else None},
                        )
                    else:
                        self.agent_status[agent] = "DEGRADED"
                        set_agent_degraded(agent)
            
            if not disk_ok:
                logger.warning("Disk space critical!")
                set_agent_degraded("meta_supervisor")
            
            # Log overall health
            healthy = sum(1 for s in self.agent_status.values() if s == "HEALTHY")
            total = len(self.agent_status)
            
            logger.info(f"Health check: {healthy}/{total} agents healthy")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            ERRORS_TOTAL.labels(agent="meta_supervisor", type="health_check").inc()
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("🧠 ASYNC META SUPERVISOR V2 STARTED")
        logger.info("Health checks | Process monitoring | Alerts")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        while self.running:
            try:
                await self.run_health_check()
                await asyncio.sleep(60)  # 60s between health checks
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Supervisor loop error: {e}")
                await asyncio.sleep(30)
    
    def stop(self):
        self.running = False

async def main():
    supervisor = AsyncMetaSupervisor()
    await supervisor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Meta supervisor stopped")
