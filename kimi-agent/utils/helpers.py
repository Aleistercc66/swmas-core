"""Utility helpers for Kimi Telegram Agent."""
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter per user."""
    
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}
    
    def allow_request(self, user_id: str) -> bool:
        """Check if request is allowed for user."""
        now = time.time()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside window
        cutoff = now - self.window_seconds
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > cutoff
        ]
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(now)
        return True


def format_analysis_response(result: dict[str, Any]) -> str:
    """Format research/analysis result for Telegram."""
    response = ""
    
    # Summary
    if result.get("summary"):
        response += f"📊 **Summary**\n{result['summary']}\n\n"
    
    # Detailed answer
    if result.get("detailed_answer"):
        response += f"---\n📖 **Detailed Answer**\n{result['detailed_answer'][:3000]}"
        if len(result["detailed_answer"]) > 3000:
            response += "\n\n_(truncated for length)_"
        response += "\n\n"
    
    # Sources
    if result.get("sources"):
        response += "---\n📚 **Sources**\n"
        for i, source in enumerate(result["sources"][:8], 1):
            title = source.get("title", "Source")[:60]
            url = source.get("url", "")
            site = source.get("site", "")
            response += f"{i}. [{title}]({url})"
            if site:
                response += f" — {site}"
            response += "\n"
    
    # Key claims with confidence
    if result.get("key_claims"):
        response += "\n---\n✅ **Key Claims**\n"
        for claim_data in result["key_claims"][:5]:
            claim = claim_data.get("claim", "")
            confidence = claim_data.get("confidence", 0)
            response += f"• {claim[:100]}{'...' if len(claim) > 100 else ''} "
            response += f"({confidence}% confident)\n"
    
    # Verification
    if result.get("claims_verification"):
        response += "\n---\n🔍 **Verification**\n"
        for v in result["claims_verification"][:5]:
            verified = v.get("verified")
            if verified is True:
                icon = "✅"
            elif verified is False:
                icon = "❌"
            else:
                icon = "⚠️"
            conf = v.get("confidence", 0)
            response += f"{icon} {v.get('claim', '')[:80]} ({conf}%)\n"
    
    # Consensus / Controversy
    if result.get("consensus"):
        response += f"\n🤝 **Consensus**: {result['consensus'][:200]}\n"
    
    if result.get("controversy"):
        response += f"\n⚡ **Controversy**: {result['controversy'][:200]}\n"
    
    # Overall confidence
    confidence = result.get("overall_confidence", 0)
    if confidence > 0:
        if confidence >= 80:
            conf_icon = "🟢"
        elif confidence >= 60:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"
        response += f"\n---\n{conf_icon} **Overall Confidence**: {confidence}/100\n"
    
    # Caveats
    if result.get("caveats"):
        response += f"\n⚠️ **Caveats**: {result['caveats'][:300]}\n"
    
    # Source diversity
    if result.get("source_diversity"):
        div = result["source_diversity"]
        if div >= 75:
            div_icon = "🟢"
        elif div >= 50:
            div_icon = "🟡"
        else:
            div_icon = "🔴"
        response += f"\n{div_icon} **Source Diversity**: {div}/100\n"
    
    return response or "No results to display."


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s<>"{}|\\^`\[\]]*',
        re.IGNORECASE
    )
    return url_pattern.findall(text)


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove control characters
    text = "".join(char for char in text if ord(char) >= 32 or char == '\n')
    return text.strip()


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to max length with indicator."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_number(num: float) -> str:
    """Format number for display."""
    if abs(num) >= 1e9:
        return f"{num/1e9:.1f}B"
    if abs(num) >= 1e6:
        return f"{num/1e6:.1f}M"
    if abs(num) >= 1e3:
        return f"{num/1e3:.1f}K"
    return f"{num:.2f}"
