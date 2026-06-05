"""
🔗 SMART MONEY COMMANDS
Telegram command handlers για τον Smart Money Tracker Agent.
Ενσωματώνεται στον Telegram Orchestrator (@WorkSS11_bot).

Commands:
/discover    — Ανακάλυψη νέων smart money wallets
/track       — Ξεκίνα tracking ενός wallet
/untrack     — Σταμάτα tracking
/list        — Λίστα wallets (με filtering)
/stats       — Stats του agent
/analyze     — Βαθιά ανάλυση ενός wallet
/top         — Top κερδοφόρα wallets
/follow      — Ακολούθησε wallet (alias για track)
"""

from typing import Dict, Optional
import asyncio
import sys
import os

# Add agent path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_money_tracker import (
    SmartMoneyAgent, BlockchainAnalyzer, TelegramAlerter,
    WalletProfile, TradeSignal
)


class SmartMoneyCommandHandler:
    """Handler για Telegram commands"""
    
    def __init__(self, bot, agent: SmartMoneyAgent = None):
        self.bot = bot
        self.agent = agent
        self.analyzer = agent.analyzer if agent else None
        self._initialized = False
    
    async def ensure_initialized(self):
        """Lazy initialization of agent"""
        if not self._initialized and self.bot:
            try:
                # Initialize the agent
                from smart_money_tracker import SmartMoneyAgent
                self.agent = SmartMoneyAgent()
                await self.agent.__aenter__()
                self.analyzer = self.agent.analyzer
                self._initialized = True
                logger.info("🎯 Smart Money agent initialized lazily")
            except Exception as e:
                logger.error(f"Failed to initialize smart money agent: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # COMMAND HANDLERS
    # ═══════════════════════════════════════════════════════════
    
    async def cmd_discover(self, update, context):
        """
        🔍 /discover — Ανακάλυψη smart money wallets
        
        Usage: /discover [source]
        Sources: dexscreener, graduation, all
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args or []
        source = args[0] if args else "all"
        
        await update.message.reply_text("🔍 Scanning blockchain for smart money... This may take a minute.")
        
        try:
            if source == "all":
                sources = ["dexscreener", "graduation"]
            else:
                sources = [source]
            
            all_discovered = []
            for src in sources:
                discovered = await self.analyzer.discover_profitable_wallets(source=src)
                all_discovered.extend(discovered)
            
            # Deduplicate
            unique = {w.address: w for w in all_discovered}
            all_discovered = list(unique.values())
            
            # Sort by score
            all_discovered.sort(key=lambda w: w.smart_money_score, reverse=True)
            
            if not all_discovered:
                await update.message.reply_text("❌ No profitable wallets found. Try again later.")
                return
            
            # Build report
            msg = f"🔍 **DISCOVERED {len(all_discovered)} SMART MONEY WALLETS** 🔍\n\n"
            
            for w in all_discovered[:15]:
                tier_emoji = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📊"}
                emoji = tier_emoji.get(w.confidence_tier, "📊")
                
                msg += f"""
{emoji} **{w.confidence_tier}-Tier** | ⭐ {w.smart_money_score:.1f}/100
`{w.address}`
💰 PnL: {w.total_pnl_sol:+.2f} SOL | Win Rate: {w.win_rate*100:.1f}%
📊 Trades: {w.total_trades} | Portfolio: {w.portfolio_value_sol:.2f} SOL
/track {w.address}

"""
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            
            # Auto-track top 3
            top_3 = [w for w in all_discovered if w.confidence_tier in ["S", "A"]][:3]
            for w in top_3:
                await self.analyzer.start_tracking_wallet(w.address)
            
            if top_3:
                auto_msg = f"🎯 **Auto-tracking top {len(top_3)} wallets!**\n"
                for w in top_3:
                    auto_msg += f"• `{w.address[:12]}...` ({w.confidence_tier}-tier)\n"
                await update.message.reply_text(auto_msg, parse_mode="Markdown")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_track(self, update, context):
        """
        🎯 /track — Ξεκίνα tracking ενός wallet
        
        Usage: /track <wallet_address>
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "🎯 **Track a Wallet**\n\n"
                "Usage: `/track <wallet_address>`\n\n"
                "I'll analyze the wallet and start tracking its moves!"
            )
            return
        
        wallet_addr = args[0]
        
        await update.message.reply_text(f"🎯 Analyzing wallet: `{wallet_addr[:12]}...`", parse_mode="Markdown")
        
        try:
            success = await self.analyzer.start_tracking_wallet(wallet_addr)
            if success:
                wallet = self.analyzer.wallets.get(wallet_addr)
                tier_emoji = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📊"}
                
                msg = f"""
🎯 **TRACKING STARTED** 🎯

{tier_emoji.get(wallet.confidence_tier, "📊")} **Wallet:** `{wallet_addr}`
⭐ **Score:** {wallet.smart_money_score:.1f}/100
🏆 **Tier:** {wallet.confidence_tier}
💰 **PnL:** {wallet.total_pnl_sol:+.2f} SOL
📊 **Win Rate:** {wallet.win_rate*100:.1f}%
📈 **Trades:** {wallet.total_trades}
💼 **Portfolio:** {wallet.portfolio_value_sol:.2f} SOL

👁️ You will receive alerts on EVERY move!
                """
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Failed to analyze wallet. Invalid address or no transaction history.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_untrack(self, update, context):
        """
        🛑 /untrack — Σταμάτα tracking
        
        Usage: /untrack <wallet_address>
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args
        if not args:
            # Show tracked wallets
            tracked = [w for w in self.analyzer.wallets.values() if w.is_tracking]
            if not tracked:
                await update.message.reply_text("No wallets currently being tracked.")
                return
            
            msg = "👁️ **Currently Tracked Wallets**\n\n"
            for w in tracked:
                msg += f"• `{w.address}` — {w.confidence_tier}-tier\n/untrack {w.address}\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        
        wallet_addr = args[0]
        
        try:
            await self.analyzer.stop_tracking_wallet(wallet_addr)
            await update.message.reply_text(f"🛑 Stopped tracking: `{wallet_addr[:12]}...`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_list(self, update, context):
        """
        📊 /list — Λίστα wallets
        
        Usage: /list [tier|tracked|all]
        Filters: S, A, B, C, tracked
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args or ["all"]
        filter_type = args[0].upper()
        
        try:
            if filter_type == "TRACKED":
                wallets = [w for w in self.analyzer.wallets.values() if w.is_tracking]
                title = "👁️ TRACKED WALLETS"
            elif filter_type in ["S", "A", "B", "C", "D"]:
                wallets = self.analyzer.get_top_wallets(tier=filter_type, limit=20)
                title = f"🏆 {filter_type}-TIER WALLETS"
            else:
                wallets = self.analyzer.get_top_wallets(limit=25)
                title = "📊 ALL WALLETS (by score)"
            
            if not wallets:
                await update.message.reply_text(f"No wallets found for filter: {filter_type}")
                return
            
            msg = f"{title}\n\n"
            
            for i, w in enumerate(wallets[:20], 1):
                track_icon = "👁️" if w.is_tracking else "○"
                msg += f"{i}. {track_icon} **{w.confidence_tier}** {w.smart_money_score:.0f}pts | `{w.address[:10]}...` | 💰{w.total_pnl_sol:+.1f} SOL\n"
            
            msg += f"\n_Use `/track <address>` to start tracking_"
            await update.message.reply_text(msg, parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_stats(self, update, context):
        """
        📈 /stats — Stats του agent
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        try:
            stats = self.analyzer.get_stats()
            
            msg = f"""
📈 **SMART MONEY TRACKER STATS**

🔍 Wallets Analyzed: {stats['wallets_analyzed']}
⭐ Qualified (Score ≥60): {stats['wallets_qualified']}
👁️ Currently Tracked: {stats['tracked_wallets']}
🚨 Signals Generated: {stats['signals_generated']}
📨 Alerts Sent: {stats['alerts_sent']}

🏆 **Tier Distribution:**
• 🏆 S-Tier: {stats['tier_distribution'].get('S', 0)}
• 🥇 A-Tier: {stats['tier_distribution'].get('A', 0)}
• 🥈 B-Tier: {stats['tier_distribution'].get('B', 0)}
• 🥉 C-Tier: {stats['tier_distribution'].get('C', 0)}
• 📊 D-Tier: {stats['tier_distribution'].get('D', 0)}

📊 Avg Smart Money Score: {stats['avg_score']:.1f}/100

🔧 Agent Status: ✅ RUNNING
            """
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_analyze(self, update, context):
        """
        🔬 /analyze — Βαθιά ανάλυση ενός wallet
        
        Usage: /analyze <wallet_address>
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "🔬 **Deep Wallet Analysis**\n\n"
                "Usage: `/analyze <wallet_address>`\n\n"
                "I'll perform a complete analysis of the wallet's trading history."
            )
            return
        
        wallet_addr = args[0]
        
        await update.message.reply_text(f"🔬 Deep analysis in progress... This may take 30-60 seconds.")
        
        try:
            profile = await self.analyzer._analyze_wallet_performance(wallet_addr)
            if not profile:
                await update.message.reply_text("❌ Could not analyze wallet. No transaction history found.")
                return
            
            # Calculate score
            profile.calculate_smart_money_score()
            
            tier_emoji = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📊"}
            
            msg = f"""
🔬 **WALLET ANALYSIS REPORT**

{tier_emoji.get(profile.confidence_tier, "📊")} **Tier:** {profile.confidence_tier} | ⭐ Score: {profile.smart_money_score:.1f}/100
`{wallet_addr}`

📊 **Performance:**
• Total Trades: {profile.total_trades}
• Profitable: {profile.profitable_trades}
• Win Rate: {profile.win_rate*100:.1f}%
• Total PnL: {profile.total_pnl_sol:+.2f} SOL
• Avg Return/Trade: {profile.avg_return_per_trade:.3f} SOL
• Max Drawdown: {profile.max_drawdown*100:.1f}%

📈 **Activity:**
• First Seen: {profile.first_seen.strftime('%Y-%m-%d') if profile.first_seen else 'N/A'}
• Last Active: {profile.last_active.strftime('%Y-%m-%d %H:%M') if profile.last_active else 'N/A'}
• Trades/Day: {profile.trades_per_day:.2f}

💼 **Current Holdings:**
• Portfolio Value: {profile.portfolio_value_sol:.2f} SOL
• Holdings: {len(profile.current_holdings)} tokens

🎯 **Recommendation:**
            """
            
            if profile.confidence_tier in ["S", "A"]:
                msg += "🏆 **HIGHLY RECOMMENDED** — Start tracking immediately!\n/track " + wallet_addr
            elif profile.confidence_tier == "B":
                msg += "🥈 **PROMISING** — Consider tracking for observation.\n/track " + wallet_addr
            else:
                msg += "📊 **NEUTRAL** — Not enough data or performance.\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_top(self, update, context):
        """
        🏆 /top — Top κερδοφόρα wallets
        
        Usage: /top [count]
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        
        args = context.args or []
        count = int(args[0]) if args and args[0].isdigit() else 10
        
        try:
            wallets = self.analyzer.get_top_wallets(limit=count)
            
            if not wallets:
                await update.message.reply_text("No wallets in database. Run /discover first!")
                return
            
            msg = f"🏆 **TOP {len(wallets[:count])} SMART MONEY WALLETS** 🏆\n\n"
            
            for i, w in enumerate(wallets[:count], 1):
                track_icon = "👁️" if w.is_tracking else ""
                msg += f"{i}. {track_icon} **{w.confidence_tier}** ⭐{w.smart_money_score:.0f} | `{w.address[:12]}...` | 💰{w.total_pnl_sol:+.1f} SOL ({w.win_rate*100:.0f}% WR)\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_follow(self, update, context):
        """
        👣 /follow — Γρήγορο alias για /track
        """
        await self.ensure_initialized()
        if not self.analyzer:
            await update.message.reply_text("❌ Smart Money tracker initialization failed. Check API keys.")
            return
        await self.cmd_track(update, context)
    
    # ═══════════════════════════════════════════════════════════
    # REGISTRATION
    # ═══════════════════════════════════════════════════════════
    
    def register_with_bot(self, application):
        """Εγγραφή όλων των handlers στο bot"""
        from telegram.ext import CommandHandler
        
        handlers = [
            ("discover", self.cmd_discover),
            ("track", self.cmd_track),
            ("untrack", self.cmd_untrack),
            ("list", self.cmd_list),
            ("stats", self.cmd_stats),
            ("analyze", self.cmd_analyze),
            ("top", self.cmd_top),
            ("follow", self.cmd_follow),
        ]
        
        for command, handler in handlers:
            application.add_handler(CommandHandler(command, handler))
        
        print("✅ Smart Money commands registered!")
        return handlers


# ═══════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════

async def run_standalone():
    """Τρέχει τον agent standalone (χωρίς orchestrator)"""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    
    # Initialize agent
    async with SmartMoneyAgent() as agent:
        handler = SmartMoneyCommandHandler(None, agent)
        
        # Create Telegram application
        application = Application.builder().token(
            os.getenv("TELEGRAM_BOT_TOKEN", "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac")
        ).build()
        
        # Register handlers
        handler.bot = application.bot
        handler.register_with_bot(application)
        
        # Start agent in background
        agent_task = asyncio.create_task(agent.run())
        
        # Start Telegram polling
        await application.initialize()
        await application.start_polling()
        
        try:
            await asyncio.gather(agent_task)
        except asyncio.CancelledError:
            await application.stop()


if __name__ == "__main__":
    asyncio.run(run_standalone())
