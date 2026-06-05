"""
SWMAS — Telegram Bot Integration
telegram_bot.py

Bridges Telegram messages to the SWMAS Orchestrator.
Supports commands: /status, /agents, /submit, /stop
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Path setup for Phase 1 imports
import sys
from pathlib import Path
_PHASE1 = Path(__file__).resolve().parent / "phase1"
if str(_PHASE1) not in sys.path:
    sys.path.insert(0, str(_PHASE1))

from orchestrator import Orchestrator, Priority
from agent_factory import AgentFactory, AgentType, AgentConfig

logger = logging.getLogger("swmas.telegram")


class TelegramBot:
    """
    Telegram bot wrapper for SWMAS.

    - Receives messages from Telegram
    - Forwards them to the Orchestrator as objectives
    - Sends results back to Telegram
    - Commands: /status, /agents, /submit, /stop
    """

    def __init__(
        self,
        token: str,
        orchestrator: Orchestrator,
        allowed_chat_ids: Optional[set[int]] = None,
    ) -> None:
        self.token = token
        self.orchestrator = orchestrator
        self.allowed_chat_ids = allowed_chat_ids
        self.application: Optional[Application] = None
        self._running = False

    async def start(self) -> None:
        """Build and start the Telegram application."""
        self.application = Application.builder().token(self.token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("status", self._cmd_status))
        self.application.add_handler(CommandHandler("agents", self._cmd_agents))
        self.application.add_handler(CommandHandler("submit", self._cmd_submit))
        self.application.add_handler(CommandHandler("stop", self._cmd_stop))
        self.application.add_handler(CommandHandler("health", self._cmd_health))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        self._running = True
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        self._running = False
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        logger.info("Telegram bot stopped")

    def _is_allowed(self, chat_id: int) -> bool:
        if self.allowed_chat_ids is None:
            return True
        return chat_id in self.allowed_chat_ids

    # ── Command handlers ──

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start."""
        if not self._is_allowed(update.effective_chat.id):
            return
        await update.message.reply_text(
            "🔥 **SWMAS Bot online!**\n\n"
            "Commands:\n"
            "• /status — Swarm status\n"
            "• /agents — List active agents\n"
            "• /submit <task> — Submit objective\n"
            "• /health — Health check\n"
            "• /stop — Stop swarm\n\n"
            "Or just send a message to submit a task!"
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status — show swarm overview."""
        if not self._is_allowed(update.effective_chat.id):
            return
        metrics = self.orchestrator.get_metrics()
        text = (
            f"📊 **Swarm Status**\n\n"
            f"Objectives: {metrics['total_objectives']}\n"
            f"Active: {metrics['active_objectives']}\n"
            f"Completed: {metrics['objectives_completed']}\n"
            f"Agents spawned: {metrics['agents_spawned']}\n"
            f"Tasks dispatched: {metrics['tasks_dispatched']}"
        )
        await update.message.reply_text(text)

    async def _cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /agents — list active agents."""
        if not self._is_allowed(update.effective_chat.id):
            return
        factory = self.orchestrator.factory
        active = factory.list_agents()
        if not active:
            await update.message.reply_text("🫡 No active agents right now.")
            return

        lines = ["🤖 **Active Agents**\n"]
        for rec in active[:20]:
            lines.append(
                f"• `{rec.agent_id}` — {rec.agent_type.value} ({rec.status.value})"
            )
        await update.message.reply_text("\n".join(lines))

    async def _cmd_submit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /submit <task> — submit objective to orchestrator."""
        if not self._is_allowed(update.effective_chat.id):
            return
        task_text = " ".join(context.args) if context.args else ""
        if not task_text:
            await update.message.reply_text("Usage: /submit <your task here>")
            return

        obj_id = await self.orchestrator.submit_objective(
            description=task_text,
            priority=Priority.NORMAL,
            metadata={"source": "telegram", "chat_id": update.effective_chat.id},
        )
        await update.message.reply_text(
            f"🎯 **Objective submitted!**\nID: `{obj_id}`\n"
            f"Task: _{task_text[:100]}..._" if len(task_text) > 100 else f"Task: _{task_text}_"
        )

    async def _cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /health — full health check."""
        if not self._is_allowed(update.effective_chat.id):
            return
        health = await self.orchestrator.health_check()
        text = (
            f"💓 **Health Check**\n\n"
            f"Orchestrator: running={health['orchestrator']['running']}\n"
            f"Bus: sent={health['bus']['messages_sent']} delivered={health['bus']['messages_delivered']}\n"
            f"Memory: {health['memory']['total_entries']}/{health['memory']['max_entries']}\n"
            f"Factory: spawned={health['factory']['total_spawned']} active={health['factory']['active']}"
        )
        await update.message.reply_text(text)

    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop — graceful shutdown."""
        if not self._is_allowed(update.effective_chat.id):
            return
        await update.message.reply_text("🛑 Shutting down swarm...")
        # Signal daemon to stop
        from daemon import shutdown_event
        shutdown_event.set()

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages as objectives."""
        if not self._is_allowed(update.effective_chat.id):
            return
        text = update.message.text or ""
        if not text.strip():
            return

        obj_id = await self.orchestrator.submit_objective(
            description=text.strip(),
            priority=Priority.NORMAL,
            metadata={"source": "telegram", "chat_id": update.effective_chat.id},
        )
        await update.message.reply_text(
            f"🎯 **Got it!** Objective queued.\nID: `{obj_id}`"
        )

    # ── Result notification ──

    async def notify(self, chat_id: int, text: str) -> None:
        """Send a message to a specific chat."""
        if self.application and self._running:
            try:
                await self.application.bot.send_message(chat_id=chat_id, text=text)
            except Exception as exc:
                logger.error(f"Failed to notify chat {chat_id}: {exc}")


def create_bot(token: str, orchestrator: Orchestrator) -> TelegramBot:
    """Factory function to create a TelegramBot instance."""
    return TelegramBot(token=token, orchestrator=orchestrator)
