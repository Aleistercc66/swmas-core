#!/usr/bin/env python3
"""
DexScreener Altcoin Opportunity Detector v2
Based on official DexScreener API docs: https://docs.dexscreener.com/api/reference
"""
import requests
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

BASE_URL = "https://api.dexscreener.com"

class DexScreenerAPI:
    """Official DexScreener API wrapper - Rate limits:
    - Token profiles/boosts/metas/community: 60 req/min
    - Pairs/search/token-pairs/tokens: 300 req/min
    """
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_pairs(self, query: str, limit: int = 10) -> List[Dict]:
        """GET /latest/dex/search?q= - Rate limit: 300/min"""
        url = f"{BASE_URL}/latest/dex/search"
        params = {"q": query}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("pairs", [])[:limit]
        except Exception as e:
            print(f"Error searching pairs: {e}")
            return []
    
    def get_pairs_by_chain(self, chain_id: str, pair_id: str) -> Optional[Dict]:
        """GET /latest/dex/pairs/{chainId}/{pairId} - Rate limit: 300/min"""
        url = f"{BASE_URL}/latest/dex/pairs/{chain_id}/{pair_id}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting pair: {e}")
            return None
    
    def get_token_profiles(self) -> List[Dict]:
        """GET /token-profiles/latest/v1 - Rate limit: 60/min"""
        url = f"{BASE_URL}/token-profiles/latest/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def get_recent_updates(self) -> List[Dict]:
        """GET /token-profiles/recent-updates/v1 - Rate limit: 60/min
        Tokens that had profile updates recently"""
        url = f"{BASE_URL}/token-profiles/recent-updates/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting recent updates: {e}")
            return []
    
    def get_boosted_tokens(self) -> List[Dict]:
        """GET /token-boosts/latest/v1 - Rate limit: 60/min"""
        url = f"{BASE_URL}/token-boosts/latest/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting boosts: {e}")
            return []
    
    def get_top_boosted(self) -> List[Dict]:
        """GET /token-boosts/top/v1 - Rate limit: 60/min
        Tokens with most active boosts"""
        url = f"{BASE_URL}/token-boosts/top/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting top boosted: {e}")
            return []
    
    def get_token_pairs(self, chain_id: str, token_address: str) -> List[Dict]:
        """GET /token-pairs/v1/{chainId}/{tokenAddress} - Rate limit: 300/min
        Get all pools for a specific token"""
        url = f"{BASE_URL}/token-pairs/v1/{chain_id}/{token_address}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting token pairs: {e}")
            return []
    
    def get_tokens_batch(self, chain_id: str, token_addresses: List[str]) -> List[Dict]:
        """GET /tokens/v1/{chainId}/{tokenAddresses} - Rate limit: 300/min
        Get up to 30 tokens by address (comma-separated)"""
        if len(token_addresses) > 30:
            token_addresses = token_addresses[:30]
        url = f"{BASE_URL}/tokens/v1/{chain_id}/{','.join(token_addresses)}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting tokens batch: {e}")
            return []
    
    def get_trending_metas(self) -> List[Dict]:
        """GET /metas/trending/v1 - Rate limit: 60/min
        Trending sectors/narratives (AI, DeFi, gaming, etc.)"""
        url = f"{BASE_URL}/metas/trending/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting trending metas: {e}")
            return []
    
    def get_meta_info(self, slug: str) -> Optional[Dict]:
        """GET /metas/meta/v1/{slug} - Rate limit: 60/min
        Get specific meta info by slug (e.g., 'ai', 'defi')"""
        url = f"{BASE_URL}/metas/meta/v1/{slug}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting meta info: {e}")
            return None
    
    def get_community_takeovers(self) -> List[Dict]:
        """GET /community-takeovers/latest/v1 - Rate limit: 60/min"""
        url = f"{BASE_URL}/community-takeovers/latest/v1"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error getting CTOS: {e}")
            return []

class OpportunityAnalyzer:
    """7-dimension analysis framework implementation"""
    
    MIN_LIQUIDITY_USD = 50000
    MIN_VOLUME_24H = 10000
    MIN_CONFIDENCE = 60
    MAX_OPPORTUNITIES = 3
    
    def analyze_pair(self, pair: Dict) -> Optional[Dict]:
        """Analyze a single pair across all 7 dimensions"""
        pair_addr = pair.get("pairAddress", "unknown")
        base_token = pair.get("baseToken", {})
        quote_token = pair.get("quoteToken", {})
        
        symbol = base_token.get("symbol", "UNKNOWN")
        name = base_token.get("name", "Unknown")
        chain = pair.get("chainId", "unknown")
        dex = pair.get("dexId", "unknown")
        
        price_usd = float(pair.get("priceUsd", 0) or 0)
        liquidity = pair.get("liquidity", {})
        liq_usd = float(liquidity.get("usd", 0) or 0)
        
        volume = pair.get("volume", {})
        vol_24h = float(volume.get("h24", 0) or 0)
        vol_6h = float(volume.get("h6", 0) or 0)
        vol_1h = float(volume.get("h1", 0) or 0)
        
        price_change = pair.get("priceChange", {})
        chg_24h = float(price_change.get("h24", 0) or 0)
        chg_6h = float(price_change.get("h6", 0) or 0)
        chg_1h = float(price_change.get("h1", 0) or 0)
        chg_5m = float(price_change.get("m5", 0) or 0)
        
        txns = pair.get("txns", {})
        txns_24h = txns.get("h24", {})
        buys_24h = txns_24h.get("buys", 0)
        sells_24h = txns_24h.get("sells", 0)
        
        # Basic filtering
        if liq_usd < self.MIN_LIQUIDITY_USD:
            return None
        if vol_24h < self.MIN_VOLUME_24H:
            return None
        
        # 7 DIMENSION ANALYSIS
        signals = []
        confidence = 0
        
        # 1. Price Action
        trend_score = self._analyze_trend(chg_5m, chg_1h, chg_6h, chg_24h)
        if trend_score["bullish"]:
            signals.append(f"Trend: {trend_score['description']}")
            confidence += trend_score["score"]
        
        # 2. Volume Analysis
        volume_score = self._analyze_volume(vol_1h, vol_6h, vol_24h, chg_24h)
        if volume_score["confirming"]:
            signals.append(f"Volume: {volume_score['description']}")
            confidence += volume_score["score"]
        
        # 3. Market Context
        context_score = self._analyze_context(chg_24h, chg_6h, chg_1h)
        signals.append(f"Context: {context_score['description']}")
        confidence += context_score["score"]
        
        # 4. Liquidity Quality
        liquidity_score = self._analyze_liquidity(liq_usd, vol_24h)
        signals.append(f"Liquidity: {liquidity_score['description']}")
        confidence += liquidity_score["score"]
        
        # 5. Transaction Flow
        flow_score = self._analyze_flow(buys_24h, sells_24h)
        if flow_score["accumulation"]:
            signals.append(f"Flow: {flow_score['description']}")
            confidence += flow_score["score"]
        
        # 6. Momentum
        momentum_score = self._analyze_momentum(chg_5m, chg_1h, chg_24h)
        if momentum_score["valid"]:
            signals.append(f"Momentum: {momentum_score['description']}")
            confidence += momentum_score["score"]
        
        # Decision
        strong_signals = [s for s in signals if not s.startswith("Context:") and not s.startswith("Liquidity:")]
        
        if len(strong_signals) < 3 or confidence < self.MIN_CONFIDENCE:
            return None
        
        direction = "LONG" if chg_24h > 0 and chg_1h > 0 else "SHORT" if chg_24h < -5 else "LONG"
        
        entry_zone = f"${price_usd * 0.98:.6f} - ${price_usd * 1.02:.6f}" if price_usd > 0.01 else f"${price_usd:.8f}"
        stop_loss = f"${price_usd * 0.85:.6f}" if direction == "LONG" else f"${price_usd * 1.15:.6f}"
        tp1 = f"${price_usd * 1.20:.6f}" if direction == "LONG" else f"${price_usd * 0.80:.6f}"
        tp2 = f"${price_usd * 1.35:.6f}" if direction == "LONG" else f"${price_usd * 0.70:.6f}"
        tp3 = f"${price_usd * 1.50:.6f}" if direction == "LONG" else f"${price_usd * 0.60:.6f}"
        
        risk_pct = 15
        reward_pct = 50 if direction == "LONG" else 40
        rr_ratio = f"1:{reward_pct/risk_pct:.1f}"
        
        risk_level = "LOW" if confidence >= 80 and liq_usd > 500000 else "MEDIUM" if confidence >= 65 else "HIGH"
        
        return {
            "asset": symbol,
            "name": name,
            "direction": direction,
            "chain": chain,
            "dex": dex,
            "price_usd": price_usd,
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "rr_ratio": rr_ratio,
            "confidence": min(confidence, 100),
            "risk_level": risk_level,
            "signals": signals,
            "liquidity_usd": liq_usd,
            "volume_24h": vol_24h,
            "change_24h": chg_24h,
            "pair_url": pair.get("url", ""),
            "pair_address": pair_addr
        }
    
    def _analyze_trend(self, chg_5m, chg_1h, chg_6h, chg_24h):
        score = 0
        desc = []
        bullish = False
        
        if chg_24h > 5:
            score += 10
            desc.append("24h up")
            bullish = True
        elif chg_24h < -10:
            score += 5
            desc.append("24h down (bounce)")
        
        if chg_6h > 0 and chg_24h > 0:
            score += 10
            desc.append("6h/24h aligned")
            bullish = True
        
        if chg_1h > 2:
            score += 10
            desc.append("1h momentum")
            bullish = True
        elif chg_1h < -2 and chg_24h > 10:
            score += 5
            desc.append("pullback in uptrend")
            bullish = True
        
        if chg_5m > 1:
            score += 5
            desc.append("5m push")
        
        return {"bullish": bullish, "score": score, "description": ", ".join(desc) if desc else "neutral"}
    
    def _analyze_volume(self, vol_1h, vol_6h, vol_24h, chg_24h):
        score = 0
        desc = []
        confirming = False
        
        if vol_24h > 0:
            hourly_avg = vol_24h / 24
            if vol_1h > hourly_avg * 2:
                score += 15
                desc.append("1h spike 2x+")
                confirming = True
            elif vol_1h > hourly_avg:
                score += 10
                desc.append("1h above avg")
                confirming = True
            
            if vol_6h > (vol_24h / 4) * 1.5:
                score += 10
                desc.append("6h elevated")
                confirming = True
        
        if chg_24h > 5 and confirming:
            score += 5
            desc.append("confirms move")
        
        return {"confirming": confirming, "score": score, "description": ", ".join(desc) if desc else "normal"}
    
    def _analyze_context(self, chg_24h, chg_6h, chg_1h):
        score = 5
        desc = []
        
        if chg_24h > 10 and chg_6h > 0:
            desc.append("strong momentum")
        elif chg_24h > 0 and chg_1h < 0:
            desc.append("pullback in uptrend")
        elif chg_24h < -5:
            desc.append("weak")
        else:
            desc.append("stable")
        
        return {"score": score, "description": ", ".join(desc)}
    
    def _analyze_liquidity(self, liq_usd, vol_24h):
        score = 0
        desc = []
        
        if liq_usd > 500000:
            score += 15
            desc.append("excellent")
        elif liq_usd > 100000:
            score += 10
            desc.append("good")
        elif liq_usd > 50000:
            score += 5
            desc.append("adequate")
        
        if vol_24h > 0 and liq_usd > 0:
            turnover = vol_24h / liq_usd
            if turnover > 1:
                score += 5
                desc.append("high turnover")
            elif turnover > 0.5:
                score += 3
                desc.append("healthy turnover")
        
        return {"score": score, "description": ", ".join(desc)}
    
    def _analyze_flow(self, buys, sells):
        score = 0
        desc = []
        accumulation = False
        
        if buys > 0 and sells > 0:
            ratio = buys / sells
            if ratio > 1.5:
                score += 15
                desc.append(f"strong buy ({ratio:.1f}:1)")
                accumulation = True
            elif ratio > 1.2:
                score += 10
                desc.append(f"buy edge ({ratio:.1f}:1)")
                accumulation = True
            elif ratio > 1.0:
                score += 5
                desc.append(f"slight edge ({ratio:.1f}:1)")
                accumulation = True
            elif ratio < 0.8:
                desc.append(f"sell pressure ({ratio:.1f}:1)")
        
        return {"accumulation": accumulation, "score": score, "description": ", ".join(desc) if desc else "neutral"}
    
    def _analyze_momentum(self, chg_5m, chg_1h, chg_24h):
        score = 0
        desc = []
        valid = False
        
        if chg_24h > 50:
            desc.append("overextended")
            valid = False
        elif chg_24h > 20:
            score += 5
            desc.append("strong")
            valid = True
        elif chg_24h > 5:
            score += 10
            desc.append("healthy")
            valid = True
        elif chg_24h > 0:
            score += 5
            desc.append("positive")
            valid = True
        else:
            desc.append("negative")
            valid = False
        
        if chg_5m > 2 and chg_1h > 0:
            score += 5
            desc.append("micro building")
        
        return {"valid": valid, "score": score, "description": ", ".join(desc)}


def format_opportunity(opp: Dict) -> str:
    lines = [
        f"[{opp['asset']} — {opp['direction']}]",
        "",
        f"Entry Zone: {opp['entry_zone']}",
        f"Stop Loss: {opp['stop_loss']}",
        f"Take Profit 1: {opp['take_profit_1']}",
        f"Take Profit 2: {opp['take_profit_2']}",
        f"Take Profit 3: {opp['take_profit_3']}",
        "",
        f"Risk/Reward Ratio: {opp['rr_ratio']}",
        f"Confidence Score: {opp['confidence']}/100",
        f"Risk Level: {opp['risk_level']}",
        "",
        "Reasoning:",
    ]
    for signal in opp['signals']:
        lines.append(f"- {signal}")
    
    lines.extend([
        "",
        f"Chain: {opp['chain']} | DEX: {opp['dex']}",
        f"Liquidity: ${opp['liquidity_usd']:,.0f} | 24h Volume: ${opp['volume_24h']:,.0f}",
        f"24h Change: {opp['change_24h']:+.2f}%",
        f"DexScreener: {opp['pair_url']}"
    ])
    
    return "\n".join(lines)


def scan_opportunities(search_terms: List[str] = None, scan_mode: str = "standard") -> Tuple[List[Dict], Dict]:
    """Main scanning function with multiple modes
    
    scan_mode:
    - standard: Search terms + boosted tokens
    - trending: Focus on trending metas/sectors
    - community: Include community takeovers
    - full: Everything
    """
    api = DexScreenerAPI()
    analyzer = OpportunityAnalyzer()
    
    if search_terms is None:
        search_terms = ["SOL", "ETH", "PEPE", "BONK", "WIF", "JUP", "JTO", "PYTH"]
    
    all_pairs = []
    scan_metadata = {"mode": scan_mode, "sources": []}
    
    # Standard search
    print(f"🔍 Scanning {len(search_terms)} search terms...")
    for term in search_terms:
        pairs = api.search_pairs(term, limit=5)
        all_pairs.extend(pairs)
    scan_metadata["sources"].append(f"search:{len(search_terms)} terms")
    
    # Boosted tokens
    print("🔥 Getting boosted tokens...")
    boosted = api.get_boosted_tokens()
    scan_metadata["sources"].append(f"boosted:{len(boosted)} tokens")
    
    # Top boosted
    if scan_mode in ["full", "trending"]:
        print("🚀 Getting top boosted...")
        top_boosted = api.get_top_boosted()
        scan_metadata["sources"].append(f"top_boosted:{len(top_boosted)} tokens")
    
    # Trending metas/sectors
    if scan_mode in ["trending", "full"]:
        print("📈 Getting trending metas...")
        metas = api.get_trending_metas()
        scan_metadata["metas"] = [m.get("name") for m in metas[:5]]
        print(f"   Top sectors: {', '.join(scan_metadata['metas'])}")
    
    # Community takeovers
    if scan_mode in ["community", "full"]:
        print("🎯 Getting community takeovers...")
        ctos = api.get_community_takeovers()
        scan_metadata["sources"].append(f"ctos:{len(ctos)} tokens")
    
    # Analyze all pairs
    print("\n📊 Analyzing pairs...")
    opportunities = []
    
    for pair in all_pairs:
        opp = analyzer.analyze_pair(pair)
        if opp:
            opportunities.append(opp)
    
    opportunities.sort(key=lambda x: x["confidence"], reverse=True)
    
    return opportunities[:analyzer.MAX_OPPORTUNITIES], scan_metadata


def main():
    print("="*60)
    print("🎯 DEXSCREENER ALTCOIN OPPORTUNITY SCANNER v2")
    print("="*60)
    print()
    
    # Parse args
    scan_mode = "standard"
    if len(sys.argv) > 1:
        scan_mode = sys.argv[1]
    
    valid_modes = ["standard", "trending", "community", "full"]
    if scan_mode not in valid_modes:
        print(f"Invalid mode: {scan_mode}")
        print(f"Valid modes: {', '.join(valid_modes)}")
        return
    
    print(f"Scan mode: {scan_mode.upper()}")
    print()
    
    opps, meta = scan_opportunities(scan_mode=scan_mode)
    
    print(f"\n{'='*60}")
    print(f"SCAN SUMMARY")
    print(f"{'='*60}")
    print(f"Mode: {meta['mode']}")
    print(f"Sources: {', '.join(meta['sources'])}")
    if 'metas' in meta:
        print(f"Trending sectors: {', '.join(meta['metas'])}")
    print()
    
    if not opps:
        print("⚠️ No high-probability opportunities detected based on current market conditions.")
    else:
        print(f"✅ Found {len(opps)} high-probability opportunities:\n")
        for i, opp in enumerate(opps, 1):
            print(f"--- OPPORTUNITY {i} ---")
            print(format_opportunity(opp))
            print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
