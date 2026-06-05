#!/usr/bin/env python3
"""
Telegram Group Monitor for Crypto Signals
Monitors @Metamoonshotschat (and other groups) for:
- Token addresses (0x..., EQ..., etc.)
- DEX links (DexScreener, Pump.fun, Raydium, Jupiter)
- Pump signals (buy, moon, 100x, gem, alpha)
- Whale calls / influencer mentions
- Contract addresses / CA

Sends filtered alerts to the owner.
"""

import re
import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger('group_monitor')

# ============== CONFIGURATION ==============

MONITORED_GROUPS: Dict[int, str] = {
    -1001633350448: "Moonshots🚀",        # @Metamoonshotschat
    -1002066575222: "SOL TRENDING",        # @trendingssol
    -1002555274292: "Sonic Trades",        # @SonicsAlphacalls
    -1001537427825: "Tonkeeper News",       # @tonkeeper_news
    -1001978596449: "EarthMeta.AI",        # @EarthMetaAI
    -1001937567727: "Vic Laranja 🔹",       # @viclaranjafeed
}

# Token address patterns
TOKEN_PATTERNS = [
    r'0x[a-fA-F0-9]{40}',           # EVM addresses
    r'[A-Za-z0-9]{32,44}',          # Solana addresses (base58)
    r'EQ[A-Za-z0-9_-]{40,48}',      # TON addresses
    r'[A-Za-z0-9]{40,64}',           # Generic contract addresses
]

# DEX / trading platform links
DEX_PATTERNS = [
    r'dexscreener\.com/[a-zA-Z0-9/\-_.]+',
    r'pump\.fun/[a-zA-Z0-9]+',
    r'raydium\.io/swap/[a-zA-Z0-9?=&]+',
    r'jup\.ag/swap/[a-zA-Z0-9_\-]+',
    r'app\.uniswap\.org/[#/a-zA-Z0-9?=&]+',
    r'dextools\.io/app/[a-zA-Z0-9/]+',
    r'birdeye\.so/token/[a-zA-Z0-9_\-]+',
    r'moonshot\.mcc\.io/[a-zA-Z0-9]+',
    r't\.me/[a-zA-Z0-9_]+',           # Telegram links (new groups)
]

# Pump signal keywords
PUMP_KEYWORDS = [
    'moon', '100x', '1000x', 'gem', 'alpha', 'pump', 'pumping',
    'breaking out', 'breakout', 'explode', 'exploding', 'send it',
    'next pepe', 'next doge', 'next shib', 'revolutionary',
    'just launched', 'fair launch', 'presale', 'ido', 'ico',
    'low cap', 'micro cap', 'early', 'undervalued', 'diamond',
    'diamond hands', 'hodl', 'accumulate', 'loading', 'chart',
    'bullish', 'bearish', 'long', 'short', 'entry', 'target',
    'take profit', 'stop loss', 'tp', 'sl', 'support', 'resistance',
    ' ATH', ' all time high', 'new high', 'volume', 'liquidity',
    'whale', 'smart money', 'insider', 'dev based', 'team based',
    'contract renounced', 'lp burned', 'locked', 'verified',
    'audit', 'safu', 'based dev', 'community', 'viral',
    'trending', 'top gainer', 'top loser', 'momentum',
]

# Ignore list (noise)
NOISE_KEYWORDS = [
    'spam', 'scam', 'rug', 'honeypot', 'fake', 'bot',
    'admin', 'moderator', 'rules', 'welcome', 'hello',
    'gm', 'gn', 'good morning', 'good night',
    'check pm', 'dm me', 'message me', 'inbox',
    'advertise', 'promotion', 'promo', 'shill',
]

# Min signal score to alert
MIN_SIGNAL_SCORE = 3

# Owner chat ID for alerts
# Owner chat ID for alerts
OWNER_ID = 158923136

# Import message analyzer
from core.message_analyzer import MessageAnalyzer, MessageAnalysis


@dataclass
class SignalExtract:
    """Extracted signal from a message"""
    text: str
    sender: str
    sender_username: Optional[str]
    chat_id: int
    chat_name: str
    message_id: int
    timestamp: datetime
    token_addresses: List[str]
    dex_links: List[str]
    tg_links: List[str]
    pump_keywords: List[str]
    signal_score: int
    is_forward: bool
    has_media: bool
    message_url: Optional[str]
    analysis: Optional[Any] = None  # MessageAnalysis from message_analyzer


class GroupMonitor:
    """
    Monitors Telegram groups for crypto signals and sends alerts.
    """

    def __init__(self, bot_app=None):
        self.bot_app = bot_app
        self.recent_alerts: List[Tuple[int, str]] = []  # (msg_id, hash) dedupe
        self.alert_count = 0
        self.last_alert_time: Optional[datetime] = None
        self.analyzer = MessageAnalyzer()  # Deep analysis engine

    def _extract_token_addresses(self, text: str) -> List[str]:
        """Extract potential token/contract addresses from text"""
        addresses = []
        # EVM
        evm = re.findall(r'0x[a-fA-F0-9]{40}', text)
        addresses.extend(evm)
        # Solana base58 (44 chars typically)
        sol = re.findall(r'[1-9A-HJ-NP-Za-km-z]{43,44}', text)
        # Filter out common false positives
        sol = [s for s in sol if not re.match(r'^[a-z]+$', s) and len(s) >= 43]
        addresses.extend(sol)
        # TON
        ton = re.findall(r'EQ[A-Za-z0-9_-]{40,48}', text)
        addresses.extend(ton)
        return list(set(addresses))  # dedupe

    def _extract_dex_links(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract DEX links and Telegram links"""
        dex = []
        tg = []
        for pattern in DEX_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if 't.me' in m.lower():
                    tg.append(m)
                else:
                    dex.append(m)
        return list(set(dex)), list(set(tg))

    def _extract_pump_keywords(self, text_lower: str) -> List[str]:
        """Find pump signal keywords"""
        found = []
        for kw in PUMP_KEYWORDS:
            if kw.lower() in text_lower:
                found.append(kw)
        return found

    def _is_noise(self, text_lower: str) -> bool:
        """Check if message is just noise"""
        for kw in NOISE_KEYWORDS:
            if kw.lower() in text_lower:
                # But if it ALSO has a token address or DEX link, keep it
                pass
        # Simple heuristic: very short messages without addresses = noise
        if len(text_lower) < 20 and not re.search(r'0x[a-f0-9]{40}', text_lower):
            return True
        return False

    def _calculate_signal_score(self, extract: SignalExtract) -> int:
        """
        Calculate a signal strength score (0-10)
        Higher = more likely to be a real signal
        """
        score = 0

        # Token address = +3 (most important)
        if extract.token_addresses:
            score += 3
            if len(extract.token_addresses) >= 2:
                score += 1

        # DEX link = +2
        if extract.dex_links:
            score += 2
            if len(extract.dex_links) >= 2:
                score += 1

        # Pump keywords = +1 each (max +3)
        kw_count = len(extract.pump_keywords)
        score += min(kw_count, 3)

        # Has media (chart screenshot) = +1
        if extract.has_media:
            score += 1

        # Forwarded message = +0 (could be spam, could be alpha)
        if extract.is_forward:
            score += 0

        # Longer message with details = +1
        if len(extract.text) > 200:
            score += 1

        return min(score, 10)

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[SignalExtract]:
        """
        Process an incoming group message and extract signals.
        Returns SignalExtract if alert-worthy, None otherwise.
        """
        msg = update.message
        if not msg:
            return None

        chat = msg.chat
        chat_id = chat.id

        # Only monitor configured groups
        if chat_id not in MONITORED_GROUPS:
            return None

        chat_name = MONITORED_GROUPS.get(chat_id, chat.title or "Unknown")

        # Get text content
        text = msg.text or msg.caption or ""
        if not text:
            # Could be image-only with caption handled above
            if not msg.photo and not msg.video:
                return None
            text = "[Media-only message]"

        text_lower = text.lower()

        # Skip noise
        if self._is_noise(text_lower):
            return None

        # Extract features
        sender = msg.from_user.first_name if msg.from_user else "Unknown"
        sender_username = msg.from_user.username if msg.from_user else None

        token_addresses = self._extract_token_addresses(text)
        dex_links, tg_links = self._extract_dex_links(text)
        pump_keywords = self._extract_pump_keywords(text_lower)

        # Build extract
        extract = SignalExtract(
            text=text[:1000],  # truncate
            sender=sender,
            sender_username=sender_username,
            chat_id=chat_id,
            chat_name=chat_name,
            message_id=msg.message_id,
            timestamp=datetime.now(),
            token_addresses=token_addresses,
            dex_links=dex_links,
            tg_links=tg_links,
            pump_keywords=pump_keywords,
            signal_score=0,  # calculated below
            is_forward=bool(msg.forward_date),
            has_media=bool(msg.photo or msg.video or msg.document),
            message_url=f"https://t.me/{chat.username or chat_id}/{msg.message_id}" if chat.username else None,
        )

        extract.signal_score = self._calculate_signal_score(extract)

        # Deep analysis with AI engine
        analysis = self.analyzer.analyze(
            text, sender, sender_username, msg.message_id, chat_name
        )
        extract.analysis = analysis

        # Override signal score with analysis if it recommends action
        if analysis.action_recommendation == 'alert' and extract.signal_score < 5:
            extract.signal_score = 5  # Boost to alert threshold
            logger.info(f"Message {msg.message_id} boosted to alert by analyzer")

        # Check if alert-worthy
        if extract.signal_score >= MIN_SIGNAL_SCORE:
            return extract

        # Also alert if there's a token address + any DEX link regardless of score
        if extract.token_addresses and extract.dex_links:
            return extract

        # Also alert if there's a token address + pump keywords
        if extract.token_addresses and extract.pump_keywords:
            return extract

        return None

    def _format_alert(self, extract: SignalExtract) -> str:
        """Format a signal extract into a clean alert message"""

        # Score emoji
        score_emoji = {
            0: "⚪", 1: "⚪", 2: "🟡", 3: "🟡",
            4: "🟠", 5: "🟠", 6: "🔴", 7: "🔴",
            8: "🚀", 9: "🚀", 10: "💎",
        }.get(extract.signal_score, "🔴")

        # Build alert text
        lines = [
            f"{score_emoji} **SIGNAL ALERT** {score_emoji}",
            f"",
            f"📊 **Score:** {extract.signal_score}/10",
            f"💬 **Group:** {extract.chat_name}",
            f"👤 **From:** {extract.sender}" + (f" (@{extract.sender_username})" if extract.sender_username else ""),
            f"",
        ]

        # Deep Analysis Section
        if extract.analysis:
            a = extract.analysis

            # Sentiment emoji
            sent_emoji = {
                'bullish': '🟢',
                'bearish': '🔴',
                'neutral': '⚪',
                'mixed': '🟡',
            }.get(a.sentiment, '⚪')

            # Intent emoji
            intent_emoji = {
                'signal': '🎯',
                'news': '📰',
                'discussion': '💬',
                'scam_warning': '⚠️',
                'question': '❓',
                'shill': '📢',
                'noise': '🔇',
            }.get(a.intent, '❓')

            lines.append(f"🧠 **AI ANALYSIS** 🧠")
            lines.append(f"   {sent_emoji} **Sentiment:** {a.sentiment} ({a.sentiment_score:+.2f})")
            lines.append(f"   {intent_emoji} **Intent:** {a.intent} ({a.intent_confidence:.0%})")
            lines.append(f"   ⏰ **Urgency:** {a.urgency_score:.0%}")
            lines.append(f"   🛡️ **Scam Risk:** {a.scam_risk:.0%}")
            lines.append(f"   ⭐ **Credibility:** {a.credibility_score:.0%}")
            lines.append(f"")

            # Token symbols from analyzer
            if a.token_symbols:
                lines.append(f"   💰 **Symbols:** ${', $'.join(a.token_symbols[:5])}")
                lines.append(f"")

            # Price targets
            if a.price_targets:
                lines.append(f"   🎯 **Targets:** ${', $'.join(a.price_targets[:3])}")
                lines.append(f"")

            # Market data
            if a.market_cap or a.liquidity:
                data_parts = []
                if a.market_cap:
                    data_parts.append(f"MCap: {a.market_cap}")
                if a.liquidity:
                    data_parts.append(f"Liq: {a.liquidity}")
                lines.append(f"   📊 **{' | '.join(data_parts)}**")
                lines.append(f"")

            # Action recommendation
            action_emoji = {
                'alert': '🚨',
                'investigate': '🔍',
                'warn': '⚠️',
                'ignore': '📝',
            }.get(a.action_recommendation, '❓')
            lines.append(f"   {action_emoji} **Action:** {a.action_recommendation.upper()}")
            lines.append(f"")

            # Summary
            if a.summary:
                lines.append(f"   📝 **Summary:** {a.summary}")
                lines.append(f"")

            # Key points
            if a.key_points:
                lines.append(f"   🔑 **Key Points:**")
                for point in a.key_points[:5]:
                    lines.append(f"      • {point}")
                lines.append(f"")

        # Token addresses
        if extract.token_addresses:
            lines.append("🔑 **Token Addresses:**")
            for addr in extract.token_addresses[:3]:  # max 3
                lines.append(f"  `{addr}`")
            lines.append("")

        # DEX links
        if extract.dex_links:
            lines.append("🔗 **Links:**")
            for link in extract.dex_links[:3]:
                lines.append(f"  • {link}")
            lines.append("")

        # TG links
        if extract.tg_links:
            lines.append("📢 **Telegram:**")
            for link in extract.tg_links[:2]:
                lines.append(f"  • t.me/{link}")
            lines.append("")

        # Keywords
        if extract.pump_keywords:
            lines.append(f"🏷️ **Keywords:** {', '.join(extract.pump_keywords[:5])}")
            lines.append("")

        # Message preview
        preview = extract.text[:300]
        if len(extract.text) > 300:
            preview += "..."
        lines.append(f"📝 **Preview:**\n{preview}")

        # Message link
        if extract.message_url:
            lines.append("")
            lines.append(f"[🔗 Open in Telegram]({extract.message_url})")

        return "\n".join(lines)

    async def send_alert(self, extract: SignalExtract):
        """Send alert to owner via Telegram"""
        if not self.bot_app:
            logger.warning("No bot app configured, cannot send alert")
            return

        alert_text = self._format_alert(extract)

        # Deduplication: hash of addresses + sender + first 50 chars
        dedupe_key = f"{extract.sender}:{','.join(extract.token_addresses)}:{extract.text[:50]}"
        dedupe_hash = hash(dedupe_key) & 0xFFFFFFFF

        # Check recent alerts (keep last 100)
        if any(h == dedupe_hash for _, h in self.recent_alerts):
            logger.info(f"Alert deduplicated: {dedupe_key[:50]}")
            return

        self.recent_alerts.append((extract.message_id, dedupe_hash))
        if len(self.recent_alerts) > 100:
            self.recent_alerts.pop(0)

        try:
            await self.bot_app.bot.send_message(
                chat_id=OWNER_ID,
                text=alert_text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            self.alert_count += 1
            self.last_alert_time = datetime.now()
            logger.info(f"Alert #{self.alert_count} sent for msg {extract.message_id} (score={extract.signal_score})")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def get_stats(self) -> Dict:
        """Return monitoring stats"""
        return {
            "groups_monitored": len(MONITORED_GROUPS),
            "group_names": list(MONITORED_GROUPS.values()),
            "alerts_sent": self.alert_count,
            "last_alert": self.last_alert_time.isoformat() if self.last_alert_time else None,
            "recent_dedupe_cache": len(self.recent_alerts),
        }


# ============== MESSAGE HANDLER ==============

_monitor_instance: Optional[GroupMonitor] = None


def get_monitor(bot_app=None) -> GroupMonitor:
    """Get or create singleton monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = GroupMonitor(bot_app=bot_app)
    elif bot_app is not None:
        _monitor_instance.bot_app = bot_app
    return _monitor_instance


async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram handler for group messages.
    Add this to your bot's handlers.
    """
    monitor = get_monitor()

    # Process message
    signal = await monitor.process_message(update, context)

    if signal:
        await monitor.send_alert(signal)


async def add_group_handler(application):
    """Add the group monitor handler to a telegram application"""
    from telegram.ext import MessageHandler, filters

    monitor = get_monitor(application)

    # Handle all text and media messages in groups
    handler = MessageHandler(
        filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP,
        group_message_handler
    )
    application.add_handler(handler)

    logger.info(f"✅ Group monitor added for {len(MONITORED_GROUPS)} groups")


# ============== CLI TEST ==============
if __name__ == "__main__":
    # Quick test
    monitor = GroupMonitor()

    test_msg = """
    🚀 NEW GEM ALERT! 🚀

    Just found this low cap gem on DexScreener!

    CA: 0x1234567890abcdef1234567890abcdef12345678

    Chart: https://dexscreener.com/solana/0x1234567890abcdef1234567890abcdef12345678

    This is going to 100x! Moon imminent! Load your bags!

    LP burned, dev based, community is growing fast!
    """

    addresses = monitor._extract_token_addresses(test_msg)
    dex, tg = monitor._extract_dex_links(test_msg)
    kw = monitor._extract_pump_keywords(test_msg.lower())

    print(f"Addresses: {addresses}")
    print(f"DEX links: {dex}")
    print(f"Keywords: {kw}")
    print("Monitor module ready!")
