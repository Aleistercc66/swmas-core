"""Text handler for Kimi Telegram Agent."""
import logging
import re
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from brain.llm import llm
from brain.memory import memory
from research.analyzer import analyzer
from research.search import search_engine
from utils.helpers import format_analysis_response, RateLimiter

logger = logging.getLogger(__name__)

# Rate limiter: 20 requests per minute per user
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)

# Auto-detect research triggers
RESEARCH_TRIGGERS = [
    r"(?i)^(what|who|when|where|why|how|is|are|did|does|can|could|would|should|will)\s",
    r"(?i)\?(\s*$|\s+[^\?]*$)",  # Ends with question mark
    r"(?i)(research|find out|look up|search for|investigate|learn about|tell me about)",
    r"(?i)(explain|what is|who is|how to|how do|why is|why does)",
]

# URL pattern for auto-detection
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)


def is_research_query(text: str) -> bool:
    """Check if text is a research query."""
    for pattern in RESEARCH_TRIGGERS:
        if re.search(pattern, text):
            return True
    return False


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text
    
    # Rate limit check
    if not rate_limiter.allow_request(str(user_id)):
        await update.message.reply_text(
            "⚠️ Rate limit reached. Please wait a minute before sending more requests."
        )
        return
    
    # Log to memory
    memory.add_message(
        telegram_id=str(user_id),
        role="user",
        content=text,
        message_type="text",
        metadata={"username": username}
    )
    
    # Show typing
    await update.message.chat.send_action(action="typing")
    
    # Check for URLs in message
    urls = URL_PATTERN.findall(text)
    if urls:
        from handlers.url import handle_url
        await handle_url(update, context, urls[0])
        return
    
    # Determine if research is needed
    if is_research_query(text):
        await handle_research(update, context, text)
    else:
        await handle_analysis(update, context, text)


async def handle_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str
) -> None:
    """Handle text analysis (summary, key points)."""
    user_id = update.effective_user.id
    
    # Get context
    history = memory.get_recent_messages(str(user_id), limit=5)
    
    # Analyze
    result = await analyzer.analyze_text(text)
    
    # Build response
    response = f"""📊 **Analysis**

{result['analysis']}

---
📝 **Stats**: {result['word_count']} words | {result['char_count']} characters
"""
    
    # If claims found, offer verification
    if result.get("claims"):
        claims_preview = result["claims"][:3]
        response += f"\n🔍 **Detected Claims** ({len(result['claims'])} total):\n"
        for i, claim in enumerate(claims_preview, 1):
            response += f"{i}. {claim[:100]}{'...' if len(claim) > 100 else ''}\n"
        if len(result["claims"]) > 3:
            response += f"\n_Use `/verify` to fact-check all claims_"
    
    await update.message.reply_text(response, parse_mode="Markdown")
    
    # Log response
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="analysis"
    )


async def handle_research(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str
) -> None:
    """Handle deep research mode."""
    user_id = update.effective_user.id
    
    # Send initial message
    status_msg = await update.message.reply_text(
        "🔍 **Research Mode Activated**\n"
        "Searching sources... This may take 30-60 seconds.",
        parse_mode="Markdown"
    )
    
    # Execute research
    result = await analyzer.research(query)
    
    if not result.get("success"):
        await status_msg.edit_text(
            f"❌ Research failed: {result.get('error', 'Unknown error')}"
        )
        return
    
    # Build response
    response = format_analysis_response(result)
    
    # Edit status message with result
    await status_msg.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    
    # Log response
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="research",
        metadata={"query": query, "sources": len(result.get("sources", []))}
    )


async def handle_research_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /research command."""
    query = " ".join(context.args) if context.args else None
    
    if not query:
        await update.message.reply_text(
            "🔍 Usage: `/research <your question>`\n\n"
            "Example: `/research What is quantum computing?`",
            parse_mode="Markdown"
        )
        return
    
    await handle_research(update, context, query)


async def handle_verify_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /verify command."""
    user_id = update.effective_user.id
    text = " ".join(context.args) if context.args else None
    
    if not text:
        # Try to get last message
        history = memory.get_recent_messages(str(user_id), limit=3)
        user_msgs = [m for m in history if m["role"] == "user"]
        if user_msgs:
            text = user_msgs[-1]["content"]
        else:
            await update.message.reply_text(
                "📝 Usage: `/verify <text to fact-check>`\n\n"
                "Or reply to a message with `/verify`",
                parse_mode="Markdown"
            )
            return
    
    status_msg = await update.message.reply_text(
        "🔍 Fact-checking... Searching sources and verifying claims..."
    )
    
    # Run verification
    result = await analyzer.verifier.deep_verify(text)
    
    # Build response
    response = f"""📋 **Fact-Check Report**

{result['summary']}

---
"""
    
    for claim_data in result.get("claims", []):
        claim = claim_data.get("claim", "")
        verified = claim_data.get("verified")
        confidence = claim_data.get("confidence", 0)
        
        if verified is True:
            status = "✅ Verified"
        elif verified is False:
            status = "❌ Contradicted"
        else:
            status = "⚠️ Uncertain"
        
        response += f"\n**{status}** ({confidence}% confidence)\n"
        response += f"_Claim_: {claim[:150]}{'...' if len(claim) > 150 else ''}\n"
        if claim_data.get("explanation"):
            response += f"_Reason_: {claim_data['explanation'][:200]}\n"
    
    response += f"\n---\n📚 Sources checked: {result.get('sources_count', 0)}"
    
    await status_msg.edit_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="verify"
    )


async def handle_analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /analyze command."""
    text = " ".join(context.args) if context.args else None
    
    if not text:
        await update.message.reply_text(
            "📝 Usage: `/analyze <text to analyze>`",
            parse_mode="Markdown"
        )
        return
    
    await handle_analysis(update, context, text)
