"""Fact verification engine for Kimi Telegram Agent."""
import logging
from typing import Any

from config import settings
from brain.llm import llm
from research.search import search_engine
from research.scraper import scraper

logger = logging.getLogger(__name__)


class FactVerifier:
    """Cross-reference claims against multiple sources."""
    
    def __init__(self):
        self.min_sources = 2
        self.confidence_threshold = 70
    
    async def verify_claim(
        self,
        claim: str,
        sources: list[dict] | None = None
    ) -> dict[str, Any]:
        """Verify a single claim against sources.
        
        If no sources provided, will search for evidence.
        
        Returns:
            {
                "verified": bool | None,
                "confidence": float,
                "supporting": list,
                "contradicting": list,
                "neutral": list,
                "explanation": str
            }
        """
        try:
            # Search for evidence if no sources
            if not sources:
                search_results = await search_engine.search(
                    claim,
                    max_results=5
                )
                sources = await scraper.scrape_multiple(
                    [r["url"] for r in search_results if r.get("url")]
                )
            
            if not sources:
                return {
                    "verified": None,
                    "confidence": 0,
                    "supporting": [],
                    "contradicting": [],
                    "neutral": [],
                    "explanation": "No sources found for verification"
                }
            
            # Use LLM to verify
            verification_result = await llm.verify_claims(
                claims=[claim],
                evidence=sources
            )
            
            if verification_result:
                result = verification_result[0]
                return {
                    "verified": result.get("verified"),
                    "confidence": result.get("confidence", 0),
                    "supporting": result.get("supporting_sources", []),
                    "contradicting": result.get("contradicting_sources", []),
                    "neutral": [],
                    "explanation": result.get("explanation", "")
                }
            
            # Fallback: simple keyword check
            return await self._simple_verify(claim, sources)
            
        except Exception as e:
            logger.error(f"Verification failed for claim '{claim[:100]}': {e}")
            return {
                "verified": None,
                "confidence": 0,
                "supporting": [],
                "contradicting": [],
                "neutral": [],
                "explanation": f"Verification error: {str(e)}"
            }
    
    async def _simple_verify(
        self,
        claim: str,
        sources: list[dict]
    ) -> dict[str, Any]:
        """Simple keyword-based verification fallback."""
        claim_keywords = set(claim.lower().split())
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "must", "shall",
                     "can", "need", "dare", "ought", "used", "to", "of", "in",
                     "for", "on", "with", "at", "by", "from", "as", "into",
                     "through", "during", "before", "after", "above", "below",
                     "between", "under", "and", "but", "or", "yet", "so",
                     "if", "because", "although", "though", "while", "where",
                     "when", "that", "which", "who", "whom", "whose", "what",
                     "this", "these", "those", "i", "you", "he", "she", "it",
                     "we", "they", "me", "him", "her", "us", "them", "my",
                     "your", "his", "its", "our", "their"}
        claim_keywords -= stop_words
        
        if len(claim_keywords) < 2:
            return {
                "verified": None,
                "confidence": 0,
                "supporting": [],
                "contradicting": [],
                "neutral": [],
                "explanation": "Claim too vague for keyword verification"
            }
        
        supporting = []
        contradicting = []
        
        for i, source in enumerate(sources):
            content = source.get("content", "").lower()
            matches = sum(1 for kw in claim_keywords if kw in content)
            match_ratio = matches / len(claim_keywords) if claim_keywords else 0
            
            if match_ratio > 0.5:
                supporting.append(i + 1)
            elif match_ratio > 0.2:
                pass  # neutral
            else:
                contradicting.append(i + 1)
        
        # Calculate confidence
        total_sources = len(sources)
        support_ratio = len(supporting) / total_sources if total_sources else 0
        
        if support_ratio > 0.6:
            verified = True
            confidence = min(100, int(support_ratio * 100))
        elif support_ratio > 0.3:
            verified = None  # Uncertain
            confidence = int(support_ratio * 100)
        else:
            verified = False
            confidence = max(0, int((1 - support_ratio) * 100))
        
        return {
            "verified": verified,
            "confidence": confidence,
            "supporting": supporting,
            "contradicting": contradicting,
            "neutral": [],
            "explanation": f"Keyword match: {len(supporting)}/{total_sources} sources support"
        }
    
    async def verify_multiple(
        self,
        claims: list[str],
        sources: list[dict] | None = None
    ) -> list[dict[str, Any]]:
        """Verify multiple claims."""
        results = []
        for claim in claims:
            result = await self.verify_claim(claim, sources)
            result["claim"] = claim
            results.append(result)
        return results
    
    async def deep_verify(
        self,
        text: str,
        auto_extract: bool = True
    ) -> dict[str, Any]:
        """Deep verification of text content.
        
        1. Extract claims (if auto_extract)
        2. Search for sources
        3. Verify each claim
        4. Return comprehensive report
        """
        if auto_extract:
            claims = await llm.extract_claims(text)
        else:
            claims = [text]  # Treat entire text as single claim
        
        if not claims:
            return {
                "claims": [],
                "overall_verified": None,
                "overall_confidence": 0,
                "summary": "No verifiable claims found"
            }
        
        # Search for evidence for all claims combined
        combined_query = " ".join(claims[:3])  # Search top 3 claims
        search_results = await search_engine.search(combined_query, max_results=10)
        sources = await scraper.scrape_multiple(
            [r["url"] for r in search_results if r.get("url")]
        )
        
        # Verify each claim
        verified_claims = await self.verify_multiple(claims, sources)
        
        # Calculate overall
        confidences = [c["confidence"] for c in verified_claims]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        verified_count = sum(1 for c in verified_claims if c["verified"] is True)
        unverified_count = sum(1 for c in verified_claims if c["verified"] is None)
        contradicted_count = sum(1 for c in verified_claims if c["verified"] is False)
        
        if contradicted_count > 0:
            overall = False
        elif verified_count == len(verified_claims):
            overall = True
        else:
            overall = None
        
        return {
            "claims": verified_claims,
            "overall_verified": overall,
            "overall_confidence": avg_confidence,
            "verified_count": verified_count,
            "unverified_count": unverified_count,
            "contradicted_count": contradicted_count,
            "sources_count": len(sources),
            "summary": self._generate_summary(verified_claims, avg_confidence)
        }
    
    def _generate_summary(
        self,
        claims: list[dict],
        confidence: float
    ) -> str:
        """Generate human-readable summary."""
        total = len(claims)
        verified = sum(1 for c in claims if c["verified"] is True)
        unverified = sum(1 for c in claims if c["verified"] is None)
        contradicted = sum(1 for c in claims if c["verified"] is False)
        
        if contradicted > 0:
            return f"⚠️ {contradicted} of {total} claims appear to be contradicted by sources. {verified} verified, {unverified} uncertain."
        elif verified == total and confidence > 80:
            return f"✅ All {total} claims verified with high confidence ({confidence:.0f}%)."
        elif verified == total:
            return f"✅ All {total} claims appear verified, but confidence is moderate ({confidence:.0f}%)."
        elif unverified > 0:
            return f"⚠️ {verified} of {total} claims verified. {unverified} claims lack sufficient evidence."
        else:
            return f"Mixed results: {verified} verified, {unverified} uncertain, {contradicted} contradicted."


verifier = FactVerifier()
