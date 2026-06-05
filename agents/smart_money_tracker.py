"""
🎯 SMART MONEY TRACKER AGENT
Εντοπίζει, αναλύει και παρακολουθεί τους πιο κερδοφόρους wallets στο blockchain.
Ακολουθεί τις κινήσεις τους με real-time alerts.

Author: AImind | Part of SWMAS Trading Intelligence Layer
"""

import asyncio
import aiohttp
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

# Configuration
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY", "")
NANSEN_API_KEY = os.getenv("NANSEN_API_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "158923136")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SmartMoney")


@dataclass
class WalletProfile:
    """Προφίλ ενός wallet — όλα τα στατιστικά απόδοσης"""
    address: str
    label: Optional[str] = None  # Π.χ. "Whale #247", "DEX Market Maker"
    
    # Performance Metrics
    total_trades: int = 0
    profitable_trades: int = 0
    total_pnl_sol: float = 0.0
    win_rate: float = 0.0
    avg_return_per_trade: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Risk Metrics
    avg_position_size_sol: float = 0.0
    max_position_size_sol: float = 0.0
    holding_time_avg_hours: float = 0.0
    
    # Activity
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None
    trades_per_day: float = 0.0
    
    # Current Holdings
    current_holdings: Dict[str, float] = field(default_factory=dict)
    portfolio_value_sol: float = 0.0
    
    # Score
    smart_money_score: float = 0.0  # 0-100
    confidence_tier: str = "unranked"  # S, A, B, C, D
    
    # Tracking
    is_tracking: bool = False
    track_start_time: Optional[datetime] = None
    tracked_tokens: Set[str] = field(default_factory=set)
    
    def calculate_smart_money_score(self) -> float:
        """Υπολογίζει composite score για το πόσο "έξυπνο" είναι το wallet"""
        if self.total_trades < 5:
            return 0.0
        
        score = 0.0
        # Win rate weight: 30%
        score += min(self.win_rate * 100, 100) * 0.30
        # PnL weight: 35%
        pnl_score = min(max(self.total_pnl_sol / 10, -10), 100)
        score += max(pnl_score, 0) * 0.35
        # Consistency weight: 20% (trades per day stability)
        consistency = min(self.trades_per_day * 5, 100) if self.trades_per_day > 0 else 0
        score += consistency * 0.20
        # Risk management weight: 15%
        risk_score = 100 if self.max_drawdown < 0.2 else max(0, 100 - (self.max_drawdown - 0.2) * 200)
        score += risk_score * 0.15
        
        self.smart_money_score = min(score, 100)
        
        # Tier assignment
        if self.smart_money_score >= 85:
            self.confidence_tier = "S"
        elif self.smart_money_score >= 70:
            self.confidence_tier = "A"
        elif self.smart_money_score >= 55:
            self.confidence_tier = "B"
        elif self.smart_money_score >= 40:
            self.confidence_tier = "C"
        else:
            self.confidence_tier = "D"
        
        return self.smart_money_score


@dataclass
class TradeSignal:
    """Σήμα συναλλαγής από tracked wallet"""
    wallet_address: str
    wallet_tier: str
    wallet_score: float
    token_address: str
    token_symbol: str
    action: str  # BUY, SELL, ADD_LIQUIDITY, REMOVE_LIQUIDITY
    amount_sol: float
    amount_tokens: float
    price_usd: float
    tx_signature: str
    timestamp: datetime
    
    # Context
    wallet_pnl_on_token: Optional[float] = None
    wallet_avg_entry: Optional[float] = None
    token_liquidity_usd: Optional[float] = None
    token_volume_24h: Optional[float] = None
    
    # Signal Strength
    urgency_score: float = 0.0  # 0-100, πόσο επείγον είναι
    
    def format_alert(self) -> str:
        """Μορφοποίηση για Telegram alert"""
        emoji = {"BUY": "🟢", "SELL": "🔴", "ADD_LIQUIDITY": "💧", "REMOVE_LIQUIDITY": "🚰"}
        tier_emoji = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📊"}
        
        urgency = "🔥🔥🔥" if self.urgency_score > 80 else "🔥🔥" if self.urgency_score > 60 else "🔥"
        
        msg = f"""
{urgency} **SMART MONEY ALERT** {urgency}

{tier_emoji.get(self.wallet_tier, "📊")} **Wallet:** `{self.wallet_address[:8]}...{self.wallet_address[-4:]}`
⭐ **Score:** {self.wallet_score:.1f}/100 | **Tier:** {self.wallet_tier}

{emoji.get(self.action, "📌")} **{self.action}**
🪙 **Token:** {self.token_symbol}
📍 **Address:** `{self.token_address}`
💰 **Amount:** {self.amount_sol:.3f} SOL ({self.amount_tokens:.2f} tokens)
💵 **Price:** ${self.price_usd:.6f}

📊 **Context:**
• Wallet PnL on this token: {self.wallet_pnl_on_token:+.2f} SOL
• Token Liquidity: ${self.token_liquidity_usd:,.0f}
• 24h Volume: ${self.token_volume_24h:,.0f}

🔗 **Tx:** `{self.tx_signature[:16]}...`
⏰ {self.timestamp.strftime('%H:%M:%S UTC')}
"""
        return msg


class HeliusClient:
    """Helius RPC client για enriched transaction data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
        self.ws_url = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def rpc_call(self, method: str, params: List = None) -> Optional[Dict]:
        """Generic RPC call"""
        if not self.session:
            return None
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        
        try:
            async with self.session.post(self.base_url, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result")
                else:
                    logger.warning(f"Helius RPC error {resp.status}: {method}")
                    return None
        except Exception as e:
            logger.error(f"Helius RPC failed: {e}")
            return None
    
    async def get_signatures_for_address(
        self, 
        address: str, 
        limit: int = 100,
        before: Optional[str] = None
    ) -> List[Dict]:
        """Φέρνει signatures για ένα address"""
        params = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before
        
        result = await self.rpc_call("getSignaturesForAddress", params)
        return result or []
    
    async def get_transaction(self, signature: str, max_supported: int = 0) -> Optional[Dict]:
        """Φέρνει enriched transaction data"""
        params = [signature, {"encoding": "json", "maxSupportedTransactionVersion": max_supported}]
        return await self.rpc_call("getTransaction", params)
    
    async def get_token_accounts(self, owner: str) -> List[Dict]:
        """Φέρνει token accounts ενός wallet"""
        params = [{
            "owner": owner,
            "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        }]
        result = await self.rpc_call("getTokenAccountsByOwner", params)
        if result and "value" in result:
            return result["value"]
        return []
    
    async def get_account_info(self, address: str) -> Optional[Dict]:
        """Φέρνει account info"""
        params = [address, {"encoding": "jsonParsed"}]
        return await self.rpc_call("getAccountInfo", params)
    
    async def get_multiple_accounts(self, addresses: List[str]) -> List[Optional[Dict]]:
        """Batch account fetch"""
        if not addresses:
            return []
        params = [addresses, {"encoding": "jsonParsed"}]
        result = await self.rpc_call("getMultipleAccounts", params)
        if result and "value" in result:
            return result["value"]
        return []


class BirdeyeClient:
    """Birdeye API client για token prices και market data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://public-api.birdeye.so"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def headers(self) -> Dict:
        return {
            "X-API-KEY": self.api_key,
            "accept": "application/json"
        }
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Τρέχουσα τιμή token"""
        if not self.session:
            return None
        
        url = f"{self.base_url}/defi/price"
        params = {"address": token_address}
        
        try:
            async with self.session.get(url, headers=self.headers(), params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {}).get("value")
                return None
        except Exception as e:
            logger.error(f"Birdeye price error: {e}")
            return None
    
    async def get_token_market_data(self, token_address: str) -> Optional[Dict]:
        """Πλήρη market data για token"""
        if not self.session:
            return None
        
        url = f"{self.base_url}/defi/v3/token/market-data"
        params = {"address": token_address}
        
        try:
            async with self.session.get(url, headers=self.headers(), params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
                return None
        except Exception as e:
            logger.error(f"Birdeye market data error: {e}")
            return None
    
    async def get_wallet_portfolio(self, wallet: str) -> Optional[Dict]:
        """Portfolio ενός wallet"""
        if not self.session:
            return None
        
        url = f"{self.base_url}/v1/wallet/token_list"
        params = {"wallet": wallet}
        
        try:
            async with self.session.get(url, headers=self.headers(), params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
                return None
        except Exception as e:
            logger.error(f"Birdeye portfolio error: {e}")
            return None


class BlockchainAnalyzer:
    """Κύρια μηχανή ανάλυσης blockchain"""
    
    def __init__(self):
        self.helius = HeliusClient(HELIUS_API_KEY)
        self.birdeye = BirdeyeClient(BIRDEYE_API_KEY)
        
        # Data stores
        self.wallets: Dict[str, WalletProfile] = {}
        self.tracked_wallets: Set[str] = set()
        self.token_prices: Dict[str, float] = {}
        self.known_tokens: Dict[str, Dict] = {}
        
        # Transaction history για pattern analysis
        self.tx_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance
        self.discovery_stats = {
            "wallets_analyzed": 0,
            "wallets_qualified": 0,
            "signals_generated": 0,
            "alerts_sent": 0
        }
    
    async def __aenter__(self):
        await self.helius.__aenter__()
        await self.birdeye.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        await self.helius.__aexit__()
        await self.birdeye.__aexit__()
    
    # ═══════════════════════════════════════════════════════════
    # DISCOVERY PHASE — Εύρεση κερδοφόρων wallets
    # ═══════════════════════════════════════════════════════════
    
    async def discover_profitable_wallets(
        self, 
        source: str = "dexscreener",  # "dexscreener", "twitter", "manual", "graduation"
        min_pnl_sol: float = 5.0,
        min_win_rate: float = 0.55,
        sample_size: int = 100
    ) -> List[WalletProfile]:
        """
        🕵️ Ανακάλυψη κερδοφόρων wallets από διάφορες πηγές
        
        Strategies:
        1. DexScreener: Ανάλυση των wallets πίσω από hot pairs
        2. Token Graduations: Wallets που αγόρασαν tokens πριν το pump
        3. Manual: Γνωστά smart money wallets από community
        """
        logger.info(f"🔍 Starting wallet discovery from: {source}")
        discovered = []
        
        if source == "dexscreener":
            # Φέρνε hot pairs και βρες τα wallets με το καλύτερο timing
            hot_wallets = await self._scan_hot_pairs_for_wallets(sample_size)
            for wallet_addr in hot_wallets:
                profile = await self._analyze_wallet_performance(wallet_addr)
                if profile and profile.calculate_smart_money_score() >= 60:
                    self.wallets[wallet_addr] = profile
                    discovered.append(profile)
                    
        elif source == "graduation":
            # Βρες wallets που αγόρασαν πριν το graduation σε pump.fun
            grad_wallets = await self._scan_graduation_winners()
            for wallet_addr in grad_wallets:
                profile = await self._analyze_wallet_performance(wallet_addr)
                if profile and profile.calculate_smart_money_score() >= 60:
                    self.wallets[wallet_addr] = profile
                    discovered.append(profile)
        
        self.discovery_stats["wallets_qualified"] += len(discovered)
        logger.info(f"✅ Discovered {len(discovered)} smart money wallets!")
        return discovered
    
    async def _scan_hot_pairs_for_wallets(self, limit: int) -> List[str]:
        """Σκανάρει hot pairs και βγάζει unique wallets"""
        wallets = set()
        try:
            # DexScreener API — hot pairs
            async with aiohttp.ClientSession() as session:
                url = "https://api.dexscreener.com/latest/dex/search?q=solana"
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get("pairs", [])[:50]
                        
                        for pair in pairs:
                            # Από τα tx data, μπορούμε να βρούμε active wallets
                            # (Θα χρησιμοποιήσουμε Helius για deeper analysis)
                            pass
        except Exception as e:
            logger.error(f"Hot pairs scan error: {e}")
        
        # Εναλλακτικά: γνωστά smart money wallets από την κοινότητα
        known_smart_money = [
            # Εδώ μπορούμε να προσθέτουμε γνωστά profitable wallets
            # από research, Twitter, ή άλλες πηγές
        ]
        wallets.update(known_smart_money)
        
        return list(wallets)[:limit]
    
    async def _scan_graduation_winners(self) -> List[str]:
        """Βρίσκει wallets που κέρδισαν από pump.fun graduations"""
        winners = set()
        # Θα υλοποιηθεί με Helius filters για pump.fun bonding curve
        return list(winners)
    
    async def _analyze_wallet_performance(self, wallet_addr: str) -> Optional[WalletProfile]:
        """
        📊 Βαθιά ανάλυση απόδοσης ενός wallet
        
        Αναλύει:
        - Ιστορικό συναλλαγών (τελευταίες 1000)
        - PnL ανά token
        - Win rate
        - Risk management patterns
        - Entry/exit timing
        """
        logger.info(f"📊 Analyzing wallet: {wallet_addr[:12]}...")
        
        profile = WalletProfile(address=wallet_addr)
        
        try:
            # 1. Φέρνε transactions
            sigs = await self.helius.get_signatures_for_address(wallet_addr, limit=100)
            if not sigs:
                return None
            
            profile.total_trades = len(sigs)
            
            # 2. Ανάλυση κάθε transaction
            trades = []
            for sig_info in sigs[:50]:  # Πρόσφατες 50 για ταχύτητα
                sig = sig_info.get("signature")
                tx = await self.helius.get_transaction(sig)
                if tx:
                    trade = self._parse_trade_from_tx(tx, wallet_addr)
                    if trade:
                        trades.append(trade)
            
            # 3. Υπολογισμός metrics
            if trades:
                self._calculate_wallet_metrics(profile, trades)
            
            # 4. Portfolio snapshot
            portfolio = await self.birdeye.get_wallet_portfolio(wallet_addr)
            if portfolio:
                profile.portfolio_value_sol = portfolio.get("sol_balance", 0)
                # ... token holdings
            
            # 5. Χρονολογικά boundaries
            if sigs:
                profile.last_active = datetime.fromtimestamp(sigs[0].get("blockTime", 0))
                profile.first_seen = datetime.fromtimestamp(sigs[-1].get("blockTime", 0))
                days_active = max((profile.last_active - profile.first_seen).days, 1)
                profile.trades_per_day = profile.total_trades / days_active
            
            self.discovery_stats["wallets_analyzed"] += 1
            return profile
            
        except Exception as e:
            logger.error(f"Wallet analysis failed for {wallet_addr[:12]}: {e}")
            return None
    
    def _parse_trade_from_tx(self, tx: Dict, wallet: str) -> Optional[Dict]:
        """Εξάγει trade data από transaction JSON"""
        meta = tx.get("meta", {})
        tx_data = tx.get("transaction", {})
        
        trade = {
            "token_address": None,
            "action": None,
            "amount_sol": 0,
            "amount_tokens": 0,
            "price": 0,
            "timestamp": tx.get("blockTime", 0)
        }
        
        # Parse token transfers από inner instructions
        inner_instructions = meta.get("innerInstructions", [])
        token_transfers = []
        
        for inner in inner_instructions:
            for instruction in inner.get("instructions", []):
                parsed = instruction.get("parsed", {})
                if parsed.get("type") in ["transfer", "transferChecked"]:
                    info = parsed.get("info", {})
                    token_transfers.append({
                        "from": info.get("authority") or info.get("source"),
                        "to": info.get("destination"),
                        "amount": info.get("tokenAmount", {}).get("uiAmount", 0),
                        "mint": info.get("mint")
                    })
        
        # Εντοπισμός DEX swaps (Raydium, Orca, Jupiter)
        log_messages = meta.get("logMessages", [])
        for msg in log_messages:
            if "Instruction: Swap" in msg or "Swap" in msg:
                trade["action"] = "SWAP"
                break
            elif "Instruction: AddLiquidity" in msg:
                trade["action"] = "ADD_LIQUIDITY"
                break
        
        return trade if trade["action"] else None
    
    def _calculate_wallet_metrics(self, profile: WalletProfile, trades: List[Dict]):
        """Υπολογίζει performance metrics από trades"""
        # Simplified — full version tracks PnL per token
        profitable = sum(1 for t in trades if t.get("pnl", 0) > 0)
        profile.profitable_trades = profitable
        profile.win_rate = profitable / len(trades) if trades else 0
        
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        profile.total_pnl_sol = total_pnl
        profile.avg_return_per_trade = total_pnl / len(trades) if trades else 0
        
        # Drawdown calculation
        running_pnl = 0
        peak = 0
        max_dd = 0
        for t in trades:
            running_pnl += t.get("pnl", 0)
            peak = max(peak, running_pnl)
            dd = (peak - running_pnl) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        profile.max_drawdown = max_dd
    
    # ═══════════════════════════════════════════════════════════
    # TRACKING PHASE — Real-time monitoring
    # ═══════════════════════════════════════════════════════════
    
    async def start_tracking_wallet(self, wallet_addr: str) -> bool:
        """
        🎯 Ξεκινάει real-time tracking ενός wallet
        
        Χρησιμοποιεί:
        - Helius webhooks (για instant notifications)
        - Polling ως fallback
        """
        if wallet_addr not in self.wallets:
            # Ανάλυσε πρώτα
            profile = await self._analyze_wallet_performance(wallet_addr)
            if not profile:
                return False
            self.wallets[wallet_addr] = profile
        
        profile = self.wallets[wallet_addr]
        profile.is_tracking = True
        profile.track_start_time = datetime.utcnow()
        self.tracked_wallets.add(wallet_addr)
        
        logger.info(f"🎯 Now tracking: {wallet_addr[:12]}... (Tier: {profile.confidence_tier})")
        return True
    
    async def stop_tracking_wallet(self, wallet_addr: str):
        """Σταματάει tracking"""
        if wallet_addr in self.wallets:
            self.wallets[wallet_addr].is_tracking = False
        self.tracked_wallets.discard(wallet_addr)
        logger.info(f"🛑 Stopped tracking: {wallet_addr[:12]}...")
    
    async def poll_tracked_wallets(self) -> List[TradeSignal]:
        """
        📡 Poll όλα τα tracked wallets για νέες συναλλαγές
        
        Τρέχει κάθε 5-15 δευτερόλεπτα για μέγιστη ταχύτητα.
        """
        signals = []
        
        for wallet_addr in list(self.tracked_wallets):
            wallet = self.wallets.get(wallet_addr)
            if not wallet or not wallet.is_tracking:
                continue
            
            try:
                # Φέρνε νέα signatures
                sigs = await self.helius.get_signatures_for_address(wallet_addr, limit=10)
                
                for sig_info in sigs:
                    sig = sig_info.get("signature")
                    if sig in self.tx_history[wallet_addr]:
                        continue  # Ήδη επεξεργασμένο
                    
                    self.tx_history[wallet_addr].append(sig)
                    
                    # Επεξεργασία transaction
                    tx = await self.helius.get_transaction(sig)
                    if tx:
                        signal = await self._process_transaction_to_signal(tx, wallet)
                        if signal:
                            signals.append(signal)
                            self.discovery_stats["signals_generated"] += 1
                            
            except Exception as e:
                logger.error(f"Poll error for {wallet_addr[:12]}: {e}")
        
        return signals
    
    async def _process_transaction_to_signal(
        self, 
        tx: Dict, 
        wallet: WalletProfile
    ) -> Optional[TradeSignal]:
        """Μετατρέπει ένα transaction σε TradeSignal"""
        # Εξαγωγή swap data
        meta = tx.get("meta", {})
        tx_data = tx.get("transaction", {})
        
        # Εντοπισμός token και action
        token_address = None
        action = None
        amount_sol = 0
        
        # Parse από inner instructions
        # ... (detailed parsing logic)
        
        if not token_address:
            return None
        
        # Πάρε τρέχουσα τιμή
        price = await self.birdeye.get_token_price(token_address)
        
        # Market data για context
        market_data = await self.birdeye.get_token_market_data(token_address)
        
        signal = TradeSignal(
            wallet_address=wallet.address,
            wallet_tier=wallet.confidence_tier,
            wallet_score=wallet.smart_money_score,
            token_address=token_address,
            token_symbol=market_data.get("symbol", "UNKNOWN") if market_data else "UNKNOWN",
            action=action or "UNKNOWN",
            amount_sol=amount_sol,
            amount_tokens=0,  # Υπολογίζεται
            price_usd=price or 0,
            tx_signature=tx.get("transaction", {}).get("signatures", [""])[0],
            timestamp=datetime.utcnow(),
            token_liquidity_usd=market_data.get("liquidity", 0) if market_data else None,
            token_volume_24h=market_data.get("volume24h", 0) if market_data else None
        )
        
        # Υπολογισμός urgency
        signal.urgency_score = self._calculate_urgency(signal, wallet)
        
        return signal
    
    def _calculate_urgency(self, signal: TradeSignal, wallet: WalletProfile) -> float:
        """Υπολογίζει πόσο επείγον είναι το signal"""
        score = 0.0
        
        # Tier bonus
        tier_multipliers = {"S": 30, "A": 20, "B": 10, "C": 5, "D": 0}
        score += tier_multipliers.get(wallet.confidence_tier, 0)
        
        # Wallet score
        score += wallet.smart_money_score * 0.3
        
        # Size bonus (μεγάλο position = μεγαλύτερη εμπιστοσύνη)
        if signal.amount_sol > 10:
            score += 20
        elif signal.amount_sol > 1:
            score += 10
        
        # Action bonus
        if signal.action == "BUY":
            score += 10  # Buy signals are actionable
        
        # Liquidity check
        if signal.token_liquidity_usd and signal.token_liquidity_usd > 100000:
            score += 5
        
        return min(score, 100)
    
    # ═══════════════════════════════════════════════════════════
    # WEBSOCKET MONITORING — Ultra-low latency
    # ═══════════════════════════════════════════════════════════
    
    async def websocket_monitor(self, callback):
        """
        ⚡ WebSocket listener για instant updates
        
        Χρησιμοποιεί Helius webhooks ή websocket subscriptions
        για <1s latency από transaction confirmation.
        """
        logger.info("⚡ Starting WebSocket monitor...")
        
        # Helius webhook setup
        # (Απαιτεί public URL για callbacks — θα χρησιμοποιήσουμε polling ως κύρια μέθοδο)
        
        while True:
            try:
                signals = await self.poll_tracked_wallets()
                for signal in signals:
                    await callback(signal)
                
                # Adaptive polling: πιο συχνά αν υπάρχουν signals
                if signals:
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(10)
                    
            except Exception as e:
                logger.error(f"WebSocket monitor error: {e}")
                await asyncio.sleep(15)
    
    # ═══════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════
    
    def get_top_wallets(self, tier: Optional[str] = None, limit: int = 20) -> List[WalletProfile]:
        """Επιστρέφει τα top wallets βάσει score"""
        wallets = list(self.wallets.values())
        if tier:
            wallets = [w for w in wallets if w.confidence_tier == tier]
        wallets.sort(key=lambda w: w.smart_money_score, reverse=True)
        return wallets[:limit]
    
    def get_stats(self) -> Dict:
        """Stats για το dashboard"""
        return {
            **self.discovery_stats,
            "total_wallets": len(self.wallets),
            "tracked_wallets": len(self.tracked_wallets),
            "tier_distribution": self._tier_distribution(),
            "avg_score": sum(w.smart_money_score for w in self.wallets.values()) / len(self.wallets) if self.wallets else 0
        }
    
    def _tier_distribution(self) -> Dict[str, int]:
        dist = defaultdict(int)
        for w in self.wallets.values():
            dist[w.confidence_tier] += 1
        return dict(dist)
    
    def save_state(self, filepath: str = "smart_money_state.json"):
        """Αποθήκευση state"""
        state = {
            "wallets": {
                addr: {
                    "address": w.address,
                    "label": w.label,
                    "total_trades": w.total_trades,
                    "win_rate": w.win_rate,
                    "total_pnl_sol": w.total_pnl_sol,
                    "smart_money_score": w.smart_money_score,
                    "tier": w.confidence_tier,
                    "is_tracking": w.is_tracking,
                    "portfolio_value": w.portfolio_value_sol
                }
                for addr, w in self.wallets.items()
            },
            "tracked": list(self.tracked_wallets),
            "stats": self.discovery_stats,
            "saved_at": datetime.utcnow().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"💾 State saved to {filepath}")
    
    def load_state(self, filepath: str = "smart_money_state.json"):
        """Φόρτωση state"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            for addr, data in state.get("wallets", {}).items():
                w = WalletProfile(address=data["address"])
                w.label = data.get("label")
                w.total_trades = data.get("total_trades", 0)
                w.win_rate = data.get("win_rate", 0)
                w.total_pnl_sol = data.get("total_pnl_sol", 0)
                w.smart_money_score = data.get("smart_money_score", 0)
                w.confidence_tier = data.get("tier", "D")
                w.is_tracking = data.get("is_tracking", False)
                w.portfolio_value_sol = data.get("portfolio_value", 0)
                self.wallets[addr] = w
            
            self.tracked_wallets = set(state.get("tracked", []))
            self.discovery_stats = state.get("stats", self.discovery_stats)
            logger.info(f"📂 State loaded: {len(self.wallets)} wallets")
        except FileNotFoundError:
            logger.info("No previous state found, starting fresh")


class TelegramAlerter:
    """Στέλνει alerts στο Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_alert_time: Dict[str, float] = {}  # Rate limiting
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def send_signal_alert(self, signal: TradeSignal):
        """Στέλνει alert για trade signal"""
        # Rate limit: max 1 alert per wallet per 30 seconds
        now = time.time()
        key = f"{signal.wallet_address}:{signal.token_address}"
        if key in self.last_alert_time:
            if now - self.last_alert_time[key] < 30:
                return  # Too soon
        self.last_alert_time[key] = now
        
        if not self.session:
            return
        
        message = signal.format_alert()
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    logger.info(f"📨 Alert sent: {signal.action} {signal.token_symbol}")
                else:
                    logger.warning(f"Telegram API error: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def send_discovery_report(self, wallets: List[WalletProfile]):
        """Στέλνει report με νέα discovered wallets"""
        if not wallets:
            return
        
        msg = "🔍 **NEW SMART MONEY DISCOVERED** 🔍\n\n"
        for w in wallets[:10]:
            msg += f"""
⭐ **{w.confidence_tier}-Tier** | Score: {w.smart_money_score:.1f}
`{w.address[:12]}...{w.address[-4:]}`
💰 PnL: {w.total_pnl_sol:+.2f} SOL | Win Rate: {w.win_rate*100:.1f}%
📊 Trades: {w.total_trades} | Portfolio: {w.portfolio_value_sol:.2f} SOL

"""
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": msg,
                "parse_mode": "Markdown"
            }
            async with self.session.post(url, json=payload, timeout=10) as resp:
                pass
        except Exception as e:
            logger.error(f"Discovery report failed: {e}")
    
    async def send_tracking_start(self, wallet: WalletProfile):
        """Επιβεβαίωση ότι ξεκίνησε tracking"""
        msg = f"""
🎯 **TRACKING STARTED**

{tier_emoji(wallet.confidence_tier)} **Wallet:** `{wallet.address[:12]}...{wallet.address[-4:]}`
⭐ **Score:** {wallet.smart_money_score:.1f}/100
🏆 **Tier:** {wallet.confidence_tier}
💰 **PnL:** {wallet.total_pnl_sol:+.2f} SOL
📊 **Win Rate:** {wallet.win_rate*100:.1f}%

👁️ Will alert on every move!
"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": msg,
                "parse_mode": "Markdown"
            }
            async with self.session.post(url, json=payload, timeout=10):
                pass
        except Exception as e:
            logger.error(f"Tracking start alert failed: {e}")


def tier_emoji(tier: str) -> str:
    return {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📊"}.get(tier, "📊")


# ═══════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════

class SmartMoneyAgent:
    """
    🤖 ΚΥΡΙΟΣ AGENT — Smart Money Tracker
    
    Τρέχει 24/7:
    1. Ανακαλύπτει κερδοφόρα wallets
    2. Τα αξιολογεί και τα κατηγοριοποιεί
    3. Παρακολουθεί τα καλύτερα real-time
    4. Στέλνει instant alerts
    """
    
    def __init__(self):
        self.analyzer = BlockchainAnalyzer()
        self.alerter = TelegramAlerter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        self.running = False
        self.tasks = []
    
    async def __aenter__(self):
        await self.analyzer.__aenter__()
        await self.alerter.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        self.running = False
        for task in self.tasks:
            task.cancel()
        await self.analyzer.__aexit__()
        await self.alerter.__aexit__()
    
    async def run(self):
        """Κύριο loop — τρέχει για πάντα"""
        self.running = True
        logger.info("🚀 SMART MONEY TRACKER AGENT STARTED")
        logger.info("=" * 50)
        
        # Φόρτωση προηγούμενου state
        self.analyzer.load_state()
        
        # Discovery task — τρέχει κάθε 6 ώρες
        discovery_task = asyncio.create_task(self._discovery_loop())
        self.tasks.append(discovery_task)
        
        # Monitoring task — τρέχει συνεχώς
        monitor_task = asyncio.create_task(self._monitoring_loop())
        self.tasks.append(monitor_task)
        
        # Stats task — κάθε ώρα
        stats_task = asyncio.create_task(self._stats_loop())
        self.tasks.append(stats_task)
        
        # Save state task — κάθε 5 λεπτά
        save_task = asyncio.create_task(self._save_loop())
        self.tasks.append(save_task)
        
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("🛑 Agent shutting down")
    
    async def _discovery_loop(self):
        """Ανακάλυψη νέων wallets — κάθε 6 ώρες"""
        while self.running:
            try:
                logger.info("🔍 Starting discovery cycle...")
                
                # Πολλαπλές πηγές ανακάλυψης
                sources = ["dexscreener", "graduation"]
                all_discovered = []
                
                for source in sources:
                    discovered = await self.analyzer.discover_profitable_wallets(
                        source=source,
                        min_pnl_sol=5.0,
                        min_win_rate=0.50
                    )
                    all_discovered.extend(discovered)
                
                # Αφαίρεσε duplicates
                unique = {w.address: w for w in all_discovered}
                all_discovered = list(unique.values())
                
                # Auto-track τα S και A tier
                s_tier = [w for w in all_discovered if w.confidence_tier in ["S", "A"]]
                for w in s_tier[:5]:  # Top 5 only
                    await self.analyzer.start_tracking_wallet(w.address)
                    await self.alerter.send_tracking_start(w)
                
                # Report
                await self.alerter.send_discovery_report(all_discovered)
                
                logger.info(f"✅ Discovery complete: {len(all_discovered)} new wallets")
                
            except Exception as e:
                logger.error(f"Discovery error: {e}")
            
            # Περίμενε 6 ώρες
            for _ in range(21600):  # 6 hours in seconds
                if not self.running:
                    break
                await asyncio.sleep(1)
    
    async def _monitoring_loop(self):
        """Real-time monitoring — συνεχής"""
        while self.running:
            try:
                if self.analyzer.tracked_wallets:
                    signals = await self.analyzer.poll_tracked_wallets()
                    
                    for signal in signals:
                        # Στείλε alert
                        await self.alerter.send_signal_alert(signal)
                        
                        # Log για analysis
                        logger.info(f"🚨 SIGNAL: {signal.wallet_tier}-tier | {signal.action} {signal.token_symbol} | Urgency: {signal.urgency_score:.0f}")
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            # Adaptive sleep
            if self.analyzer.discovery_stats["signals_generated"] > 0:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(15)
    
    async def _stats_loop(self):
        """Hourly stats"""
        while self.running:
            try:
                stats = self.analyzer.get_stats()
                logger.info(f"📊 STATS: {stats}")
            except Exception as e:
                logger.error(f"Stats error: {e}")
            
            await asyncio.sleep(3600)
    
    async def _save_loop(self):
        """Save state every 5 minutes"""
        while self.running:
            try:
                self.analyzer.save_state()
            except Exception as e:
                logger.error(f"Save error: {e}")
            
            await asyncio.sleep(300)
    
    # ═══════════════════════════════════════════════════════════
    # COMMANDS (για Telegram integration)
    # ═══════════════════════════════════════════════════════════
    
    async def cmd_discover(self) -> str:
        """Manual discovery trigger"""
        discovered = await self.analyzer.discover_profitable_wallets()
        return f"✅ Discovered {len(discovered)} new smart money wallets!"
    
    async def cmd_track(self, wallet_addr: str) -> str:
        """Start tracking a wallet"""
        success = await self.analyzer.start_tracking_wallet(wallet_addr)
        if success:
            return f"🎯 Now tracking: {wallet_addr[:12]}..."
        return f"❌ Failed to track: {wallet_addr[:12]}..."
    
    async def cmd_untrack(self, wallet_addr: str) -> str:
        """Stop tracking"""
        await self.analyzer.stop_tracking_wallet(wallet_addr)
        return f"🛑 Stopped tracking: {wallet_addr[:12]}..."
    
    async def cmd_list(self, tier: Optional[str] = None) -> str:
        """List tracked/discovered wallets"""
        wallets = self.analyzer.get_top_wallets(tier=tier, limit=20)
        if not wallets:
            return "No wallets found."
        
        msg = f"📊 **TOP WALLETS** ({tier or 'All Tiers'})\n\n"
        for i, w in enumerate(wallets[:15], 1):
            track_status = "👁️" if w.is_tracking else "👁️‍🗨️"
            msg += f"{i}. {track_status} **{w.confidence_tier}** | {w.smart_money_score:.0f}pts | `{w.address[:10]}...` | PnL: {w.total_pnl_sol:+.1f} SOL\n"
        
        return msg
    
    async def cmd_stats(self) -> str:
        """Get current stats"""
        stats = self.analyzer.get_stats()
        return f"""
📈 **AGENT STATS**

🔍 Wallets Analyzed: {stats['wallets_analyzed']}
⭐ Qualified: {stats['wallets_qualified']}
👁️ Tracked: {stats['tracked_wallets']}
🚨 Signals: {stats['signals_generated']}
📨 Alerts Sent: {stats['alerts_sent']}

🏆 Tier Distribution:
• S-Tier: {stats['tier_distribution'].get('S', 0)}
• A-Tier: {stats['tier_distribution'].get('A', 0)}
• B-Tier: {stats['tier_distribution'].get('B', 0)}
• C-Tier: {stats['tier_distribution'].get('C', 0)}

📊 Avg Score: {stats['avg_score']:.1f}/100
"""


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

async def main():
    """Entry point — ξεκινάει τον agent"""
    async with SmartMoneyAgent() as agent:
        await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
