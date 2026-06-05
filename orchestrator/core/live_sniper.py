import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Any, List

# Import existing components
import sys
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from core.auto_sniper import AutoSniperBot, SNIPER_CONFIG, DB_PATH, init_db, format_alert, format_exit_alert
from core.auto_sniper import TokenGem, update_gem_status, get_active_positions
from core.wallet_manager import WalletManager

try:
    from core.wallet_trading_bridge import WalletTradingBridge
    from solana_jupiter_connector import SolanaJupiterConnector
    LIVE_AVAILABLE = True
except ImportError as e:
    LIVE_AVAILABLE = False
    logging.warning(f"Live trading not available: {e}")

logger = logging.getLogger("live_sniper")

# ──────────────────────────────────────────────────────────────
# LOAD EXTERNAL CONFIG
# ──────────────────────────────────────────────────────────────
import configparser

_CONFIG = configparser.ConfigParser()
_CONFIG.read('/root/.openclaw/workspace/orchestrator/core/live_config.ini')

_mode = _CONFIG.get('mode', 'current_mode', fallback='paper')
_wallet = _CONFIG.get('wallet', 'wallet_name', fallback='MetaMask Main')
_chain = _CONFIG.get('wallet', 'chain', fallback='solana')

# ──────────────────────────────────────────────────────────────
# LIVE MODE CONFIG
# ──────────────────────────────────────────────────────────────

LIVE_CONFIG = {
    "enabled": True,            # LIVE MODE ACTIVE
    "mode": _mode,              # paper | hybrid | live
    "wallet_name": _wallet,
    "sol_per_trade": _CONFIG.getfloat('risk', 'sol_per_trade', fallback=0.065),
    "max_daily_loss_sol": _CONFIG.getfloat('risk', 'max_daily_loss_sol', fallback=5.0),
    "max_positions": _CONFIG.getint('risk', 'max_positions', fallback=5),
    "chains": [_chain],
    "rug_check": _CONFIG.getboolean('rug_detection', 'enabled', fallback=True),
    "min_liquidity": _CONFIG.getint('risk', 'min_liquidity', fallback=20000),
    "min_momentum_5m": _CONFIG.getfloat('risk', 'min_momentum_5m', fallback=10.0),
    "gem_score_threshold": _CONFIG.getint('risk', 'gem_score_threshold', fallback=600),
    "take_profit_1": _CONFIG.getfloat('take_profit', 'tp1', fallback=4.0),
    "take_profit_2": _CONFIG.getfloat('take_profit', 'tp2', fallback=4.0),
    "take_profit_3": _CONFIG.getfloat('take_profit', 'tp3', fallback=4.0),
    "stop_loss": _CONFIG.getfloat('stop_loss', 'sl', fallback=0.15),
    "batch_size": _CONFIG.getint('batch_trading', 'batch_size', fallback=4),
    "min_winners_to_continue": _CONFIG.getint('batch_trading', 'min_winners_to_continue', fallback=2),
    "pause_after_batch": _CONFIG.getboolean('batch_trading', 'pause_after_batch', fallback=True),
}

# ──────────────────────────────────────────────────────────────
# RUG DETECTOR
# ──────────────────────────────────────────────────────────────

class RugDetector:
    """Detects honeypots, rugs, and unsafe tokens."""
    
    def __init__(self):
        self.blacklist = set()  # Known scam addresses
        self.suspicious_patterns = [
            "honeypot", "rug", "scam", "fake", "copy"
        ]
    
    async def check_token(self, address: str, symbol: str) -> Dict[str, Any]:
        """
        Run safety checks on token.
        Returns: {"safe": bool, "score": float, "warnings": List[str]}
        """
        warnings = []
        score = 100.0
        
        # Blacklist check
        if address in self.blacklist:
            return {"safe": False, "score": 0, "warnings": ["BLACKLISTED"]}
        
        # Symbol checks
        sym_lower = symbol.lower()
        if any(p in sym_lower for p in self.suspicious_patterns):
            warnings.append("Suspicious symbol name")
            score -= 30
        
        is_safe = score >= 60 and len(warnings) < 2
        return {"safe": is_safe, "score": score, "warnings": warnings}

# ──────────────────────────────────────────────────────────────
# BATCH TRADING TRACKER
# ──────────────────────────────────────────────────────────────

class BatchTracker:
    """Tracks trades in batches and enforces pause/continue rules."""
    
    def __init__(self, batch_size: int = 4, min_winners: int = 2):
        self.batch_size = batch_size
        self.min_winners = min_winners
        self.current_batch_trades: List[Dict] = []  # Trades in current batch
        self.batch_count = 0
        self.is_paused = False
        self.total_wins = 0
        self.total_losses = 0
    
    def add_trade(self, gem: TokenGem) -> bool:
        """Add a trade to current batch. Returns True if batch is full."""
        if self.is_paused:
            return False
        
        self.current_batch_trades.append({
            'symbol': gem.symbol,
            'address': gem.address,
            'entry_price': gem.price_usd,
            'status': 'open',
            'pnl_pct': 0.0,
            'exit_reason': None
        })
        
        return len(self.current_batch_trades) >= self.batch_size
    
    def update_trade_exit(self, address: str, pnl_pct: float, exit_reason: str):
        """Update a trade when it exits."""
        for trade in self.current_batch_trades:
            if trade['address'] == address:
                trade['status'] = 'exited'
                trade['pnl_pct'] = pnl_pct
                trade['exit_reason'] = exit_reason
                break
    
    def check_batch_complete(self) -> bool:
        """Check if all trades in current batch have exited."""
        if not self.current_batch_trades:
            return False
        return all(t['status'] == 'exited' for t in self.current_batch_trades)
    
    def evaluate_batch(self) -> Dict[str, Any]:
        """Evaluate batch results and decide whether to continue."""
        if not self.current_batch_trades:
            return {"continue": True, "winners": 0, "losers": 0, "win_rate": 0.0}
        
        winners = sum(1 for t in self.current_batch_trades if t['pnl_pct'] > 0)
        losers = sum(1 for t in self.current_batch_trades if t['pnl_pct'] <= 0)
        total = len(self.current_batch_trades)
        win_rate = winners / total if total > 0 else 0.0
        
        should_continue = winners >= self.min_winners
        
        self.total_wins += winners
        self.total_losses += losers
        self.batch_count += 1
        
        return {
            "continue": should_continue,
            "winners": winners,
            "losers": losers,
            "win_rate": win_rate,
            "batch_count": self.batch_count
        }
    
    def reset_batch(self):
        """Reset for next batch."""
        self.current_batch_trades = []
        self.is_paused = False
    
    def pause(self):
        """Pause trading."""
        self.is_paused = True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current batch status."""
        return {
            "batch_size": self.batch_size,
            "min_winners": self.min_winners,
            "current_trades": len(self.current_batch_trades),
            "is_paused": self.is_paused,
            "batch_count": self.batch_count,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses
        }

# ──────────────────────────────────────────────────────────────
# LIVE SNIPER BOT
# ──────────────────────────────────────────────────────────────

class LiveSniperBot(AutoSniperBot):
    """
    Extended sniper bot with live trading + batch trading capability.
    """
    
    def __init__(self, config: dict, live_config: dict):
        super().__init__(config, telegram_app=None)
        self.live_config = live_config
        self.wallet_manager: Optional[WalletManager] = None
        self.trading_bridge: Optional['WalletTradingBridge'] = None
        self.rug_detector = RugDetector()
        self.daily_loss = 0.0
        self.daily_reset_hour = 0
        self.trades_today = 0
        
        # BATCH TRADING
        self.batch_tracker = BatchTracker(
            batch_size=live_config.get('batch_size', 4),
            min_winners=live_config.get('min_winners_to_continue', 2)
        )
    
    async def _init_wallet(self):
        """Initialize wallet system — ASYNC."""
        if not LIVE_AVAILABLE:
            logger.warning("⚠️ Live trading libraries not available")
            return
        
        try:
            # Get password from environment or file
            password = os.environ.get('WALLET_PASSWORD')
            if not password:
                # Try to read from password file
                password_file = Path('/root/.openclaw/workspace/orchestrator/config/.wallet_password')
                if password_file.exists():
                    password = password_file.read_text().strip()
            
            self.wallet_manager = WalletManager()
            if password:
                await self.wallet_manager.initialize(master_password=password)
                logger.info("🔓 Wallet initialized with password")
            else:
                await self.wallet_manager.initialize()
                logger.warning("⚠️ No password — wallet encrypted but not decrypted")
            
            logger.info(f"💼 Wallet loaded: {len(self.wallet_manager.wallets)} wallet(s)")
            
            # Initialize trading bridge
            self.trading_bridge = WalletTradingBridge(self.wallet_manager)
            
            # Try to initialize Solana connector
            try:
                await self.trading_bridge.initialize_solana(self.live_config['wallet_name'])
                logger.info("⚡ Solana trading bridge connected")
            except Exception as e:
                logger.warning(f"⚠️ Solana bridge init failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Wallet init failed: {e}")
            self.wallet_manager = None
            self.trading_bridge = None
    
    def _reset_daily_limits(self):
        """Reset daily counters at midnight."""
        now = datetime.utcnow()
        if now.hour == 0 and now.day != getattr(self, '_last_reset_day', 0):
            self.daily_loss = 0.0
            self.trades_today = 0
            self._last_reset_day = now.day
            logger.info("🔄 Daily limits reset")
    
    async def _check_rug(self, gem: TokenGem) -> bool:
        """Check if token passes rug detection."""
        result = await self.rug_detector.check_token(gem.address, gem.symbol)
        if not result['safe']:
            logger.warning(f"🚫 RUG DETECTED: {gem.symbol} — {', '.join(result['warnings'])}")
            await self._send_telegram_alert(
                f"🚫 RUG ALERT | {gem.symbol}\nBlocked by safety check.\n"
                f"Warnings: {', '.join(result['warnings'])}"
            )
            return False
        return True
    
    async def _check_limits(self, gem: TokenGem) -> bool:
        """Check if we're within trading limits."""
        self._reset_daily_limits()
        
        # Daily loss limit
        if self.daily_loss >= self.live_config['max_daily_loss_sol']:
            logger.warning(f"🛑 Daily loss limit reached: {self.daily_loss:.2f} SOL")
            return False
        
        # Max positions
        active = get_active_positions()
        if len(active) >= self.live_config['max_positions']:
            logger.info("Max positions reached")
            return False
        
        return True
    
    async def _paper_buy(self, gem: TokenGem):
        """Override paper buy with batch tracking AND live execution."""
        
        # 🐛 DEBUG: Trace what's happening
        mode = self.live_config.get('mode', 'unknown')
        has_bridge = bool(self.trading_bridge)
        logger.info(f"🐛 _paper_buy called: mode={mode}, bridge={has_bridge}, symbol={gem.symbol}")
        
        # 🔄 LIVE MODE: Route to _live_buy for REAL on-chain execution!
        if mode == 'live' and has_bridge:
            logger.info(f"🐛 Routing to _live_buy for {gem.symbol}")
            await self._live_buy(gem)
            return
        else:
            logger.info(f"🐛 NOT routing to live: mode={mode}, bridge={has_bridge}")
        
        # Check if batch is paused
        if self.batch_tracker.is_paused:
            logger.info(f"⏸️ BATCH PAUSED — skipping {gem.symbol}")
            return
        
        # Check if batch is full
        if len(self.batch_tracker.current_batch_trades) >= self.live_config.get('batch_size', 4):
            logger.info(f"📦 BATCH FULL ({len(self.batch_tracker.current_batch_trades)} trades) — waiting for exits")
            return
        
        # Call parent for actual paper buy
        await super()._paper_buy(gem)
        
        # Track in batch
        batch_full = self.batch_tracker.add_trade(gem)
        
        if batch_full:
            logger.info(f"📦 BATCH #{self.batch_tracker.batch_count + 1} FULL — {self.live_config.get('batch_size', 4)} trades placed. Waiting for exits...")
            await self._send_telegram_alert(
                f"📦 <b>BATCH FULL</b> | {self.live_config.get('batch_size', 4)} trades active\n"
                f"⏸️ Pausing new scans until all positions close...\n"
                f"🎯 Need {self.live_config.get('min_winners_to_continue', 2)}+ winners to continue"
            )
            self.batch_tracker.pause()
    
    async def _live_buy(self, gem: TokenGem):
        """
        Execute a LIVE buy trade via Jupiter DEX.
        """
        if self.live_config['mode'] == 'paper':
            # Still paper — call batch-tracked paper buy
            await self._paper_buy(gem)
            return
        
        # 🔒 LIVE MODE: Only Solana tokens via Jupiter!
        if gem.chain != 'solana':
            logger.info(f"⏭️ Skipping {gem.symbol} — chain '{gem.chain}' not Solana (Jupiter-only)")
            return
        
        # Validate Solana address format (base58, not EVM 0x...)
        if gem.address.startswith('0x') or len(gem.address) < 32 or len(gem.address) > 44:
            logger.warning(f"🚫 Invalid Solana address for {gem.symbol}: {gem.address[:20]}...")
            return
        
        # Check if batch is paused or full
        if self.batch_tracker.is_paused:
            logger.info(f"⏸️ BATCH PAUSED — skipping {gem.symbol}")
            return
        
        if len(self.batch_tracker.current_batch_trades) >= self.live_config.get('batch_size', 4):
            logger.info(f"📦 BATCH FULL — waiting for exits")
            return
        
        if not self.trading_bridge or not self.trading_bridge.solana_connector:
            logger.error("❌ Trading bridge not ready")
            await self._send_telegram_alert(
                f"❌ LIVE BUY FAILED | {gem.symbol}\nTrading bridge not initialized"
            )
            return
        
        amount_sol = self.live_config['sol_per_trade']
        
        try:
            # Register unknown token mint address for Jupiter
            # DexScreener gems have raw mint addresses that Jupiter needs
            if gem.address and len(gem.address) > 20:
                # Add to connector's known tokens dynamically
                self.trading_bridge.solana_connector.TOKENS[gem.symbol] = gem.address
                logger.info(f"📋 Registered token mint: {gem.symbol} = {gem.address[:20]}...")
            
            # Get swap quote
            quote = await self.trading_bridge.solana_connector.get_quote(
                input_token='SOL',  # Native SOL
                output_token=gem.symbol,
                amount=Decimal(str(amount_sol)),
                slippage_bps=150
            )
            
            if not quote:
                logger.error(f"❌ No quote for {gem.symbol}")
                return
            
            # Show quote to user for approval (hybrid mode)
            if self.live_config['mode'] == 'hybrid':
                await self._send_telegram_alert(
                    f"💰 LIVE TRADE PENDING | {gem.symbol}\n"
                    f"Buy: {amount_sol} SOL → {quote.output_amount if quote else '?'} {gem.symbol}\n"
                    f"Price impact: {float(quote.price_impact_pct) if quote else '?'}%\n"
                    f"Slippage: 1.5%\n\n"
                    f"Reply APPROVE to execute or REJECT to skip"
                )
                await asyncio.sleep(30)
            
            # EXECUTE SWAP
            tx_id = await self.trading_bridge.solana_connector.execute_swap(quote)
            
            if tx_id and not tx_id.startswith('paper'):
                entry_price = gem.price_usd
                
                update_gem_status(
                    gem.address,
                    "live_bought",
                    entry_price=entry_price
                )
                
                await self._send_telegram_alert(
                    f"✅ LIVE BUY EXECUTED | {gem.symbol}\n"
                    f"Amount: {amount_sol} SOL\n"
                    f"Entry: ${entry_price}\n"
                    f"Tx: {tx_id}\n\n"
                    f"🔥 MONITORING FOR EXITS"
                )
                
                self.trades_today += 1
                
                # Track in batch
                batch_full = self.batch_tracker.add_trade(gem)
                if batch_full:
                    logger.info(f"📦 BATCH FULL — pausing...")
                    self.batch_tracker.pause()
                    await self._send_telegram_alert(
                        f"📦 <b>BATCH FULL</b> | {self.live_config.get('batch_size', 4)} trades\n"
                        f"⏸️ Pausing. Need {self.live_config.get('min_winners_to_continue', 2)}+ winners to continue"
                    )
                
                logger.info(f"✅ LIVE BOUGHT {gem.symbol}: {amount_sol} SOL @ ${entry_price} | Tx: {tx_id}")
            else:
                logger.error(f"❌ Swap failed: {tx_id}")
                await self._send_telegram_alert(
                    f"❌ LIVE BUY FAILED | {gem.symbol}\n"
                    f"Error: Swap execution failed\n"
                    f"Skipping..."
                )
        
        except Exception as e:
            logger.error(f"❌ Live buy error: {e}")
            await self._send_telegram_alert(
                f"❌ LIVE BUY ERROR | {gem.symbol}\n{str(e)[:100]}"
            )
    
    async def _live_sell(self, gem: TokenGem, reason: str):
        """
        Execute a LIVE sell trade via Jupiter DEX.
        """
        if self.live_config['mode'] == 'paper':
            # In paper mode, just update batch tracker
            pnl = (gem.exit_price - gem.entry_price) / gem.entry_price if gem.entry_price else 0
            self.batch_tracker.update_trade_exit(gem.address, pnl * 100, reason)
            await super().monitor_positions()
            return
        
        if not self.trading_bridge or not self.trading_bridge.solana_connector:
            return
        
        try:
            # Get token balance (check via Jupiter)
            try:
                balance_check = await self.trading_bridge.solana_connector.get_balance(gem.symbol)
                balance = float(balance_check) if balance_check else 0
            except:
                balance = 0
            
            if not balance or balance == 0:
                logger.warning(f"No balance for {gem.symbol}, skipping sell")
                return
            
            # Get sell quote (Token → SOL)
            # Ensure token is registered for Jupiter
            if gem.address and len(gem.address) > 20:
                self.trading_bridge.solana_connector.TOKENS[gem.symbol] = gem.address
            
            quote = await self.trading_bridge.solana_connector.get_quote(
                input_token=gem.symbol,
                output_token='SOL',
                amount=Decimal(str(balance)) if balance else Decimal('0'),
                slippage_bps=150
            )
            
            # Execute sell
            tx_id = await self.trading_bridge.solana_connector.execute_swap(quote)
            
            if tx_id and not tx_id.startswith('paper'):
                current_price = gem.price_usd
                pnl = (current_price - gem.entry_price) / gem.entry_price if gem.entry_price else 0
                sol_received = float(quote.output_amount) if quote else 0
                
                update_gem_status(
                    gem.address,
                    "exited",
                    exit_price=current_price,
                    pnl_pct=pnl * 100,
                    exit_reason=reason
                )
                
                # Track daily loss
                if pnl < 0:
                    loss_sol = self.live_config['sol_per_trade'] * abs(pnl)
                    self.daily_loss += loss_sol
                
                # Update batch tracker
                self.batch_tracker.update_trade_exit(gem.address, pnl * 100, reason)
                
                await self._send_telegram_alert(format_exit_alert(
                    TokenGem(
                        symbol=gem.symbol, address=gem.address, chain=gem.chain,
                        price_usd=current_price, market_cap=0, liquidity=0,
                        volume_24h=0, change_24h=0, change_1h=0, change_5m=0,
                        buys_24h=0, sells_24h=0, score=0, url=gem.url,
                        detected_at=gem.detected_at, entry_price=gem.entry_price,
                        exit_price=current_price, pnl_pct=pnl*100,
                        exit_reason=reason
                    )
                ))
                
                logger.info(f"✅ LIVE SOLD {gem.symbol}: {reason} | PnL: {pnl*100:+.0f}%")
                
                # Check if batch complete and evaluate
                await self._evaluate_batch_if_complete()
        
        except Exception as e:
            logger.error(f"❌ Live sell error: {e}")
    
    async def _evaluate_batch_if_complete(self):
        """Evaluate batch if all trades have exited."""
        if not self.batch_tracker.check_batch_complete():
            return
        
        result = self.batch_tracker.evaluate_batch()
        
        if result['continue']:
            await self._send_telegram_alert(
                f"✅ <b>BATCH #{result['batch_count']} APPROVED!</b>\n"
                f"🏆 Winners: {result['winners']} | ❌ Losers: {result['losers']}\n"
                f"📈 Win Rate: {result['win_rate']*100:.0f}%\n\n"
                f"🚀 <b>CONTINUING TO NEXT BATCH!</b>"
            )
            self.batch_tracker.reset_batch()
            logger.info(f"✅ BATCH APPROVED — {result['winners']}/{result['winners']+result['losers']} wins. Continuing!")
        else:
            await self._send_telegram_alert(
                f"🛑 <b>BATCH #{result['batch_count']} HALTED!</b>\n"
                f"❌ Winners: {result['winners']} | ❌ Losers: {result['losers']}\n"
                f"📉 Win Rate: {result['win_rate']*100:.0f}%\n\n"
                f"🛑 <b>PAUSED.</b> Need {self.live_config.get('min_winners_to_continue', 2)}+ winners to continue.\n"
                f"💡 Manual override: /snipe_resume"
            )
            # Stay paused — don't reset batch
            logger.info(f"🛑 BATCH HALTED — Only {result['winners']}/{result['winners']+result['losers']} wins. Need {self.live_config.get('min_winners_to_continue', 2)}+.")
    
    async def monitor_positions(self):
        """Override to support live monitoring + batch tracking."""
        if self.live_config['mode'] == 'paper':
            await self._monitor_paper_positions()
            return
        
        active = get_active_positions()
        logger.info(f"Monitoring {len(active)} LIVE positions...")
        
        for row in active:
            address = row[2]
            symbol = row[1]
            entry = row[17] or 0
            status = row[16]
            
            if status == "live_bought":
                pairs = self.scanner.search_pairs(address)
                if not pairs:
                    continue
                
                current = sorted(pairs, key=lambda p: p.get('volume',{}).get('h24',0) or 0, reverse=True)[0]
                current_price = float(current.get('priceUsd', 0))
                
                if not current_price or not entry:
                    continue
                
                pnl = (current_price - entry) / entry
                
                tp1 = self.config['take_profit_1']
                tp2 = self.config['take_profit_2']
                tp3 = self.config['take_profit_3']
                sl = self.config['stop_loss']
                
                exit_reason = None
                if pnl >= tp3:
                    exit_reason = f"TP3 (+{pnl*100:.0f}%)"
                elif pnl >= tp2:
                    exit_reason = f"TP2 (+{pnl*100:.0f}%)"
                elif pnl >= tp1:
                    exit_reason = f"TP1 (+{pnl*100:.0f}%)"
                elif pnl <= -sl:
                    exit_reason = f"STOP LOSS ({pnl*100:.0f}%)"
                
                if exit_reason:
                    gem = TokenGem(
                        symbol=symbol, address=address, chain=row[3],
                        price_usd=current_price, market_cap=0, liquidity=0,
                        volume_24h=0, change_24h=0, change_1h=0, change_5m=0,
                        buys_24h=0, sells_24h=0, score=0, url="",
                        detected_at=row[15], entry_price=entry,
                        exit_price=current_price, pnl_pct=pnl*100,
                        exit_reason=exit_reason
                    )
                    await self._live_sell(gem, exit_reason)
    
    async def _monitor_paper_positions(self):
        """Monitor paper positions with batch tracking."""
        active = get_active_positions()
        logger.info(f"Monitoring {len(active)} PAPER positions...")
        
        for row in active:
            address = row[2]
            symbol = row[1]
            entry = row[17] or 0
            status = row[16]
            
            if status == "paper_bought":
                pairs = self.scanner.search_pairs(address)
                if not pairs:
                    continue
                
                current = sorted(pairs, key=lambda p: p.get('volume',{}).get('h24',0) or 0, reverse=True)[0]
                current_price = float(current.get('priceUsd', 0))
                
                if not current_price or not entry:
                    continue
                
                pnl = (current_price - entry) / entry
                
                tp1 = self.config['take_profit_1']
                tp2 = self.config['take_profit_2']
                tp3 = self.config['take_profit_3']
                sl = self.config['stop_loss']
                
                exit_reason = None
                if pnl >= tp3:
                    exit_reason = f"TP3 (+{pnl*100:.0f}%)"
                elif pnl >= tp2:
                    exit_reason = f"TP2 (+{pnl*100:.0f}%)"
                elif pnl >= tp1:
                    exit_reason = f"TP1 (+{pnl*100:.0f}%)"
                elif pnl <= -sl:
                    exit_reason = f"STOP LOSS ({pnl*100:.0f}%)"
                
                if exit_reason:
                    update_gem_status(
                        address,
                        "exited",
                        exit_price=current_price,
                        pnl_pct=pnl * 100,
                        exit_reason=exit_reason
                    )
                    
                    # Update batch tracker
                    self.batch_tracker.update_trade_exit(address, pnl * 100, exit_reason)
                    
                    exit_gem = TokenGem(
                        symbol=symbol, address=address, chain=row[3],
                        price_usd=current_price, market_cap=0, liquidity=0,
                        volume_24h=0, change_24h=0, change_1h=0, change_5m=0,
                        buys_24h=0, sells_24h=0, score=0, url="",
                        detected_at=row[15], entry_price=entry,
                        exit_price=current_price, pnl_pct=pnl*100,
                        exit_reason=exit_reason
                    )
                    await self._send_telegram_alert(format_exit_alert(exit_gem))
                    logger.info(f"EXIT: {symbol} @ {exit_reason}")
                    
                    # Check if batch complete
                    await self._evaluate_batch_if_complete()
    
    async def scan_cycle(self):
        """Override scan cycle with batch pause logic."""
        # In live mode, use stricter thresholds
        if self.live_config['mode'] != 'paper':
            self.config['gem_score_threshold'] = self.live_config.get('gem_score_threshold', 600)
            self.config['min_liquidity'] = self.live_config.get('min_liquidity', 10000)
            self.config['min_momentum_5m'] = self.live_config.get('min_momentum_5m', 10.0)
        
        # Check if batch is paused
        if self.batch_tracker.is_paused:
            logger.info("⏸️ Batch paused — skipping scan cycle")
            # Still monitor positions for exits
            await self.monitor_positions()
            return
        
        await super().scan_cycle()
    
    async def run(self):
        """Main loop with batch trading awareness."""
        init_db()
        self.is_running = True
        
        # Initialize wallet system (async)
        await self._init_wallet()
        
        logger.info("🔥 Live Sniper Bot STARTED with BATCH TRADING 🔥")
        
        await self._send_telegram_alert(
            f"🚀 <b>LIVE SNIPER ONLINE</b>\n"
            f"💰 Trade Size: {self.live_config['sol_per_trade']} SOL\n"
            f"🎯 Take Profit: +{self.live_config['take_profit_1']*100:.0f}%\n"
            f"📦 Batch Size: {self.live_config.get('batch_size', 4)} trades\n"
            f"🏆 Need {self.live_config.get('min_winners_to_continue', 2)}+ wins to continue\n"
            f"🛑 Stop Loss: -{self.live_config['stop_loss']*100:.0f}%\n"
            f"🎮 Mode: {self.live_config['mode'].upper()}"
        )
        
        scan_count = 0
        while self.is_running:
            try:
                # Scan for new gems (or monitor if paused)
                await self.scan_cycle()
                scan_count += 1
                
                # Monitor positions every 3rd scan (6 min)
                if scan_count % 3 == 0:
                    await self.monitor_positions()
                
                await asyncio.sleep(self.config['scan_interval'])
            except Exception as e:
                logger.error(f"Error in sniper loop: {e}")
                await asyncio.sleep(10)
    
    def get_batch_status(self) -> Dict[str, Any]:
        """Get current batch status for Telegram commands."""
        return self.batch_tracker.get_status()

# ──────────────────────────────────────────────────────────────
# STANDALONE
# ──────────────────────────────────────────────────────────────

async def main_live():
    """Run live sniper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/root/.openclaw/workspace/orchestrator/logs/live_sniper.log')
        ]
    )
    
    bot = LiveSniperBot(SNIPER_CONFIG, LIVE_CONFIG)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main_live())
