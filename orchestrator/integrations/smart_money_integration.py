# Smart Money Tracker Integration
# Add these imports to telegram_orchestrator.py

# At the top (with other imports):
# from agents.smart_money_commands import SmartMoneyCommandHandler

# In initialize() method, after wallet_handler:
# self.smart_money_handler = SmartMoneyCommandHandler(self.app, None)  # Will set agent after

# In _setup_handlers(), add:
# Smart Money commands
# self.app.add_handler(CommandHandler("discover", self.cmd_discover))
# self.app.add_handler(CommandHandler("track", self.cmd_track))
# self.app.add_handler(CommandHandler("untrack", self.cmd_untrack))
# self.app.add_handler(CommandHandler("smart_list", self.cmd_smart_list))
# self.app.add_handler(CommandHandler("smart_stats", self.cmd_smart_stats))
# self.app.add_handler(CommandHandler("smart_top", self.cmd_smart_top))
# self.app.add_handler(CommandHandler("smart_analyze", self.cmd_smart_analyze))
# self.app.add_handler(CommandHandler("follow", self.cmd_follow))

# Add these handler methods to OrchestratorBot class:

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
