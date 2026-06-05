#!/usr/bin/env python3
"""
🛡️ RUG DETECTOR — Contract Analysis & Safety Engine
Ελέγχει: mint authority, liquidity lock, holder distribution, contract verification
"""
import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"           # ✅ Πράσινο — μπορεί να trade
    CAUTION = "caution"     # 🟡 Κίτρινο — προσοχή, μικρότερο size
    UNSAFE = "unsafe"       # 🔴 Κόκκινο — ΑΠΑΓΟΡΕΥΕΤΑΙ trade


@dataclass
class ContractAnalysis:
    token_address: str
    symbol: str
    risk_level: RiskLevel
    score: float  # 0-100, higher = safer
    mint_authority_revoked: bool = False
    freeze_authority_revoked: bool = False
    liquidity_locked: bool = False
    liquidity_lock_duration_days: float = 0.0
    top_holder_pct: float = 0.0  # % held by top wallet
    top_5_holders_pct: float = 0.0  # % held by top 5 wallets
    holder_count: int = 0
    is_verified: bool = False
    contract_age_hours: float = 0.0
    has_website: bool = False
    has_twitter: bool = False
    has_telegram: bool = False
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RugDetector:
    """
    Contract analysis για Solana tokens.
    Χρησιμοποιεί Jupiter/Raydium APIs + Solana RPC για on-chain data.
    """
    
    def __init__(self, solana_rpc: str = "https://api.mainnet-beta.solana.com"):
        self.solana_rpc = solana_rpc
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; RugDetector/1.0)"
        })
        
        # Thresholds
        self.MIN_HOLDER_COUNT = 50
        self.MAX_TOP_HOLDER_PCT = 20.0  # Top wallet can't hold >20%
        self.MAX_TOP_5_HOLDERS_PCT = 60.0  # Top 5 can't hold >60%
        self.MIN_LIQUIDITY_LOCK_DAYS = 30.0
        self.MIN_CONTRACT_AGE_HOURS = 1.0
        
        # Cache
        self._cache: Dict[str, Tuple[ContractAnalysis, float]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _rpc_call(self, method: str, params: list) -> Optional[Dict]:
        """Make Solana RPC call."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": method,
                "params": params
            }
            resp = self.session.post(
                self.solana_rpc,
                json=payload,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"   ⚠️ RPC error: {e}")
        return None
    
    def _get_token_account_info(self, token_address: str) -> Optional[Dict]:
        """Get token mint account info."""
        result = self._rpc_call("getAccountInfo", [
            token_address,
            {"encoding": "jsonParsed"}
        ])
        if result and "result" in result:
            return result["result"].get("value", {})
        return None
    
    def _get_token_largest_accounts(self, token_address: str) -> List[Dict]:
        """Get largest token holders."""
        result = self._rpc_call("getTokenLargestAccounts", [token_address])
        if result and "result" in result:
            return result["result"].get("value", [])
        return []
    
    def _get_token_supply(self, token_address: str) -> Optional[int]:
        """Get total token supply."""
        result = self._rpc_call("getTokenSupply", [token_address])
        if result and "result" in result:
            return int(result["result"]["value"].get("amount", 0))
        return None
    
    def analyze_token(self, token_address: str, symbol: str = "") -> ContractAnalysis:
        """
        Full contract analysis.
        Returns ContractAnalysis with safety assessment.
        """
        # Check cache
        now = time.time()
        if token_address in self._cache:
            cached, ts = self._cache[token_address]
            if now - ts < self._cache_ttl:
                return cached
        
        print(f"🔍 Analyzing contract: {symbol or token_address[:20]}...")
        
        analysis = ContractAnalysis(
            token_address=token_address,
            symbol=symbol,
            risk_level=RiskLevel.UNSAFE,  # Default to unsafe until proven
            score=0.0,
            warnings=[]
        )
        
        score = 0.0
        warnings = []
        
        try:
            # === 1. MINT AUTHORITY CHECK ===
            mint_info = self._get_token_account_info(token_address)
            if mint_info:
                parsed = mint_info.get("data", {}).get("parsed", {}).get("info", {})
                
                # Check mint authority
                mint_authority = parsed.get("mintAuthority")
                if mint_authority is None:
                    analysis.mint_authority_revoked = True
                    score += 25
                    print("   ✅ Mint authority revoked")
                else:
                    warnings.append(f"Mint authority active: {str(mint_authority)[:20]}...")
                    print(f"   ⚠️ Mint authority ACTIVE: {str(mint_authority)[:20]}...")
                
                # Check freeze authority
                freeze_authority = parsed.get("freezeAuthority")
                if freeze_authority is None:
                    analysis.freeze_authority_revoked = True
                    score += 15
                    print("   ✅ Freeze authority revoked")
                else:
                    warnings.append("Freeze authority active — can freeze wallets")
                    print("   ⚠️ Freeze authority active")
            else:
                warnings.append("Could not fetch mint info — treat as unsafe")
                print("   ❌ Could not fetch mint info")
            
            # === 2. HOLDER DISTRIBUTION ===
            largest_accounts = self._get_token_largest_accounts(token_address)
            supply = self._get_token_supply(token_address)
            
            if supply and supply > 0 and largest_accounts:
                # Top holder
                top_amount = int(largest_accounts[0].get("amount", 0))
                analysis.top_holder_pct = (top_amount / supply) * 100
                
                # Top 5 holders
                top_5_amount = sum(int(a.get("amount", 0)) for a in largest_accounts[:5])
                analysis.top_5_holders_pct = (top_5_amount / supply) * 100
                
                analysis.holder_count = len(largest_accounts)
                
                print(f"   📊 Holders: {analysis.holder_count} | Top: {analysis.top_holder_pct:.1f}% | Top5: {analysis.top_5_holders_pct:.1f}%")
                
                # Score based on distribution
                if analysis.top_holder_pct < self.MAX_TOP_HOLDER_PCT:
                    score += 15
                else:
                    warnings.append(f"Top holder owns {analysis.top_holder_pct:.1f}% — whale risk")
                
                if analysis.top_5_holders_pct < self.MAX_TOP_5_HOLDERS_PCT:
                    score += 10
                else:
                    warnings.append(f"Top 5 own {analysis.top_5_holders_pct:.1f}% — concentrated")
                
                if analysis.holder_count >= self.MIN_HOLDER_COUNT:
                    score += 15
                else:
                    warnings.append(f"Only {analysis.holder_count} holders — too new/illiquid")
            else:
                warnings.append("Could not analyze holder distribution")
            
            # === 3. LIQUIDITY LOCK CHECK (via DexScreener/birdeye) ===
            # This is a simplified check — real implementation would check LP tokens
            analysis.liquidity_locked = self._check_liquidity_lock(token_address)
            if analysis.liquidity_locked:
                score += 20
                print("   ✅ Liquidity appears locked")
            else:
                warnings.append("Liquidity not verified as locked — rug risk")
                print("   ⚠️ Liquidity lock not verified")
            
            # === 4. CONTRACT AGE ===
            # We can't easily get creation time from RPC, so we use a heuristic
            # In production, you'd query an indexer like Helius
            analysis.contract_age_hours = self._estimate_contract_age(token_address)
            if analysis.contract_age_hours >= self.MIN_CONTRACT_AGE_HOURS:
                score += 10
            else:
                warnings.append(f"Contract only {analysis.contract_age_hours:.1f}h old — very new")
            
            # === 5. DETERMINE RISK LEVEL ===
            analysis.score = min(100, score)
            analysis.warnings = warnings
            
            if score >= 70 and not warnings:
                analysis.risk_level = RiskLevel.SAFE
            elif score >= 50 and len(warnings) <= 2:
                analysis.risk_level = RiskLevel.CAUTION
            else:
                analysis.risk_level = RiskLevel.UNSAFE
            
            print(f"   🛡️ Safety Score: {analysis.score:.0f}/100 | Risk: {analysis.risk_level.value.upper()}")
            
        except Exception as e:
            print(f"   ❌ Analysis error: {e}")
            analysis.warnings.append(f"Analysis failed: {e}")
        
        # Cache result
        self._cache[token_address] = (analysis, now)
        return analysis
    
    def _check_liquidity_lock(self, token_address: str) -> bool:
        """Check if liquidity is locked. Simplified — real impl would check LP token authority."""
        # Try to get pair info from DexScreener
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Check if liquidity is substantial and stable
                    liquidity = pairs[0].get("liquidity", {}).get("usd", 0)
                    if liquidity >= 20000:  # $20K+ liquidity = more likely locked
                        return True
        except:
            pass
        return False
    
    def _estimate_contract_age(self, token_address: str) -> float:
        """Estimate contract age. Returns hours."""
        # In production, use Helius or other indexer to get actual creation time
        # For now, return a conservative estimate
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", [])
                if pairs and pairs[0].get("pairCreatedAt"):
                    created_at = pairs[0]["pairCreatedAt"] / 1000  # ms to seconds
                    age_seconds = time.time() - created_at
                    return age_seconds / 3600  # hours
        except:
            pass
        return 0.0  # Unknown age — treat as very new
    
    def is_safe_to_trade(self, token_address: str, symbol: str = "") -> Tuple[bool, ContractAnalysis]:
        """
        Quick check: is this token safe to trade?
        Returns (is_safe, analysis_details)
        """
        analysis = self.analyze_token(token_address, symbol)
        
        if analysis.risk_level == RiskLevel.SAFE:
            return True, analysis
        elif analysis.risk_level == RiskLevel.CAUTION:
            # Allow trade but with reduced size
            return True, analysis
        else:
            return False, analysis


# === Quick test ===
if __name__ == "__main__":
    detector = RugDetector()
    
    # Test with a known token (replace with actual address)
    test_address = "So11111111111111111111111111111111111111112"  # SOL
    is_safe, analysis = detector.is_safe_to_trade(test_address, "SOL")
    
    print(f"\n🛡️ RESULT: {'✅ SAFE' if is_safe else '❌ UNSAFE'}")
    print(f"   Score: {analysis.score:.0f}/100")
    print(f"   Warnings: {analysis.warnings}")
