#!/usr/bin/env python3
"""
🧠 AI SCORING ENGINE
ML-based scoring για tokens, wallets, και opportunities.
"""
import logging
import time
from typing import Dict, List, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('AIScoring')

class AIScoringEngine:
    """
    AI-based scoring για trading opportunities.
    Χρησιμοποιεί heuristic models και pattern recognition.
    """
    
    def __init__(self):
        self.model_version = "2.0.0"
        self.scoring_history: List[Dict] = []
        
        # Feature weights
        self.weights = {
            'momentum': 0.25,
            'volume': 0.20,
            'liquidity': 0.15,
            'social': 0.15,
            'onchain': 0.15,
            'risk': 0.10
        }
    
    def score_token(self, token_data: Dict) -> Dict:
        """
        Score ένα token με βάση πολλαπλά features.
        
        Returns:
            Dict με score, tier, confidence, analysis
        """
        scores = {}
        
        # 1. Momentum Score (0-100)
        momentum = self._calculate_momentum(token_data)
        scores['momentum'] = momentum
        
        # 2. Volume Score (0-100)
        volume = self._calculate_volume_score(token_data)
        scores['volume'] = volume
        
        # 3. Liquidity Score (0-100)
        liquidity = self._calculate_liquidity_score(token_data)
        scores['liquidity'] = liquidity
        
        # 4. Social Score (0-100)
        social = self._calculate_social_score(token_data)
        scores['social'] = social
        
        # 5. On-chain Score (0-100)
        onchain = self._calculate_onchain_score(token_data)
        scores['onchain'] = onchain
        
        # 6. Risk Score (0-100, lower is better)
        risk = self._calculate_risk_score(token_data)
        scores['risk'] = risk
        
        # Weighted composite score
        composite = (
            scores['momentum'] * self.weights['momentum'] +
            scores['volume'] * self.weights['volume'] +
            scores['liquidity'] * self.weights['liquidity'] +
            scores['social'] * self.weights['social'] +
            scores['onchain'] * self.weights['onchain'] +
            (100 - scores['risk']) * self.weights['risk']
        )
        
        # Determine tier
        if composite >= 85:
            tier = 'S'
            emoji = '🔥🔥🔥'
            recommendation = 'STRONG BUY'
        elif composite >= 70:
            tier = 'A'
            emoji = '🔥🔥'
            recommendation = 'BUY'
        elif composite >= 55:
            tier = 'B'
            emoji = '🔥'
            recommendation = 'CONSIDER'
        elif composite >= 40:
            tier = 'C'
            emoji = '⚡'
            recommendation = 'WATCH'
        else:
            tier = 'D'
            emoji = '⚠️'
            recommendation = 'AVOID'
        
        result = {
            'composite_score': round(composite, 2),
            'tier': tier,
            'emoji': emoji,
            'recommendation': recommendation,
            'component_scores': scores,
            'confidence': self._calculate_confidence(scores),
            'timestamp': datetime.now().isoformat(),
            'model_version': self.model_version
        }
        
        self.scoring_history.append(result)
        
        return result
    
    def _calculate_momentum(self, data: Dict) -> float:
        """Υπολογίζει momentum score"""
        score = 0
        
        price_change = data.get('price_change_24h', 0)
        if price_change > 100:
            score += 40
        elif price_change > 50:
            score += 35
        elif price_change > 20:
            score += 25
        elif price_change > 10:
            score += 15
        elif price_change > 0:
            score += 5
        else:
            score -= 10
        
        # Check multi-timeframe momentum
        h6_change = data.get('price_change_6h', price_change * 0.5)
        h1_change = data.get('price_change_1h', price_change * 0.2)
        
        if h6_change > 0 and h1_change > 0:
            score += 20  # Sustained momentum
        
        if h1_change < -5:
            score -= 15  # Recent dump
        
        return max(0, min(100, score + 40))
    
    def _calculate_volume_score(self, data: Dict) -> float:
        """Υπολογίζει volume score"""
        score = 0
        
        volume = data.get('volume_24h', 0)
        liquidity = data.get('liquidity', 1)
        
        # Volume/Liquidity ratio
        ratio = volume / liquidity if liquidity > 0 else 0
        
        if ratio > 10:
            score += 40
        elif ratio > 5:
            score += 30
        elif ratio > 2:
            score += 20
        elif ratio > 1:
            score += 10
        
        # Absolute volume
        if volume > 1000000:
            score += 30
        elif volume > 500000:
            score += 20
        elif volume > 100000:
            score += 10
        
        return max(0, min(100, score + 30))
    
    def _calculate_liquidity_score(self, data: Dict) -> float:
        """Υπολογίζει liquidity score"""
        score = 0
        
        liquidity = data.get('liquidity', 0)
        
        if liquidity > 500000:
            score += 40
        elif liquidity > 200000:
            score += 30
        elif liquidity > 100000:
            score += 20
        elif liquidity > 50000:
            score += 15
        elif liquidity > 20000:
            score += 10
        else:
            score -= 20
        
        return max(0, min(100, score + 60))
    
    def _calculate_social_score(self, data: Dict) -> float:
        """Υπολογίζει social score"""
        score = 0
        
        # Twitter/X mentions
        twitter_mentions = data.get('twitter_mentions', 0)
        if twitter_mentions > 1000:
            score += 40
        elif twitter_mentions > 500:
            score += 30
        elif twitter_mentions > 100:
            score += 20
        elif twitter_mentions > 10:
            score += 10
        
        # Telegram members
        telegram_members = data.get('telegram_members', 0)
        if telegram_members > 5000:
            score += 30
        elif telegram_members > 1000:
            score += 20
        elif telegram_members > 100:
            score += 10
        
        # Description quality
        if data.get('description', ''):
            score += 10
        
        return min(100, score + 20)
    
    def _calculate_onchain_score(self, data: Dict) -> float:
        """Υπολογίζει on-chain score"""
        score = 0
        
        # Buy/Sell ratio
        buys = data.get('buys', 0)
        sells = data.get('sells', 1)
        ratio = buys / sells if sells > 0 else 0
        
        if ratio > 3:
            score += 40
        elif ratio > 2:
            score += 30
        elif ratio > 1.5:
            score += 20
        elif ratio > 1:
            score += 10
        else:
            score -= 10
        
        # Unique buyers
        unique_buyers = data.get('unique_buyers', 0)
        if unique_buyers > 1000:
            score += 30
        elif unique_buyers > 500:
            score += 20
        elif unique_buyers > 100:
            score += 10
        
        # Holder count
        holders = data.get('holders', 0)
        if holders > 5000:
            score += 20
        elif holders > 1000:
            score += 10
        
        return max(0, min(100, score + 10))
    
    def _calculate_risk_score(self, data: Dict) -> float:
        """
        Υπολογίζει risk score (0 = low risk, 100 = high risk)
        """
        risk = 0
        
        # Low liquidity = high risk
        liquidity = data.get('liquidity', 0)
        if liquidity < 20000:
            risk += 40
        elif liquidity < 50000:
            risk += 20
        
        # Extreme price changes = risky
        price_change = data.get('price_change_24h', 0)
        if abs(price_change) > 500:
            risk += 30
        elif abs(price_change) > 200:
            risk += 15
        
        # No contract verification = risky
        if not data.get('verified', False):
            risk += 20
        
        # Suspicious patterns
        if data.get('honeypot_risk', False):
            risk += 50
        
        return min(100, risk)
    
    def _calculate_confidence(self, scores: Dict) -> float:
        """Υπολογίζει confidence level"""
        # Higher when scores are consistent
        values = list(scores.values())
        if not values:
            return 0
        
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        
        # Lower variance = higher confidence
        confidence = 100 - (variance ** 0.5)
        
        return max(0, min(100, confidence))
    
    def batch_score(self, tokens: List[Dict]) -> List[Dict]:
        """Score multiple tokens"""
        results = []
        
        for token in tokens:
            scored = token.copy()
            scored['ai_analysis'] = self.score_token(token)
            results.append(scored)
        
        return results
    
    def get_model_stats(self) -> Dict:
        """Get model statistics"""
        if not self.scoring_history:
            return {'scorings': 0}
        
        scores = [s['composite_score'] for s in self.scoring_history]
        
        return {
            'scorings': len(self.scoring_history),
            'avg_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'model_version': self.model_version,
            'tier_distribution': self._get_tier_distribution()
        }
    
    def _get_tier_distribution(self) -> Dict:
        """Get tier distribution"""
        tiers = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
        
        for scoring in self.scoring_history:
            tier = scoring.get('tier', 'D')
            tiers[tier] = tiers.get(tier, 0) + 1
        
        return tiers


# Test function
def test_scoring():
    """Test AI scoring"""
    engine = AIScoringEngine()
    
    test_token = {
        'name': 'TEST_TOKEN',
        'symbol': 'TEST',
        'price': 0.001,
        'price_change_24h': 150,
        'price_change_6h': 80,
        'price_change_1h': 20,
        'volume_24h': 500000,
        'liquidity': 200000,
        'buys': 1200,
        'sells': 400,
        'holders': 3000,
        'twitter_mentions': 500,
        'verified': True
    }
    
    result = engine.score_token(test_token)
    
    print(f"\n🧠 AI SCORING RESULT:")
    print(f"Composite Score: {result['composite_score']}")
    print(f"Tier: {result['tier']} {result['emoji']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Confidence: {result['confidence']:.1f}%")
    print(f"\nComponent Scores:")
    for component, score in result['component_scores'].items():
        print(f"  {component}: {score:.1f}")


if __name__ == '__main__':
    test_scoring()
