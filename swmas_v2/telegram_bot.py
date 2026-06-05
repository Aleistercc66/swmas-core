"""
SWMAS — Telegram Bot Integration (Greek Edition)
telegram_bot.py

Connects the SWMAS swarm to Telegram.
Users can submit objectives, check status, and receive results via Telegram.
ALL responses are in Greek (Ελληνικά).
"""

from __future__ import annotations

import asyncio
from typing import Any
import json
from pathlib import Path

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False
    class Update: pass
    class ContextTypes:
        DEFAULT_TYPE = None
    class Application: pass
    class ApplicationBuilder:
        def token(self, t): return self
        def build(self): return Application()
    class CommandHandler: pass
    class MessageHandler: pass
    class filters:
        TEXT = None
        COMMAND = None

from communication_bus import Priority


class SwarmTelegramBot:
    """
    Telegram bot wrapper for SWMAS — ALL responses in Greek.

    Commands:
        /start      — Καλωσόρισμα
        /status     — Υγεία swarm
        /agents     — Ενεργοί agents
        /submit     — Νέο objective
        /objectives — Τελευταία tasks
        /help       — Εντολές
    """

    def __init__(
        self,
        token: str,
        orchestrator: Any,
        factory: Any,
        memory: Any,
        bus: Any,
        allowed_usernames: list[str] | None = None,
    ) -> None:
        self.token = token
        self.orchestrator = orchestrator
        self.factory = factory
        self.memory = memory
        self.bus = bus
        self.allowed_usernames = set(allowed_usernames or [])
        self._app: Application | None = None
        self._running = False
        # File bridge for external AI responses
        self._inbox_path = Path("/root/.openclaw/workspace/swmas_v2/telegram_inbox.jsonl")
        self._outbox_path = Path("/root/.openclaw/workspace/swmas_v2/telegram_outbox.jsonl")
        self._processed_outbox = set()
        self._inbox_path.parent.mkdir(parents=True, exist_ok=True)

    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized."""
        if not self.allowed_usernames:
            return True
        username = update.effective_user.username if update.effective_user else None
        return username in self.allowed_usernames

    async def _send_unauthorized(self, update: Update) -> None:
        await update.message.reply_text(
            "🚫 Δεν έχεις πρόσβαση. Επικοινώνησε με τον admin του swarm."
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return
        await update.message.reply_text(
            "🔥 **SWMAS Bot** 🔥\n"
            "Self-Wvolving Multiplicative AI Swarm\n\n"
            "Μιλάω Ελληνικά! 🇬🇷\n\n"
            "Εντολές:\n"
            "  /status — Υγεία swarm\n"
            "  /agents — Ενεργοί agents\n"
            "  /submit <task> — Νέο objective\n"
            "  /objectives — Τελευταία tasks\n"
            "  /help — Όλες οι εντολές\n\n"
            "Ή απλά γράψε μου ό,τι θες — το swarm ακούει! ⚡"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return
        await update.message.reply_text(
            "📋 **Διαθέσιμες Εντολές**\n\n"
            "/start — Καλωσόρισμα & πληροφορίες\n"
            "/status — Πλήρες health check του swarm\n"
            "/agents — Λίστα όλων των ενεργών agents\n"
            "/submit <περιγραφή> — Νέο objective στο swarm\n"
            "  Παράδειγμα: /submit Research Bitcoin trends\n"
            "/objectives — Τελευταία 10 objectives με status\n"
            "/help — Αυτό το μήνυμα\n\n"
            "💬 Μπορείς επίσης να στείλεις οποιοδήποτε μήνυμα — "
            "θα το διαβάσω ως objective ή θα σου απαντήσω απευθείας!"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return
        try:
            health = await self.orchestrator.health_check()
            orch = health["orchestrator"]
            fac = health["factory"]
            bus = health["bus"]
            mem = health["memory"]

            text = (
                "🎯 **SWARM STATUS**\n"
                f"🧠 Orchestrator: {'τρέχει' if orch.get('running') else 'σταματημένος'}\n"
                f"📋 Objectives: {orch['total_objectives']} συνολικά / {orch['active_objectives']} ενεργά\n"
                f"🤖 Agents: {fac['total_spawned']} spawned / {fac['active']} ενεργοί / {fac['paused']} paused\n"
                f"📡 Messages: {bus['messages_sent']} sent / {bus['messages_delivered']} delivered\n"
                f"🗄️ Memory: {mem['total_entries']} entries / {mem['max_entries']} max\n\n"
                "⚡ Το swarm είναι ΖΩΝΤΑΝΟ!"
            )
            await update.message.reply_text(text)
        except Exception as exc:
            await update.message.reply_text(f"❌ Σφάλμα status: {exc}")

    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return
        agents = self.factory.list_agents()
        if not agents:
            await update.message.reply_text("🔍 Κανένας agent ενεργός αυτή τη στιγμή.")
            return

        lines = ["🤖 **ΕΝΕΡΓΟΙ AGENTS**"]
        for rec in agents[:20]:
            emoji = "🟢" if rec.status.value == "active" else "🟡" if rec.status.value == "paused" else "🔴"
            lines.append(f"{emoji} `{rec.agent_id}` — {rec.agent_type.value} [{rec.status.value}]")

        await update.message.reply_text("\n".join(lines))

    async def cmd_submit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return

        text = update.message.text
        parts = text.split(" ", 1)
        if len(parts) < 2:
            await update.message.reply_text(
                "📝 **Χρήση:** /submit <περιγραφή>\n"
                "Παράδειγμα: /submit Research Bitcoin price trends"
            )
            return

        description = parts[1].strip()
        chat_id = update.effective_chat.id

        obj_id = await self.orchestrator.submit_objective(
            description,
            priority=Priority.NORMAL,
            metadata={"source": "telegram", "chat_id": chat_id},
        )

        await update.message.reply_text(
            f"✅ **Objective υποβλήθηκε!**\n"
            f"🆔 ID: `{obj_id}`\n"
            f"📝 Task: {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
            f"⚡ Το swarm το επεξεργάζεται! Γράψε /objectives για progress."
        )

        self.memory.store(
            key=f"telegram:chat:{obj_id}",
            value={"chat_id": chat_id, "description": description},
            agent_id="telegram_bot",
            channel="telegram",
            tags=["telegram", "notification"],
        )

    async def cmd_objectives(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return

        objectives = self.orchestrator.list_objectives()
        if not objectives:
            await update.message.reply_text("📭 Κανένα objective ακόμα.")
            return

        lines = ["📋 **ΤΕΛΕΥΤΑΙΑ OBJECTIVES**"]
        for obj in objectives[-10:]:
            emoji = "✅" if obj.status.value == "completed" else "⚙️" if obj.status.value == "executing" else "⏳"
            lines.append(
                f"{emoji} `{obj.objective_id[:12]}` — [{obj.status.value.upper()}]\n"
                f"   {obj.description[:60]}{'...' if len(obj.description) > 60 else ''}"
            )

        await update.message.reply_text("\n".join(lines))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text — bridge to external AI + submit to swarm."""
        if not self._is_authorized(update):
            await self._send_unauthorized(update)
            return

        user_text = update.message.text.strip()
        if not user_text:
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else 0
        username = update.effective_user.username if update.effective_user else "unknown"

        # Write to inbox bridge file for external AI (me) to read
        entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "chat_id": chat_id,
            "user_id": user_id,
            "username": username,
            "message": user_text,
        }
        with open(self._inbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Immediate smart response (bot personality)
        response = self._smart_greek_response(user_text)
        await update.message.reply_text(response)

        # Also submit as objective to swarm
        obj_id = await self.orchestrator.submit_objective(
            user_text,
            priority=Priority.NORMAL,
            metadata={"source": "telegram", "chat_id": chat_id},
        )

        self.memory.store(
            key=f"telegram:chat:{obj_id}",
            value={"chat_id": chat_id, "description": user_text},
            agent_id="telegram_bot",
            channel="telegram",
            tags=["telegram", "notification"],
        )

    async def _outbox_poller(self) -> None:
        """Poll outbox file for AI responses and send them to Telegram."""
        while self._running:
            try:
                if self._outbox_path.exists():
                    lines = []
                    with open(self._outbox_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    new_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line or line in self._processed_outbox:
                            continue
                        self._processed_outbox.add(line)
                        try:
                            data = json.loads(line)
                            chat_id = data.get("chat_id")
                            text = data.get("message", "")
                            if chat_id and text and self._app:
                                await self._app.bot.send_message(
                                    chat_id=chat_id,
                                    text=text,
                                    parse_mode="Markdown",
                                )
                                print(f"[Bridge] Sent AI response to {chat_id}")
                        except Exception as exc:
                            print(f"[Bridge] Outbox parse error: {exc}")

                    # Clear processed lines from file
                    if new_lines:
                        with open(self._outbox_path, "w", encoding="utf-8") as f:
                            for line in new_lines:
                                f.write(line + "\n")

                await asyncio.sleep(3)
            except Exception as exc:
                print(f"[Bridge] Poller error: {exc}")
                await asyncio.sleep(5)

    def _smart_greek_response(self, text: str) -> str:
        """Generate a Greek response based on user input — no external LLM needed."""
        t = text.lower()

        if any(w in t for w in ["γεια", "hello", "hi", "hey", "καλημέρα", "καλησπέρα"]):
            return (
                "🔥 **Γεια σου!** 🔥\n\n"
                "Είμαι το SWMAS bot — ο εκτελεστικός agent του swarm!\n\n"
                "Μπορώ να κάνω:\n"
                "📝 Να υποβάλω objectives στο swarm\n"
                "📊 Να δείξω status και agents\n"
                "🎯 Να συντονίσω tasks\n\n"
                "Γράψε `/help` για όλες τις εντολές ή απλά πες μου τι θες! ⚡"
            )

        if any(w in t for w in ["bitcoin", "btc", "crypto", "altcoin", "token", "coin"]):
            return (
                "🚀 **Crypto mode ON!**\n\n"
                "Το SWMAS μπορεί να αναλύσει crypto opportunities!\n\n"
                "Υπέβαλα ήδη το request στο swarm:\n"
                "🔍 Researcher agent → συλλογή δεδομένων\n"
                "📊 Analyst agent → τεχνική ανάλυση\n"
                "⚡ Θα έχεις αποτέλεσμα σύντομα!\n\n"
                "Χρησιμοποίησε `/objectives` για να δεις το progress."
            )

        if any(w in t for w in ["swmas", "swarm", "agent", "system", "ποιος είσαι", "τι είσαι"]):
            return (
                "🧠 **SWMAS — Self-Wvolving Multiplicative AI Swarm**\n\n"
                "Ένα αυτόνομο AI swarm που:\n"
                "🤖 Δημιουργεί agents αυτόματα\n"
                "📡 Επικοινωνεί μέσω async bus\n"
                "🗄️ Μοιράζεται μνήμη\n"
                "🎯 Εκτελεί objectives\n"
                "📈 Αυτο-βελτιώνεται\n\n"
                "Είμαι το Telegram interface του. Το κεντρικό brain τρέχει 24/7! ⚡"
            )

        if any(w in t for w in ["τι μπορείς", "βοήθεια", "help", "commands", "εντολές"]):
            return (
                "📋 **Τι μπορώ να κάνω:**\n\n"
                "/start — Καλωσόρισμα\n"
                "/status — Υγεία swarm\n"
                "/agents — Ενεργοί agents\n"
                "/submit <task> — Νέο objective\n"
                "/objectives — Τελευταία tasks\n"
                "/help — Βοήθεια\n\n"
                "Ή απλά γράψε μου ό,τι θες — θα το υποβάλω στο swarm! 🔥"
            )

        if any(w in t for w in ["ευχαριστ", "thanks", "thank you", "perfect", "τέλεια", "πολύ καλά"]):
            return "🫡 **Πάντα στη διάθεσή σου!** Το swarm είναι εδώ 24/7. ⚡🔥"

        # Default: acknowledge + submit to swarm
        return (
            "✅ **Πήρα το μήνυμα!**\n\n"
            f"📝 Task: `{text[:80]}{'...' if len(text) > 80 else ''}`\n\n"
            "⚡ Υπέβαλα το objective στο swarm. Οι agents επεξεργάζονται...\n\n"
            "Χρησιμοποίησε `/objectives` για να δεις το progress!"
        )

    async def _result_notifier(self) -> None:
        """Watch for completed objectives and notify Telegram in Greek."""
        while self._running:
            try:
                completed = self.orchestrator.list_objectives(status="completed")
                for obj in completed:
                    chat_entry = self.memory.retrieve(f"telegram:chat:{obj.objective_id}")
                    if chat_entry and isinstance(chat_entry, dict):
                        chat_id = chat_entry.get("chat_id")
                        if chat_id and self._app:
                            result = obj.results[-1] if obj.results else {}
                            summary = result.get("summary", "Ολοκληρώθηκε!") if isinstance(result, dict) else "Ολοκληρώθηκε!"
                            await self._app.bot.send_message(
                                chat_id=chat_id,
                                text=(
                                    f"🎯 **Objective Ολοκληρώθηκε!**\n"
                                    f"🆔 `{obj.objective_id[:12]}`\n"
                                    f"📊 Αποτέλεσμα: {summary[:200]}"
                                ),
                            )
                            self.memory.delete(f"telegram:chat:{obj.objective_id}")
                await asyncio.sleep(5)
            except Exception as exc:
                print(f"[TelegramBot] Notifier error: {exc}")
                await asyncio.sleep(5)

    async def start(self) -> None:
        """Start the Telegram bot."""
        if not _TELEGRAM_AVAILABLE:
            print("[TelegramBot] python-telegram-bot not installed.")
            return

        self._app = ApplicationBuilder().token(self.token).build()

        self._app.add_handler(CommandHandler("start", self.cmd_start))
        self._app.add_handler(CommandHandler("help", self.cmd_help))
        self._app.add_handler(CommandHandler("status", self.cmd_status))
        self._app.add_handler(CommandHandler("agents", self.cmd_agents))
        self._app.add_handler(CommandHandler("submit", self.cmd_submit))
        self._app.add_handler(CommandHandler("objectives", self.cmd_objectives))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        self._running = True
        notifier_task = asyncio.create_task(self._result_notifier())
        outbox_task = asyncio.create_task(self._outbox_poller())

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        print("[TelegramBot] Bot is polling... (Greek mode ON 🇬🇷)")
        print(f"[Bridge] Inbox: {self._inbox_path}")
        print(f"[Bridge] Outbox: {self._outbox_path}")

        while self._running:
            await asyncio.sleep(1)

        notifier_task.cancel()
        outbox_task.cancel()
        try:
            await notifier_task
        except asyncio.CancelledError:
            pass
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass

        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()
        print("[TelegramBot] Bot stopped.")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        self._running = False
