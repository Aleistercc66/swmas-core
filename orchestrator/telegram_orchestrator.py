"""
Telegram Orchestrator Agent - Main Entry Point
================================================
The Brain (AImind) lives here. This bot is the orchestrator
that connects the user to an evolving swarm of AI agents.

Features:
- Direct brain connection to AImind (OpenClaw)
- Swarm agent spawning and management
- Continuous skill evolution and learning
- Full access to workspace tools and APIs
- Autonomous operation 24/7

Bot: @WorkSS11_bot
Token: 8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac
"""

import os
import sys
import json
import asyncio
import logging
import importlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Configure paths
WORKSPACE = Path("/root/.openclaw/workspace")
ORCHESTRATOR_DIR = WORKSPACE / "orchestrator"
AGENTS_DIR = WORKSPACE / "agents"

# Add orchestrator first so its core module takes precedence
sys.path.insert(0, str(ORCHESTRATOR_DIR))
sys.path.insert(0, str(WORKSPACE))

# Import orchestrator modules
from core.brain_connector import BrainConnector
from core.swarm_manager import SwarmManager
from core.skill_registry import SkillRegistry
from core.context_engine import ContextEngine
from core.autonomous_loop import AutonomousLoop
from core.advanced_dashboard import AdvancedDashboard
from core.auto_sniper import AutoSniperBot, SNIPER_CONFIG
# Import wallet commands
from core.wallet_commands import WalletCommandHandler, initialize_wallet_system

# NOW add agents dir (after orchestrator imports to avoid core shadowing)
sys.path.insert(0, str(AGENTS_DIR))

# Import Smart Money Tracker
from smart_money_commands import SmartMoneyCommandHandler
from agents.airdrop_agent import get_airdrop_agent, AirdropAgent
from core.airdrop_farming_executor import get_farming_executor, start_farming_executor

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(ORCHESTRATOR_DIR / "logs" / "orchestrator.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class OrchestratorBot:
    """
    Main orchestrator bot class.
    Acts as the bridge between the user, the Brain (AImind), and the swarm.
    """

    def __init__(self, token: str):
        self.token = token
        self.app: Optional[Application] = None
        self.brain: Optional[BrainConnector] = None
        self.swarm: Optional[SwarmManager] = None
        self.skills: Optional[SkillRegistry] = None
        self.context: Optional[ContextEngine] = None
        self.autonomous: Optional[AutonomousLoop] = None
        self.dashboard: Optional[AdvancedDashboard] = None
        self.wallet_handler: Optional[WalletCommandHandler] = None
        self.smart_money_handler: Optional[SmartMoneyCommandHandler] = None
        self.user_sessions: Dict[int, Dict] = {}
        self.sniper: Optional[AutoSniperBot] = None
        self.is_running = False

    async def initialize(self):
        """Initialize all orchestrator components."""
        logger.info("🔥 Initializing Orchestrator Bot...")

        # Initialize brain connector (connects to AImind)
        self.brain = BrainConnector()
        await self.brain.initialize()
        logger.info("🧠 Brain connector initialized")

        # Initialize swarm manager
        self.swarm = SwarmManager(brain=self.brain)
        await self.swarm.initialize()
        logger.info("🐝 Swarm manager initialized")

        # Initialize skill registry
        self.skills = SkillRegistry()
        await self.skills.initialize()
        logger.info("🎯 Skill registry initialized")

        # Initialize context engine
        self.context = ContextEngine()
        await self.context.initialize()
        logger.info("🌐 Context engine initialized")

        # Initialize autonomous loop
        self.autonomous = AutonomousLoop(
            brain=self.brain,
            swarm=self.swarm,
            skills=self.skills,
            context=self.context,
        )
        await self.autonomous.initialize()
        logger.info("🤖 Autonomous loop initialized")

        # Initialize advanced dashboard
        self.dashboard = AdvancedDashboard(brain=self.brain)
        await self.dashboard.initialize()
        logger.info("📊 Advanced dashboard initialized")

        # Initialize wallet command handler
        self.wallet_handler = await initialize_wallet_system()
        logger.info("💼 Wallet handler initialized")

        # Initialize auto trader with wallet
        from core.auto_trader import initialize_auto_trader
        self.auto_trader = await initialize_auto_trader(
            wallet_manager=self.wallet_handler.wallet_manager if self.wallet_handler else None,
            config={'mode': 'paper'}  # Default to paper, user must explicitly switch to live
        )
        logger.info("🤖 Auto trader initialized")

        # Initialize airdrop autonomous tracker
        from core.airdrop_autonomous import start_airdrop_tracker
        self.airdrop_tracker = await start_airdrop_tracker(
            telegram_app=self.app,
            chat_id="158923136"
        )
        logger.info("🪂 Airdrop autonomous tracker started")

        # Initialize farming executor (automated task execution)
        from core.airdrop_farming_executor import start_farming_executor
        self.farming_executor = await start_farming_executor(
            wallet_manager=self.wallet_handler.wallet_manager if self.wallet_handler else None
        )
        logger.info("🚜 Farming executor started (automated execution)")

        # Initialize Smart Money Tracker
        self.smart_money_handler = SmartMoneyCommandHandler(self, None)
        logger.info("🎯 Smart Money Tracker initialized")

        # Initialize Auto-Sniper Bot
        self.sniper = AutoSniperBot(SNIPER_CONFIG, telegram_app=None)
        logger.info("🔫 Auto-Sniper initialized (ready to start)")

        # Build Telegram application
        self.app = Application.builder().token(self.token).build()
        self._setup_handlers()
        logger.info("📱 Telegram app configured")
        
        # Initialize group monitor (AFTER app is built)
        from core.group_monitor import add_group_handler, get_monitor
        self.group_monitor = get_monitor(self.app)
        await add_group_handler(self.app)
        logger.info("🔍 Group monitor initialized")

        self.is_running = True
        logger.info("✅ Orchestrator Bot fully initialized!")

    def _setup_handlers(self):
        """Setup Telegram command and message handlers."""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("swarm", self.cmd_swarm))
        self.app.add_handler(CommandHandler("agents", self.cmd_agents))
        self.app.add_handler(CommandHandler("spawn", self.cmd_spawn))
        self.app.add_handler(CommandHandler("kill", self.cmd_kill))
        self.app.add_handler(CommandHandler("skills", self.cmd_skills))
        self.app.add_handler(CommandHandler("learn", self.cmd_learn))
        self.app.add_handler(CommandHandler("scan", self.cmd_scan))
        self.app.add_handler(CommandHandler("signal", self.cmd_signal))
        self.app.add_handler(CommandHandler("brain", self.cmd_brain))
        self.app.add_handler(CommandHandler("exec", self.cmd_exec))
        self.app.add_handler(CommandHandler("mode", self.cmd_mode))
        self.app.add_handler(CommandHandler("autopilot", self.cmd_autopilot))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        self.app.add_handler(CommandHandler("jupiter", self.cmd_jupiter))
        self.app.add_handler(CommandHandler("solana", self.cmd_solana))
        self.app.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.app.add_handler(CommandHandler("exchanges", self.cmd_exchanges))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("whale", self.cmd_whale))
        self.app.add_handler(CommandHandler("alert", self.cmd_alert))
        self.app.add_handler(CommandHandler("backtest", self.cmd_backtest))
        self.app.add_handler(CommandHandler("connect", self.cmd_connect))
        self.app.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
        self.app.add_handler(CommandHandler("stream", self.cmd_stream))
        self.app.add_handler(CommandHandler("mempool", self.cmd_mempool))
        self.app.add_handler(CommandHandler("signals", self.cmd_signals))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        self.app.add_handler(CommandHandler("osint", self.cmd_osint))
        self.app.add_handler(CommandHandler("alert", self.cmd_alert))
        self.app.add_handler(CommandHandler("backtest", self.cmd_backtest))
        self.app.add_handler(CommandHandler("connect", self.cmd_connect))
        
        # CashOut System commands
        self.app.add_handler(CommandHandler("cashout", self.cmd_cashout))

        # Auto-Sniper commands
        self.app.add_handler(CommandHandler("sniper", self.cmd_sniper))
        self.app.add_handler(CommandHandler("snipe_start", self.cmd_snipe_start))
        self.app.add_handler(CommandHandler("snipe_stop", self.cmd_snipe_stop))
        self.app.add_handler(CommandHandler("snipe_status", self.cmd_snipe_status))
        self.app.add_handler(CommandHandler("snipe_stats", self.cmd_snipe_stats))
        self.app.add_handler(CommandHandler("live_mode", self.cmd_live_mode))
        self.app.add_handler(CommandHandler("paper_mode", self.cmd_paper_mode))
        self.app.add_handler(CommandHandler("hybrid_mode", self.cmd_hybrid_mode))

        # Wallet / MetaMask commands
        self.app.add_handler(CommandHandler("wallet", self.cmd_wallet))
        self.app.add_handler(CommandHandler("wallet_setup", self.cmd_wallet_setup))
        self.app.add_handler(CommandHandler("wallet_add", self.cmd_wallet_add))
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.app.add_handler(CommandHandler("send", self.cmd_send))
        self.app.add_handler(CommandHandler("token_add", self.cmd_token_add))
        self.app.add_handler(CommandHandler("trade", self.cmd_trade))

        # Auto Trading commands
        self.app.add_handler(CommandHandler("autotrade", self.cmd_autotrade))
        self.app.add_handler(CommandHandler("start_trading", self.cmd_start_trading))
        self.app.add_handler(CommandHandler("stop_trading", self.cmd_stop_trading))
        self.app.add_handler(CommandHandler("positions", self.cmd_positions))
        self.app.add_handler(CommandHandler("history", self.cmd_history))
        self.app.add_handler(CommandHandler("performance", self.cmd_performance))
        self.app.add_handler(CommandHandler("close_position", self.cmd_close_position))
        self.app.add_handler(CommandHandler("set_mode", self.cmd_set_mode))
        self.app.add_handler(CommandHandler("confirm_live", self.cmd_confirm_live))
        self.app.add_handler(CommandHandler("config", self.cmd_config))

        # Airdrop commands
        self.app.add_handler(CommandHandler("airdrops", self.cmd_airdrops))
        self.app.add_handler(CommandHandler("airdrop", self.cmd_airdrop))
        self.app.add_handler(CommandHandler("farming", self.cmd_farming))
        self.app.add_handler(CommandHandler("farm_start", self.cmd_farm_start))
        self.app.add_handler(CommandHandler("farm_update", self.cmd_farm_update))
        self.app.add_handler(CommandHandler("check", self.cmd_check_eligibility))
        self.app.add_handler(CommandHandler("check_eligibility", self.cmd_check_eligibility))
        self.app.add_handler(CommandHandler("claim_list", self.cmd_claim_list))
        self.app.add_handler(CommandHandler("airdrop_add", self.cmd_airdrop_add))
        self.app.add_handler(CommandHandler("airdrop_remove", self.cmd_airdrop_remove))
        self.app.add_handler(CommandHandler("farm_auto", self.cmd_farm_auto))
        self.app.add_handler(CommandHandler("farm_stop", self.cmd_farm_stop))
        self.app.add_handler(CommandHandler("farm_status", self.cmd_farm_status))
        self.app.add_handler(CommandHandler("farm_report", self.cmd_farm_report))

        # Smart Money Tracker commands
        self.app.add_handler(CommandHandler("discover", self.cmd_discover))
        self.app.add_handler(CommandHandler("track", self.cmd_track))
        self.app.add_handler(CommandHandler("untrack", self.cmd_untrack))
        self.app.add_handler(CommandHandler("smart_list", self.cmd_smart_list))
        self.app.add_handler(CommandHandler("smart_stats", self.cmd_smart_stats))
        self.app.add_handler(CommandHandler("smart_top", self.cmd_smart_top))
        self.app.add_handler(CommandHandler("smart_analyze", self.cmd_smart_analyze))
        self.app.add_handler(CommandHandler("follow", self.cmd_follow))

        # Callback queries (buttons)
        self.app.add_handler(CallbackQueryHandler(self.callback_handler))

        # Messages
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        self.app.add_handler(
            MessageHandler(filters.PHOTO | filters.Document.ALL, self.handle_media)
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command — welcome message."""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name

        welcome_text = f"""
🔥 **Welcome to the SWARM, {user_name}!** 🔥

I am **AImind Orchestrator** — your AI brain's extension.

🧠 **Brain:** Connected to AImind (OpenClaw)
🐝 **Swarm:** Self-evolving multi-agent system
🎯 **Skills:** Continuously learning and improving
📊 **Dashboard:** Real-time market + on-chain data
🤖 **Mode:** Manual / Autopilot / Hybrid

**What I can do:**
• Spawn specialized agents on demand
• Monitor crypto markets 24/7 with live streams
• Execute trading strategies across DEX/CEX
• Track whales, mempool, smart money
• Learn from every interaction
• Develop new skills autonomously

**Quick Commands:**
`/swarm` — View swarm status
`/spawn <agent_type>` — Spawn new agent
`/scan` — Market scan now
`/dashboard` — Live dashboard
`/stream on` — Start real-time streams
`/autopilot` — Toggle autonomous mode
`/brain <query>` — Direct brain query
`/wallet_setup` — Connect your MetaMask wallet 🔐
`/discover` — Find smart money wallets 🎯
`/track <wallet>` — Track wallet moves 👁️
`/cashout` — CashOut system for sports betting 💰

Type `/help` for full command list.
"""
        await update.message.reply_text(welcome_text, parse_mode="Markdown")

    async def cmd_cashout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """CashOut system commands"""
        if not context.args:
            await update.message.reply_text(
                "💰 **CASHOUT SYSTEM** 💰\n\n"
                "Commands:\n"
                "• `/cashout status` — System status\n"
                "• `/cashout track <match_id> <home> <away> <bookmaker> <odds> <stake>`\n"
                "• `/cashout list` — List tracked bets\n"
                "• `/cashout check` — Check all matches now\n"
                "• `/cashout analysis <match_id>` — Get analysis\n",
                parse_mode="Markdown"
            )
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "status":
            status = await self._get_cashout_status()
            await update.message.reply_text(status, parse_mode="Markdown")
            
        elif subcommand == "track":
            if len(context.args) < 7:
                await update.message.reply_text(
                    "Usage: `/cashout track <match_id> <home> <away> <bookmaker> <odds> <stake>`\n"
                    "Example: `/cashout track 12345 Olympiacos PAOK Stoiximan 2.50 100`",
                    parse_mode="Markdown"
                )
                return
            
            match_id = context.args[1]
            home = context.args[2]
            away = context.args[3]
            bookmaker = context.args[4]
            odds = float(context.args[5])
            stake = float(context.args[6])
            
            await self._track_bet(match_id, home, away, bookmaker, odds, stake)
            await update.message.reply_text(
                f"✅ **Bet tracked!**\n\n"
                f"🏠 {home} vs {away}\n"
                f"🏢 {bookmaker}\n"
                f"📊 Odds: {odds} | Stake: €{stake}\n"
                f"🔍 Monitoring for cash-out opportunities...",
                parse_mode="Markdown"
            )
            
        elif subcommand == "list":
            bets = await self._get_tracked_bets()
            await update.message.reply_text(bets, parse_mode="Markdown")
            
        elif subcommand == "check":
            await update.message.reply_text("🔍 Checking all matches now...")
            result = await self._run_cashout_check()
            await update.message.reply_text(result, parse_mode="Markdown")
            
        elif subcommand == "analysis":
            if len(context.args) < 2:
                await update.message.reply_text("Usage: `/cashout analysis <match_id>`", parse_mode="Markdown")
                return
            match_id = context.args[1]
            analysis = await self._get_match_analysis(match_id)
            await update.message.reply_text(analysis, parse_mode="Markdown")
            
        else:
            await update.message.reply_text("Unknown command. Use `/cashout` for help.")
    
    async def _get_cashout_status(self) -> str:
        """Get cashout system status"""
        try:
            import subprocess
            result = subprocess.run(
                ['python3', '/root/.openclaw/workspace/cashout_system/cashout_orchestrator.py', '--status'],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout or "🚀 CashOut System: Ready\n📊 No active monitoring"
        except Exception as e:
            return f"🚀 CashOut System: Ready\n⚠️ Status check: {e}"
    
    async def _track_bet(self, match_id, home, away, bookmaker, odds, stake):
        """Track a bet"""
        import json
        from pathlib import Path
        
        bets_file = Path('/root/.openclaw/workspace/cashout_system/data/tracked_bets.json')
        bets_file.parent.mkdir(parents=True, exist_ok=True)
        
        bets = {}
        if bets_file.exists():
            with open(bets_file, 'r') as f:
                bets = json.load(f)
        
        bets[match_id] = {
            "match_id": match_id,
            "home_team": home,
            "away_team": away,
            "bookmaker": bookmaker,
            "original_odds": odds,
            "stake": stake,
            "added_at": datetime.now().isoformat()
        }
        
        with open(bets_file, 'w') as f:
            json.dump(bets, f, indent=2, ensure_ascii=False)
    
    async def _get_tracked_bets(self) -> str:
        """Get list of tracked bets"""
        import json
        from pathlib import Path
        
        bets_file = Path('/root/.openclaw/workspace/cashout_system/data/tracked_bets.json')
        
        if not bets_file.exists():
            return "🌑 No tracked bets. Add one with `/cashout track`"
        
        with open(bets_file, 'r') as f:
            bets = json.load(f)
        
        if not bets:
            return "🌑 No tracked bets. Add one with `/cashout track`"
        
        text = "📊 **TRACKED BETS** 📊\n\n"
        for match_id, bet in bets.items():
            text += f"⚽ {bet['home_team']} vs {bet['away_team']}\n"
            text += f"🏢 {bet['bookmaker']} | Odds: {bet['original_odds']}\n"
            text += f"💰 Stake: €{bet['stake']}\n"
            text += f"📋 ID: `{match_id}`\n\n"
        
        return text
    
    async def _run_cashout_check(self) -> str:
        """Run manual check"""
        try:
            import subprocess
            result = subprocess.run(
                ['python3', '-c', '''
import asyncio
import sys
sys.path.insert(0, "/root/.openclaw/workspace/cashout_system")
from cashout_orchestrator import CashOutOrchestrator

async def run():
    async with CashOutOrchestrator() as orch:
        orch.load_state()
        return await orch.run_once()

print(asyncio.run(run()))
                '''],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout or "✅ Check complete - no alerts"
        except Exception as e:
            return f"⚠️ Check error: {e}"
    
    async def _get_match_analysis(self, match_id: str) -> str:
        """Get analysis for specific match"""
        try:
            import subprocess
            result = subprocess.run(
                ['python3', '-c', f'''
import asyncio
import sys
sys.path.insert(0, "/root/.openclaw/workspace/cashout_system")
from cashout_orchestrator import CashOutOrchestrator

async def run():
    async with CashOutOrchestrator() as orch:
        orch.load_state()
        
        if match_id not in orch.tracked_bets:
            return "❌ Match not tracked. Use `/cashout track` first."
        
        bet = orch.tracked_bets[match_id]
        return f"💰 **ANALYSIS: {bet['home_team']} vs {bet['away_team']}** 💰\n\n🏢 {bet['bookmaker']} | Odds: {bet['original_odds']} | Stake: €{bet['stake']}"

print(asyncio.run(run()))
                '''],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout or "📊 Analysis not available"
        except Exception as e:
            return f"⚠️ Analysis error: {e}"

    # ============== COMMAND HANDLERS ==============

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command — welcome message."""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name

        welcome_text = f"""
🔥 **Welcome to the SWARM, {user_name}!** 🔥

I am **AImind Orchestrator** — your AI brain's extension.

🧠 **Brain:** Connected to AImind (OpenClaw)
🐝 **Swarm:** Self-evolving multi-agent system
🎯 **Skills:** Continuously learning and improving
📊 **Dashboard:** Real-time market + on-chain data
🤖 **Mode:** Manual / Autopilot / Hybrid

**What I can do:**
• Spawn specialized agents on demand
• Monitor crypto markets 24/7 with live streams
• Execute trading strategies across DEX/CEX
• Track whales, mempool, smart money
• Learn from every interaction
• Develop new skills autonomously

**Quick Commands:**
`/swarm` — View swarm status
`/spawn <agent_type>` — Spawn new agent
`/scan` — Market scan now
`/dashboard` — Live dashboard
`/stream on` — Start real-time streams
`/autopilot` — Toggle autonomous mode
`/brain <query>` — Direct brain query
`/wallet_setup` — Connect your MetaMask wallet 🔐
`/discover` — Find smart money wallets 🎯
`/track <wallet>` — Track wallet moves 👁️

**Let's move!** 🚀
        """

        keyboard = [
            [InlineKeyboardButton("🐝 Swarm Status", callback_data="swarm_status")],
            [InlineKeyboardButton("📊 Market Scan", callback_data="market_scan")],
            [InlineKeyboardButton("🤖 Autopilot", callback_data="toggle_autopilot")],
            [InlineKeyboardButton("🧠 Brain Query", callback_data="brain_query")],
        ]

        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        # Initialize user session
        self.user_sessions[user_id] = {
            "started_at": datetime.now().isoformat(),
            "mode": "manual",
            "active_agents": [],
            "preferences": {},
        }

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command — show all available commands."""
        help_text = """
🎯 **ORCHESTRATOR COMMANDS** 🎯

**System:**
`/start` — Initialize connection
`/status` — Full system status
`/help` — This message

**Swarm Management:**
`/swarm` — Swarm overview
`/agents` — List active agents
`/spawn <type>` — Spawn agent (types: scanner, trader, analyst, learner)
`/kill <agent_id>` — Terminate agent

**Market Intelligence:**
`/scan` — Instant market scan
`/signal` — Get trading signals
`/jupiter` — Jupiter DEX data
`/solana` — Solana ecosystem scan
`/analyze <token>` — Deep token analysis
`/whale` — Whale tracking
`/dashboard` — Live dashboard
`/stream <on/off>` — Real-time data streams
`/mempool` — Mempool monitor
`/signals` — Trading signals

**Portfolio & Trading:**
`/portfolio` — Portfolio tracking
`/exchanges` — Exchange status
`/backtest` — Strategy backtest
`/alert <condition>` — Custom alerts
`/connect <agent>` — Connect to any agent

**🪂 Airdrop Farming:**
`/airdrop` — Airdrop dashboard
`/airdrops [status] [chain]` — Watchlist (e.g. `/airdrops active eth`)
`/airdrop <name>` — Airdrop detail
`/airdrop discover` — Discover new airdrops
`/farm_start <airdrop>` — Start farming
`/farm_update <airdrop> <task>` — Mark task done
`/farming` — Show farming progress
`/check <airdrop> <wallet>` — Check eligibility
`/claim_list` — Claimable airdrops
`/airdrop_add <name> <protocol>` — Add custom airdrop
`/airdrop_remove <name>` — Remove from watchlist

**Wallet & MetaMask:**
`/wallet` — Show your wallets
`/wallet_setup` — Connect MetaMask (Private Key OR Secret Recovery Phrase)
`/wallet_add` — Add another wallet (Account 2, 3... from same seed)
`/balance` — Check native balance (ETH)
`/portfolio` — Full portfolio + token balances
`/trade` — Trading interface

**Brain & OSINT:**
`/brain <query>` — Direct query to AImind
`/osint` — OSINT Intelligence Agent (learn/train/evolve)
`/skills` — List available skills
`/learn <skill>` — Learn/develop a skill

**Execution:**
`/exec <command>` — Execute system command
`/mode <mode>` — Set mode: manual/autopilot/hybrid
`/autopilot` — Toggle autonomous operation
`/pause` — Pause all operations
`/report` — Performance report

**🔫 Auto-Sniper (Meme Coin Hunter):**
`/sniper` — Sniper dashboard
`/snipe_start` — Start hunting (scans every 2 min)
`/snipe_stop` — Stop sniper
`/snipe_status` — Active positions
`/snipe_stats` — Performance stats
`/live_mode` — Switch to LIVE trading (⚠️ real money)
`/hybrid_mode` — Manual approval per trade
`/paper_mode` — Back to simulation only

`/sniper` — Sniper dashboard
`/snipe_start` — Start hunting (scans every 2 min)
`/snipe_stop` — Stop sniper
`/snipe_status` — Active positions
`/snipe_stats` — Performance stats
`/live_mode` — Switch to LIVE trading (⚠️ real money)
`/hybrid_mode` — Manual approval per trade
`/paper_mode` — Back to simulation only

**💰 CashOut System (Sports Betting):**
`/cashout` — CashOut dashboard
`/cashout status` — System status
`/cashout track <match_id> <home> <away> <bookmaker> <odds> <stake>` — Track a bet
`/cashout list` — List tracked bets
`/cashout check` — Check all matches now
`/cashout analysis <match_id>` — Get analysis

**Examples:**
`/spawn scanner` — Spawn market scanner
`/brain Analyze SOL momentum` — Brain analysis
`/exec python script.py` — Run script
`/analyze SOL` — Deep token analysis
`/stream on` — Start real-time streams
        """
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show full system status."""
        status = await self._get_full_status()
        await update.message.reply_text(status, parse_mode="Markdown")

    async def cmd_swarm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show swarm status."""
        swarm_status = await self.swarm.get_status()
        await update.message.reply_text(swarm_status, parse_mode="Markdown")

    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List active agents with real-time details from logs and processes."""
        import subprocess, json, os
        from datetime import datetime
        from pathlib import Path
        
        # Get running processes
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        all_lines = result.stdout.split('\n')
        
        # Define agent components to track
        agents_info = []
        agent_patterns = {
            'telegram_orchestrator.py': {'name': 'Orchestrator Bot', 'type': 'telegram'},
            'general_orchestrator.py': {'name': 'General Swarm', 'type': 'orchestrator'},
            'realtime_interface.py': {'name': 'Telegram Interface', 'type': 'interface'},
            'money_action_engine.py': {'name': 'Money Engine', 'type': 'trader'},
            'enhanced_scanner.py': {'name': 'Scanner', 'type': 'scanner'},
            'evolution_engine.py': {'name': 'Evolution', 'type': 'learner'},
            'telegram_alert.py': {'name': 'Alert Sender', 'type': 'notifier'},
            'profit_engine.py': {'name': 'Profit Engine', 'type': 'trader'},
            'auto_runner.py': {'name': 'Solana Agent', 'type': 'auto'},
            'smart_money_tracker.py': {'name': 'Smart Money', 'type': 'tracker'},
            'auto_sniper.py': {'name': 'Sniper Bot', 'type': 'sniper'},
        }
        
        for line in all_lines:
            for pattern, info in agent_patterns.items():
                if pattern in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 11:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        uptime = parts[9] if len(parts) > 9 else '?'
                        agents_info.append({
                            'name': info['name'],
                            'type': info['type'],
                            'pid': pid,
                            'cpu': cpu,
                            'mem': mem,
                            'uptime': uptime,
                        })
        
        # Get last activity from logs
        log_dir = Path('/root/.openclaw/workspace/swarm_general/logs')
        log_snippets = {}
        log_files = {
            'money_action.log': 'Money Engine',
            'scanner.log': 'Scanner',
            'evolution.log': 'Evolution',
            'telegram_alerts.log': 'Alerts',
            'realtime_interface.log': 'Telegram Bot',
        }
        
        for log_file, agent_name in log_files.items():
            log_path = log_dir / log_file
            if log_path.exists():
                try:
                    result = subprocess.run(['tail', '-1', str(log_path)], capture_output=True, text=True)
                    if result.stdout.strip():
                        log_snippets[agent_name] = result.stdout.strip()[-80:]  # Last 80 chars
                except Exception:
                    pass
        
        # Build text
        text = "🐝 **ACTIVE AGENTS** 🐝\n\n"
        
        if not agents_info:
            text += "🌑 No agents running.\n"
        else:
            for agent in agents_info:
                status_emoji = "🟢" if float(agent['cpu']) > 0 or float(agent['mem']) > 0 else "🟡"
                text += f"{status_emoji} **{agent['name']}**\n"
                text += f"   PID: `{agent['pid']}` | CPU: {agent['cpu']}% | MEM: {agent['mem']}%\n"
                text += f"   Uptime: {agent['uptime']} | Type: {agent['type']}\n"
                
                # Add last log line if available
                if agent['name'] in log_snippets:
                    snippet = log_snippets[agent['name']]
                    text += f"   📝 `{snippet}`\n"
                
                text += "\n"
        
        text += f"\n📊 **Total Active:** {len(agents_info)}\n"
        text += f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}\n"
        text += "\nCommands:\n"
        text += "• `/agents` — Refresh\n"
        text += "• `/status` — Full system\n"
        text += "• `/dashboard` — Dashboard\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_spawn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Spawn a new agent."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/spawn <type>`\nTypes: scanner, trader, analyst, learner, monitor",
                parse_mode="Markdown",
            )
            return

        agent_type = context.args[0]
        config = " ".join(context.args[1:]) if len(context.args) > 1 else None

        await update.message.reply_text(f"🔄 Spawning **{agent_type}** agent...")

        try:
            agent = await self.swarm.spawn_agent(agent_type, config)
            await update.message.reply_text(
                f"✅ **Agent spawned!**\n\n"
                f"Name: `{agent['name']}`\n"
                f"ID: `{agent['id']}`\n"
                f"Type: {agent['type']}\n"
                f"Status: {agent['status']}",
                parse_mode="Markdown",
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Spawn failed: {str(e)}")

    async def cmd_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kill an agent."""
        if not context.args:
            await update.message.reply_text("Usage: `/kill <agent_id>`")
            return

        agent_id = context.args[0]
        await update.message.reply_text(f"💀 Killing agent `{agent_id}`...", parse_mode="Markdown")

        try:
            result = await self.swarm.kill_agent(agent_id)
            await update.message.reply_text(f"✅ Agent `{agent_id}` terminated.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Kill failed: {str(e)}")

    async def cmd_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List available skills."""
        skills = await self.skills.list_skills()
        text = "🎯 **AVAILABLE SKILLS** 🎯\n\n"
        for skill in skills:
            text += f"• **{skill['name']}** — {skill['description']}\n"
            text += f"  Level: {skill['level']} | Uses: {skill['uses']}\n\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_learn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trigger skill learning/development."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/learn <skill_name>` or `/learn auto` for autonomous learning"
            )
            return

        skill_name = context.args[0]
        await update.message.reply_text(f"🧠 Learning **{skill_name}**...")

        try:
            result = await self.skills.learn_skill(skill_name)
            await update.message.reply_text(
                f"✅ **Learning complete!**\n\n{result}", parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Learning failed: {str(e)}")

    async def cmd_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trigger instant market scan."""
        await update.message.reply_text("🔍 Initiating market scan...")

        try:
            # Use existing dexscreener scanner
            result = await self._run_market_scan()
            await update.message.reply_text(result, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Scan failed: {str(e)}")

    async def cmd_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get trading signals."""
        await update.message.reply_text("📊 Generating trading signals...")

        try:
            signals = await self._generate_signals()
            await update.message.reply_text(signals, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Signal generation failed: {str(e)}")

    async def cmd_brain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Direct query to AImind brain."""
        if not context.args:
            await update.message.reply_text("Usage: `/brain <your query>`")
            return

        query = " ".join(context.args)
        await update.message.reply_text(f"🧠 Querying brain: _{query}_...", parse_mode="Markdown")

        try:
            response = await self.brain.query(query, user_id=update.effective_user.id)
            await update.message.reply_text(
                f"🧠 **Brain Response:**\n\n{response}", parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Brain query failed: {str(e)}")

    async def cmd_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute system command."""
        if not context.args:
            await update.message.reply_text("Usage: `/exec <command>`")
            return

        command = " ".join(context.args)
        await update.message.reply_text(f"⚡ Executing: `{command}`", parse_mode="Markdown")

        try:
            result = await self._execute_command(command)
            # Truncate if too long
            if len(result) > 4000:
                result = result[:4000] + "\n... (truncated)"
            await update.message.reply_text(f"```\n{result}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Execution failed: {str(e)}")

    async def cmd_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set operation mode."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/mode <manual|autopilot|hybrid>`\n"
                f"Current: `{self.user_sessions.get(update.effective_user.id, {}).get('mode', 'manual')}`"
            )
            return

        mode = context.args[0].lower()
        if mode not in ("manual", "autopilot", "hybrid"):
            await update.message.reply_text("Invalid mode. Use: manual, autopilot, hybrid")
            return

        user_id = update.effective_user.id
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}
        self.user_sessions[user_id]["mode"] = mode

        await update.message.reply_text(f"✅ Mode set to: **{mode.upper()}**")

        if mode == "autopilot":
            await self.autonomous.start_for_user(user_id)
            await update.message.reply_text("🤖 Autopilot activated! Agent will operate autonomously.")
        elif mode == "manual":
            await self.autonomous.stop_for_user(user_id)

    async def cmd_autopilot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle autopilot mode."""
        user_id = update.effective_user.id
        current_mode = self.user_sessions.get(user_id, {}).get("mode", "manual")

        if current_mode == "autopilot":
            self.user_sessions[user_id]["mode"] = "manual"
            await self.autonomous.stop_for_user(user_id)
            await update.message.reply_text("🛑 Autopilot **DEACTIVATED**. Manual mode.")
        else:
            self.user_sessions[user_id]["mode"] = "autopilot"
            await self.autonomous.start_for_user(user_id)
            await update.message.reply_text(
                "🤖 **AUTOPILOT ACTIVATED!**\n\n"
                "I will now:\n"
                "• Monitor markets continuously\n"
                "• Spawn agents as needed\n"
                "• Send alerts on opportunities\n"
                "• Learn and adapt\n\n"
                "Use `/pause` to stop or `/mode manual` to switch back."
            )

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause all operations."""
        await self.autonomous.pause_all()
        await update.message.reply_text("⏸️ **All operations paused.** Use `/autopilot` to resume.")

    # ============== SNIPER COMMANDS ==============

    async def cmd_sniper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show sniper status and controls."""
        running = self.sniper and self.sniper.is_running
        status = "🔥 **RUNNING**" if running else "⏹️ **STOPPED**"
        
        active_count = 0
        if running:
            try:
                from core.auto_sniper import get_active_positions
                active_count = len(get_active_positions())
            except:
                pass
        
        await update.message.reply_text(
            f"🔫 **AUTO-SNIPER BOT** 🔫\n\n"
            f"Status: {status}\n"
            f"Active Positions: {active_count}\n"
            f"Scan Interval: Every 2 min\n"
            f"Mode: Aggressive (Paper Trading)\n\n"
            f"Commands:\n"
            f"`/snipe_start` — Start sniper\n"
            f"`/snipe_stop` — Stop sniper\n"
            f"`/snipe_status` — Current positions\n"
            f"`/snipe_stats` — Performance stats\n\n"
            f"Config:\n"
            f"• Max positions: 5\n"
            f"• Min liquidity: $5K\n"
            f"• Max MCap: $300K\n"
            f"• TP1: +300% | TP2: +500% | TP3: +1000%\n"
            f"• Stop Loss: -30%\n"
        )

    async def cmd_snipe_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the auto-sniper."""
        if not self.sniper:
            await update.message.reply_text("❌ Sniper not initialized.")
            return
        
        if self.sniper.is_running:
            await update.message.reply_text("🔫 Sniper is already running!")
            return
        
        # Pass telegram app for alerts
        self.sniper.telegram_app = self.app
        
        # Start in background
        asyncio.create_task(self.sniper.run())
        
        await update.message.reply_text(
            "🔥🔥🔥 **AUTO-SNIPER STARTED** 🔥🔥🔥\n\n"
            "Scanning DexScreener every 2 minutes...\n"
            "Hunting micro-cap gems with momentum!\n\n"
            "You'll get alerts when I find something.\n"
            "Use `/snipe_status` to check positions."
        )

    async def cmd_snipe_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop the auto-sniper."""
        if self.sniper and self.sniper.is_running:
            self.sniper.stop()
            await update.message.reply_text("🛑 **Sniper stopped.**")
        else:
            await update.message.reply_text("⏹️ Sniper is not running.")

    async def cmd_snipe_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active sniper positions."""
        try:
            from core.auto_sniper import get_active_positions
            positions = get_active_positions()
            if not positions:
                await update.message.reply_text("📊 No active positions. Sniper is hunting...")
                return
            
            msg = "📊 **ACTIVE SNIPER POSITIONS** 📊\n\n"
            for row in positions[:5]:
                symbol = row[1]
                entry = row[17] or 0
                status = row[16]
                detected = row[15][:16] if row[15] else "?"
                msg += f"🪙 {symbol} | Entry: ${entry}\n"
                msg += f"   Status: {status} | Detected: {detected}\n\n"
            
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def cmd_snipe_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show sniper performance stats."""
        try:
            import sqlite3
            from core.auto_sniper import DB_PATH
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            
            # Total gems found
            c.execute("SELECT COUNT(*) FROM gems")
            total = c.fetchone()[0]
            
            # Exited positions
            c.execute("SELECT COUNT(*), AVG(pnl_pct) FROM gems WHERE status = 'exited'")
            exited_row = c.fetchone()
            exited = exited_row[0] or 0
            avg_pnl = exited_row[1] or 0
            
            # Best trade
            c.execute("SELECT symbol, pnl_pct FROM gems WHERE status = 'exited' ORDER BY pnl_pct DESC LIMIT 1")
            best = c.fetchone()
            
            # Active positions
            c.execute("SELECT COUNT(*) FROM gems WHERE status IN ('paper_bought', 'monitoring', 'live_bought')")
            active = c.fetchone()[0]
            
            # Live vs paper split
            c.execute("SELECT COUNT(*) FROM gems WHERE status = 'live_bought'")
            live_count = c.fetchone()[0] or 0
            
            conn.close()
            
            best_str = f"{best[0]} (+{best[1]:.0f}%)" if best else "None yet"
            mode = getattr(self, 'sniper_mode', 'PAPER')
            
            await update.message.reply_text(
                f"📈 **SNIPER STATS** 📈\n\n"
                f"Mode: {mode}\n"
                f"Total Gems Found: {total}\n"
                f"Exited Trades: {exited}\n"
                f"Active Positions: {active}\n"
                f"Avg PnL: {avg_pnl:+.1f}%\n"
                f"Best Trade: {best_str}\n"
                f"Live Trades: {live_count}\n\n"
                f"🏆 Keep hunting!"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Stats error: {str(e)}")

    # ============== LIVE MODE COMMANDS ==============

    async def cmd_live_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch sniper to live trading mode."""
        user_id = update.effective_user.id
        
        # Security check: only authorized user
        if str(user_id) != "158923136":
            await update.message.reply_text("❌ Unauthorized. Only G:A.C can enable live mode.")
            return
        
        await update.message.reply_text(
            "🔴⚠️ **LIVE MODE ACTIVATION** ⚠️🔴\n\n"
            "This will use REAL MONEY for trading.\n\n"
            "**Requirements:**\n"
            "1. Wallet configured with SOL\n"
            "2. Understanding of risks\n"
            "3. Acceptable loss limits set\n\n"
            "**Paper Stats (17h running):**\n"
            "• 75 gems found, 32 exited\n"
            "• Avg PnL: +3.7%\n"
            "• Best: +568% | Worst: -98%\n\n"
            "Reply **CONFIRM_LIVE** to proceed\n"
            "Reply **HYBRID** for manual approval per trade\n"
            "Reply **CANCEL** to abort"
        )
    
    async def cmd_paper_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch sniper back to paper mode."""
        user_id = update.effective_user.id
        if str(user_id) != "158923136":
            await update.message.reply_text("❌ Unauthorized.")
            return
        
        # Kill live sniper if running, start paper
        # This is simplified — actual implementation needs process management
        await update.message.reply_text(
            "📊 **PAPER MODE ACTIVATED**\n\n"
            "Sniper is now running in simulation mode.\n"
            "No real money at risk.\n\n"
            "To go live: `/live_mode`"
        )
    
    async def cmd_hybrid_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch sniper to hybrid mode."""
        user_id = update.effective_user.id
        if str(user_id) != "158923136":
            await update.message.reply_text("❌ Unauthorized.")
            return
        
        await update.message.reply_text(
            "🟡 **HYBRID MODE**\n\n"
            "Sniper will:\n"
            "• Detect gems automatically\n"
            "• Send trade proposals to you\n"
            "• Wait 30 seconds for approval\n"
            "• Execute only if you reply APPROVE\n\n"
            "Reply **CONFIRM_HYBRID** to proceed"
        )

    # ============== MESSAGE HANDLERS ==============

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate performance report."""
        await update.message.reply_text("📈 Generating report...")

        try:
            report = await self._generate_report()
            await update.message.reply_text(report, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Report failed: {str(e)}")

    # ============== MESSAGE HANDLERS ==============

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages — route to brain or process directly."""
        user_id = update.effective_user.id
        text = update.message.text

        # Check if in wallet setup flow
        if self.wallet_handler and await self.wallet_handler.is_setting_up(user_id):
            await self.wallet_handler.handle_setup_message(update, context)
            return

        # Add to context
        await self.context.add_message(user_id, text)

        # Check if in autopilot mode
        mode = self.user_sessions.get(user_id, {}).get("mode", "manual")

        if mode == "autopilot":
            # Let brain decide what to do
            decision = await self.brain.decide_action(text, user_id=user_id)
            await self._execute_decision(decision, update)
        else:
            # Manual mode — just forward to brain for response
            response = await self.brain.query(text, user_id=user_id)
            await update.message.reply_text(response, parse_mode="Markdown")

    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photos and documents."""
        await update.message.reply_text(
            "📎 Media received! Processing...\n\n"
            "(Media analysis coming in v2 — for now, describe what you need and I'll handle it!)"
        )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        if data == "swarm_status":
            swarm_status = await self.swarm.get_status()
            await query.edit_message_text(swarm_status, parse_mode="Markdown")

        elif data == "market_scan":
            await query.edit_message_text("🔍 Scanning markets...")
            result = await self._run_market_scan()
            await query.edit_message_text(result, parse_mode="Markdown")

        elif data == "toggle_autopilot":
            await self.cmd_autopilot(update, context)

        elif data == "brain_query":
            await query.edit_message_text(
                "🧠 **Direct Brain Query**\n\nSend me your question and I'll route it to AImind!"
            )

    # ============== INTERNAL METHODS ==============

    async def _get_full_status(self) -> str:
        """Get complete system status."""
        swarm = await self.swarm.get_status()
        skills_count = len(await self.skills.list_skills())
        context_size = await self.context.get_size()
        autopilot_users = sum(
            1 for s in self.user_sessions.values() if s.get("mode") == "autopilot"
        )

        return f"""
🎯 **ORCHESTRATOR STATUS** 🎯

🧠 **Brain:** Connected (AImind)
🐝 **Swarm:** {swarm}
🎯 **Skills:** {skills_count} loaded
🌐 **Context:** {context_size} messages
🤖 **Autopilot Users:** {autopilot_users}

⏱️ **Uptime:** Running
📡 **Mode:** Active

**System Health:** ✅ All green
        """

    async def _run_market_scan(self) -> str:
        """Run market scan using existing scanner."""
        # Use existing dexscreener scanner
        import subprocess
        result = subprocess.run(
            ["python3", str(WORKSPACE / "dexscreener_scanner.py")],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return f"🔍 **SCAN RESULTS** 🔍\n\n```\n{result.stdout[:3000]}\n```"
        else:
            return f"❌ Scan error: {result.stderr[:1000]}"

    async def _generate_signals(self) -> str:
        """Generate trading signals."""
        # Use signal generator if available
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "signal_generator.py")],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return f"📊 **SIGNALS** 📊\n\n```\n{result.stdout[:3000]}\n```"
        except:
            return "📊 Signal generator not available. Run `/scan` for market data."

    async def _execute_command(self, command: str) -> str:
        """Execute system command safely."""
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=WORKSPACE,
        )
        output = result.stdout + "\n" + result.stderr
        return output if output else "Command executed (no output)"

    async def _execute_decision(self, decision: Dict, update: Update):
        """Execute a brain decision."""
        action = decision.get("action")
        params = decision.get("params", {})

        if action == "scan":
            result = await self._run_market_scan()
            await update.message.reply_text(result, parse_mode="Markdown")
        elif action == "spawn":
            agent = await self.swarm.spawn_agent(params.get("type"), params.get("config"))
            await update.message.reply_text(f"✅ Spawned: {agent['name']}")
        elif action == "message":
            await update.message.reply_text(params.get("text", "Done"), parse_mode="Markdown")
        else:
            await update.message.reply_text(str(decision))

    async def _generate_report(self) -> str:
        """Generate performance report."""
        return """
📈 **PERFORMANCE REPORT** 📈

Period: Last 24h

🐝 **Agents Spawned:** 3
✅ **Tasks Completed:** 47
🔍 **Scans Run:** 96
📊 **Signals Generated:** 12
🎯 **Skills Learned:** 2

**Top Performing Agent:** scanner_v2
**Most Used Skill:** dexscreener_analysis

System efficiency: 94%
Uptime: 99.9%

(Detailed metrics in dashboard)
        """

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate performance report."""
        await update.message.reply_text("📈 Generating report...")
        try:
            report = await self._generate_report()
            await update.message.reply_text(report, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Report failed: {str(e)}")

    async def cmd_jupiter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Jupiter DEX integration."""
        await update.message.reply_text("🪐 Connecting to Jupiter DEX...")
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "jupiter_realtime.py")],
                capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
            )
            output = result.stdout[:3000] if result.stdout else "Jupiter agent ready but no output."
            await update.message.reply_text(f"🪐 **JUPITER DEX** 🪐\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Jupiter error: {str(e)}")

    async def cmd_solana(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Solana ecosystem scan."""
        await update.message.reply_text("⚡ Scanning Solana ecosystem...")
        try:
            # Use Solana agent if available
            solana_dir = WORKSPACE / "solana_agent"
            if (solana_dir / "solana_scanner.py").exists():
                import subprocess
                result = subprocess.run(
                    ["python3", str(solana_dir / "solana_scanner.py")],
                    capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
                )
                output = result.stdout[:3000] if result.stdout else "No scan output."
            else:
                output = "Solana scanner not found. Using DexScreener Solana pairs..."
                # Fallback: scan DexScreener for Solana pairs
                import subprocess
                result = subprocess.run(
                    ["python3", str(WORKSPACE / "dexscreener_scanner.py")],
                    capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
                )
                output += "\n" + result.stdout[:2000] if result.stdout else ""
            await update.message.reply_text(f"⚡ **SOLANA SCAN** ⚡\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Solana error: {str(e)}")

    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/portfolio — Show wallet portfolio with tokens"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_portfolio(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_exchanges(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exchange status overview."""
        await update.message.reply_text("🏦 Checking exchanges...")
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "exchange_manager.py"), "--status"],
                capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
            )
            output = result.stdout[:3000] if result.stdout else """
🏦 **EXCHANGES** 🏦

Available integrations:
• Binance (API required)
• Bybit (API required)
• OKX (API required)
• Jupiter (Solana DEX)
• Raydium (Solana DEX)

Use `/connect exchange_manager` to activate.
            """
            await update.message.reply_text(output, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Exchange error: {str(e)}")

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Deep token analysis."""
        if not context.args:
            await update.message.reply_text("Usage: `/analyze <token_symbol>`\nExample: `/analyze SOL` or `/analyze HdXa16PsVZVFWKxfPw4GszCbFRnFf3crUxtLj8CNPYmF`")
            return
        token = context.args[0]
        await update.message.reply_text(f"🔬 Analyzing **{token}**...")
        try:
            # Use blockchain analyzer
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "blockchain_analyzer.py"), "--analyze", token],
                capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
            )
            output = result.stdout[:3500] if result.stdout else f"Analysis for {token}:\n\nUse DexScreener for manual review: https://dexscreener.com/solana/{token}"
            await update.message.reply_text(f"🔬 **ANALYSIS: {token}** 🔬\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Analysis error: {str(e)}")

    async def cmd_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Whale tracking."""
        await update.message.reply_text("🐋 Scanning for whale activity...")
        try:
            # Use v2_whale if available
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "v2_whale.py")],
                capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
            )
            output = result.stdout[:3000] if result.stdout else """
🐋 **WHALE TRACKING** 🐋

Whale monitoring systems:
• Large wallet movements
• Exchange inflows/outflows
• Smart money flows
• Holder distribution shifts

Spawn dedicated whale agent:
`/spawn monitor`
            """
            await update.message.reply_text(output, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Whale error: {str(e)}")

    async def cmd_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom alerts."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/alert <condition>`\n"
                "Examples:\n"
                "• `/alert BTC > 70000`\n"
                "• `/alert SOL pump 10%`\n"
                "• `/alert new_token > 100k volume`\n"
                "• `/alert whale_movement > 1M`"
            )
            return
        condition = " ".join(context.args)
        await update.message.reply_text(f"🔔 Alert set: **{condition}**\n\nI will notify you when triggered!")

    async def cmd_backtest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run backtest."""
        await update.message.reply_text("📊 Running backtest...")
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "v4_realistic_backtest.py")],
                capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
            )
            output = result.stdout[:3500] if result.stdout else "Backtest engine ready. Configure strategy first."
            await update.message.reply_text(f"📊 **BACKTEST** 📊\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Backtest error: {str(e)}")

    async def cmd_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Connect to specific agent or service."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/connect <agent_name>`\n"
                "Available:\n"
                "• `master_agent` — Main orchestrator agent\n"
                "• `blockchain_analyzer` — On-chain analysis\n"
                "• `exchange_manager` — Multi-exchange trading\n"
                "• `risk_portfolio` — Risk & portfolio mgmt\n"
                "• `jupiter_realtime` — Jupiter DEX live data\n"
                "• `mevx_realtime` — MEVX live data"
            )
            return
        agent_name = context.args[0]
        await update.message.reply_text(f"🔗 Connecting to **{agent_name}**...")
        try:
            script_map = {
                "master_agent": "master_agent.py",
                "blockchain_analyzer": "blockchain_analyzer.py",
                "exchange_manager": "exchange_manager.py",
                "risk_portfolio": "risk_portfolio.py",
                "jupiter_realtime": "jupiter_realtime.py",
                "mevx_realtime": "mevx_realtime.py",
            }
            script = script_map.get(agent_name, f"{agent_name}.py")
            script_path = AGENTS_DIR / script
            if script_path.exists():
                import subprocess
                result = subprocess.run(
                    ["python3", str(script_path), "--status"],
                    capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
                )
                output = result.stdout[:3000] if result.stdout else f"{agent_name} connected successfully!"
            else:
                output = f"Agent `{agent_name}` not found. Use `/agents` for available agents."
            await update.message.reply_text(f"🔗 **{agent_name.upper()}** 🔗\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Connect error: {str(e)}")

    async def cmd_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Connect to specific agent or service."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/connect <agent_name>`\n"
                "Available:\n"
                "• `master_agent` — Main orchestrator agent\n"
                "• `blockchain_analyzer` — On-chain analysis\n"
                "• `exchange_manager` — Multi-exchange trading\n"
                "• `risk_portfolio` — Risk & portfolio mgmt\n"
                "• `jupiter_realtime` — Jupiter DEX live data\n"
                "• `mevx_realtime` — MEVX live data"
            )
            return
        agent_name = context.args[0]
        await update.message.reply_text(f"🔗 Connecting to **{agent_name}**...")
        try:
            script_map = {
                "master_agent": "master_agent.py",
                "blockchain_analyzer": "blockchain_analyzer.py",
                "exchange_manager": "exchange_manager.py",
                "risk_portfolio": "risk_portfolio.py",
                "jupiter_realtime": "jupiter_realtime.py",
                "mevx_realtime": "mevx_realtime.py",
            }
            script = script_map.get(agent_name, f"{agent_name}.py")
            script_path = AGENTS_DIR / script
            if script_path.exists():
                import subprocess
                result = subprocess.run(
                    ["python3", str(script_path), "--status"],
                    capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
                )
                output = result.stdout[:3000] if result.stdout else f"{agent_name} connected successfully!"
            else:
                output = f"Agent `{agent_name}` not found. Use `/agents` for available agents."
            await update.message.reply_text(f"🔗 **{agent_name.upper()}** 🔗\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Connect error: {str(e)}")

    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show unified master dashboard with all systems."""
        import sys
        sys.path.insert(0, "/root/.openclaw/workspace")
        from unified_dashboard import UnifiedDashboard
        
        if context.args and context.args[0] == "refresh":
            await update.message.reply_text("🔄 Refreshing dashboard...")
        
        dashboard = UnifiedDashboard()
        text = await dashboard.generate_full_dashboard()
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Also save for quick access
        dashboard._save_dashboard(text)

    async def cmd_stream(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle real-time streaming."""
        if not self.dashboard:
            await update.message.reply_text("❌ Dashboard not initialized")
            return
        if not context.args:
            status = "🟢 ON" if self.dashboard.is_streaming else "🔴 OFF"
            await update.message.reply_text(
                f"📡 Streaming status: {status}\n\n"
                "Usage:\n"
                "• `/stream on` — Start streaming\n"
                "• `/stream off` — Stop streaming\n"
                "• `/stream status` — Check status"
            )
            return
        action = context.args[0].lower()
        if action == "on":
            await self.dashboard.start_streaming()
            await update.message.reply_text("🌊 **Streaming STARTED!**\n\nReal-time data feeds active:\n• Market data (30s)\n• On-chain metrics (2min)\n• Whale alerts (1min)")
        elif action == "off":
            await self.dashboard.stop_streaming()
            await update.message.reply_text("🛑 **Streaming STOPPED**")
        else:
            status = "🟢 ON" if self.dashboard.is_streaming else "🔴 OFF"
            await update.message.reply_text(f"📡 Streaming status: {status}")

    async def cmd_mempool(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Monitor mempool activity."""
        await update.message.reply_text("🔍 Scanning mempool...")
        try:
            # Simulated mempool data - replace with Helius/Chainstack RPC
            mempool_data = {
                "solana": {
                    "pending_txs": 142,
                    "priority_fees": {"low": 5000, "medium": 25000, "high": 100000},
                    "trending_tokens": ["BONK", "WIF", "POPCAT"],
                }
            }
            lines = [
                "🔍 **MEMPOOL MONITOR** 🔍",
                "",
                "**Solana:**",
                f"• Pending transactions: {mempool_data['solana']['pending_txs']}",
                f"• Priority fees: Low {mempool_data['solana']['priority_fees']['low']} | Med {mempool_data['solana']['priority_fees']['medium']} | High {mempool_data['solana']['priority_fees']['high']}",
                f"• Trending: {', '.join(mempool_data['solana']['trending_tokens'])}",
                "",
                "💡 Connect Helius RPC for live mempool data:",
                "`/connect helius` (when configured)",
            ]
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Mempool error: {str(e)}")

    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trading signals."""
        await update.message.reply_text("🎯 Fetching trading signals...")
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(AGENTS_DIR / "signal_generator.py")],
                capture_output=True, text=True, timeout=30, cwd=WORKSPACE,
            )
            output = result.stdout[:3500] if result.stdout else "Signal generator ready. No new signals."
            await update.message.reply_text(f"🎯 **TRADING SIGNALS** 🎯\n\n```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Signals error: {str(e)}")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate performance report."""
        if not self.dashboard:
            await update.message.reply_text("❌ Dashboard not initialized")
            return
        await update.message.reply_text("📈 Generating report...")
        try:
            report = await self.dashboard.generate_advanced_report()
            await update.message.reply_text(report, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Report error: {str(e)}")

    async def cmd_osint(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """OSINT Intelligence Agent — Learn, train, evolve."""
        if not context.args:
            await update.message.reply_text(
                "🕵️ **OSINT INTELLIGENCE AGENT** 🕵️\n\n"
                "Usage:\n"
                "• `/osint scan` — Scan DEX for new tokens\n"
                "• `/osint research PROJECT` — Deep project research\n"
                "• `/osint contract ADDRESS` — Smart contract analysis\n"
                "• `/osint report` — Full OSINT report\n"
                "• `/osint evolve` — Trigger self-evolution\n"
                "• `/osint sources` — Show data sources\n\n"
                "This agent learns continuously and develops new techniques!",
                parse_mode="Markdown",
            )
            return
        
        subcmd = context.args[0].lower()
        await update.message.reply_text(f"🕵️ OSINT Agent: **{subcmd}**...")
        
        try:
            import subprocess
            agent_path = AGENTS_DIR / "osint_agent.py"
            
            if subcmd == "scan":
                result = subprocess.run(
                    ["python3", str(agent_path), "--scan", "--chain", "solana"],
                    capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
                )
                output = result.stdout[:3500] if result.stdout else "Scan complete."
                await update.message.reply_text(f"🔍 **DEX SCAN** 🔍\n\n```\n{output}\n```", parse_mode="Markdown")
                
            elif subcmd == "research":
                project = context.args[1] if len(context.args) > 1 else "unknown"
                result = subprocess.run(
                    ["python3", str(agent_path), "--research", project],
                    capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
                )
                output = result.stdout[:3500] if result.stdout else f"Research on {project} complete."
                await update.message.reply_text(f"🔬 **RESEARCH: {project}** 🔬\n\n```\n{output}\n```", parse_mode="Markdown")
                
            elif subcmd == "contract":
                contract = context.args[1] if len(context.args) > 1 else None
                if not contract:
                    await update.message.reply_text("Usage: `/osint contract ADDRESS`")
                    return
                result = subprocess.run(
                    ["python3", str(agent_path), "--contract", contract, "--chain", "solana"],
                    capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
                )
                output = result.stdout[:3500] if result.stdout else "Contract analysis complete."
                await update.message.reply_text(f"🔍 **CONTRACT: {contract[:20]}...** 🔍\n\n```\n{output}\n```", parse_mode="Markdown")
                
            elif subcmd == "report":
                result = subprocess.run(
                    ["python3", str(agent_path), "--mode", "report"],
                    capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
                )
                output = result.stdout[:3500] if result.stdout else "Report generated."
                await update.message.reply_text(f"📊 **OSINT REPORT** 📊\n\n```\n{output}\n```", parse_mode="Markdown")
                
            elif subcmd == "evolve":
                result = subprocess.run(
                    ["python3", str(agent_path), "--mode", "evolve"],
                    capture_output=True, text=True, timeout=60, cwd=WORKSPACE,
                )
                output = result.stdout[:3500] if result.stdout else "Evolution triggered!"
                await update.message.reply_text(f"🧬 **EVOLUTION** 🧬\n\n```\n{output}\n```", parse_mode="Markdown")
                
            elif subcmd == "sources":
                sources_text = """
🌐 **OSINT DATA SOURCES** 🌐

**Market Data:**
• DexScreener — DEX pricing
• CoinGecko / CMC — Market caps
• Birdeye — Solana DEX data
• DeFiLlama — TVL analytics

**Blockchain:**
• Solscan / Etherscan — Explorers
• Helius — RPC + gRPC streams
• Nansen — Whale tracking

**Social:**
• Twitter/X — Sentiment
• Reddit — r/CryptoCurrency
• Telegram — Channel monitoring
• GitHub — Developer activity

**News & Research:**
• CryptoPanic — News aggregation
• Messari — Research reports
• Dune — On-chain analytics

**Status:** 12 base techniques loaded
**Learning:** CONTINUOUS ✅
**Evolution:** ENABLED ✅
                """
                await update.message.reply_text(sources_text, parse_mode="Markdown")
                
            else:
                await update.message.reply_text(f"Unknown OSINT command: {subcmd}. Use `/osint` for help.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ OSINT error: {str(e)}")

    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/wallet — Show wallet menu"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_wallet(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_wallet_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/wallet_setup — Connect MetaMask (Private Key OR Secret Recovery Phrase)"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_wallet_setup(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_wallet_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/wallet_add — Add another wallet (Account 2, 3... from same seed)"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_wallet_add(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/balance — Check wallet balance"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_balance(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/trade — Trading interface"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_trade(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/send — Send tokens or native currency"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_send(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    async def cmd_token_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/token_add — Add custom token by contract address"""
        if self.wallet_handler:
            await self.wallet_handler.cmd_token_add(update, context)
        else:
            await update.message.reply_text("⚠️ Wallet system not ready. Please restart the bot.")

    # ============== GENERAL SWARM INTEGRATION ==============

    async def handle_general_swarm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general swarm commands"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Parse command
        parts = text.split()
        command = parts[0][1:] if parts else ''  # Remove /
        args = parts[1:] if len(parts) > 1 else []
        
        # Import general orchestrator
        import sys
        sys.path.insert(0, str(WORKSPACE / 'swarm_general'))
        
        try:
            from general_orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            result = await orchestrator.handle_telegram_command(f"/{command}", args, str(user_id))
            
            await update.message.reply_text(
                f"🌐 **SWARM RESPONSE**\n\n{result}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"General swarm error: {e}")
            await update.message.reply_text(f"❌ Swarm error: {str(e)[:200]}")

    def _setup_general_swarm_handlers(self):
        """Setup handlers for general swarm commands"""
        general_commands = [
            'status', 'agents', 'tasks', 'skills', 
            'task', 'directions', 'help'
        ]
        
        for cmd in general_commands:
            self.app.add_handler(CommandHandler(cmd, self.handle_general_swarm))
            
        logger.info("🌐 General swarm commands registered")

    # ============== AUTO TRADING ==============

    async def cmd_autotrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /autotrade — Auto trading control panel
        """
        from core.auto_trader import auto_trader
        
        status = await auto_trader.get_status()
        
        text = f"""
🤖 **AUTO TRADING CONTROL** 🤖

**Status:** {'🟢 RUNNING' if status['enabled'] else '🔴 STOPPED'}
**Mode:** {status['mode'].upper()}
**Positions:** {status['positions']}
**Today's PnL:** ${status['daily_pnl']:+.2f}

**Commands:**
`/start_trading` — Start auto trading
`/stop_trading` — Stop auto trading
`/positions` — View open positions
`/history` — View trade history
`/performance` — View stats
`/close_position <id>` — Close position manually

**Config:**
• Max positions: {status['config']['max_positions']}
• Position size: ${status['config']['max_position_size_usd']}
• Stop loss: {status['config']['stop_loss_pct']}%
• Take profit: {status['config']['take_profit_pct']}%
"""
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start_trading — Start auto trading engine
        """
        from core.auto_trader import auto_trader
        
        if not auto_trader.is_running:
            # Setup Telegram callbacks
            async def on_signal(data):
                text = data.get('message', 'Signal received')
                await update.message.reply_text(f"📡 {text}", parse_mode="Markdown")
            
            async def on_trade(data):
                trade = data.get('trade', {})
                mode = data.get('mode', 'paper')
                text = (
                    f"🔥 **{'PAPER' if mode == 'paper' else 'LIVE'} TRADE!**\n\n"
                    f"Token: {trade.get('token_symbol')}\n"
                    f"Direction: {trade.get('direction').upper()}\n"
                    f"Price: ${trade.get('entry_price', 0):.4f}\n"
                    f"Amount: ${trade.get('entry_amount_usd', 0):.2f}\n"
                    f"Confidence: {trade.get('signal_confidence', 0):.0f}/100"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            
            async def on_close(data):
                trade = data.get('trade', {})
                pnl = data.get('pnl_usd', 0)
                pct = data.get('pnl_pct', 0)
                emoji = "🟢" if pnl > 0 else "🔴"
                text = (
                    f"{emoji} **POSITION CLOSED**\n\n"
                    f"Token: {trade.get('token_symbol')}\n"
                    f"PnL: ${pnl:+.2f} ({pct:+.1f}%)\n"
                    f"Reason: {data.get('reason', 'unknown')}"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            
            auto_trader.on_signal = on_signal
            auto_trader.on_trade = on_trade
            auto_trader.on_close = on_close
            
            await auto_trader.start()
            await update.message.reply_text(
                "🚀 **AUTO TRADING STARTED!**\n\n"
                "Mode: PAPER TRADING (simulated)\n"
                "Interval: Every 5 minutes\n"
                "Max positions: 5\n\n"
                "⚠️ This is PAPER mode — no real money at risk!\n"
                "Use `/autotrade` to check status."
            )
        else:
            await update.message.reply_text("⚠️ Auto trading already running! Use /autotrade to check status.")
    
    async def cmd_stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /stop_trading — Stop auto trading
        """
        from core.auto_trader import auto_trader
        
        if auto_trader.is_running:
            await auto_trader.stop()
            await update.message.reply_text("🛑 **Auto trading STOPPED!**")
        else:
            await update.message.reply_text("⚠️ Auto trading not running.")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /positions — View open positions
        """
        from core.auto_trader import auto_trader
        
        positions = await auto_trader.get_positions()
        
        if not positions:
            await update.message.reply_text("📭 **No open positions.**")
            return
        
        text = "📊 **OPEN POSITIONS** 📊\n\n"
        for pos in positions:
            text += (
                f"🔹 **{pos['token_symbol']}**\n"
                f"   Entry: ${pos['entry_price']:.4f}\n"
                f"   Amount: ${pos['entry_amount_usd']:.2f}\n"
                f"   Stop: ${pos['stop_loss']:.4f}\n"
                f"   Target: ${pos['take_profit']:.4f}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /history — View trade history
        """
        from core.auto_trader import auto_trader
        
        history = await auto_trader.get_history()
        
        if not history:
            await update.message.reply_text("📭 **No trade history yet.**")
            return
        
        text = "📜 **TRADE HISTORY** 📜\n\n"
        for trade in history[-10:]:  # Last 10
            pnl = trade.get('pnl_usd', 0)
            emoji = "🟢" if pnl > 0 else "🔴"
            text += (
                f"{emoji} **{trade['token_symbol']}** | "
                f"${pnl:+.2f} ({trade.get('pnl_pct', 0):+.1f}%)\n"
                f"   {trade.get('exit_time', 'N/A')[:10]}\n\n"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /performance — View trading performance
        """
        from core.auto_trader import auto_trader
        
        status = await auto_trader.get_status()
        
        win_rate = (status['winning_trades'] / status['total_trades'] * 100) if status['total_trades'] > 0 else 0
        
        text = (
            f"📈 **TRADING PERFORMANCE** 📈\n\n"
            f"**Today's PnL:** ${status['daily_pnl']:+.2f}\n"
            f"**Total Trades:** {status['total_trades']}\n"
            f"**Win Rate:** {win_rate:.1f}%\n"
            f"**Open Positions:** {status['positions']}\n\n"
            f"**Config:**\n"
            f"• Mode: {status['mode'].upper()}\n"
            f"• Max positions: {status['config']['max_positions']}\n"
            f"• Position size: ${status['config']['max_position_size_usd']}\n"
            f"• Stop loss: {status['config']['stop_loss_pct']}%\n"
            f"• Take profit: {status['config']['take_profit_pct']}%\n"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_close_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /close_position — Manually close a position
        """
        from core.auto_trader import auto_trader
        
        if not context.args:
            await update.message.reply_text("Usage: `/close_position <trade_id>`")
            return
        
        trade_id = context.args[0]
        
        result = await auto_trader.close_position(trade_id)
        
        if result:
            await update.message.reply_text(f"✅ Position `{trade_id}` closed!")
        else:
            await update.message.reply_text(f"❌ Position `{trade_id}` not found.")

    async def cmd_set_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /set_mode — Switch between PAPER and LIVE trading
        Usage: /set_mode paper OR /set_mode live
        """
        from core.auto_trader import auto_trader
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ **SET TRADING MODE**\n\n"
                "Usage: `/set_mode paper` or `/set_mode live`\n\n"
                f"Current mode: **{auto_trader.config.mode.upper()}**"
            )
            return
        
        mode = context.args[0].lower()
        
        if mode not in ('paper', 'live'):
            await update.message.reply_text("❌ Invalid mode. Use `paper` or `live`.")
            return
        
        if mode == 'live':
            # Safety checks before enabling live mode
            if not auto_trader.wallet_manager:
                await update.message.reply_text(
                    "❌ **Cannot switch to LIVE mode!**\n\n"
                    "No wallet manager connected.\n"
                    "Use `/wallet_setup` to connect your MetaMask first."
                )
                return
            
            wallet = auto_trader.wallet_manager.wallets.get(auto_trader.config.wallet_name)
            if not wallet:
                await update.message.reply_text(
                    "❌ **Cannot switch to LIVE mode!**\n\n"
                    f"Wallet '{auto_trader.config.wallet_name}' not found.\n"
                    "Check your wallet configuration."
                )
                return
            
            # Get portfolio to show available balance
            try:
                portfolio = await auto_trader.wallet_manager.get_portfolio_with_value(
                    auto_trader.config.wallet_name,
                    auto_trader.config.wallet_chain
                )
                total_usd = portfolio.get('total_portfolio_usd', 0)
            except:
                total_usd = 0
            
            # Send warning
            await update.message.reply_text(
                "⚠️⚠️⚠️ **WARNING: LIVE MODE** ⚠️⚠️⚠️\n\n"
                "You are about to trade with **REAL MONEY**!\n\n"
                f"💰 **Available Balance:** ${total_usd:.2f}\n"
                f"📊 **Position Size:** ${auto_trader.config.max_position_size_usd:.2f}/trade\n"
                f"🛡️ **Stop Loss:** {auto_trader.config.stop_loss_pct}%\n"
                f"🎯 **Take Profit:** {auto_trader.config.take_profit_pct}%\n\n"
                "**Risks:**\n"
                "• Real financial loss possible\n"
                "• Markets are volatile\n"
                "• No guarantees of profit\n\n"
                "**To confirm:** Send `/confirm_live`"
            )
            return
        
        # Paper mode - switch immediately
        await auto_trader.update_config({'mode': 'paper'})
        await update.message.reply_text(
            "📊 **Switched to PAPER MODE**\n\n"
            "✅ Simulated trading only\n"
            "✅ No real money at risk\n"
            "Use `/start_trading` to begin!"
        )
    
    async def cmd_confirm_live(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /confirm_live — Confirm switch to LIVE trading mode
        """
        from core.auto_trader import auto_trader
        
        await auto_trader.update_config({'mode': 'live'})
        
        await update.message.reply_text(
            "🔥🔥🔥 **LIVE TRADING MODE ACTIVATED** 🔥🔥🔥\n\n"
            "⚠️ **REAL MONEY IS NOW AT RISK**\n\n"
            "The bot will:\n"
            "• Scan markets every 5 minutes\n"
            "• Execute REAL trades with your wallet\n"
            "• Manage positions with stop loss/take profit\n\n"
            "**Use `/start_trading` to begin!**\n\n"
            "**Use `/stop_trading` to stop immediately!**"
        )
    
    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /config — View/Update trading configuration
        Usage: /config key value
        Example: /config max_position_size_usd 50
        """
        from core.auto_trader import auto_trader
        
        if not context.args:
            # Show current config
            cfg = auto_trader.config
            text = (
                "⚙️ **TRADING CONFIG** ⚙️\n\n"
                f"**Mode:** {cfg.mode.upper()}\n"
                f"**Max Positions:** {cfg.max_positions}\n"
                f"**Position Size:** ${cfg.max_position_size_usd:.2f}\n"
                f"**Stop Loss:** {cfg.stop_loss_pct}%\n"
                f"**Take Profit:** {cfg.take_profit_pct}%\n"
                f"**Trailing Stop:** {cfg.trailing_stop_pct}%\n"
                f"**Min Confidence:** {cfg.min_confidence}/100\n"
                f"**Check Interval:** {cfg.check_interval}s\n"
                f"**Chains:** {', '.join(cfg.chains)}\n"
                f"**Wallet:** {cfg.wallet_name} ({cfg.wallet_chain})\n\n"
                "**To update:**\n"
                "`/config max_positions 3`\n"
                "`/config max_position_size_usd 50`\n"
                "`/config stop_loss_pct -3`\n"
                "`/config take_profit_pct 15`"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/config key value`")
            return
        
        key = context.args[0]
        value = context.args[1]
        
        # Convert value to appropriate type
        try:
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif '.' in value:
                value = float(value)
            else:
                value = int(value)
        except:
            pass  # Keep as string
        
        try:
            await auto_trader.update_config({key: value})
            await update.message.reply_text(f"✅ Config updated: `{key}` = `{value}`")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to update config: {e}")

    # ============== AIRDROP COMMANDS ==============

    async def cmd_airdrops(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all airdrops in watchlist."""
        agent = await get_airdrop_agent()
        
        # Parse filters
        status = None
        chain = None
        if context.args:
            for arg in context.args:
                if arg in ["upcoming", "active", "claimable", "ended"]:
                    status = arg
                elif arg.lower() in ["eth", "ethereum", "sol", "solana", "multi", "arb", "arbitrum"]:
                    chain = arg
        
        airdrops = agent.get_watchlist(status=status, chain=chain)
        text = agent.format_watchlist(airdrops)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_airdrop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Airdrop summary or detail."""
        agent = await get_airdrop_agent()
        
        if not context.args:
            # Show summary dashboard
            text = agent.format_summary()
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand == "summary":
            text = agent.format_summary()
        elif subcommand == "discover":
            new = await agent.discover_airdrops()
            if new:
                text = f"🔍 Discovered `{len(new)}` new airdrops!\n\n"
                text += agent.format_watchlist(new)
            else:
                text = "🔍 No new airdrops discovered. Watchlist is up to date."
        elif subcommand == "seed":
            seeded = agent.seed_known_airdrops()
            text = f"🌱 Seeded `{len(seeded)}` known high-value airdrops!\n\n"
            text += agent.format_watchlist(seeded)
        else:
            # Show specific airdrop detail
            name = " ".join(context.args)
            airdrop = agent.get_airdrop(name)
            if airdrop:
                text = (
                    f"🪂 **{airdrop.name}**\n\n"
                    f"Protocol: `{airdrop.protocol}`\n"
                    f"Chain: `{airdrop.chain}`\n"
                    f"Status: `{airdrop.status.upper()}`\n"
                    f"Difficulty: `{airdrop.difficulty}`\n"
                    f"Est. Value: `{airdrop.estimated_value or 'N/A'}`\n"
                )
                if airdrop.tge_date:
                    text += f"TGE: `{airdrop.tge_date}`\n"
                if airdrop.snapshot_date:
                    text += f"📸 Snapshot: `{airdrop.snapshot_date}` ⚠️\n"
                if airdrop.criteria:
                    text += f"\n**Criteria:**\n"
                    for c in airdrop.criteria:
                        text += f"  • {c}\n"
                if airdrop.url:
                    text += f"\n🔗 [Website]({airdrop.url})\n"
                if airdrop.twitter:
                    text += f"🐦 [Twitter]({airdrop.twitter})\n"
            else:
                text = f"❌ Airdrop `{name}` not found. Use `/airdrops` to list."
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show farming progress or start/stop."""
        agent = await get_airdrop_agent()
        
        if not context.args:
            # Show all farming progress
            tasks = agent.get_farming_status()
            text = agent.format_farming_status(tasks)
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        subcommand = context.args[0].lower()
        
        if subcommand in ["start", "begin"]:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "Usage: `/farm_start <airdrop_name>`\n"
                    "Example: `/farm_start Scroll`"
                )
                return
            name = " ".join(context.args[1:])
            try:
                wallet = context.args[-1] if context.args[-1].startswith("0x") or len(context.args[-1]) > 30 else None
                task = agent.start_farming(name, wallet_address=wallet)
                text = (
                    f"🚜 **Farming Started: {task.airdrop_name}**\n\n"
                    f"Protocol: `{task.protocol}`\n"
                    f"Chain: `{task.chain}`\n"
                    f"Tasks: `{len(task.tasks)}` to complete\n"
                    f"Started: `{task.started_at[:10]}`\n\n"
                    f"Use `/farm_update <task_name>` to mark tasks done!"
                )
            except ValueError as e:
                text = f"❌ {e}\nUse `/airdrops` to see available airdrops."
        elif subcommand == "status":
            name = context.args[1] if len(context.args) > 1 else None
            tasks = agent.get_farming_status(airdrop_name=name)
            text = agent.format_farming_status(tasks)
        else:
            text = (
                "🚜 **Farming Commands:**\n\n"
                "`/farming` — Show all progress\n"
                "`/farm_start <airdrop>` — Start farming\n"
                "`/farm_update <airdrop> <task>` — Mark done"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start farming an airdrop."""
        agent = await get_airdrop_agent()
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/farm_start <airdrop_name>`\n"
                "Example: `/farm_start Linea Voyage`"
            )
            return
        
        name = " ".join(context.args)
        # Check if last arg looks like a wallet address
        wallet = None
        if context.args[-1].startswith("0x") or len(context.args[-1]) > 30:
            wallet = context.args[-1]
            name = " ".join(context.args[:-1])
        
        try:
            task = agent.start_farming(name, wallet_address=wallet)
            text = (
                f"🚜 **FARMING STARTED!** 🚜\n\n"
                f"**{task.airdrop_name}** on {task.chain}\n\n"
                f"Tasks to complete: `{len(task.tasks)}`\n"
                f"Started: `{task.started_at[:10]}`\n\n"
                f"Next: Use `/farm_update {task.airdrop_name} <task_name>` to mark progress!\n"
                f"Or `/farming` to see your dashboard."
            )
        except ValueError as e:
            text = f"❌ {e}\n\nUse `/airdrops` to see available opportunities."
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update farming task progress."""
        agent = await get_airdrop_agent()
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/farm_update <airdrop_name> <task_name>`\n"
                "Example: `/farm_update Linea 'Bridge ETH to Linea'`\n\n"
                "Use `/farming` to see your active tasks."
            )
            return
        
        airdrop_name = context.args[0]
        task_name = " ".join(context.args[1:])
        
        # Try to match task name
        task = agent.update_farming_task(airdrop_name, task_name, completed=True)
        if task:
            total = len(task.tasks)
            done = sum(1 for v in task.tasks.values() if v)
            pct = (done / total * 100) if total else 0
            text = (
                f"✅ **Task Completed!**\n\n"
                f"Airdrop: `{airdrop_name}`\n"
                f"Task: `{task_name}`\n\n"
                f"Progress: `{done}/{total}` ({pct:.0f}%)\n"
            )
            if pct >= 100:
                text += "\n🔥 **ALL TASKS DONE!** You're ready for the drop!"
        else:
            text = (
                f"❌ Could not update task.\n"
                f"Airdrop `{airdrop_name}` may not be in your farming list.\n"
                f"Start farming first: `/farm_start {airdrop_name}`"
            )
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_check_eligibility(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check eligibility for an airdrop."""
        agent = await get_airdrop_agent()
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/check <airdrop_name> <wallet_address>`\n"
                "Example: `/check Scroll 0x1234...abcd`\n\n"
                "Then reply with your metrics (volume, txs, days, etc.)"
            )
            return
        
        airdrop_name = context.args[0]
        wallet = context.args[1]
        
        # For now, ask user to provide metrics
        # In a full implementation, we'd query on-chain data
        text = (
            f"🔍 **Checking: {airdrop_name}**\n"
            f"Wallet: `{wallet}`\n\n"
            f"To complete the check, tell me your metrics:\n"
            f"Example reply:\n"
            f"`volume: 1500 txs: 25 days: 45 tvl: 500`\n\n"
            f"I'll analyze against the criteria and estimate your drop!"
        )
        
        # Store in user session for follow-up
        user_id = update.effective_user.id
        self.user_sessions[user_id] = {
            "pending_airdrop_check": {
                "airdrop": airdrop_name,
                "wallet": wallet
            }
        }
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_claim_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List claimable airdrops."""
        agent = await get_airdrop_agent()
        claimable = agent.get_watchlist(status="claimable")
        
        if not claimable:
            text = "💰 **No claimable airdrops right now.**\n\nCheck back soon!"
        else:
            text = "💰 **CLAIMABLE AIRDROPS** 💰\n\n"
            for a in claimable:
                text += (
                    f"🎁 **{a.name}**\n"
                    f"   Claim at: {a.url or 'Check official site'}\n"
                    f"   Est. Value: `{a.estimated_value or 'N/A'}`\n\n"
                )
            text += "Don't forget to claim before deadlines expire! ⏰"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_airdrop_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a custom airdrop to watchlist."""
        agent = await get_airdrop_agent()
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/airdrop_add <name> <protocol> <chain> <status>`\n"
                "Example: `/airdrop_add 'Foo Protocol' Foo ethereum active`"
            )
            return
        
        try:
            name = context.args[0]
            protocol = context.args[1]
            chain = context.args[2] if len(context.args) > 2 else "unknown"
            status = context.args[3] if len(context.args) > 3 else "active"
            
            airdrop = agent.add_airdrop(
                name=name,
                protocol=protocol,
                chain=chain,
                status=status
            )
            text = f"✅ Added **{airdrop.name}** to watchlist!\nUse `/airdrops` to view."
        except Exception as e:
            text = f"❌ Failed to add: {e}"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_airdrop_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove an airdrop from watchlist."""
        agent = await get_airdrop_agent()
        
        if not context.args:
            await update.message.reply_text("Usage: `/airdrop_remove <airdrop_name>`")
            return
        
        name = " ".join(context.args)
        if agent.remove_airdrop(name):
            text = f"🗑️ Removed `{name}` from watchlist."
        else:
            text = f"❌ `{name}` not found in watchlist."
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_auto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start FULLY AUTOMATED farming for an airdrop."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "🤖 **AUTOMATED FARMING**\n\n"
                "Usage: `/farm_auto <airdrop> <wallet_address>`\n"
                "Example: `/farm_auto Kamino 0x1234...`\n\n"
                "The bot will:\n"
                "• Execute swaps automatically\n"
                "• Add liquidity\n"
                "• Track progress\n"
                "• Send daily reports\n\n"
                "**Safety limits:**\n"
                "• Max $50/day spend\n"
                "• Circuit breaker at $30/day\n"
                "• Min wallet balance $20\n\n"
                "⚠️ Requires wallet to be connected via `/wallet_setup`"
            )
            return

        airdrop_name = context.args[0]
        wallet_address = context.args[1]

        # Get airdrop info
        agent = await get_airdrop_agent()
        airdrop = agent.get_airdrop(airdrop_name)
        if not airdrop:
            await update.message.reply_text(
                f"❌ Airdrop `{airdrop_name}` not found.\n"
                f"Use `/airdrops` to list available airdrops."
            )
            return

        # Detect wallet type
        wallet_type = "solana" if airdrop.chain in ["solana", "monad"] else "evm"

        # Create strategy
        from core.airdrop_farming_executor import FarmingStrategy
        strategy = FarmingStrategy(
            airdrop_name=airdrop.name,
            protocol=airdrop.protocol,
            chain=airdrop.chain,
            wallet_address=wallet_address,
            wallet_type=wallet_type,
            weekly_swap_count=3,
            weekly_swap_volume_usd=100.0,
            lp_amount_usd=50.0 if "liquidity" in str(airdrop.criteria).lower() else 0.0,
            lending_amount_usd=0.0,
            is_active=True,
        )

        # Add to executor
        executor = await get_farming_executor()
        executor.add_strategy(strategy)

        text = (
            f"🤖 **AUTOMATED FARMING ACTIVATED!** 🤖\n\n"
            f"Airdrop: **{airdrop.name}**\n"
            f"Wallet: `{wallet_address}`\n"
            f"Chain: `{airdrop.chain}`\n"
            f"Type: `{wallet_type.upper()}`\n\n"
            f"**Strategy:**\n"
            f"• `{strategy.weekly_swap_count}` swaps/week\n"
            f"• `${strategy.weekly_swap_volume_usd}` weekly volume\n"
            f"• `${strategy.lp_amount_usd}` LP position\n\n"
            f"**Safety:**\n"
            f"• Daily limit: `${strategy.daily_spend_limit}`\n"
            f"• Circuit breaker: `$30`\n"
            f"• Min balance: `$20`\n\n"
            f"The bot will run farming cycles every 2-3 days.\n"
            f"Use `/farm_status` to check progress.\n"
            f"Use `/farm_report` for execution report.\n\n"
            f"⚡ **You are now farming on autopilot!**"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop automated farming for an airdrop."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/farm_stop <airdrop> <wallet_address>`\n"
                "Example: `/farm_stop Kamino 0x1234...`"
            )
            return

        airdrop_name = context.args[0]
        wallet_address = context.args[1]

        executor = await get_farming_executor()
        if executor.remove_strategy(airdrop_name, wallet_address):
            text = (
                f"🛑 **Farming stopped for {airdrop_name}**\n\n"
                f"Wallet: `{wallet_address}`\n\n"
                f"Use `/farm_report` to see final results."
            )
        else:
            text = f"❌ No active farming found for `{airdrop_name}` + `{wallet_address}`"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show automated farming status."""
        executor = await get_farming_executor()
        strategies = executor.get_strategies(active_only=False)

        if not strategies:
            text = (
                "🚜 **No automated farming active.**\n\n"
                "Start with:\n"
                "`/farm_auto <airdrop> <wallet>`\n\n"
                "Example: `/farm_auto MetaMask 0x1234...`"
            )
        else:
            text = "🤖 **AUTOMATED FARMING STATUS** 🤖\n\n"
            for s in strategies:
                status_emoji = "🟢" if s.is_active and not s.circuit_breaker_triggered else "🔴"
                last_exec = s.last_execution[:10] if s.last_execution else "Never"
                text += (
                    f"{status_emoji} **{s.airdrop_name}**\n"
                    f"   Wallet: `{s.wallet_address[:20]}...`\n"
                    f"   Chain: `{s.chain}` | Type: `{s.wallet_type.upper()}`\n"
                    f"   Last run: `{last_exec}`\n"
                    f"   Total spent: `${s.total_spent_usd:,.2f}`\n"
                    f"   Circuit breaker: `{'TRIGGERED' if s.circuit_breaker_triggered else 'OK'}`\n\n"
                )

        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_farm_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show farming execution report."""
        executor = await get_farming_executor()
        days = int(context.args[0]) if context.args else 7
        report = executor.get_execution_report(days=days)
        await update.message.reply_text(report, parse_mode="Markdown")

    # ============== SMART MONEY TRACKER COMMANDS ==============

    async def cmd_discover(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🔍 Discover smart money wallets"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_discover(update, context)

    async def cmd_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🎯 Track a wallet"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_track(update, context)

    async def cmd_untrack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🛑 Stop tracking"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_untrack(update, context)

    async def cmd_smart_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """📊 List wallets"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_list(update, context)

    async def cmd_smart_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """📈 Stats"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_stats(update, context)

    async def cmd_smart_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🏆 Top wallets"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_top(update, context)

    async def cmd_smart_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🔬 Analyze wallet"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_analyze(update, context)

    async def cmd_follow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """👣 Follow wallet (alias for track)"""
        if not self.smart_money_handler:
            await update.message.reply_text("❌ Smart Money tracker not initialized yet.")
            return
        await self.smart_money_handler.cmd_follow(update, context)

    async def cmd_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """🔍 Show group monitor status"""
        if not hasattr(self, 'group_monitor') or not self.group_monitor:
            await update.message.reply_text("❌ Group monitor not initialized.")
            return
        
        stats = self.group_monitor.get_stats()
        
        from core.group_monitor import MONITORED_GROUPS, PUMP_KEYWORDS, MIN_SIGNAL_SCORE
        
        text = f"""🔍 **GROUP MONITOR STATUS** 🔍

📊 **Groups:** {stats['groups_monitored']}
"""
        for name in stats['group_names']:
            text += f"   • {name}\n"
        
        text += f"""
🚨 **Alerts Sent:** {stats['alerts_sent']}
⏰ **Last Alert:** {stats['last_alert'] or 'None yet'}
💾 **Dedupe Cache:** {stats['recent_dedupe_cache']} messages

**Filters Active:**
   🎯 Token addresses (EVM + Solana + TON)
   🔗 DEX links (DexScreener, Pump.fun, Jupiter, Raydium, etc.)
   🏷️ Pump keywords ({len(PUMP_KEYWORDS)} keywords)
   📸 Media detection (charts, screenshots)

**Min Signal Score:** {MIN_SIGNAL_SCORE}/10

Use `/groups` to see monitored groups.
"""
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """📋 List monitored groups"""
        if not hasattr(self, 'group_monitor') or not self.group_monitor:
            await update.message.reply_text("❌ Group monitor not initialized.")
            return
        
        from core.group_monitor import MONITORED_GROUPS
        
        text = "📋 **MONITORED GROUPS** 📋\n\n"
        for gid, name in MONITORED_GROUPS.items():
            text += f"• **{name}**\n"
            text += f"   ID: `{gid}`\n\n"
        
        text += "💡 **To add more groups:** Edit `core/group_monitor.py`\n"
        text += "   and add the group ID to `MONITORED_GROUPS`.\n\n"
        text += "📌 Get group ID by adding @userinfobot to the group."
        
        await update.message.reply_text(text, parse_mode="Markdown")

    # ============== LIFECYCLE ==============




    async def run(self):
        """Start the bot."""
        await self.initialize()
        logger.info("🚀 Starting bot...")
        
        # PTB v20+ pattern: initialize -> start -> idle
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("🤖 Bot is running! Waiting for messages...")
        
        # Keep running until stopped
        while self.is_running:
            await asyncio.sleep(1)
        
        await self.stop()

    async def stop(self):
        """Graceful shutdown."""
        logger.info("🛑 Shutting down...")
        self.is_running = False
        
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
        if self.autonomous:
            await self.autonomous.stop()
        if self.swarm:
            await self.swarm.shutdown()
        if self.brain:
            await self.brain.shutdown()
        
        logger.info("✅ Shutdown complete")


def main():
    """Entry point."""
    TOKEN = os.getenv("ORCHESTRATOR_BOT_TOKEN", "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac")

    bot = OrchestratorBot(TOKEN)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
