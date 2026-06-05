"""
Airdrop Agent - Automated Airdrop Farming & Hunting
====================================================
Discovers, tracks, and farms airdrops across ecosystems.
Monitors eligibility, tracks farming progress, and alerts on new opportunities.

Features:
- Scans for active and upcoming airdrops
- Tracks user farming progress per protocol
- Checks eligibility criteria (volume, txs, time, TVL)
- Estimates airdrop value / farming ROI
- Alerts on snapshot dates and claim windows
- Maintains airdrop watchlist

Author: AImind (OpenClaw)
"""
import os
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Airdrop data directory
AIRDROP_DIR = Path("/root/.openclaw/workspace/orchestrator/data/airdrops")
AIRDROP_DIR.mkdir(parents=True, exist_ok=True)

WATCHLIST_FILE = AIRDROP_DIR / "watchlist.json"
FARMING_FILE = AIRDROP_DIR / "farming.json"
ELIGIBILITY_FILE = AIRDROP_DIR / "eligibility.json"


@dataclass
class Airdrop:
    """Represents a single airdrop opportunity."""
    name: str
    protocol: str
    chain: str
    status: str  # upcoming | active | claimable | ended
    tge_date: Optional[str] = None
    snapshot_date: Optional[str] = None
    criteria: List[str] = field(default_factory=list)
    estimated_value: Optional[str] = None
    farming_apr: Optional[float] = None
    difficulty: str = "medium"  # easy | medium | hard
    url: Optional[str] = None
    twitter: Optional[str] = None
    discord: Optional[str] = None
    notes: Optional[str] = None
    added_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FarmingTask:
    """Tracks farming progress for a specific airdrop."""
    airdrop_name: str
    protocol: str
    chain: str
    tasks: Dict[str, bool] = field(default_factory=dict)
    volume_usd: float = 0.0
    tx_count: int = 0
    days_active: int = 0
    tvl_contributed: float = 0.0
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    status: str = "active"  # active | paused | completed
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EligibilityCheck:
    """Stores eligibility check result."""
    airdrop_name: str
    protocol: str
    eligible: bool = False
    confidence: float = 0.0
    meets_criteria: Dict[str, bool] = field(default_factory=dict)
    missing_criteria: List[str] = field(default_factory=list)
    estimated_drop: Optional[str] = None
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    wallet_address: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class AirdropAgent:
    """
    Intelligent airdrop farming agent.
    Scans, tracks, and optimizes airdrop farming across chains.
    """

    def __init__(self):
        self.watchlist: List[Airdrop] = []
        self.farming_tasks: Dict[str, FarmingTask] = {}
        self.eligibility_checks: Dict[str, EligibilityCheck] = {}
        self._load_data()

    def _load_data(self):
        """Load persisted data."""
        if WATCHLIST_FILE.exists():
            try:
                with open(WATCHLIST_FILE, 'r') as f:
                    data = json.load(f)
                    self.watchlist = [Airdrop(**item) for item in data]
            except Exception:
                self.watchlist = []

        if FARMING_FILE.exists():
            try:
                with open(FARMING_FILE, 'r') as f:
                    data = json.load(f)
                    self.farming_tasks = {
                        k: FarmingTask(**v) for k, v in data.items()
                    }
            except Exception:
                self.farming_tasks = {}

        if ELIGIBILITY_FILE.exists():
            try:
                with open(ELIGIBILITY_FILE, 'r') as f:
                    data = json.load(f)
                    self.eligibility_checks = {
                        k: EligibilityCheck(**v) for k, v in data.items()
                    }
            except Exception:
                self.eligibility_checks = {}

    def _save_watchlist(self):
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump([a.to_dict() for a in self.watchlist], f, indent=2)

    def _save_farming(self):
        with open(FARMING_FILE, 'w') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.farming_tasks.items()},
                f, indent=2
            )

    def _save_eligibility(self):
        with open(ELIGIBILITY_FILE, 'w') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.eligibility_checks.items()},
                f, indent=2
            )

    # ═══════════════════════════════════════════════════════════
    # WATCHLIST MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def add_airdrop(self, **kwargs) -> Airdrop:
        """Add an airdrop to the watchlist."""
        airdrop = Airdrop(**kwargs)
        # Remove duplicate if exists
        self.watchlist = [
            a for a in self.watchlist
            if a.name.lower() != airdrop.name.lower()
        ]
        self.watchlist.append(airdrop)
        self._save_watchlist()
        return airdrop

    def remove_airdrop(self, name: str) -> bool:
        """Remove an airdrop from watchlist."""
        original_len = len(self.watchlist)
        self.watchlist = [
            a for a in self.watchlist
            if a.name.lower() != name.lower()
        ]
        if len(self.watchlist) < original_len:
            self._save_watchlist()
            return True
        return False

    def get_watchlist(self, status: Optional[str] = None, chain: Optional[str] = None) -> List[Airdrop]:
        """Get filtered watchlist."""
        results = self.watchlist
        if status:
            results = [a for a in results if a.status == status]
        if chain:
            results = [a for a in results if a.chain.lower() == chain.lower()]
        return sorted(results, key=lambda x: x.added_at, reverse=True)

    def get_airdrop(self, name: str) -> Optional[Airdrop]:
        """Get a specific airdrop by name."""
        for a in self.watchlist:
            if a.name.lower() == name.lower():
                return a
        return None

    # ═══════════════════════════════════════════════════════════
    # FARMING TASKS
    # ═══════════════════════════════════════════════════════════

    def start_farming(self, airdrop_name: str, wallet_address: Optional[str] = None) -> FarmingTask:
        """Start tracking farming for an airdrop."""
        airdrop = self.get_airdrop(airdrop_name)
        if not airdrop:
            raise ValueError(f"Airdrop '{airdrop_name}' not found in watchlist")

        key = f"{airdrop_name.lower()}_{wallet_address or 'default'}"
        task = FarmingTask(
            airdrop_name=airdrop.name,
            protocol=airdrop.protocol,
            chain=airdrop.chain,
            started_at=datetime.utcnow().isoformat(),
            last_activity=datetime.utcnow().isoformat(),
            status="active",
        )
        # Pre-populate criteria as tasks
        if airdrop.criteria:
            for criterion in airdrop.criteria:
                task.tasks[criterion] = False

        self.farming_tasks[key] = task
        self._save_farming()
        return task

    def update_farming_task(self, airdrop_name: str, task_name: str, completed: bool = True,
                           wallet_address: Optional[str] = None, **metrics) -> Optional[FarmingTask]:
        """Update a farming task's completion status."""
        key = f"{airdrop_name.lower()}_{wallet_address or 'default'}"
        task = self.farming_tasks.get(key)
        if not task:
            return None

        task.tasks[task_name] = completed
        task.last_activity = datetime.utcnow().isoformat()

        # Update metrics if provided
        for metric, value in metrics.items():
            if hasattr(task, metric):
                setattr(task, metric, value)

        self._save_farming()
        return task

    def get_farming_status(self, airdrop_name: Optional[str] = None,
                           wallet_address: Optional[str] = None) -> List[FarmingTask]:
        """Get farming status."""
        if airdrop_name and wallet_address:
            key = f"{airdrop_name.lower()}_{wallet_address}"
            task = self.farming_tasks.get(key)
            return [task] if task else []
        elif airdrop_name:
            return [
                t for t in self.farming_tasks.values()
                if t.airdrop_name.lower() == airdrop_name.lower()
            ]
        else:
            return list(self.farming_tasks.values())

    # ═══════════════════════════════════════════════════════════
    # ELIGIBILITY CHECKING
    # ═══════════════════════════════════════════════════════════

    def check_eligibility(self, airdrop_name: str, wallet_address: str,
                          metrics: Dict[str, Any]) -> EligibilityCheck:
        """
        Check eligibility for an airdrop based on provided metrics.
        Metrics should include things like: volume_usd, tx_count, days_active, tvl_contributed
        """
        airdrop = self.get_airdrop(airdrop_name)
        if not airdrop:
            raise ValueError(f"Airdrop '{airdrop_name}' not found")

        check = EligibilityCheck(
            airdrop_name=airdrop.name,
            protocol=airdrop.protocol,
            wallet_address=wallet_address,
        )

        # Evaluate each criterion
        meets = {}
        missing = []
        confidence_points = 0
        total_criteria = len(airdrop.criteria) if airdrop.criteria else 1

        for criterion in (airdrop.criteria or []):
            criterion_lower = criterion.lower()
            met = False

            # Volume-based criteria
            if "volume" in criterion_lower or "$" in criterion:
                required_vol = self._extract_number(criterion)
                actual_vol = metrics.get("volume_usd", 0)
                met = actual_vol >= required_vol if required_vol else actual_vol > 0
                meets[criterion] = met

            # Transaction count criteria
            elif "transaction" in criterion_lower or "tx" in criterion_lower or "swap" in criterion_lower:
                required_txs = self._extract_number(criterion)
                actual_txs = metrics.get("tx_count", 0)
                met = actual_txs >= required_txs if required_txs else actual_txs > 0
                meets[criterion] = met

            # Time-based criteria
            elif "day" in criterion_lower or "week" in criterion_lower or "month" in criterion_lower:
                required_days = self._extract_number(criterion)
                actual_days = metrics.get("days_active", 0)
                met = actual_days >= required_days if required_days else actual_days > 0
                meets[criterion] = met

            # TVL/deposit criteria
            elif "tvl" in criterion_lower or "deposit" in criterion_lower or "liquidity" in criterion_lower:
                required_tvl = self._extract_number(criterion)
                actual_tvl = metrics.get("tvl_contributed", 0)
                met = actual_tvl >= required_tvl if required_tvl else actual_tvl > 0
                meets[criterion] = met

            # Social/bridge criteria (assume true if mentioned in metrics)
            elif any(k in criterion_lower for k in ["follow", "discord", "twitter", "x", "retweet", "bridge"]):
                met = metrics.get(f"social_{criterion_lower.replace(' ', '_')}", False)
                meets[criterion] = met

            else:
                # Generic criteria — flag for manual review
                meets[criterion] = metrics.get("manual_verified", False)

            if met:
                confidence_points += 1
            else:
                missing.append(criterion)

        check.meets_criteria = meets
        check.missing_criteria = missing
        check.confidence = (confidence_points / total_criteria * 100) if total_criteria else 0
        check.eligible = check.confidence >= 70  # 70% threshold

        # Estimate drop value
        if check.eligible and airdrop.estimated_value:
            check.estimated_drop = airdrop.estimated_value

        self.eligibility_checks[f"{airdrop_name.lower()}_{wallet_address}"] = check
        self._save_eligibility()
        return check

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract a number from text (handles K, M, $ formatting)."""
        import re
        # Find numbers with optional K/M suffix
        match = re.search(r'[\$]?([0-9,.]+)\s*(K|M|k|m)?', text)
        if match:
            num_str = match.group(1).replace(',', '')
            num = float(num_str)
            suffix = match.group(2)
            if suffix and suffix.upper() == 'K':
                num *= 1_000
            elif suffix and suffix.upper() == 'M':
                num *= 1_000_000
            return num
        return None

    # ═══════════════════════════════════════════════════════════
    # AUTO-DISCOVERY
    # ═══════════════════════════════════════════════════════════

    async def discover_airdrops(self) -> List[Airdrop]:
        """
        Scrape and discover active airdrops from known sources.
        Returns list of newly discovered airdrops.
        """
        discovered = []

        # Try airdrops.io API / scraping
        try:
            async with aiohttp.ClientSession() as session:
                # Check airdrops.io listing
                async with session.get(
                    "https://airdrops.io",
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Basic parsing would go here
                        pass
        except Exception as e:
            pass  # Fail silently, we'll use built-in data

        # Also check dropsearn
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://dropsearn.com/airdrops/",
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status == 200:
                        pass
        except Exception:
            pass

        # Return any newly found (for now, we seed with known ones)
        return discovered

    def seed_known_airdrops(self) -> List[Airdrop]:
        """Seed watchlist with currently known high-value airdrops."""
        discovered = []  # FIX: Initialize discovered list
        known = [
            Airdrop(
                name="Kamino",
                protocol="Kamino",
                chain="solana",
                status="active",
                criteria=[
                    "Deposit USDC or SOL into Kamino vaults",
                    "Maintain deposits for 30+ days",
                    "Use leverage features",
                    "Provide liquidity to Kamino pools"
                ],
                estimated_value="$300-$2000",
                difficulty="medium",
                url="https://kamino.finance",
                twitter="https://twitter.com/KaminoFinance"
            ),
            Airdrop(
                name="MetaMask $MASK",
                protocol="MetaMask",
                chain="multi",
                status="upcoming",
                criteria=[
                    "Use MetaMask as primary wallet",
                    "Perform regular swaps via MetaMask",
                    "Bridge assets using MetaMask bridges",
                    "Hold assets in MetaMask for 90+ days",
                    "Use MetaMask on multiple chains"
                ],
                estimated_value="$200-$2000",
                difficulty="easy",
                url="https://metamask.io",
                twitter="https://twitter.com/MetaMask"
            ),
            Airdrop(
                name="Hyperliquid Season 2",
                protocol="Hyperliquid",
                chain="hyperliquid",
                status="active",
                criteria=[
                    "Generate trading volume on Hyperliquid",
                    "10+ trades per week",
                    "Maintain positions for 30+ days",
                    "Use Hyperliquid vaults",
                    "Referral activity"
                ],
                estimated_value="$300-$3000",
                difficulty="medium",
                url="https://hyperliquid.xyz",
                twitter="https://twitter.com/HyperliquidX"
            ),
            Airdrop(
                name="Rainbow Wallet",
                protocol="Rainbow",
                chain="ethereum",
                status="upcoming",
                criteria=[
                    "Use Rainbow as primary wallet",
                    "Perform swaps via Rainbow",
                    "Hold referral points",
                    "Active for 60+ days",
                    "Bridge using Rainbow"
                ],
                estimated_value="$100-$1000",
                difficulty="easy",
                url="https://rainbow.me",
                twitter="https://twitter.com/rainbowdotme"
            ),
            Airdrop(
                name="Monad Testnet",
                protocol="Monad",
                chain="monad",
                status="upcoming",
                criteria=[
                    "Join testnet",
                    "Run validator or full node",
                    "Participate in devnet activities",
                    "Community engagement"
                ],
                estimated_value="TBD (High potential)",
                difficulty="hard",
                url="https://monad.xyz",
                twitter="https://twitter.com/monad_xyz"
            ),
            Airdrop(
                name="Scroll Marks",
                protocol="Scroll",
                chain="ethereum",
                status="active",
                criteria=[
                    "Bridge to Scroll",
                    "10+ transactions",
                    "Interact with Scroll-native dApps",
                    "Maintain balance for 30+ days"
                ],
                estimated_value="$300-$1500",
                difficulty="easy",
                url="https://scroll.io",
                twitter="https://twitter.com/Scroll_ZKP"
            ),
            Airdrop(
                name="LayerZero ZRO",
                protocol="LayerZero",
                chain="multi",
                status="claimable",
                tge_date="2024-06-20",
                criteria=[
                    "Bridge via Stargate",
                    "Use LayerZero dApps across chains",
                    "Minimum $1000 volume",
                    "Active for 60+ days"
                ],
                estimated_value="$200-$5000",
                difficulty="medium",
                url="https://layerzero.network",
                twitter="https://twitter.com/LayerZero_Labs"
            ),
            Airdrop(
                name="Monad",
                protocol="Monad",
                chain="monad",
                status="upcoming",
                criteria=[
                    "Join testnet",
                    "Run validator or full node",
                    "Participate in devnet activities",
                    "Community engagement"
                ],
                estimated_value="TBD (High potential)",
                difficulty="hard",
                url="https://monad.xyz",
                twitter="https://twitter.com/monad_xyz"
            ),
            Airdrop(
                name="Berachain BERA",
                protocol="Berachain",
                chain="berachain",
                status="active",
                criteria=[
                    "Bridge to Berachain testnet",
                    "Use BEX DEX",
                    "Provide liquidity",
                    "Mint NFTs on Berachain",
                    "30+ days activity"
                ],
                estimated_value="$1000-$5000",
                difficulty="medium",
                url="https://berachain.com",
                twitter="https://twitter.com/berachain"
            ),
            Airdrop(
                name="EigenLayer EIGEN",
                protocol="EigenLayer",
                chain="ethereum",
                status="claimable",
                tge_date="2024-05-10",
                criteria=[
                    "Restake ETH via EigenLayer",
                    "Delegate to operators",
                    "Participate in AVSs",
                    "Hold stETH, rETH, or cbETH"
                ],
                estimated_value="$100-$3000",
                difficulty="easy",
                url="https://eigenlayer.xyz",
                twitter="https://twitter.com/eigenlayer"
            ),
            Airdrop(
                name="Celestia TIA",
                protocol="Celestia",
                chain="celestia",
                status="claimable",
                tge_date="2023-10-31",
                criteria=[
                    "Run light node",
                    "Participate in testnets",
                    "Developer activity on modular stack"
                ],
                estimated_value="$500-$2000",
                difficulty="hard",
                url="https://celestia.org",
                twitter="https://twitter.com/CelestiaOrg"
            ),
            Airdrop(
                name="Hyperlane",
                protocol="Hyperlane",
                chain="multi",
                status="active",
                criteria=[
                    "Bridge via Hyperlane",
                    "Warp route usage",
                    "Deploy interchain apps",
                    "1000+ volume across chains"
                ],
                estimated_value="$200-$1000",
                difficulty="medium",
                url="https://hyperlane.xyz",
                twitter="https://twitter.com/Hyperlane_xyz"
            ),
            Airdrop(
                name="Swell L2",
                protocol="Swell",
                chain="ethereum",
                status="upcoming",
                criteria=[
                    "Stake ETH via Swell",
                    "Hold swETH",
                    "Participate in pre-launch campaign",
                    "Referral activity"
                ],
                estimated_value="$300-$2000",
                difficulty="easy",
                url="https://swellnetwork.io",
                twitter="https://twitter.com/swellnetworkio"
            ),
            Airdrop(
                name="Karak",
                protocol="Karak",
                chain="multi",
                status="active",
                criteria=[
                    "Restake assets",
                    "Run DSS",
                    "50+ days restaked",
                    "Minimum $500 TVL"
                ],
                estimated_value="$200-$1500",
                difficulty="medium",
                url="https://karak.network",
                twitter="https://twitter.com/Karak_Network"
            ),
        ]

        # Add only new ones
        existing_names = {a.name.lower() for a in self.watchlist}
        for airdrop in known:
            if airdrop.name.lower() not in existing_names:
                self.watchlist.append(airdrop)
                discovered.append(airdrop)

        self._save_watchlist()
        return discovered

    # ═══════════════════════════════════════════════════════════
    # FORMATTING FOR TELEGRAM
    # ═══════════════════════════════════════════════════════════

    def format_watchlist(self, airdrops: List[Airdrop]) -> str:
        """Format watchlist for Telegram display."""
        if not airdrops:
            return "🪂 **No airdrops in watchlist.**\nUse `/airdrop add <name>` to add one!"

        lines = ["🪂 **AIRDROPS WATCHLIST** 🪂\n"]

        for a in airdrops:
            status_emoji = {
                "upcoming": "⏳",
                "active": "🔥",
                "claimable": "💰",
                "ended": "🏁"
            }.get(a.status, "❓")

            diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(a.difficulty, "⚪")

            lines.append(
                f"{status_emoji} **{a.name}** ({a.protocol})\n"
                f"   Chain: `{a.chain}` | Difficulty: {diff_emoji}\n"
                f"   Status: `{a.status.upper()}`\n"
                f"   Est. Value: `{a.estimated_value or 'N/A'}`\n"
            )
            if a.criteria:
                lines.append(f"   Criteria: {len(a.criteria)} requirements")
            if a.tge_date:
                lines.append(f"   TGE: `{a.tge_date}`")
            if a.snapshot_date:
                lines.append(f"   📸 Snapshot: `{a.snapshot_date}` ⚠️")
            lines.append("")

        return "\n".join(lines)

    def format_farming_status(self, tasks: List[FarmingTask]) -> str:
        """Format farming progress for Telegram."""
        if not tasks:
            return "🚜 **No active farming.**\nStart with `/farming start <airdrop>`"

        lines = ["🚜 **FARMING PROGRESS** 🚜\n"]

        for t in tasks:
            total = len(t.tasks)
            done = sum(1 for v in t.tasks.values() if v)
            pct = (done / total * 100) if total else 0

            # Progress bar
            filled = int(pct / 10)
            bar = "█" * filled + "░" * (10 - filled)

            lines.append(
                f"**{t.airdrop_name}** ({t.chain})\n"
                f"`[{bar}]` {done}/{total} tasks ({pct:.0f}%)\n"
                f"Volume: `${t.volume_usd:,.0f}` | Txs: `{t.tx_count}` | Days: `{t.days_active}`\n"
                f"Status: `{t.status.upper()}`\n"
            )

        return "\n".join(lines)

    def format_eligibility(self, check: EligibilityCheck) -> str:
        """Format eligibility check for Telegram."""
        emoji = "✅" if check.eligible else "❌"
        conf_bar = "█" * int(check.confidence / 10) + "░" * (10 - int(check.confidence / 10))

        lines = [
            f"{emoji} **ELIGIBILITY: {check.airdrop_name}**\n",
            f"Wallet: `{check.wallet_address or 'N/A'}`",
            f"Result: **`{'ELIGIBLE' if check.eligible else 'NOT ELIGIBLE'}`**",
            f"Confidence: `{conf_bar}` {check.confidence:.0f}%\n",
        ]

        if check.meets_criteria:
            lines.append("**✓ Met Criteria:**")
            for criterion, met in check.meets_criteria.items():
                lines.append(f"  {'✅' if met else '❌'} {criterion}")

        if check.missing_criteria:
            lines.append("\n**⚠️ Missing:**")
            for m in check.missing_criteria:
                lines.append(f"  • {m}")

        if check.estimated_drop:
            lines.append(f"\n💰 **Estimated Drop:** `{check.estimated_drop}`")

        return "\n".join(lines)

    def format_summary(self) -> str:
        """Overall airdrop summary."""
        total = len(self.watchlist)
        by_status = {}
        for a in self.watchlist:
            by_status[a.status] = by_status.get(a.status, 0) + 1

        active_farms = len([t for t in self.farming_tasks.values() if t.status == "active"])
        eligible = len([c for c in self.eligibility_checks.values() if c.eligible])

        return (
            f"🪂 **AIRDROP DASHBOARD** 🪂\n\n"
            f"📋 Watchlist: `{total}` airdrops\n"
            f"  🔥 Active: `{by_status.get('active', 0)}`\n"
            f"  ⏳ Upcoming: `{by_status.get('upcoming', 0)}`\n"
            f"  💰 Claimable: `{by_status.get('claimable', 0)}`\n"
            f"  🏁 Ended: `{by_status.get('ended', 0)}`\n\n"
            f"🚜 Active Farming: `{active_farms}`\n"
            f"✅ Eligible Checks: `{eligible}`\n\n"
            f"Commands:\n"
            f"  `/airdrops` — View watchlist\n"
            f"  `/farming` — Check progress\n"
            f"  `/check <airdrop>` — Check eligibility\n"
            f"  `/farm_start <airdrop>` — Start farming"
        )


# ═══════════════════════════════════════════════════════════════
# Singleton factory
# ═══════════════════════════════════════════════════════════════
_agent_instance: Optional[AirdropAgent] = None


async def get_airdrop_agent() -> AirdropAgent:
    """Get or create the airdrop agent singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AirdropAgent()
        # Seed with known airdrops on first run
        if not _agent_instance.watchlist:
            _agent_instance.seed_known_airdrops()
    return _agent_instance
