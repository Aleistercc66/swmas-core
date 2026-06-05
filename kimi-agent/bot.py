"""Telegram bot entrypoint and dispatcher for Kimi Telegram Agent."""
import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import settings
from brain.memory import memory
from handlers import (
    handle_text,
    handle_photo,
    handle_research_command,
    handle_verify_command,
    handle_analyze_command,
    handle_url_command,
    handle_news_command,
    handle_photo_command
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    # Register user
    memory.get_or_create_user(
        telegram_id=str(user.id),
        username=user.username,
        first_name=user.first_name,
        language_code=user.language_code
    )
    
    welcome_text = f"""🤖 **Welcome to Kimi Agent, {user.first_name}!**

I'm your intelligent research assistant. I can:

📊 **Analyze** — Summarize and analyze any text
🔍 **Research** — Deep research with source verification
📸 **Photos** — OCR text extraction + image analysis
🔗 **URLs** — Scrape and verify webpage content
📰 **News** — Aggregate and fact-check news
✅ **Fact-Check** — Verify claims against sources

**Commands:**
/research <query> — Deep research mode
/verify <text> — Fact-check text
/analyze <text> — Analyze text
/news <topic> — Latest news analysis
/analyze_url <url> — Analyze a URL
/analyze_photo — Reply to a photo to analyze
/status — Bot status
/clear — Clear conversation memory
/help — Show this help

**Or just send me:**
• Any question → I'll research it
• Any text → I'll analyze it
• Any photo → I'll extract text/describe it
• Any URL → I'll analyze the page

Let's get started! 🚀"""
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    logger.info(f"User {user.id} ({user.username}) started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """📖 **Kimi Agent Help**

**Research Commands:**
`/research <query>` — Multi-step deep research
`/verify <text>` — Fact-check specific text
`/news <topic>` — News aggregation + analysis

**Analysis Commands:**
`/analyze <text>` — Text analysis & summary
`/analyze_url <url>` — URL scraping & verification
`/analyze_photo` — Reply to photo for OCR/analysis

**Utility Commands:**
`/status` — Bot status & your stats
`/clear` — Clear your conversation memory
`/help` — Show this help

**Automatic Detection:**
• Questions → Auto-trigger research
• URLs → Auto-analyze webpage
• Photos → Auto OCR + analysis

**Output Format:**
All responses include:
📊 Summary
📚 Sources with links
✅ Verification status
⚠️ Caveats & limitations

Need help? Just ask! 🤖"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user = update.effective_user
    stats = memory.get_user_stats(str(user.id))
    
    status_text = f"""📊 **Bot Status**

👤 **User**: {user.first_name or 'Unknown'}
🆔 **ID**: `{user.id}`
📝 **Messages**: {stats.get('messages', 0)}
🌐 **Language**: {stats.get('language', 'en')}
📅 **First seen**: {stats.get('first_seen', 'Unknown')[:10] if stats.get('first_seen') else 'Unknown'}

⚙️ **Bot Settings**:
• Model: `{settings.OPENAI_MODEL}`
• Max search results: {settings.MAX_SEARCH_RESULTS}
• Memory limit: {settings.MEMORY_MESSAGE_LIMIT} messages
• Rate limit: {settings.RATE_LIMIT_PER_MINUTE}/min

✅ All systems operational!"""
    
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command."""
    user_id = update.effective_user.id
    deleted = memory.clear_memory(str(user_id))
    
    await update.message.reply_text(
        f"🗑️ Cleared {deleted} messages from your conversation memory.\n\n"
        f"Starting fresh! 🚀"
    )
    
    logger.info(f"User {user_id} cleared memory")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later.\n\n"
            "If the problem persists, try /clear and start over."
        )


def main() -> None:
    """Start the bot."""
    logger.info("Starting Kimi Telegram Agent...")
    
    # Check required settings
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Please configure your .env file.")
        sys.exit(1)
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. LLM features will not work.")
    
    # Build application
    application = Application.builder().token(settings.BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("research", handle_research_command))
    application.add_handler(CommandHandler("verify", handle_verify_command))
    application.add_handler(CommandHandler("analyze", handle_analyze_command))
    application.add_handler(CommandHandler("news", handle_news_command))
    application.add_handler(CommandHandler("analyze_url", handle_url_command))
    application.add_handler(CommandHandler("analyze_photo", handle_photo_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("Bot started! Press Ctrl+C to stop.")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
