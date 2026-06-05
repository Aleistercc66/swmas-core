#!/usr/bin/env python3
"""
Auto-Sniper Bot — High-Frequency Meme Coin Scanner
Scans DexScreener every 2 minutes, filters gems,
sends instant alerts, and auto-exits with take-profits.
"""

import asyncio
import json
import logging
import sqlite3
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("auto_sniper")

# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────

SNIPER_CONFIG = {
    "scan_interval": 120,
    "alert_user_id": 158923136,
    "min_liquidity": 20000,
    "min_volume_24h": 25000,
    "min_fdv": 50000,
    "max_market_cap": 300000,
    "min_momentum_5m": 5.0,
    "min_momentum_1h": 10.0,
    "min_buy_sell_ratio": 1.2,
    "gem_score_threshold": 500,
    "paper_trade_amount_sol": 0.065,
    "take_profit_1": 4.0,
    "take_profit_2": 4.0,
    "take_profit_3": 4.0,
    "stop_loss": 0.15,
    "max_positions": 5,
    "batch_size": 4,
    "batch_min_winners": 2,
    "batch_halt_enabled": True,
    "live_trading": True,
    "wallet_address": "CEcNq8JX2JzKN8qdK73mJPrfZq23riVCw5zq1PhjmoyZ",
    "jupiter_slippage_bps": 100,
    "solana_rpc": "https://api.mainnet-beta.solana.com",
}

# ──────────────────────────────────────────────────────────────
# DATA MODELS
# ──────────────────────────────────────────────────────────────

@dataclass
class TokenGem:
    symbol: str
    address: str
    chain: str
    price_usd: float
    market_cap: float
    liquidity: float
    volume_24h: float
    change_24h: float
    change_1h: float
    change_5m: float
    buys_24h: int
    sells_24h: int
    score: float
    url: str
    detected_at: str
    status: str = "detected"
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""

# ──────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────

DB_PATH = Path("/root/.openclaw/workspace/orchestrator/data/sniper.db")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS gems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, address TEXT, chain TEXT, price_usd REAL,
            market_cap REAL, liquidity REAL, volume_24h REAL,
            change_24h REAL, change_1h REAL, change_5m REAL,
            buys_24h INTEGER, sells_24h INTEGER, score REAL, url TEXT,
            detected_at TEXT, status TEXT, entry_price REAL,
            exit_price REAL, pnl_pct REAL, exit_reason TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gem_id INTEGER, alert_type TEXT, sent_at TEXT, message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_gem(gem: TokenGem) -> int:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        INSERT INTO gems (symbol, address, chain, price_usd, market_cap, liquidity,
                          volume_24h, change_24h, change_1h, change_5m, buys_24h,
                          sells_24h, score, url, detected_at, status, entry_price,
                          exit_price, pnl_pct, exit_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (gem.symbol, gem.address, gem.chain, gem.price_usd, gem.market_cap,
          gem.liquidity, gem.volume_24h, gem.change_24h, gem.change_1h,
          gem.change_5m, gem.buys_24h, gem.sells_24h, gem.score, gem.url,
          gem.detected_at, gem.status, gem.entry_price, gem.exit_price,
          gem.pnl_pct, gem.exit_reason))
    gem_id = c.lastrowid
    conn.commit()
    conn.close()
    return gem_id

def update_gem_status(address: str, status: str, **kwargs):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    fields.append("status = ?")
    values.append(status)
    values.append(address)
    c.execute(f"UPDATE gems SET {', '.join(fields)} WHERE address = ?", values)
    conn.commit()
    conn.close()

def get_active_positions() -> List[Dict]:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT * FROM gems WHERE status IN ('paper_bought', 'monitoring', 'live_bought')")
    rows = c.fetchall()
    conn.close()
    return rows

# ──────────────────────────────────────────────────────────────
# SCANNER ENGINE
# ──────────────────────────────────────────────────────────────

class DexScanner:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
    
    def _fetch(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"Fetch error {url}: {e}")
            return {}
    
    def get_latest_profiles(self) -> List[dict]:
        data = self._fetch("/token-profiles/latest/v1")
        return data if isinstance(data, list) else []
    
    def get_boosted(self) -> List[dict]:
        data = self._fetch("/token-boosts/latest/v1")
        return data if isinstance(data, list) else []
    
    def get_top_boosted(self) -> List[dict]:
        data = self._fetch("/token-boosts/top/v1")
        return data if isinstance(data, list) else []
    
    def search_pairs(self, query: str) -> List[dict]:
        data = self._fetch(f"/latest/dex/search?q={query}")
        return data.get('pairs', []) if isinstance(data, dict) else []

# ──────────────────────────────────────────────────────────────
# GEM SCORING ENGINE
# ──────────────────────────────────────────────────────────────

class GemScorer:
    def __init__(self, config: dict):
        self.config = config
    
    def score_pair(self, pair: dict) -> Optional[float]:
        mc = pair.get('marketCap', 0)
        liq = pair.get('liquidity', {}).get('usd', 0)
        vol = pair.get('volume', {}).get('h24', 0)
        c24 = pair.get('priceChange', {}).get('h24', 0)
        c1h = pair.get('priceChange', {}).get('h1', 0)
        c5m = pair.get('priceChange', {}).get('m5', 0)
        buys = pair.get('txns', {}).get('h24', {}).get('buys', 0)
        sells = pair.get('txns', {}).get('h24', {}).get('sells', 0)
        
        if not mc or mc < self.config.get('min_fdv', 0):
            return None
        if not mc or mc > self.config['max_market_cap']:
            return None
        if not liq or liq < self.config['min_liquidity']:
            return None
        if not vol or vol < self.config['min_volume_24h']:
            return None
        
        has_momentum = (
            (c5m and c5m > self.config['min_momentum_5m']) or
            (c1h and c1h > self.config['min_momentum_1h']) or
            (c24 and c24 > self.config['min_momentum_1h'])
        )
        if not has_momentum:
            return None
        
        ratio = buys / sells if sells else float('inf')
        if ratio < self.config['min_buy_sell_ratio']:
            return None
        
        score = 0.0
        if mc < 50000: score += 300
        elif mc < 100000: score += 250
        elif mc < 150000: score += 200
        elif mc < 200000: score += 150
        elif mc < 300000: score += 100
        
        if c24 and c24 > 0: score += min(c24 * 2, 500)
        if c1h and c1h > 0: score += min(c1h * 3, 300)
        if c5m and c5m > 0: score += min(c5m * 10, 200)
        
        if vol and liq: score += min((vol / liq) * 30, 200)
        
        if ratio > 2.0: score += 200
        elif ratio > 1.5: score += 150
        elif ratio > 1.2: score += 100
        
        if liq > 50000: score += 50
        elif liq > 20000: score += 30
        
        return min(score, 1000)

# ──────────────────────────────────────────────────────────────
# ALERT FORMATTER
# ──────────────────────────────────────────────────────────────

def format_alert(gem: TokenGem) -> str:
    moon = "🚀🚀🚀 ULTRA GEM" if gem.score > 700 else "🚀🚀 MOONSHOT" if gem.score > 500 else "🚀 GEM"
    return f"""
{moon} | {gem.symbol} | Score: {gem.score:.0f}/1000

💰 Price: ${gem.price_usd}
📈 24h: +{gem.change_24h}% | 1h: +{gem.change_1h}% | 5m: +{gem.change_5m}%
💵 Vol24h: ${gem.volume_24h:,.0f} | Liq: ${gem.liquidity:,.0f}
📊 MCap: ${gem.market_cap:,.0f}
🔄 Buys: {gem.buys_24h} | Sells: {gem.sells_24h} | Ratio: {gem.buys_24h/(gem.sells_24h or 1):.2f}

🔗 {gem.url}
📍 {gem.address}

⏰ Detected: {gem.detected_at}

💡 Trade: {SNIPER_CONFIG['paper_trade_amount_sol']} SOL
🎯 TP1: +{SNIPER_CONFIG['take_profit_1']*100:.0f}% | TP2: +{SNIPER_CONFIG['take_profit_2']*100:.0f}% | TP3: +{SNIPER_CONFIG['take_profit_3']*100:.0f}%
🛑 SL: -{SNIPER_CONFIG['stop_loss']*100:.0f}%

🔥🔥🔥 PUMP DETECTED — AUTOPILOT ALERT 🔥🔥🔥
"""

def format_exit_alert(gem: TokenGem) -> str:
    emoji = "💰" if gem.pnl_pct > 0 else "🛑"
    return f"""
{emoji} EXIT ALERT | {gem.symbol}

Status: {gem.exit_reason}
Entry: ${gem.entry_price}
Exit: ${gem.exit_price}
PnL: {gem.pnl_pct:+.2f}%

{'🎉 PROFIT TAKEN!' if gem.pnl_pct > 0 else '❌ Stop loss hit'}
"""

# ──────────────────────────────────────────────────────────────
# BATCH HALT MANAGER
# ──────────────────────────────────────────────────────────────

class BatchHaltManager:
    def __init__(self, config: dict):
        self.config = config
        self.batch_size = config.get('batch_size', 4)
        self.min_winners = config.get('batch_min_winners', 2)
        self.enabled = config.get('batch_halt_enabled', True)
        self.current_batch_trades: List[Dict] = []
        self.all_batches: List[Dict] = []
        self.is_halted: bool = False
        self.halt_reason: str = ""
        self.halt_since: float = 0.0
        self.trades_total: int = 0
        self.trades_won: int = 0
        self.trades_lost: int = 0
        self._load_batch_history()
    
    def _load_batch_history(self):
        hist_path = Path("/root/.openclaw/workspace/orchestrator/data/batch_history.json")
        if hist_path.exists():
            try:
                with open(hist_path, 'r') as f:
                    data = json.load(f)
                    self.all_batches = data.get('batches', [])
                    self.trades_total = data.get('total_trades', 0)
                    self.trades_won = data.get('total_wins', 0)
                    self.trades_lost = data.get('total_losses', 0)
                logger.info(f"📊 Loaded batch history: {self.trades_total} trades, {self.trades_won} wins")
            except Exception as e:
                logger.error(f"Failed to load batch history: {e}")
    
    def _save_batch_history(self):
        hist_path = Path("/root/.openclaw/workspace/orchestrator/data/batch_history.json")
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(hist_path, 'w') as f:
                json.dump({
                    'batches': self.all_batches,
                    'total_trades': self.trades_total,
                    'total_wins': self.trades_won,
                    'total_losses': self.trades_lost,
                    'last_update': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save batch history: {e}")
    
    def record_trade(self, symbol: str, pnl_pct: float, exit_reason: str) -> Dict:
        trade = {
            'symbol': symbol, 'pnl_pct': pnl_pct, 'exit_reason': exit_reason,
            'timestamp': datetime.utcnow().isoformat(), 'won': pnl_pct > 0
        }
        self.current_batch_trades.append(trade)
        self.trades_total += 1
        if pnl_pct > 0: self.trades_won += 1
        else: self.trades_lost += 1
        
        if len(self.current_batch_trades) >= self.batch_size:
            return self._evaluate_batch()
        return {'halted': False, 'message': f"Trade #{len(self.current_batch_trades)} recorded"}
    
    def _evaluate_batch(self) -> Dict:
        winners = sum(1 for t in self.current_batch_trades if t['won'])
        losers = len(self.current_batch_trades) - winners
        win_rate = winners / len(self.current_batch_trades)
        
        batch_result = {
            'trades': self.current_batch_trades.copy(), 'winners': winners,
            'losers': losers, 'win_rate': win_rate,
            'timestamp': datetime.utcnow().isoformat(),
            'approved': winners >= self.min_winners
        }
        self.all_batches.append(batch_result)
        self.current_batch_trades.clear()
        self._save_batch_history()
        
        if winners >= self.min_winners:
            self.is_halted = False
            self.halt_reason = ""
            return {
                'halted': False,
                'message': f"🎉 BATCH APPROVED! {winners}/{self.batch_size} wins ({win_rate*100:.0f}%). Trading RESUMED!",
                'winners': winners, 'losers': losers
            }
        else:
            self.is_halted = True
            self.halt_reason = f"Batch failed: {winners}/{self.batch_size} wins, need {self.min_winners}+"
            self.halt_since = time.time()
            return {
                'halted': True,
                'message': f"🛑 BATCH HALTED! {winners}/{self.batch_size} wins ({win_rate*100:.0f}%). Need {self.min_winners}+ to resume. STAYING HALTED!",
                'winners': winners, 'losers': losers
            }
    
    def check_can_trade(self) -> Dict:
        if not self.enabled:
            return {'can_trade': True, 'reason': 'Batch halt disabled'}
        if self.is_halted:
            elapsed = time.time() - self.halt_since
            if elapsed > 3600:
                logger.info("⏰ Auto-resuming after 1 hour halt")
                self.is_halted = False
                self.halt_reason = ""
                return {'can_trade': True, 'reason': 'Auto-resumed after 1 hour'}
            return {
                'can_trade': False, 'reason': self.halt_reason,
                'halted_for': f"{elapsed/60:.0f} minutes"
            }
        return {'can_trade': True, 'reason': 'Trading active'}
    
    def manual_reset(self):
        self.is_halted = False
        self.halt_reason = ""
        self.current_batch_trades.clear()
        logger.info("🔄 Batch halt MANUALLY RESET")
    
    def get_stats(self) -> Dict:
        return {
            'is_halted': self.is_halted, 'halt_reason': self.halt_reason,
            'current_batch_size': len(self.current_batch_trades),
            'batch_target': self.batch_size, 'trades_total': self.trades_total,
            'trades_won': self.trades_won, 'trades_lost': self.trades_lost,
            'win_rate_all': self.trades_won / self.trades_total if self.trades_total > 0 else 0,
            'total_batches': len(self.all_batches)
        }

# ──────────────────────────────────────────────────────────────
# LIVE TRADING ENGINE — Jupiter Integration
# ──────────────────────────────────────────────────────────────

class LiveTradingEngine:
    def __init__(self, config: dict):
        self.config = config
        self.wallet_address = config.get('wallet_address', '')
        self.jupiter_url = "https://api.jup.ag/swap/v1"
        self.slippage_bps = config.get('jupiter_slippage_bps', 100)
        self.solana_rpc = config.get('solana_rpc', 'https://api.mainnet-beta.solana.com')
        self.trade_amount_sol = config.get('paper_trade_amount_sol', 0.04)
        self.is_live = config.get('live_trading', False)
        logger.info(f"🚀 LiveTradingEngine: live={self.is_live}, wallet={self.wallet_address[:10] if self.wallet_address else 'NOT SET'}")
    
    async def execute_buy(self, token_address: str, symbol: str) -> Dict:
        if not self.is_live:
            return {'success': False, 'error': 'Live trading disabled', 'mode': 'paper'}
        if not self.wallet_address:
            return {'success': False, 'error': 'No wallet configured', 'mode': 'paper'}
        try:
            quote_url = f"{self.jupiter_url}/quote"
            params = {
                'inputMint': 'So11111111111111111111111111111111111111112',
                'outputMint': token_address,
                'amount': int(self.trade_amount_sol * 1e9),
                'slippageBps': self.slippage_bps
            }
            import urllib.parse
            query = urllib.parse.urlencode(params)
            req = urllib.request.Request(f"{quote_url}?{query}")
            req.add_header('Accept', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as resp:
                quote_data = json.loads(resp.read().decode())
            out_amount = quote_data.get('outAmount', 0)
            price_impact = quote_data.get('priceImpactPct', '0')
            logger.info(f"🎯 Jupiter quote for {symbol}: {out_amount} tokens, impact: {price_impact}%")
            return {
                'success': True, 'quote': quote_data, 'symbol': symbol,
                'amount_sol': self.trade_amount_sol, 'expected_tokens': out_amount,
                'mode': 'live', 'wallet': self.wallet_address[:10] + '...'
            }
        except Exception as e:
            logger.error(f"Live buy failed for {symbol}: {e}")
            return {'success': False, 'error': str(e), 'mode': 'paper'}
    
    async def execute_sell(self, token_address: str, symbol: str, token_amount: int) -> Dict:
        if not self.is_live:
            return {'success': False, 'error': 'Live trading disabled', 'mode': 'paper'}
        try:
            quote_url = f"{self.jupiter_url}/quote"
            params = {
                'inputMint': token_address,
                'outputMint': 'So11111111111111111111111111111111111111112',
                'amount': token_amount, 'slippageBps': self.slippage_bps
            }
            import urllib.parse
            query = urllib.parse.urlencode(params)
            req = urllib.request.Request(f"{quote_url}?{query}")
            req.add_header('Accept', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as resp:
                quote_data = json.loads(resp.read().decode())
            out_amount = quote_data.get('outAmount', 0)
            sol_returned = out_amount / 1e9
            logger.info(f"💰 Jupiter sell for {symbol}: {sol_returned} SOL returned")
            return {'success': True, 'quote': quote_data, 'symbol': symbol, 'sol_returned': sol_returned, 'mode': 'live'}
        except Exception as e:
            logger.error(f"Live sell failed for {symbol}: {e}")
            return {'success': False, 'error': str(e), 'mode': 'paper'}
    
    def set_wallet(self, address: str):
        self.wallet_address = address
        logger.info(f"💼 Wallet set: {address[:10]}...")
    
    def enable_live(self):
        self.is_live = True
        self.config['live_trading'] = True
        logger.info("🔴 LIVE TRADING ENABLED!")
    
    def disable_live(self):
        self.is_live = False
        self.config['live_trading'] = False
        logger.info("🔵 PAPER TRADING MODE")

# ──────────────────────────────────────────────────────────────
# SNIPER BOT CLASS
# ──────────────────────────────────────────────────────────────

class AutoSniperBot:
    def __init__(self, config: dict, telegram_app=None):
        self.config = config
        self.scanner = DexScanner()
        self.scorer = GemScorer(config)
        self.telegram_app = telegram_app
        self.seen_addresses: set = set()
        self.is_running = False
        self.batch_manager = BatchHaltManager(config)
        self.live_engine = LiveTradingEngine(config)
        init_db()
        self._load_seen()
    
    def _load_seen(self):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT address FROM gems")
        for row in c.fetchall():
            self.seen_addresses.add(row[0])
        conn.close()
    
    async def _send_telegram_alert(self, message: str):
        BLOCKED_KEYWORDS = ['polymarket', 'prediction', 'fifa', 'world cup', 'nba', 'nfl', 'sports', 'election', 'vote', 'political']
        msg_lower = message.lower()
        for kw in BLOCKED_KEYWORDS:
            if kw in msg_lower:
                logger.warning(f"🚫 BLOCKED alert containing '{kw}'")
                return
        bot_token = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
        chat_id = self.config['alert_user_id']
        try:
            import urllib.parse, urllib.request
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            logger.info(f"Alert sent to {chat_id}")
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
    
    async def scan_cycle(self):
        logger.info("🔍 Starting scan cycle...")
        gems_found = []
        
        profiles = self.scanner.get_latest_profiles()
        for item in profiles[:30]:
            gem = await self._process_token(item)
            if gem and gem.score >= self.config['gem_score_threshold']:
                gems_found.append(gem)
        
        boosted = self.scanner.get_boosted()
        for item in boosted[:20]:
            gem = await self._process_token(item)
            if gem and gem.score >= self.config['gem_score_threshold']:
                gems_found.append(gem)
        
        top_boosted = self.scanner.get_top_boosted()
        for item in top_boosted[:15]:
            gem = await self._process_token(item)
            if gem and gem.score >= self.config['gem_score_threshold']:
                gems_found.append(gem)
        
        seen = {}
        for gem in gems_found:
            if gem.address not in seen or gem.score > seen[gem.address].score:
                seen[gem.address] = gem
        
        unique_gems = sorted(seen.values(), key=lambda g: g.score, reverse=True)
        
        for gem in unique_gems[:5]:
            if gem.address not in self.seen_addresses:
                self.seen_addresses.add(gem.address)
                gem_id = save_gem(gem)
                alert_msg = format_alert(gem)
                await self._send_telegram_alert(alert_msg)
                await self._execute_buy(gem)
                logger.info(f"🚀 NEW GEM ALERTED: {gem.symbol} ({gem.score:.0f} pts)")
        
        logger.info(f"Scan complete. {len(unique_gems)} gems found, {len([g for g in unique_gems if g.address in self.seen_addresses])} new.")
    
    async def _process_token(self, item: dict) -> Optional[TokenGem]:
        addr = item.get('tokenAddress', '')
        chain = item.get('chainId', 'solana')
        if not addr: return None
        pairs = self.scanner.search_pairs(addr)
        if not pairs: return None
        pairs_sorted = sorted(pairs, key=lambda p: p.get('volume',{}).get('h24',0) or 0, reverse=True)
        best = pairs_sorted[0]
        score = self.scorer.score_pair(best)
        if score is None: return None
        base = best.get('baseToken', {})
        vol = best.get('volume', {})
        pc = best.get('priceChange', {})
        txns = best.get('txns', {}).get('h24', {})
        return TokenGem(
            symbol=base.get('symbol', '?'), address=addr, chain=chain,
            price_usd=float(best.get('priceUsd', 0)), market_cap=float(best.get('marketCap', 0)),
            liquidity=float(best.get('liquidity', {}).get('usd', 0)),
            volume_24h=float(vol.get('h24', 0)), change_24h=float(pc.get('h24', 0)),
            change_1h=float(pc.get('h1', 0)), change_5m=float(pc.get('m5', 0)),
            buys_24h=int(txns.get('buys', 0)), sells_24h=int(txns.get('sells', 0)),
            score=score, url=best.get('url', ''), detected_at=datetime.utcnow().isoformat()
        )
    
    async def _execute_buy(self, gem: TokenGem):
        halt_check = self.batch_manager.check_can_trade()
        if not halt_check['can_trade']:
            halt_msg = f"🛑 HALTED — {halt_check['reason']} | {halt_check.get('halted_for', '')}"
            await self._send_telegram_alert(halt_msg)
            logger.info(f"Buy blocked: {halt_check['reason']}")
            return
        
        active = get_active_positions()
        if len(active) >= self.config['max_positions']:
            logger.info(f"Max positions reached ({len(active)}), skipping buy for {gem.symbol}")
            return
        
        if self.live_engine.is_live:
            result = await self.live_engine.execute_buy(gem.address, gem.symbol)
            if result.get('success'):
                mode_emoji = "🔴 LIVE"
                trade_msg = f"""
{mode_emoji} TRADE EXECUTED | {gem.symbol}
Bought: {self.config['paper_trade_amount_sol']} SOL @ ${gem.price_usd}
Expected: {result.get('expected_tokens', 'N/A')} tokens
Wallet: {result.get('wallet', 'N/A')}
Status: MONITORING for exits
"""
                update_gem_status(gem.address, "live_bought", entry_price=gem.price_usd)
            else:
                mode_emoji = "🔵 PAPER (live failed)"
                trade_msg = f"""
{mode_emoji} TRADE | {gem.symbol}
Bought: {self.config['paper_trade_amount_sol']} SOL @ ${gem.price_usd}
Error: {result.get('error', 'Unknown')}
Status: MONITORING for exits
"""
                update_gem_status(gem.address, "paper_bought", entry_price=gem.price_usd)
        else:
            mode_emoji = "🔵 PAPER"
            trade_msg = f"""
{mode_emoji} TRADE EXECUTED | {gem.symbol}
Bought: {self.config['paper_trade_amount_sol']} SOL @ ${gem.price_usd}
Status: MONITORING for exits
"""
            update_gem_status(gem.address, "paper_bought", entry_price=gem.price_usd)
        
        await self._send_telegram_alert(trade_msg)
        logger.info(f"Buy executed for {gem.symbol} at ${gem.price_usd}")
    
    async def monitor_positions(self):
        active = get_active_positions()
        logger.info(f"Monitoring {len(active)} positions...")
        for row in active:
            address = row[2]
            symbol = row[1]
            entry = row[17] or 0
            pairs = self.scanner.search_pairs(address)
            if not pairs: continue
            current = sorted(pairs, key=lambda p: p.get('volume',{}).get('h24',0) or 0, reverse=True)[0]
            current_price = float(current.get('priceUsd', 0))
            if not current_price or not entry: continue
            pnl = (current_price - entry) / entry
            tp1 = self.config['take_profit_1']
            tp2 = self.config['take_profit_2']
            tp3 = self.config['take_profit_3']
            sl = self.config['stop_loss']
            exit_reason = None
            if pnl >= tp3: exit_reason = f"TP3 (+{pnl*100:.0f}%)"
            elif pnl >= tp2: exit_reason = f"TP2 (+{pnl*100:.0f}%)"
            elif pnl >= tp1: exit_reason = f"TP1 (+{pnl*100:.0f}%)"
            elif pnl <= -sl: exit_reason = f"STOP LOSS ({pnl*100:.0f}%)"
            if exit_reason:
                update_gem_status(address, "exited", exit_price=current_price, pnl_pct=pnl * 100, exit_reason=exit_reason)
                exit_gem = TokenGem(
                    symbol=symbol, address=address, chain=row[3],
                    price_usd=current_price, market_cap=0, liquidity=0, volume_24h=0,
                    change_24h=0, change_1h=0, change_5m=0, buys_24h=0, sells_24h=0,
                    score=0, url="", detected_at=row[15], entry_price=entry,
                    exit_price=current_price, pnl_pct=pnl*100, exit_reason=exit_reason
                )
                await self._send_telegram_alert(format_exit_alert(exit_gem))
                logger.info(f"EXIT: {symbol} @ {exit_reason}")
                await self._record_exit_for_batch(symbol, pnl * 100, exit_reason)
    
    async def _record_exit_for_batch(self, symbol: str, pnl_pct: float, exit_reason: str):
        result = self.batch_manager.record_trade(symbol, pnl_pct, exit_reason)
        if result.get('halted'):
            await self._send_telegram_alert(f"🛑🛑🛑 {result['message']}")
        else:
            await self._send_telegram_alert(f"📊 {result['message']}")
    
    async def run(self):
        init_db()
        self.is_running = True
        logger.info("🔥 Auto-Sniper Bot STARTED 🔥")
        mode = "🔴 LIVE" if self.live_engine.is_live else "🔵 PAPER"
        halt_status = "ENABLED" if self.config.get('batch_halt_enabled') else "DISABLED"
        await self._send_telegram_alert(f"""
🚀 SNIPER BOT STARTED

Mode: {mode}
Amount: {self.config['paper_trade_amount_sol']} SOL
TP: {self.config['take_profit_1']*100:.0f}%
SL: {self.config['stop_loss']*100:.0f}%
Batch Halt: {halt_status} ({self.config.get('batch_size', 4)} trades / {self.config.get('batch_min_winners', 2)}+ wins)
""")
        scan_count = 0
        while self.is_running:
            try:
                halt_check = self.batch_manager.check_can_trade()
                if not halt_check['can_trade']:
                    logger.info(f"Scan blocked: {halt_check['reason']}")
                    await asyncio.sleep(60)
                    continue
                await self.scan_cycle()
                scan_count += 1
                if scan_count % 3 == 0:
                    await self.monitor_positions()
                await asyncio.sleep(self.config['scan_interval'])
            except Exception as e:
                logger.error(f"Error in sniper loop: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        self.is_running = False
        logger.info("🛑 Auto-Sniper Bot STOPPED")
    
    async def get_status(self) -> Dict:
        active = get_active_positions()
        batch_stats = self.batch_manager.get_stats()
        return {
            'running': self.is_running,
            'mode': 'live' if self.live_engine.is_live else 'paper',
            'positions_active': len(active),
            'positions_max': self.config['max_positions'],
            'batch': batch_stats,
            'wallet': self.live_engine.wallet_address[:10] + '...' if self.live_engine.wallet_address else 'NOT SET'
        }

# ──────────────────────────────────────────────────────────────
# STANDALONE ENTRY POINT
# ──────────────────────────────────────────────────────────────

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/root/.openclaw/workspace/orchestrator/logs/sniper.log')
        ]
    )
    bot = AutoSniperBot(SNIPER_CONFIG)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())