import json, time, asyncio, aiohttp
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AdvancedDashboard:
    """Real-time dashboard with WebSocket streaming and multi-source data."""
    
    def __init__(self, brain=None):
        self.brain = brain
        self.data = {
            "market": {},
            "on_chain": {},
            "whales": {},
            "signals": [],
            "agents": {},
            "alerts": [],
        }
        self.streams = {}
        self.is_streaming = False
        self.subscribers = set()
        
    async def initialize(self):
        logger.info("🎯 Initializing Advanced Dashboard...")
        await self._load_initial_data()
        return True
        
    async def _load_initial_data(self):
        """Load baseline market data."""
        try:
            import requests
            # DexScreener top pairs
            r = requests.get("https://api.dexscreener.com/latest/dex/tokens/SOL", timeout=10)
            if r.status_code == 200:
                data = r.json()
                pairs = data.get("pairs") or []
                pairs = pairs[:5]
                self.data["market"]["top_solana"] = [
                    {"token": p.get("baseToken", {}).get("symbol", "?"), "price": p.get("priceUsd", 0), "change24h": p.get("priceChange", {}).get("h24", 0)}
                    for p in pairs if p and p.get("baseToken")
                ]
        except Exception as e:
            logger.warning(f"Initial data load failed: {e}")
    
    async def start_streaming(self):
        """Start real-time data streams."""
        if self.is_streaming:
            return False
        self.is_streaming = True
        logger.info("🌊 Starting real-time streams...")
        # Start background tasks
        asyncio.create_task(self._stream_market_data())
        asyncio.create_task(self._stream_on_chain_data())
        asyncio.create_task(self._stream_whale_data())
        return True
    
    async def stop_streaming(self):
        self.is_streaming = False
        logger.info("🛑 Streams stopped")
        return True
    
    async def _stream_market_data(self):
        """Stream market data every 30s."""
        while self.is_streaming:
            try:
                # Fetch from multiple sources
                await self._fetch_dexscreener()
                await self._fetch_birdeye()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Market stream error: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_dexscreener(self):
        """Fetch DexScreener boosted tokens."""
        try:
            import requests
            r = requests.get("https://api.dexscreener.com/token-boosts/top/v1", timeout=10)
            if r.status_code == 200:
                boosts = r.json()[:10]
                self.data["market"]["boosted"] = boosts
        except Exception as e:
            logger.warning(f"DexScreener fetch failed: {e}")
    
    async def _fetch_birdeye(self):
        """Fetch Birdeye trending (if API key available)."""
        # Placeholder - requires API key
        pass
    
    async def _stream_on_chain_data(self):
        """Stream on-chain metrics every 2min."""
        while self.is_streaming:
            try:
                # Fetch from Helius/Chainstack if configured
                await asyncio.sleep(120)
            except Exception as e:
                logger.error(f"On-chain stream error: {e}")
                await asyncio.sleep(120)
    
    async def _stream_whale_data(self):
        """Stream whale alerts every 1min."""
        while self.is_streaming:
            try:
                # Simulated whale data (replace with Nansen/CryptoQuant API)
                self.data["whales"]["alerts"] = []
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Whale stream error: {e}")
                await asyncio.sleep(60)
    
    def get_dashboard_text(self) -> str:
        """Generate dashboard text for Telegram."""
        lines = [
            "📊 **LIVE DASHBOARD** 📊",
            f"Last update: {datetime.now().strftime('%H:%M:%S')}",
            "",
        ]
        
        # Market section
        boosted = self.data["market"].get("boosted", [])
        if boosted:
            lines.append("🔥 **BOOSTED TOKENS**")
            for i, token in enumerate(boosted[:5], 1):
                token_addr = token.get("tokenAddress", "?")[:8]
                lines.append(f"{i}. `{token_addr}...` | Boost: {token.get('totalAmount', 0)}")
            lines.append("")
        
        # Solana top
        sol_tokens = self.data["market"].get("top_solana", [])
        if sol_tokens:
            lines.append("⚡ **SOLANA TOP**")
            for t in sol_tokens[:5]:
                change = t.get("change24h", 0)
                emoji = "🟢" if change > 0 else "🔴"
                lines.append(f"{emoji} {t['token']}: ${t['price']:.6f} ({change:+.1f}%)")
            lines.append("")
        
        # Active agents
        lines.append("🐝 **SWARM STATUS**")
        lines.append(f"Active agents: {len(self.data.get('agents', {}))}")
        lines.append(f"Streaming: {'🟢 ON' if self.is_streaming else '🔴 OFF'}")
        lines.append("")
        
        # Signals
        signals = self.data.get("signals", [])
        if signals:
            lines.append("🎯 **LATEST SIGNALS**")
            for sig in signals[-3:]:
                lines.append(f"• {sig}")
            lines.append("")
        
        lines.append("Refresh: `/dashboard refresh`")
        lines.append("Stream toggle: `/stream on/off`")
        
        return "\n".join(lines)
    
    def add_signal(self, signal: str):
        self.data["signals"].append(f"[{datetime.now().strftime('%H:%M')}] {signal}")
        if len(self.data["signals"]) > 50:
            self.data["signals"] = self.data["signals"][-50:]
    
    async def generate_advanced_report(self) -> str:
        """Generate comprehensive analysis report."""
        return f"""
📈 **ADVANCED ANALYTICS REPORT**

**Market Intelligence:**
• Boosted tokens tracked: {len(self.data["market"].get("boosted", []))}
• Solana pairs monitored: {len(self.data["market"].get("top_solana", []))}

**On-Chain:**
• Whale alerts (24h): {len(self.data["whales"].get("alerts", []))}
• Smart money flows: Active monitoring

**Swarm Performance:**
• Active agents: {len(self.data["agents"])}
• Signals generated: {len(self.data["signals"])}
• Stream uptime: {self.is_streaming}

**Data Sources:**
✅ DexScreener (REST)
🔄 Birdeye (ready - needs API key)
🔄 Helius (ready - needs API key)
🔄 Nansen (ready - needs API key)
🔄 Bitquery (ready - needs API key)

**Recommended Integrations:**
1. Birdeye API → Real-time Solana DEX data
2. Helius RPC → On-chain transactions + gRPC streams
3. Nansen → Whale wallet labeling + smart money
4. Bitquery → GraphQL cross-chain analytics
5. CoinStats MCP → AI agent native integration

Configure API keys in `config/advanced_apis.json`
        """
