#!/usr/bin/env python3
"""
Unified Dashboard - Master Control Panel
Combines: Crypto, CashOut, Swarm, Agents, System Health
"""

import asyncio
import aiohttp
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unified_dashboard")


@dataclass
class DashboardSection:
    name: str
    icon: str
    status: str
    data: Dict
    last_updated: str


class UnifiedDashboard:
    """Master dashboard combining all systems"""
    
    def __init__(self):
        self.sections: Dict[str, DashboardSection] = {}
        self.data_dir = Path("/root/.openclaw/workspace/dashboard_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_full_dashboard(self) -> str:
        """Generate complete dashboard"""
        
        # Collect all data
        await self._collect_crypto_data()
        await self._collect_cashout_data()
        await self._collect_swarm_data()
        await self._collect_agent_data()
        await self._collect_system_data()
        await self._collect_telegram_data()
        
        # Build dashboard text
        dashboard = self._build_dashboard_text()
        
        # Save to file
        self._save_dashboard(dashboard)
        
        return dashboard
    
    async def _collect_crypto_data(self):
        """Collect crypto market data"""
        try:
            # Fetch from DexScreener
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.dexscreener.com/latest/dex/tokens/SOL",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get("pairs", [])
                        
                        sol_price = 0
                        sol_change = 0
                        top_tokens = []
                        
                        if pairs:
                            sol_price = float(pairs[0].get("priceUsd", 0))
                            sol_change = float(pairs[0].get("priceChange", {}).get("h24", 0))
                            
                            for pair in pairs[:5]:
                                top_tokens.append({
                                    "token": pair.get("baseToken", {}).get("symbol", "?"),
                                    "price": float(pair.get("priceUsd", 0)),
                                    "change": float(pair.get("priceChange", {}).get("h24", 0)),
                                    "volume": float(pair.get("volume", {}).get("h24", 0))
                                })
                        
                        self.sections["crypto"] = DashboardSection(
                            name="CRYPTO MARKETS",
                            icon="📈",
                            status="🟢 ACTIVE",
                            data={
                                "sol_price": sol_price,
                                "sol_change": sol_change,
                                "top_tokens": top_tokens,
                                "pairs_count": len(pairs)
                            },
                            last_updated=datetime.now().isoformat()
                        )
                    else:
                        raise Exception(f"HTTP {resp.status}")
                        
        except Exception as e:
            self.sections["crypto"] = DashboardSection(
                name="CRYPTO MARKETS",
                icon="📈",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    async def _collect_cashout_data(self):
        """Collect CashOut system data"""
        try:
            # Read tracked bets
            bets_file = Path("/root/.openclaw/workspace/cashout_system/data/tracked_bets.json")
            bets = {}
            if bets_file.exists():
                with open(bets_file, 'r') as f:
                    bets = json.load(f)
            
            # Read state
            state_file = Path("/root/.openclaw/workspace/cashout_system/data/state.json")
            state = {}
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
            
            self.sections["cashout"] = DashboardSection(
                name="CASHOUT SYSTEM",
                icon="💰",
                status="🟢 ACTIVE",
                data={
                    "tracked_bets": len(bets),
                    "active_matches": len(state.get("active_matches", {})),
                    "bookmakers": ["Stoiximan", "Novibet"]
                },
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.sections["cashout"] = DashboardSection(
                name="CASHOUT SYSTEM",
                icon="💰",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    async def _collect_swarm_data(self):
        """Collect swarm intelligence data"""
        try:
            # Read evolution state
            evo_file = Path("/root/.openclaw/workspace/swarm_general/data/evolution_state.json")
            evo = {"generation": 0, "current_score": 0}
            if evo_file.exists():
                with open(evo_file, 'r') as f:
                    evo = json.load(f)
            
            # Read money state
            money_file = Path("/root/.openclaw/workspace/swarm_general/data/money_state.json")
            money = {"actions_taken": 0, "opportunities_found": 0}
            if money_file.exists():
                with open(money_file, 'r') as f:
                    money = json.load(f)
            
            self.sections["swarm"] = DashboardSection(
                name="SWARM INTELLIGENCE",
                icon="🐝",
                status="🟢 ACTIVE",
                data={
                    "generation": evo.get("generation", 0),
                    "score": evo.get("current_score", 0),
                    "actions": money.get("actions_taken", 0),
                    "opportunities": money.get("opportunities_found", 0)
                },
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.sections["swarm"] = DashboardSection(
                name="SWARM INTELLIGENCE",
                icon="🐝",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    async def _collect_agent_data(self):
        """Collect agent status data"""
        try:
            # Count processes
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True
            )
            
            agent_patterns = [
                'telegram_orchestrator', 'general_orchestrator', 'realtime_interface',
                'money_action', 'enhanced_scanner', 'evolution_engine', 'telegram_alert',
                'profit_engine', 'auto_runner', 'smart_money', 'auto_sniper'
            ]
            
            agents = []
            for line in result.stdout.split('\n'):
                for pattern in agent_patterns:
                    if pattern in line and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            agents.append({
                                "name": pattern.replace('_', ' ').title(),
                                "pid": parts[1],
                                "cpu": parts[2],
                                "mem": parts[3],
                                "uptime": parts[9] if len(parts) > 9 else '?'
                            })
            
            self.sections["agents"] = DashboardSection(
                name="AGENT SWARM",
                icon="🤖",
                status="🟢 ACTIVE",
                data={
                    "active_agents": len(agents),
                    "agents": agents[:10]  # Top 10
                },
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.sections["agents"] = DashboardSection(
                name="AGENT SWARM",
                icon="🤖",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    async def _collect_system_data(self):
        """Collect system health data"""
        try:
            # CPU
            cpu = 0
            try:
                with open('/proc/loadavg', 'r') as f:
                    cpu = round(float(f.read().split()[0]) * 10, 1)
            except:
                pass
            
            # Memory
            mem = 0
            try:
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                    total = avail = 0
                    for line in lines:
                        if 'MemTotal' in line:
                            total = int(line.split()[1])
                        elif 'MemAvailable' in line:
                            avail = int(line.split()[1])
                    if total:
                        mem = round(((total - avail) / total) * 100, 1)
            except:
                pass
            
            # Processes
            procs = 0
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                procs = len(result.stdout.strip().split('\n')) - 1
            except:
                pass
            
            # Disk
            disk = 0
            try:
                result = subprocess.run(['df', '/'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    disk = int(lines[1].split()[4].replace('%', ''))
            except:
                pass
            
            self.sections["system"] = DashboardSection(
                name="SYSTEM HEALTH",
                icon="💻",
                status="🟢 HEALTHY",
                data={
                    "cpu": cpu,
                    "memory": mem,
                    "processes": procs,
                    "disk": disk
                },
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.sections["system"] = DashboardSection(
                name="SYSTEM HEALTH",
                icon="💻",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    async def _collect_telegram_data(self):
        """Collect Telegram bot status"""
        try:
            # Check if bot is running
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True
            )
            
            bot_running = 'telegram_orchestrator.py' in result.stdout
            
            # Count handlers
            handlers = 40  # Approximate
            
            self.sections["telegram"] = DashboardSection(
                name="TELEGRAM BOT",
                icon="📱",
                status="🟢 ONLINE" if bot_running else "🔴 OFFLINE",
                data={
                    "bot": "@WorkSS11_bot",
                    "handlers": handlers,
                    "commands": [
                        "/dashboard", "/agents", "/cashout", "/scan",
                        "/swarm", "/status", "/help"
                    ]
                },
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.sections["telegram"] = DashboardSection(
                name="TELEGRAM BOT",
                icon="📱",
                status=f"🟡 ERROR: {str(e)[:30]}",
                data={},
                last_updated=datetime.now().isoformat()
            )
    
    def _build_dashboard_text(self) -> str:
        """Build the dashboard text"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        text = f"""🎯 **UNIFIED MASTER DASHBOARD** 🎯
Last update: {now}

"""
        
        # Crypto Section
        if "crypto" in self.sections:
            crypto = self.sections["crypto"]
            text += f"""📈 **CRYPTO MARKETS** {crypto.status}

💰 SOL: ${crypto.data.get('sol_price', 0):.2f} ({crypto.data.get('sol_change', 0):+.1f}%)
📊 Pairs: {crypto.data.get('pairs_count', 0)}

🔥 **Top Tokens:**
"""
            for token in crypto.data.get('top_tokens', []):
                emoji = "🟢" if token['change'] > 0 else "🔴"
                text += f"{emoji} {token['token']}: ${token['price']:.6f} ({token['change']:+.1f}%)\n"
            text += "\n"
        
        # CashOut Section
        if "cashout" in self.sections:
            cash = self.sections["cashout"]
            text += f"""💰 **CASHOUT SYSTEM** {cash.status}

📊 Tracked Bets: {cash.data.get('tracked_bets', 0)}
⚽ Active Matches: {cash.data.get('active_matches', 0)}
🏢 Bookmakers: {', '.join(cash.data.get('bookmakers', []))}

Commands: `/cashout track`, `/cashout list`, `/cashout check`

"""
        
        # Swarm Section
        if "swarm" in self.sections:
            swarm = self.sections["swarm"]
            text += f"""🐝 **SWARM INTELLIGENCE** {swarm.status}

🧬 Generation: {swarm.data.get('generation', 0)}
⭐ Score: {swarm.data.get('score', 0):.2f}/10.0
💰 Actions: {swarm.data.get('actions', 0)}
📈 Opportunities: {swarm.data.get('opportunities', 0)}

"""
        
        # Agents Section
        if "agents" in self.sections:
            agents = self.sections["agents"]
            text += f"""🤖 **AGENT SWARM** {agents.status}

📊 Active Agents: {agents.data.get('active_agents', 0)}

"""
            for agent in agents.data.get('agents', [])[:5]:
                text += f"• {agent['name']}: PID {agent['pid']} | CPU {agent['cpu']}% | MEM {agent['mem']}%\n"
            text += "\n"
        
        # System Section
        if "system" in self.sections:
            sys = self.sections["system"]
            text += f"""💻 **SYSTEM HEALTH** {sys.status}

🖥️ CPU: {sys.data.get('cpu', 0):.1f}% {'🟢' if sys.data.get('cpu', 0) < 70 else '🟡' if sys.data.get('cpu', 0) < 90 else '🔴'}
🧠 Memory: {sys.data.get('memory', 0):.1f}% {'🟢' if sys.data.get('memory', 0) < 80 else '🟡' if sys.data.get('memory', 0) < 95 else '🔴'}
💾 Disk: {sys.data.get('disk', 0)}% {'🟢' if sys.data.get('disk', 0) < 80 else '🟡'}
⚙️ Processes: {sys.data.get('processes', 0)}

"""
        
        # Telegram Section
        if "telegram" in self.sections:
            tel = self.sections["telegram"]
            text += f"""📱 **TELEGRAM BOT** {tel.status}

🤖 Bot: {tel.data.get('bot', 'Unknown')}
📋 Handlers: {tel.data.get('handlers', 0)}

**Key Commands:**
"""
            for cmd in tel.data.get('commands', []):
                text += f"• {cmd}\n"
            text += "\n"
        
        text += """---
🔄 **Refresh:** `/dashboard refresh`
📊 **Full Status:** `/status`
💰 **CashOut:** `/cashout`
🤖 **Agents:** `/agents`
"""
        
        return text
    
    def _save_dashboard(self, dashboard: str):
        """Save dashboard to file"""
        with open(self.data_dir / "dashboard.txt", 'w') as f:
            f.write(dashboard)
        
        # Also save JSON
        with open(self.data_dir / "dashboard.json", 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "sections": {k: asdict(v) for k, v in self.sections.items()}
            }, f, indent=2)
        
        logger.info("Dashboard saved")
    
    def get_dashboard(self) -> str:
        """Get cached dashboard"""
        try:
            with open(self.data_dir / "dashboard.txt", 'r') as f:
                return f.read()
        except:
            return "Dashboard not generated yet. Run `/dashboard` command."


# Example usage
async def main():
    dashboard = UnifiedDashboard()
    text = await dashboard.generate_full_dashboard()
    print(text)


if __name__ == "__main__":
    asyncio.run(main())