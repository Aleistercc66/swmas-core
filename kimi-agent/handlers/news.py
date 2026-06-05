"""News handler for Kimi Telegram Agent."""
import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from brain.memory import memory
from research.analyzer import analyzer
from utils.helpers import format_analysis_response

logger = logging.getLogger(__name__)


async def handle_news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: str | None = None
) -> None:
    """Handle news analysis."""
    user_id = update.effective_user.id
    
    if topic is None:
        topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "📰 Usage: `/news <topic>`\n\n"
            "Example: `/news AI technology`\n"
            "Example: `/news Bitcoin price`",
            parse_mode="Markdown"
        )
        return
    
    # Send status
    status_msg = await update.message.reply_text(
        f"📰 Searching latest news on: *{topic}*...",
        parse_mode="Markdown"
    )
    
    # Analyze news
    result = await analyzer.analyze_news(topic)
    
    if not result.get("success"):
        await status_msg.edit_text(
            f"❌ News search failed: {result.get('error', 'Unknown error')}"
        )
        return
    
    # Build response
    analysis = result.get("analysis", "No analysis available.")
    articles = result.get("articles", [])
    diversity = result.get("source_diversity_score", 0)
    
    # Diversity indicator
    if diversity >= 75:
        diversity_icon = "🟢"
    elif diversity >= 50:
        diversity_icon = "🟡"
    else:
        diversity_icon = "🔴"
    
    response = f"""📰 **News Analysis: {topic}**

📊 **Summary**
{analysis}

---
📚 **Sources** ({len(articles)} articles)
"""
    
    for i, article in enumerate(articles[:5], 1):
        title = article.get("title", "Untitled")
        url = article.get("url", "")
        site = article.get("site", "")
        response += f"{i}. [{title[:60]}]({url}) — {site}\n"
    
    response += f"\n---\n{diversity_icon} **Source Diversity**: {diversity}/100\n"
    
    if diversity < 50:
        response += "⚠️ Low diversity — articles may share similar perspectives\n"
    elif diversity >= 75:
        response += "✅ Good diversity — multiple independent sources\n"
    
    await status_msg.edit_text(
        response,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    # Log to memory
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="news",
        metadata={"topic": topic, "articles": len(articles)}
    )


async def handle_news_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /news command."""
    await handle_news(update, context)
