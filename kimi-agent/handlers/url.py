"""URL handler for Kimi Telegram Agent."""
import logging
import re
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from brain.llm import llm
from brain.memory import memory
from research.analyzer import analyzer
from utils.helpers import format_analysis_response

logger = logging.getLogger(__name__)

# URL regex pattern
URL_PATTERN = re.compile(
    r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*',
    re.IGNORECASE
)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    return URL_PATTERN.findall(text)


async def handle_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str | None = None
) -> None:
    """Handle URL analysis."""
    user_id = update.effective_user.id
    
    if url is None:
        # Extract URL from message
        text = update.message.text
        urls = extract_urls(text)
        if not urls:
            await update.message.reply_text("❌ No URL found in message.")
            return
        url = urls[0]
    
    # Send status
    status_msg = await update.message.reply_text(
        f"🔍 Analyzing URL...\n{url[:80]}{'...' if len(url) > 80 else ''}"
    )
    
    # Analyze
    result = await analyzer.analyze_url(url)
    
    if not result.get("success"):
        await status_msg.edit_text(
            f"❌ Failed to analyze URL: {result.get('error', 'Unknown error')}"
        )
        return
    
    # Build response
    title = result.get("title", "Untitled")
    site = result.get("metadata", {}).get("site_name", "")
    
    response = f"""🔗 **URL Analysis**

📄 **{title}**
🏠 {site}
🔗 {url}

---
📊 **Summary**
{result['analysis']}
"""
    
    # Add claims if found
    if result.get("claims"):
        response += f"\n📝 **Key Claims** ({len(result['claims'])}):\n"
        for i, claim in enumerate(result["claims"][:5], 1):
            response += f"{i}. {claim[:120]}{'...' if len(claim) > 120 else ''}\n"
    
    # Add verification if available
    if result.get("verification"):
        verified_count = sum(1 for v in result["verification"] if v.get("verified") is True)
        total = len(result["verification"])
        response += f"\n✅ **Verification**: {verified_count}/{total} claims verified\n"
    
    await status_msg.edit_text(
        response,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    # Log to memory
    memory.add_message(
        telegram_id=str(user_id),
        role="user",
        content=f"[URL] {url}",
        message_type="url"
    )
    
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="url_analysis"
    )


async def handle_url_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /analyze_url command."""
    url = " ".join(context.args) if context.args else None
    
    if not url:
        await update.message.reply_text(
            "🔗 Usage: `/analyze_url <url>`\n\n"
            "Or just send a URL directly!",
            parse_mode="Markdown"
        )
        return
    
    await handle_url(update, context, url)
