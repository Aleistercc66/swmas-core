#!/usr/bin/env python3
"""
🧠 AI EVALUATION LAYER — Layer 3 Intelligence
Scam detection, whale tracking, sentiment analysis, rug pull probability
"""
import json
import re
from datetime import datetime
from typing import Dict, List

class AIEvaluationLayer:
    """Multi-dimensional AI analysis for token evaluation"""
    
    def __init__(self):
        self.scam_patterns = self._load_scam_patterns()
        self.known_rug_addresses = set()
        
    def _load_scam_patterns(self) -> List[str]:
        """Load known scam indicators"""
        return [
            "honeypot",
            "owner can mint",
            "blacklist",
            "cannot sell",
            "only owner can sell",
            "massive dev allocation",
            "fake volume",
            "same contract as"
        ]
        
    def analyze_token(self, token_data: Dict) -> Dict:
        """Full AI analysis of a token"""
        analysis = {
            "symbol": token_data.get("symbol", "???"),
            "timestamp": datetime.now().isoformat(),
            "scores": {}
        }
        
        # Run all analyses
        analysis["scores"]["scam_probability"] = self.detect_scam(token_data)
        analysis["scores"]["rug_probability"] = self.detect_rug_pull(token_data)
        analysis["scores"]["whale_score"] = self.analyze_whales(token_data)
        analysis["scores"]["momentum_score"] = self.calculate_momentum(token_data)
        analysis["scores"]["liquidity_health"] = self.check_liquidity_health(token_data)
        
        # Overall score
        overall = self.calculate_overall_score(analysis["scores"])
        analysis["overall_score"] = overall
        analysis["recommendation"] = self.get_recommendation(overall)
        
        return analysis
        
    def detect_scam(self, token: Dict) -> float:
        """Detect scam probability (0-100)"""
        red_flags = 0
        
        # Check for suspicious patterns
        name = token.get("name", "").lower()
        symbol = token.get("symbol", "").lower()
        
        for pattern in self.scam_patterns:
            if pattern in name or pattern in symbol:
                red_flags += 20
                
        # Check liquidity vs volume ratio
        liquidity = token.get("liquidity", 0)
        volume = token.get("volume_24h", 0)
        
        if volume > 0 and liquidity / volume < 0.1:
            red_flags += 15  # Fake volume
            
        # Check for massive price swings
        change_24h = abs(token.get("change_24h", 0))
        if change_24h > 1000:
            red_flags += 10
            
        # Check age
        age_hours = token.get("age_hours", 999)
        if age_hours < 1:
            red_flags += 25  # Brand new = higher risk
            
        return min(red_flags, 100)
        
    def detect_rug_pull(self, token: Dict) -> float:
        """Detect rug pull probability (0-100)"""
        risk = 0
        
        # Low liquidity = high rug risk
        liquidity = token.get("liquidity", 0)
        if liquidity < 10000:
            risk += 40
        elif liquidity < 50000:
            risk += 20
        elif liquidity < 100000:
            risk += 10
            
        # High dev allocation
        # (Would need on-chain data for this)
        
        # Sudden volume drop
        volume_1h = token.get("volume_1h", 0)
        volume_24h = token.get("volume_24h", 0)
        if volume_24h > 0 and volume_1h / (volume_24h / 24) < 0.5:
            risk += 15  # Volume dying
            
        return min(risk, 100)
        
    def analyze_whales(self, token: Dict) -> float:
        """Analyze whale activity (0-100, higher = more whale interest)"""
        score = 50  # Neutral base
        
        # Buy/sell ratio
        buys = token.get("buys_24h", 0)
        sells = token.get("sells_24h", 0)
        
        if sells > 0:
            ratio = buys / sells
            if ratio > 2:
                score += 20  # Heavy buying
            elif ratio > 1.5:
                score += 10
            elif ratio < 0.5:
                score -= 20  # Heavy selling
                
        # Volume concentration
        volume_5m = token.get("volume_5m", 0)
        volume_1h = token.get("volume_1h", 0)
        
        if volume_1h > 0:
            recent_ratio = volume_5m * 12 / volume_1h  # Normalize to 1h
            if recent_ratio > 2:
                score += 10  # Recent spike
                
        return max(0, min(100, score))
        
    def calculate_momentum(self, token: Dict) -> float:
        """Calculate momentum score (0-100)"""
        score = 50
        
        # Timeframe momentum
        c24h = token.get("change_24h", 0)
        c6h = token.get("change_6h", 0)
        c1h = token.get("change_1h", 0)
        c5m = token.get("change_5m", 0)
        
        # Weighted momentum
        momentum = (
            c24h * 0.1 +
            c6h * 0.2 +
            c1h * 0.3 +
            c5m * 0.4
        )
        
        # Normalize to 0-100
        score = 50 + momentum * 2
        
        return max(0, min(100, score))
        
    def check_liquidity_health(self, token: Dict) -> float:
        """Check liquidity health (0-100)"""
        liquidity = token.get("liquidity", 0)
        
        if liquidity > 1000000:
            return 90
        elif liquidity > 500000:
            return 80
        elif liquidity > 100000:
            return 70
        elif liquidity > 50000:
            return 60
        elif liquidity > 25000:
            return 40
        else:
            return 20
            
    def calculate_overall_score(self, scores: Dict) -> float:
        """Calculate weighted overall score"""
        weights = {
            "scam_probability": -0.3,  # Inverted (lower is better)
            "rug_probability": -0.3,  # Inverted
            "whale_score": 0.2,
            "momentum_score": 0.15,
            "liquidity_health": 0.15
        }
        
        total = 50  # Base score
        
        for metric, weight in weights.items():
            if metric in scores:
                if weight < 0:
                    # Inverted metrics (lower is better)
                    total += (100 - scores[metric]) * abs(weight)
                else:
                    total += scores[metric] * weight
                    
        return max(0, min(100, total))
        
    def get_recommendation(self, score: float) -> str:
        """Get trading recommendation"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 50:
            return "HOLD"
        elif score >= 35:
            return "WATCH"
        else:
            return "AVOID"
            
    def batch_analyze(self, tokens: List[Dict]) -> List[Dict]:
        """Analyze multiple tokens"""
        results = []
        for token in tokens:
            results.append(self.analyze_token(token))
        return results
        
    def save_analysis(self, analysis: Dict):
        """Save analysis to shared state"""
        filepath = "/root/.openclaw/workspace/agents/tmp_state/ai_analysis.json"
        
        try:
            with open(filepath, 'r') as f:
                existing = json.load(f)
        except:
            existing = {"analyses": []}
            
        existing["analyses"].append(analysis)
        existing["analyses"] = existing["analyses"][-100:]  # Keep last 100
        
        with open(filepath, 'w') as f:
            json.dump(existing, f, indent=2)

if __name__ == "__main__":
    ai = AIEvaluationLayer()
    
    # Test with sample data
    test_token = {
        "symbol": "TEST",
        "price": 0.001,
        "liquidity": 75000,
        "volume_24h": 500000,
        "volume_1h": 25000,
        "volume_5m": 3000,
        "change_24h": 45,
        "change_6h": 20,
        "change_1h": 5,
        "change_5m": 2,
        "buys_24h": 150,
        "sells_24h": 80,
        "age_hours": 5
    }
    
    result = ai.analyze_token(test_token)
    print(f"[AI LAYER] Analysis complete:")
    print(f"   Scam: {result['scores']['scam_probability']}/100")
    print(f"   Rug: {result['scores']['rug_probability']}/100")
    print(f"   Whale: {result['scores']['whale_score']}/100")
    print(f"   Momentum: {result['scores']['momentum_score']}/100")
    print(f"   Liquidity: {result['scores']['liquidity_health']}/100")
    print(f"   Overall: {result['overall_score']}/100")
    print(f"   Recommendation: {result['recommendation']}")
