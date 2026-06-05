#!/usr/bin/env python3
"""
🛡️ TOKEN SAFETY ANALYZER v2.0 — Rug Pull & Scam Detection
Enhanced with real contract analysis, FDV filtering, liquidity locks,
pump.fun detection, and dev wallet history.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field


@dataclass
class SafetyReport:
    """Complete safety report for a token."""
    token_address: str
    symbol: str
    
    # Contract analysis
    is_mintable: bool = True
    mint_authority: Optional[str] = None
    freeze_authority: Optional[str] = None
    has_honeypot: bool = False
    has_blacklist: bool = False
    has_pause_function: bool = False
    ownership_renounced: bool = False
    
    # Dev analysis
    dev_wallet: str = ""
    dev_history: List[Dict] = field(default_factory=list)
    dev_rug_count: int = 0
    dev_success_count: int = 0
    
    # Liquidity & Market
    liquidity_usd: float = 0.0
    fdv: float = 0.0
    market_cap: float = 0.0
    volume_24h: float = 0.0
    liquidity_locked: bool = False
    liquidity_lock_duration: float = 0.0  # days
    lp_tokens_burned: bool = False
    
    # Holder analysis
    holder_count: int = 0
    top_holder_pct: float = 0.0
    top_5_holders_pct: float = 0.0
    
    # Pump.fun specific
    is_pump_fun: bool = False
    pump_fun_stage: str = "unknown"  # bonding, graduated, unknown
    bonding_curve_progress: float = 0.0
    
    # Overall score (0-100, lower = safer)
    risk_score: float = 100.0
    is_safe: bool = False
    is_tradeable: bool = False  # Meets ALL criteria for trading
    
    # Red flags
    red_flags: List[str] = field(default_factory=list)
    
    # Trading criteria failures
    failures: List[str] = field(default_factory=list)


class TokenSafetyAnalyzer:
    """
    Advanced token safety analyzer.
    Integrates RugCheck, DexScreener, Solana RPC, and pump.fun data.
    """
    
    # Trading thresholds — MUST ALL pass for trade
    MIN_LIQUIDITY_USD = 20000
    MIN_FDV_USD = 50000
    MIN_VOLUME_24H = 25000
    MIN_HOLDERS = 50
    MAX_TOP_HOLDER_PCT = 20.0
    MAX_TOP5_HOLDERS_PCT = 50.0
    MIN_LIQUIDITY_LOCK_DAYS = 7
    MAX_RISK_SCORE = 50  # Lower is safer
    
    # Pump.fun specific
    MAX_BONDING_CURVE_PROGRESS = 95.0  # Don't trade if >95% bonding
    
    def __init__(self):
        self.known_scam_patterns = [
            "honeypot", "blacklist", "mint", "pause", "selfdestruct",
            "reentrancy", "owner", "unlimited"
        ]
        
        # Known rug pull devs (populate from DB/history)
        self.known_rugger_wallets: Set[str] = set()
        
        # Load known ruggers
        self.load_known_ruggers()
    
    def load_known_ruggers(self):
        """Load known rug pull wallets from history."""
        try:
            with open("/root/.openclaw/workspace/agents/logs/known_ruggers.json", 'r') as f:
                data = json.load(f)
                self.known_rugger_wallets = set(data.get("wallets", []))
        except FileNotFoundError:
            pass
    
    def save_known_rugger(self, wallet: str, token: str):
        """Save a known rugger wallet."""
        if not wallet or wallet in self.known_rugger_wallets:
            return
        self.known_rugger_wallets.add(wallet)
        try:
            path = "/root/.openclaw/workspace/agents/logs/known_ruggers.json"
            data = {"wallets": list(self.known_rugger_wallets)}
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    async def analyze_token(self, session: aiohttp.ClientSession,
                           token_address: str) -> SafetyReport:
        """Full safety analysis with ALL checks."""
        
        report = SafetyReport(token_address=token_address, symbol="")
        
        # 1. Fetch DexScreener data (market data)
        dex_data = await self._fetch_dexscreener_data(session, token_address)
        if dex_data:
            report.symbol = dex_data.get("symbol", "UNKNOWN")
            report.liquidity_usd = dex_data.get("liquidity", 0)
            report.fdv = dex_data.get("fdv", 0)
            report.market_cap = dex_data.get("marketCap", 0)
            report.volume_24h = dex_data.get("volume_24h", 0)
            report.holder_count = dex_data.get("holder_count", 0)
            
            # Check if pump.fun
            report.is_pump_fun = dex_data.get("is_pump_fun", False)
            report.pump_fun_stage = dex_data.get("pump_fun_stage", "unknown")
            report.bonding_curve_progress = dex_data.get("bonding_curve_progress", 0)
        
        # 2. Fetch RugCheck report (contract analysis)
        rugcheck_data = await self._fetch_rugcheck(session, token_address)
        if rugcheck_data:
            report.is_mintable = rugcheck_data.get("mintable", True)
            report.mint_authority = rugcheck_data.get("mint_authority")
            report.freeze_authority = rugcheck_data.get("freeze_authority")
            report.has_honeypot = rugcheck_data.get("is_honeypot", False)
            report.has_blacklist = rugcheck_data.get("has_blacklist", False)
            report.has_pause_function = rugcheck_data.get("has_pause", False)
            report.ownership_renounced = rugcheck_data.get("owner_renounced", False)
            report.dev_wallet = rugcheck_data.get("creator", "")
            
            # Top holders from RugCheck
            holders = rugcheck_data.get("top_holders", [])
            if holders:
                report.top_holder_pct = holders[0].get("pct", 0) if holders else 0
                report.top_5_holders_pct = sum(h.get("pct", 0) for h in holders[:5])
                report.holder_count = max(report.holder_count, len(holders))
            
            # Liquidity lock info
            lp_data = rugcheck_data.get("lp", {})
            if lp_data:
                report.liquidity_locked = lp_data.get("locked", False)
                report.liquidity_lock_duration = lp_data.get("lock_days", 0)
                report.lp_tokens_burned = lp_data.get("burned", False)
            
            # Check dev history
            if report.dev_wallet:
                if report.dev_wallet in self.known_rugger_wallets:
                    report.dev_rug_count = 999  # Known rugger
                # Could fetch dev history from API here
        
        # 3. Calculate risk score
        report.risk_score = self._calculate_risk_score(report)
        report.is_safe = report.risk_score < self.MAX_RISK_SCORE
        
        # 4. Generate red flags
        report.red_flags = self._generate_red_flags(report)
        
        # 5. Check trading criteria
        report.is_tradeable, report.failures = self._check_tradeable(report)
        
        return report
    
    def _calculate_risk_score(self, report: SafetyReport) -> float:
        """Calculate risk score 0-100 (lower = safer)."""
        score = 0.0
        
        # Critical risks
        if report.has_honeypot:
            score += 50  # CANNOT SELL
        if report.dev_rug_count > 0:
            score += 40  # Known rugger
        if report.has_blacklist:
            score += 25
        if report.is_mintable and not report.ownership_renounced:
            score += 20  # Can mint more + owns contract
        if report.has_pause_function:
            score += 15
        if not report.ownership_renounced:
            score += 10
        
        # Market risks
        if report.liquidity_usd < 5000:
            score += 30
        elif report.liquidity_usd < 20000:
            score += 15
        
        if report.fdv < 10000:
            score += 20
        elif report.fdv < 50000:
            score += 10
        
        if report.volume_24h < 1000:
            score += 15
        elif report.volume_24h < 5000:
            score += 5
        
        # Holder concentration
        if report.top_holder_pct > 50:
            score += 30
        elif report.top_holder_pct > 20:
            score += 15
        
        if report.top_5_holders_pct > 80:
            score += 20
        elif report.top_5_holders_pct > 50:
            score += 10
        
        # Low holders
        if report.holder_count < 10:
            score += 20
        elif report.holder_count < 50:
            score += 10
        
        # Liquidity lock
        if not report.liquidity_locked and not report.lp_tokens_burned:
            score += 15
        elif report.liquidity_locked and report.liquidity_lock_duration < 7:
            score += 10
        
        # Pump.fun specific
        if report.is_pump_fun:
            score += 10  # Base risk for pump.fun
            if report.bonding_curve_progress > 95:
                score += 15  # About to graduate or rug
        
        return min(100, score)
    
    def _generate_red_flags(self, report: SafetyReport) -> List[str]:
        """Generate red flags list."""
        flags = []
        
        if report.has_honeypot:
            flags.append("🔴 HONEYPOT — Cannot sell!")
        if report.dev_rug_count > 0:
            flags.append(f"🔴 Known rugger dev: {report.dev_wallet[:8]}...")
        if report.has_blacklist:
            flags.append("🟠 Has blacklist function")
        if report.is_mintable and not report.ownership_renounced:
            flags.append("🟠 Dev can mint + owns contract")
        elif report.is_mintable:
            flags.append("🟠 Can mint more tokens")
        if report.has_pause_function:
            flags.append("🟠 Trading can be paused")
        if not report.ownership_renounced:
            flags.append("🟡 Ownership not renounced")
        if report.top_holder_pct > 20:
            flags.append(f"🟡 Top holder: {report.top_holder_pct:.1f}%")
        if report.top_5_holders_pct > 50:
            flags.append(f"🟡 Top 5 holders: {report.top_5_holders_pct:.1f}%")
        if not report.liquidity_locked and not report.lp_tokens_burned:
            flags.append("🟡 Liquidity NOT locked")
        if report.liquidity_usd < 20000:
            flags.append(f"🟡 Low liquidity: ${report.liquidity_usd:,.0f}")
        if report.fdv < 50000:
            flags.append(f"🟡 Low FDV: ${report.fdv:,.0f}")
        if report.holder_count < 50:
            flags.append(f"🟡 Few holders: {report.holder_count}")
        if report.is_pump_fun and report.bonding_curve_progress > 90:
            flags.append(f"🟡 Pump.fun bonding: {report.bonding_curve_progress:.1f}%")
        
        return flags
    
    def _check_tradeable(self, report: SafetyReport) -> tuple[bool, List[str]]:
        """Check if token meets ALL trading criteria."""
        failures = []
        
        # Must pass ALL these
        if report.liquidity_usd < self.MIN_LIQUIDITY_USD:
            failures.append(f"Liquidity ${report.liquidity_usd:,.0f} < ${self.MIN_LIQUIDITY_USD:,.0f}")
        
        if report.fdv < self.MIN_FDV_USD:
            failures.append(f"FDV ${report.fdv:,.0f} < ${self.MIN_FDV_USD:,.0f}")
        
        if report.volume_24h < self.MIN_VOLUME_24H:
            failures.append(f"Volume ${report.volume_24h:,.0f} < ${self.MIN_VOLUME_24H:,.0f}")
        
        if report.holder_count < self.MIN_HOLDERS:
            failures.append(f"Holders {report.holder_count} < {self.MIN_HOLDERS}")
        
        if report.top_holder_pct > self.MAX_TOP_HOLDER_PCT:
            failures.append(f"Top holder {report.top_holder_pct:.1f}% > {self.MAX_TOP_HOLDER_PCT}%")
        
        if report.top_5_holders_pct > self.MAX_TOP5_HOLDERS_PCT:
            failures.append(f"Top 5 {report.top_5_holders_pct:.1f}% > {self.MAX_TOP5_HOLDERS_PCT}%")
        
        if report.risk_score >= self.MAX_RISK_SCORE:
            failures.append(f"Risk score {report.risk_score:.0f} >= {self.MAX_RISK_SCORE}")
        
        if report.has_honeypot:
            failures.append("HONEYPOT — Cannot sell!")
        
        if report.is_pump_fun and report.bonding_curve_progress > self.MAX_BONDING_CURVE_PROGRESS:
            failures.append(f"Pump.fun bonding {report.bonding_curve_progress:.1f}% > {self.MAX_BONDING_CURVE_PROGRESS}%")
        
        return len(failures) == 0, failures
    
    async def _fetch_dexscreener_data(self, session: aiohttp.ClientSession,
                                       token_address: str) -> Optional[Dict]:
        """Fetch token data from DexScreener."""
        try:
            async with session.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if not pairs:
                        return None
                    
                    # Get the best pair (highest liquidity)
                    best_pair = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
                    
                    lp = best_pair.get("liquidity", {})
                    vol = best_pair.get("volume", {})
                    base = best_pair.get("baseToken", {})
                    
                    # Detect pump.fun
                    is_pump_fun = "pump" in str(best_pair.get("url", "")).lower() or \
                                  "pump" in str(best_pair.get("marketId", "")).lower()
                    
                    return {
                        "symbol": base.get("symbol", "UNKNOWN"),
                        "liquidity": lp.get("usd", 0) or 0,
                        "fdv": best_pair.get("fdv", 0) or 0,
                        "marketCap": best_pair.get("marketCap", 0) or 0,
                        "volume_24h": vol.get("h24", 0) or 0,
                        "holder_count": best_pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0,
                        "is_pump_fun": is_pump_fun,
                        "pump_fun_stage": "bonding" if is_pump_fun else "unknown",
                        "bonding_curve_progress": 0,  # Would need pump.fun API
                    }
        except Exception as e:
            print(f"[SAFETY] DexScreener error: {e}")
        return None
    
    async def _fetch_rugcheck(self, session: aiohttp.ClientSession,
                              token_address: str) -> Optional[Dict]:
        """Fetch RugCheck report."""
        try:
            async with session.get(
                f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report",
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract risks
                    risks = data.get("risks", [])
                    risk_names = [r.get("name", "").lower() for r in risks]
                    
                    # Token metadata
                    token_meta = data.get("token", {})
                    token_prog = data.get("tokenProgram", "")
                    
                    # Mint/Freeze authority
                    mint_auth = token_meta.get("mintAuthority")
                    freeze_auth = token_meta.get("freezeAuthority")
                    
                    # Top holders
                    holders = data.get("topHolders", [])
                    
                    # LP info
                    lp = data.get("markets", [{}])[0] if data.get("markets") else {}
                    
                    return {
                        "mintable": mint_auth is not None,
                        "mint_authority": mint_auth,
                        "freeze_authority": freeze_auth,
                        "is_honeypot": any("honeypot" in r or "rugged" in r for r in risk_names),
                        "has_blacklist": any("blacklist" in r for r in risk_names),
                        "has_pause": any("freeze" in r or "pause" in r for r in risk_names),
                        "owner_renounced": mint_auth is None and freeze_auth is None,
                        "creator": data.get("creator", ""),
                        "top_holders": [
                            {
                                "address": h.get("address", ""),
                                "pct": h.get("pct", 0)
                            }
                            for h in holders[:10]
                        ],
                        "lp": {
                            "locked": any("locked" in r or "burn" in r for r in risk_names),
                            "burned": any("burn" in r for r in risk_names),
                            "lock_days": 0,  # Not always available
                        }
                    }
        except Exception as e:
            print(f"[SAFETY] RugCheck error: {e}")
        return None
    
    def quick_safety_check(self, token_data: Dict) -> Dict:
        """Quick safety check without API calls (uses cached DexScreener data)."""
        
        red_flags = []
        score = 0
        failures = []
        
        liquidity = token_data.get("liquidity", 0)
        fdv = token_data.get("fdv", 0)
        volume = token_data.get("volume_24h", 0)
        holders = token_data.get("holder_count", 0)
        
        # Liquidity
        if liquidity < 20000:
            red_flags.append(f"Low liquidity: ${liquidity:,.0f}")
            score += 20
            failures.append(f"Liquidity ${liquidity:,.0f} < $20K")
        
        # FDV
        if fdv < 50000:
            red_flags.append(f"Low FDV: ${fdv:,.0f}")
            score += 15
            failures.append(f"FDV ${fdv:,.0f} < $50K")
        
        # Volume
        if volume < 25000:
            red_flags.append(f"Low volume: ${volume:,.0f}")
            score += 10
            failures.append(f"Volume ${volume:,.0f} < $25K")
        
        # Holders
        if holders < 50:
            red_flags.append(f"Few holders: {holders}")
            score += 10
            failures.append(f"Holders {holders} < 50")
        
        # Price stability
        changes = token_data.get("changes", {})
        h24 = abs(changes.get("h24", 0))
        if h24 > 1000:
            red_flags.append("Extreme 24h volatility")
            score += 10
        
        is_tradeable = len(failures) == 0 and score < 50
        
        return {
            "score": min(100, score),
            "is_safe": score < 50,
            "is_tradeable": is_tradeable,
            "red_flags": red_flags,
            "failures": failures,
        }


if __name__ == "__main__":
    analyzer = TokenSafetyAnalyzer()
    print("🛡️ Token Safety Analyzer v2.0 initialized")
    print(f"   MIN LIQUIDITY: ${analyzer.MIN_LIQUIDITY_USD:,.0f}")
    print(f"   MIN FDV: ${analyzer.MIN_FDV_USD:,.0f}")
    print(f"   MIN HOLDERS: {analyzer.MIN_HOLDERS}")
    print(f"   MAX RISK SCORE: {analyzer.MAX_RISK_SCORE}")
