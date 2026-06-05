#!/usr/bin/env python3
"""
Advanced Message Analyzer for Telegram Crypto Groups
Performs deep analysis on group messages to extract:
- Sentiment (bullish/bearish/neutral)
- Intent classification (signal, news, scam, discussion)
- Entity extraction (tokens, projects, influencers)
- Urgency scoring
- Action recommendations
- Smart summaries
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('message_analyzer')

# ============== SENTIMENT LEXICONS ==============

BULLISH_WORDS = [
    'moon', 'pump', 'pumping', 'bullish', 'breakout', 'breaking out', 'explode',
    'exploding', 'send it', 'send', 'rocket', 'to the moon', 'gem', 'alpha',
    '100x', '1000x', '10x', 'gain', 'gains', 'profit', 'profits', ' ATH',
    'all time high', 'new high', 'rally', 'surge', 'soaring', 'flying',
    'load', 'loading', 'accumulate', 'buy', 'bought', 'dip', 'discount',
    'undervalued', 'cheap', 'entry', 'long', 'hold', 'hodl', 'diamond hands',
    'generational wealth', 'life changing', 'dont miss', 'dont sleep',
    'early', 'ground floor', 'first mover', 'insider', 'whale buying',
    'smart money', 'dev based', 'based dev', 'renounced', 'lp burned',
    'locked', 'verified', 'audit', 'safu', 'community driven',
    'viral', 'trending', 'hype', 'fomo', 'fear of missing out',
]

BEARISH_WORDS = [
    'dump', 'dumping', 'bearish', 'crash', 'crashing', 'rug', 'rugpull',
    'honeypot', 'scam', 'fake', 'ponzi', 'sell', 'selling', 'exit',
    'get out', 'leave', 'avoid', 'stay away', 'dont buy', 'not buying',
    'red flag', 'suspicious', 'unverified', 'unlock', 'unlocking',
    'dev selling', 'team selling', 'insider selling', 'whale selling',
    'low volume', 'dead', 'dying', 'rekt', 'liquidated', 'stop loss',
    'SL hit', 'dumped', 'crash', 'correction', 'pullback', 'retrace',
    'bagholder', 'bags', 'stuck', 'trapped', 'down bad',
]

URGENCY_WORDS = [
    'now', 'hurry', 'quick', 'fast', 'asap', 'immediately', 'urgent',
    'dont miss', 'last chance', 'final call', 'closing soon', 'ending',
    'limited time', 'soon', 'shortly', 'about to', 'ready to',
    'launching', 'just launched', 'new', 'fresh', 'first',
    'before', 'prior to', 'pre', 'early access', 'whitelist',
    'presale', 'ido', 'ico', 'fair launch',
]

SCAM_INDICATORS = [
    'guaranteed', 'guarantee', 'risk free', 'no risk', '100% safe',
    'double your', 'triple your', '10x guaranteed', 'instant profit',
    'send me', 'send eth', 'send sol', 'send bnb', 'dm for',
    'private sale', 'exclusive offer', 'limited spots', 'only for you',
    'click here', 'link in bio', 'check my', 'follow me', 'join my',
    'free money', 'airdrop claim', 'claim now', 'verify wallet',
    'connect wallet', 'approve token', 'giveaway', 'free',
]

# ============== ENTITY PATTERNS ==============

TOKEN_SYMBOL_PATTERN = re.compile(
    r'\$([A-Za-z][A-Za-z0-9]{1,15})'  # $TOKEN
)

HASHTAG_PATTERN = re.compile(
    r'#([A-Za-z][A-Za-z0-9]+)'  # #token
)

MENTION_PATTERN = re.compile(
    r'@([A-Za-z][A-Za-z0-9_]+)'  # @username
)

PRICE_PATTERN = re.compile(
    r'(\$[\d,.]+[KkMmBb]?)'  # $1.5M, $100K
)

MCAP_PATTERN = re.compile(
    r'(mcap|marketcap|market cap)[\s:]*([\d,.]+[KkMmBb]?)',
    re.IGNORECASE
)

LIQUIDITY_PATTERN = re.compile(
    r'(liq|liquidity|lp)[\s:]*([\d,.]+[KkMmBb]?)',
    re.IGNORECASE
)

# ============== DATA CLASSES ==============

@dataclass
class MessageAnalysis:
    """Complete analysis of a crypto group message"""
    
    # Basic info
    message_id: int
    sender: str
    sender_username: Optional[str]
    chat_name: str
    timestamp: datetime
    raw_text: str
    
    # Sentiment
    sentiment: str  # 'bullish', 'bearish', 'neutral', 'mixed'
    sentiment_score: float  # -1.0 to +1.0
    
    # Intent
    intent: str  # 'signal', 'news', 'discussion', 'scam_warning', 'question', 'shill', 'noise'
    intent_confidence: float  # 0.0 to 1.0
    
    # Entities
    token_symbols: List[str]  # $TOKEN mentions
    token_names: List[str]  # Extracted project names
    contract_addresses: List[str]
    dex_links: List[str]
    telegram_links: List[str]
    mentioned_users: List[str]
    price_targets: List[str]
    market_cap: Optional[str]
    liquidity: Optional[str]
    
    # Analysis
    urgency_score: float  # 0.0 to 1.0
    scam_risk: float  # 0.0 to 1.0
    credibility_score: float  # 0.0 to 1.0
    
    # Output
    action_recommendation: str  # 'alert', 'investigate', 'ignore', 'warn'
    summary: str  # 1-2 sentence summary
    key_points: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'sentiment': self.sentiment,
            'sentiment_score': round(self.sentiment_score, 2),
            'intent': self.intent,
            'intent_confidence': round(self.intent_confidence, 2),
            'token_symbols': self.token_symbols,
            'contract_addresses': self.contract_addresses,
            'dex_links': self.dex_links,
            'urgency_score': round(self.urgency_score, 2),
            'scam_risk': round(self.scam_risk, 2),
            'credibility_score': round(self.credibility_score, 2),
            'action': self.action_recommendation,
            'summary': self.summary,
        }


class MessageAnalyzer:
    """
    Deep analyzer for crypto group messages.
    Extracts sentiment, intent, entities, and actionable insights.
    """
    
    def __init__(self):
        self.analyzed_count = 0
        
    def analyze(self, text: str, sender: str, sender_username: Optional[str],
                message_id: int, chat_name: str) -> MessageAnalysis:
        """
        Perform complete analysis of a message.
        """
        self.analyzed_count += 1
        text_lower = text.lower()
        
        # 1. Sentiment Analysis
        sentiment, sentiment_score = self._analyze_sentiment(text_lower)
        
        # 2. Entity Extraction
        token_symbols = self._extract_token_symbols(text)
        token_names = self._extract_token_names(text)
        contract_addresses = self._extract_contract_addresses(text)
        dex_links = self._extract_dex_links(text)
        tg_links = self._extract_telegram_links(text)
        mentioned_users = self._extract_mentions(text)
        price_targets = self._extract_price_targets(text)
        mcap = self._extract_market_cap(text)
        liq = self._extract_liquidity(text)
        
        # 3. Intent Classification
        intent, intent_confidence = self._classify_intent(
            text_lower, token_symbols, contract_addresses, dex_links, sender
        )
        
        # 4. Urgency Scoring
        urgency = self._calculate_urgency(text_lower, intent)
        
        # 5. Scam Risk Assessment
        scam_risk = self._assess_scam_risk(text_lower, sender, intent)
        
        # 6. Credibility Scoring
        credibility = self._calculate_credibility(
            text, sender_username, intent, scam_risk, token_symbols
        )
        
        # 7. Action Recommendation
        action = self._recommend_action(
            sentiment_score, intent, scam_risk, urgency, credibility,
            contract_addresses, dex_links
        )
        
        # 8. Summary Generation
        summary = self._generate_summary(
            text, sentiment, intent, token_symbols, contract_addresses, action
        )
        
        # 9. Key Points Extraction
        key_points = self._extract_key_points(text, token_symbols, dex_links)
        
        return MessageAnalysis(
            message_id=message_id,
            sender=sender,
            sender_username=sender_username,
            chat_name=chat_name,
            timestamp=datetime.now(),
            raw_text=text,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            intent=intent,
            intent_confidence=intent_confidence,
            token_symbols=token_symbols,
            token_names=token_names,
            contract_addresses=contract_addresses,
            dex_links=dex_links,
            telegram_links=tg_links,
            mentioned_users=mentioned_users,
            price_targets=price_targets,
            market_cap=mcap,
            liquidity=liq,
            urgency_score=urgency,
            scam_risk=scam_risk,
            credibility_score=credibility,
            action_recommendation=action,
            summary=summary,
            key_points=key_points,
        )
    
    # ============== SENTIMENT ==============
    
    def _analyze_sentiment(self, text_lower: str) -> Tuple[str, float]:
        """
        Calculate sentiment score between -1.0 (bearish) and +1.0 (bullish).
        """
        bullish_count = sum(1 for word in BULLISH_WORDS if word in text_lower)
        bearish_count = sum(1 for word in BEARISH_WORDS if word in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 'neutral', 0.0
        
        # Calculate score
        score = (bullish_count - bearish_count) / max(total, 5)
        score = max(-1.0, min(1.0, score))  # clamp
        
        # Determine label
        if score > 0.3:
            label = 'bullish'
        elif score < -0.3:
            label = 'bearish'
        elif bullish_count > 0 and bearish_count > 0:
            label = 'mixed'
        else:
            label = 'neutral'
        
        return label, round(score, 2)
    
    # ============== ENTITIES ==============
    
    def _extract_token_symbols(self, text: str) -> List[str]:
        """Extract $TOKEN mentions"""
        matches = TOKEN_SYMBOL_PATTERN.findall(text)
        # Filter common false positives
        filtered = [m for m in matches if m.upper() not in ['ETH', 'BTC', 'SOL', 'USD', 'USDT', 'USDC', 'BNB']]
        return list(set(filtered))
    
    def _extract_token_names(self, text: str) -> List[str]:
        """Extract potential token/project names from text"""
        # Heuristic: capitalize words after certain patterns
        names = []
        # After "token", "coin", "project"
        patterns = [
            r'(?:token|coin|project|gem)\s+(?:is|called|name[d:]?)\s+([A-Z][a-zA-Z0-9]{2,20})',
            r'(?:new|upcoming|launching)\s+([A-Z][a-zA-Z0-9]{2,20})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            names.extend(matches)
        return list(set(names))
    
    def _extract_contract_addresses(self, text: str) -> List[str]:
        """Extract contract addresses"""
        addresses = []
        # EVM
        evm = re.findall(r'0x[a-fA-F0-9]{40}', text)
        addresses.extend(evm)
        # Solana
        sol = re.findall(r'[1-9A-HJ-NP-Za-km-z]{43,44}', text)
        sol = [s for s in sol if not re.match(r'^[a-z]+$', s)]
        addresses.extend(sol)
        # TON
        ton = re.findall(r'EQ[A-Za-z0-9_-]{40,48}', text)
        addresses.extend(ton)
        return list(set(addresses))
    
    def _extract_dex_links(self, text: str) -> List[str]:
        """Extract DEX/trading links"""
        dex_patterns = [
            r'https?://dexscreener\.com/[^\s\)]+',
            r'https?://pump\.fun/[^\s\)]+',
            r'https?://raydium\.io/[^\s\)]+',
            r'https?://jup\.ag/[^\s\)]+',
            r'https?://app\.uniswap\.org/[^\s\)]+',
            r'https?://dextools\.io/[^\s\)]+',
            r'https?://birdeye\.so/[^\s\)]+',
        ]
        links = []
        for pattern in dex_patterns:
            links.extend(re.findall(pattern, text, re.IGNORECASE))
        return list(set(links))
    
    def _extract_telegram_links(self, text: str) -> List[str]:
        """Extract Telegram group/channel links"""
        return list(set(re.findall(r'https?://t\.me/[^\s\)]+', text)))
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract @username mentions"""
        return list(set(MENTION_PATTERN.findall(text)))
    
    def _extract_price_targets(self, text: str) -> List[str]:
        """Extract price targets or predictions"""
        targets = []
        # Patterns like "target $1", "to $5", "at $0.50"
        patterns = [
            r'target[s]?\s*[:]?\s*\$?([\d,.]+[KkMmBb]?)',
            r'to\s+\$?([\d,.]+[KkMmBb]?)',
            r'\$([\d,.]+)\s*(?:is|would be|will be|target)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            targets.extend(matches)
        return list(set(targets))
    
    def _extract_market_cap(self, text: str) -> Optional[str]:
        """Extract market cap mention"""
        match = MCAP_PATTERN.search(text)
        if match:
            return match.group(2)
        return None
    
    def _extract_liquidity(self, text: str) -> Optional[str]:
        """Extract liquidity mention"""
        match = LIQUIDITY_PATTERN.search(text)
        if match:
            return match.group(2)
        return None
    
    # ============== INTENT CLASSIFICATION ==============
    
    def _classify_intent(self, text_lower: str, token_symbols: List[str],
                         contract_addresses: List[str], dex_links: List[str],
                         sender: str) -> Tuple[str, float]:
        """
        Classify message intent.
        Returns (intent, confidence)
        """
        scores = {
            'signal': 0,
            'news': 0,
            'discussion': 0,
            'scam_warning': 0,
            'question': 0,
            'shill': 0,
            'noise': 0,
        }
        
        # Signal indicators
        if contract_addresses or dex_links:
            scores['signal'] += 3
        if token_symbols:
            scores['signal'] += 2
        if any(w in text_lower for w in ['buy', 'entry', 'target', 'stop loss', 'tp', 'sl', 'long', 'short']):
            scores['signal'] += 2
        if any(w in text_lower for w in ['chart', 'technical', 'support', 'resistance', 'breakout']):
            scores['signal'] += 1
        
        # News indicators
        if any(w in text_lower for w in ['announced', 'partnership', 'listing', 'exchange', 'update', 'released']):
            scores['news'] += 3
        if any(w in text_lower for w in ['just', 'breaking', 'new', 'latest']):
            scores['news'] += 1
        
        # Scam warning indicators
        if any(w in text_lower for w in ['scam', 'rug', 'honeypot', 'fake', 'avoid', 'dont buy', 'red flag']):
            scores['scam_warning'] += 3
        if any(w in text_lower for w in BEARISH_WORDS[:10]):
            scores['scam_warning'] += 1
        
        # Question indicators
        if text_lower.endswith('?'):
            scores['question'] += 2
        if any(w in text_lower for w in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'is this']):
            scores['question'] += 2
        
        # Shill indicators
        if any(w in text_lower for w in ['dm me', 'check pm', 'message me', 'join my', 'my group']):
            scores['shill'] += 3
        if text_lower.count('$') > 3:
            scores['shill'] += 1
        
        # Discussion (default if nothing else strong)
        if len(text_lower) > 100 and not contract_addresses and not dex_links:
            scores['discussion'] += 2
        
        # Noise (very short, no value)
        if len(text_lower) < 15 and not contract_addresses:
            scores['noise'] += 3
        
        # Pick highest
        intent = max(scores, key=scores.get)
        confidence = min(scores[intent] / 5, 1.0)
        
        return intent, round(confidence, 2)
    
    # ============== URGENCY ==============
    
    def _calculate_urgency(self, text_lower: str, intent: str) -> float:
        """Calculate urgency score 0.0-1.0"""
        score = 0.0
        
        # Urgency words
        for word in URGENCY_WORDS:
            if word in text_lower:
                score += 0.15
        
        # Time-sensitive phrases
        if 'minutes' in text_lower or 'hours' in text_lower:
            score += 0.2
        
        # Intent boost
        if intent == 'signal':
            score += 0.1
        if intent == 'news':
            score += 0.15
        
        return min(score, 1.0)
    
    # ============== SCAM RISK ==============
    
    def _assess_scam_risk(self, text_lower: str, sender: str, intent: str) -> float:
        """Calculate scam risk score 0.0-1.0"""
        score = 0.0
        
        # Scam keyword matches
        for indicator in SCAM_INDICATORS:
            if indicator in text_lower:
                score += 0.15
        
        # DM requests are suspicious
        if 'dm me' in text_lower or 'dm for' in text_lower:
            score += 0.3
        
        # Too many guarantees
        guarantee_count = text_lower.count('guarantee') + text_lower.count('guaranteed')
        score += guarantee_count * 0.2
        
        # Shill intent is suspicious
        if intent == 'shill':
            score += 0.25
        
        # Cap at 1.0
        return min(score, 1.0)
    
    # ============== CREDIBILITY ==============
    
    def _calculate_credibility(self, text: str, sender_username: Optional[str],
                                intent: str, scam_risk: float,
                                token_symbols: List[str]) -> float:
        """Calculate credibility score 0.0-1.0"""
        score = 0.5  # Start neutral
        
        # Has verifiable data = more credible
        if re.search(r'0x[a-fA-F0-9]{40}', text):
            score += 0.1
        if re.search(r'https?://', text):
            score += 0.05
        
        # Detailed analysis = more credible
        if len(text) > 300:
            score += 0.1
        
        # Known intent types
        if intent in ['signal', 'news', 'discussion']:
            score += 0.1
        if intent in ['shill', 'noise']:
            score -= 0.2
        
        # Scam risk reduces credibility
        score -= scam_risk * 0.5
        
        # Has username = slightly more credible
        if sender_username:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    # ============== ACTION RECOMMENDATION ==============
    
    def _recommend_action(self, sentiment_score: float, intent: str,
                          scam_risk: float, urgency: float,
                          credibility: float,
                          contract_addresses: List[str],
                          dex_links: List[str]) -> str:
        """
        Recommend action based on analysis.
        """
        # High scam risk = warn
        if scam_risk > 0.5:
            return 'warn'
        
        # Very low credibility = ignore
        if credibility < 0.2:
            return 'ignore'
        
        # Signal with contract + dex link = alert
        if intent == 'signal' and (contract_addresses or dex_links):
            if sentiment_score > 0:
                return 'alert'
            else:
                return 'investigate'
        
        # News with high urgency = alert
        if intent == 'news' and urgency > 0.5:
            return 'alert'
        
        # Discussion with tokens = investigate
        if intent == 'discussion' and contract_addresses:
            return 'investigate'
        
        # Scam warning = always alert
        if intent == 'scam_warning':
            return 'alert'
        
        # Default
        if contract_addresses or dex_links:
            return 'investigate'
        
        return 'ignore'
    
    # ============== SUMMARY ==============
    
    def _generate_summary(self, text: str, sentiment: str, intent: str,
                          token_symbols: List[str],
                          contract_addresses: List[str],
                          action: str) -> str:
        """Generate a 1-2 sentence summary"""
        parts = []
        
        # Sentiment
        if sentiment == 'bullish':
            parts.append("Bullish")
        elif sentiment == 'bearish':
            parts.append("Bearish")
        elif sentiment == 'mixed':
            parts.append("Mixed sentiment")
        
        # Intent
        intent_desc = {
            'signal': 'trading signal',
            'news': 'news update',
            'discussion': 'discussion',
            'scam_warning': '⚠️ SCAM WARNING',
            'question': 'question',
            'shill': 'promotion',
            'noise': 'noise',
        }
        parts.append(intent_desc.get(intent, intent))
        
        # Tokens
        if token_symbols:
            parts.append(f"for ${', $'.join(token_symbols[:3])}")
        elif contract_addresses:
            parts.append(f"with contract {contract_addresses[0][:10]}...")
        
        # Action
        action_desc = {
            'alert': '🚨 ALERT WORTHY',
            'investigate': '🔍 Worth investigating',
            'warn': '⚠️ WARNING',
            'ignore': '📝 For reference',
        }
        parts.append(action_desc.get(action, ''))
        
        return ' | '.join(p for p in parts if p)
    
    def _extract_key_points(self, text: str, token_symbols: List[str],
                            dex_links: List[str]) -> List[str]:
        """Extract key bullet points from message"""
        points = []
        text_lower = text.lower()
        
        # Look for numbered or bulleted lists
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*', '>', '→', '✅', '🔥', '🚀', '💎', '⚠️')):
                if len(line) > 5:
                    points.append(line[:200])
        
        # Look for key facts
        if 'market cap' in text_lower or 'mcap' in text_lower:
            match = re.search(r'(?:mcap|marketcap|market cap)[\s:]*([\d,.]+[KkMmBb]?)', text, re.IGNORECASE)
            if match:
                points.append(f"Market Cap: {match.group(1)}")
        
        if 'liquidity' in text_lower or 'liq' in text_lower:
            match = re.search(r'(?:liq|liquidity|lp)[\s:]*([\d,.]+[KkMmBb]?)', text, re.IGNORECASE)
            if match:
                points.append(f"Liquidity: {match.group(1)}")
        
        if 'volume' in text_lower:
            match = re.search(r'(?:volume|vol)[\s:]*([\d,.]+[KkMmBb]?)', text, re.IGNORECASE)
            if match:
                points.append(f"Volume: {match.group(1)}")
        
        # DEX links as points
        for link in dex_links[:2]:
            points.append(f"Link: {link}")
        
        return points[:5]  # Max 5 points


# ============== TEST ==============
if __name__ == "__main__":
    analyzer = MessageAnalyzer()
    
    test_messages = [
        "🚀 $PEPE just broke resistance at $0.000001! Target $0.000005! Chart: https://dexscreener.com/solana/0x1234567890abcdef1234567890abcdef12345678",
        "⚠️ WARNING: This project is a scam. Honeypot detected. Do NOT buy!",
        "What do you guys think about $SOL? Is it a good entry here?",
        "Just launched! New gem $MOON with 100x potential! CA: 0xabcdef1234567890abcdef1234567890abcdef12 LP burned, dev based!",
        "Hey check out my group t.me/moneygroup dm me for private sale guaranteed 10x",
    ]
    
    for msg in test_messages:
        analysis = analyzer.analyze(msg, "TestUser", "testuser", 1, "TestGroup")
        print(f"\n{'='*60}")
        print(f"TEXT: {msg[:80]}...")
        print(f"SENTIMENT: {analysis.sentiment} ({analysis.sentiment_score})")
        print(f"INTENT: {analysis.intent} ({analysis.intent_confidence})")
        print(f"TOKENS: {analysis.token_symbols}")
        print(f"CA: {analysis.contract_addresses}")
        print(f"URGENCY: {analysis.urgency_score}")
        print(f"SCAM RISK: {analysis.scam_risk}")
        print(f"CREDIBILITY: {analysis.credibility_score}")
        print(f"ACTION: {analysis.action_recommendation}")
        print(f"SUMMARY: {analysis.summary}")
        print(f"KEY POINTS: {analysis.key_points}")
    
    print(f"\n{'='*60}")
    print(f"✅ Analyzer ready! Total analyzed: {analyzer.analyzed_count}")
