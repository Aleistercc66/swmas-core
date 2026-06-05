"""Handlers package for Kimi Telegram Agent."""
from handlers.text import (
    handle_text,
    handle_research_command,
    handle_verify_command,
    handle_analyze_command
)
from handlers.photo import handle_photo, handle_photo_command
from handlers.url import handle_url, handle_url_command
from handlers.news import handle_news, handle_news_command

__all__ = [
    "handle_text",
    "handle_research_command",
    "handle_verify_command",
    "handle_analyze_command",
    "handle_photo",
    "handle_photo_command",
    "handle_url",
    "handle_url_command",
    "handle_news",
    "handle_news_command"
]
