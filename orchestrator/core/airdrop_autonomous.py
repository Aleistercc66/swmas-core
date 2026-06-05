"""
Autonomous Airdrop Tracker
============================
Background task that:
1. Auto-discovers new airdrops every 6 hours
2. Alerts on upcoming snapshots / claim windows
3. Tracks farming progress and sends reminders
4. Monitors eligibility criteria changes
5. Sends daily farming summary

Integrates with Telegram orchestrator for alerts.
"""
import os
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Config
CHECK_INTERVAL_HOURS = 6
DAILY_SUMMARY_HOUR = 9  # 9 AM UTC
ALERT_DAYS_BEFORE_SNAPSHOT = 7

DATA_DIR = Path("/root/.openclaw/workspace/orchestrator/data/airdrops")
TRACKER_STATE_FILE = DATA_DIR / "tracker_state.json"


class AirdropAutonomousTracker:
    """
    Autonomous background tracker for airdrops.
    Runs checks every 6 hours and sends Telegram alerts.
    """

    def __init__(self, telegram_app=None, target_chat_id: Optional[str] = None):
        self.telegram_app = telegram_app
        self.target_chat_id = target_chat_id or os.getenv("ORCHESTRATOR_TARGET_CHAT", "158923136")
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_check: Optional[datetime] = None
        self.last_daily_summary: Optional[datetime] = None
        self._load_state()

    def _load_state(self):
        if TRACKER_STATE_FILE.exists():
            try:
                with open(TRACKER_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.last_check = datetime.fromisoformat(data.get("last_check")) if data.get("last_check") else None
                    self.last_daily_summary = datetime.fromisoformat(data.get("last_daily_summary")) if data.get("last_daily_summary") else None
            except Exception:
                pass

    def _save_state(self):
        data = {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_daily_summary": self.last_daily_summary.isoformat() if self.last_daily_summary else None,
        }
        with open(TRACKER_STATE_FILE, 'w') as f:
            json.dump(data, f)

    async def _send_alert(self, message: str, parse_mode: str = "Markdown"):
        """Send alert via Telegram."""
        if not self.telegram_app:
            logger.info(f"[ALERT] {message[:100]}...")
            return

        try:
            from telegram import Bot
            bot = Bot(token=self.telegram_app.bot.token)
            await bot.send_message(
                chat_id=self.target_chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            logger.info("Alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    async def _check_new_airdrops(self):
        """Discover and alert on new airdrops."""
        try:
            from agents.airdrop_agent import get_airdrop_agent
            agent = await get_airdrop_agent()
            new = await agent.discover_airdrops()

            if new:
                msg = f"🔍 **{len(new)} NEW AIRDROPS DISCOVERED!**\n\n"
                for a in new:
                    msg += f"🪂 **{a.name}** — `{a.protocol}`\n"
                    msg += f"   Chain: `{a.chain}` | Status: `{a.status}`\n"
                    msg += f"   Est. Value: `{a.estimated_value or 'TBD'}`\n\n"
                msg += "Use `/airdrops` to view full watchlist!"
                await self._send_alert(msg)
        except Exception as e:
            logger.error(f"Error checking new airdrops: {e}")

    async def _check_snapshot_alerts(self):
        """Alert on upcoming snapshots."""
        try:
            from agents.airdrop_agent import get_airdrop_agent
            agent = await get_airdrop_agent()

            now = datetime.utcnow()
            alerts = []

            for a in agent.watchlist:
                if a.snapshot_date and a.status in ["active", "upcoming"]:
                    try:
                        snapshot = datetime.strptime(a.snapshot_date, "%Y-%m-%d")
                        days_until = (snapshot - now).days

                        if 0 < days_until <= ALERT_DAYS_BEFORE_SNAPSHOT:
                            alerts.append({
                                "name": a.name,
                                "days": days_until,
                                "date": a.snapshot_date,
                                "protocol": a.protocol,
                            })
                    except Exception:
                        pass

            if alerts:
                msg = "⚠️ **SNAPSHOT ALERTS!** ⚠️\n\n"
                for alert in sorted(alerts, key=lambda x: x["days"]):
                    urgency = "🔴" if alert["days"] <= 2 else "🟡" if alert["days"] <= 5 else "⏳"
                    msg += (
                        f"{urgency} **{alert['name']}**\n"
                        f"   Snapshot in `{alert['days']} days` ({alert['date']})\n"
                        f"   Protocol: `{alert['protocol']}`\n\n"
                    )
                msg += "Make sure you're eligible! Use `/check <airdrop> <wallet>`"
                await self._send_alert(msg)

        except Exception as e:
            logger.error(f"Error checking snapshots: {e}")

    async def _check_farming_reminders(self):
        """Send reminders for active farming tasks."""
        try:
            from agents.airdrop_agent import get_airdrop_agent
            agent = await get_airdrop_agent()

            reminders = []
            for task in agent.farming_tasks.values():
                if task.status != "active":
                    continue

                total = len(task.tasks)
                done = sum(1 for v in task.tasks.values() if v)
                pct = (done / total * 100) if total else 0

                # Remind if progress is low
                if pct < 30:
                    reminders.append({
                        "name": task.airdrop_name,
                        "pct": pct,
                        "done": done,
                        "total": total,
                        "urgency": "🔴",
                    })
                elif pct < 70:
                    reminders.append({
                        "name": task.airdrop_name,
                        "pct": pct,
                        "done": done,
                        "total": total,
                        "urgency": "🟡",
                    })

            if reminders:
                msg = "🚜 **FARMING REMINDERS** 🚜\n\n"
                for r in reminders:
                    msg += (
                        f"{r['urgency']} **{r['name']}** — `{r['pct']:.0f}%` complete\n"
                        f"   Progress: `{r['done']}/{r['total']}` tasks\n\n"
                    )
                msg += "Keep pushing! Use `/farming` for details."
                await self._send_alert(msg)

        except Exception as e:
            logger.error(f"Error checking farming reminders: {e}")

    async def _send_daily_summary(self):
        """Send daily farming summary at configured hour."""
        now = datetime.utcnow()

        # Check if already sent today
        if self.last_daily_summary and self.last_daily_summary.date() == now.date():
            return

        if now.hour != DAILY_SUMMARY_HOUR:
            return

        try:
            from agents.airdrop_agent import get_airdrop_agent
            agent = await get_airdrop_agent()

            # Count stats
            total = len(agent.watchlist)
            by_status = {}
            for a in agent.watchlist:
                by_status[a.status] = by_status.get(a.status, 0) + 1

            active_farms = len([t for t in agent.farming_tasks.values() if t.status == "active"])
            total_tasks_done = sum(
                sum(1 for v in t.tasks.values() if v)
                for t in agent.farming_tasks.values()
            )

            # Upcoming snapshots in next 14 days
            upcoming_snapshots = []
            for a in agent.watchlist:
                if a.snapshot_date and a.status in ["active", "upcoming"]:
                    try:
                        snapshot = datetime.strptime(a.snapshot_date, "%Y-%m-%d")
                        days_until = (snapshot - now).days
                        if 0 < days_until <= 14:
                            upcoming_snapshots.append({
                                "name": a.name,
                                "days": days_until,
                            })
                    except Exception:
                        pass

            msg = (
                f"📅 **DAILY AIRDROP SUMMARY** — {now.strftime('%Y-%m-%d')}\n\n"
                f"📋 Watchlist: `{total}` airdrops\n"
                f"  🔥 Active: `{by_status.get('active', 0)}`\n"
                f"  ⏳ Upcoming: `{by_status.get('upcoming', 0)}`\n"
                f"  💰 Claimable: `{by_status.get('claimable', 0)}`\n\n"
                f"🚜 Active Farms: `{active_farms}`\n"
                f"✅ Tasks Completed Today: `{total_tasks_done}`\n\n"
            )

            if upcoming_snapshots:
                msg += "📸 **Upcoming Snapshots:**\n"
                for s in sorted(upcoming_snapshots, key=lambda x: x["days"]):
                    msg += f"  • {s['name']} — `{s['days']} days`\n"
                msg += "\n"

            # Recommendations
            if by_status.get('active', 0) > 0:
                msg += "💡 **Tip:** "
                if active_farms < 3:
                    msg += "Consider starting more farms! `/farm_start <airdrop>`\n"
                else:
                    msg += "Great farm count! Keep the weekly routine.\n"

            msg += "\nCommands: `/airdrop` `/farming` `/claim_list`"
            await self._send_alert(msg)
            self.last_daily_summary = now
            self._save_state()

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    async def _run_check_cycle(self):
        """Run one full check cycle."""
        logger.info("🔍 Running airdrop tracker check cycle...")
        self.last_check = datetime.utcnow()

        await self._check_new_airdrops()
        await self._check_snapshot_alerts()
        await self._check_farming_reminders()
        await self._send_daily_summary()

        self._save_state()
        logger.info("✅ Airdrop tracker cycle complete")

    async def start(self):
        """Start the autonomous tracker loop."""
        self.is_running = True
        logger.info(f"🤖 Airdrop tracker starting (check every {CHECK_INTERVAL_HOURS}h)")

        # Run immediately on start
        await self._run_check_cycle()

        # Schedule periodic checks
        while self.is_running:
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
            if self.is_running:
                await self._run_check_cycle()

    async def stop(self):
        """Stop the tracker."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Airdrop tracker stopped")


# Singleton
_tracker_instance: Optional[AirdropAutonomousTracker] = None


async def start_airdrop_tracker(telegram_app=None, chat_id: Optional[str] = None):
    """Start the global airdrop tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = AirdropAutonomousTracker(
            telegram_app=telegram_app,
            target_chat_id=chat_id,
        )
        asyncio.create_task(_tracker_instance.start())
    return _tracker_instance


async def stop_airdrop_tracker():
    """Stop the global tracker."""
    global _tracker_instance
    if _tracker_instance:
        await _tracker_instance.stop()
        _tracker_instance = None
