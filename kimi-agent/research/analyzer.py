"""Main analysis orchestrator for research tasks."""
import logging
from typing import Any

from brain.llm import llm
from research.search import search_engine
from research.scraper import scraper
from research.verifier import verifier

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """Orchestrates multi-step research and analysis workflows."""
    
    async def research(
        self,
        query: str,
        depth: str = "standard"
    ) -> dict[str, Any]:
        """Execute deep research workflow.
        
        1. Search for sources
        2. Scrape top results
        3. Extract claims
        4. Verify claims
        5. Synthesize answer
        
        Returns structured report.
        """
        logger.info(f"Starting research: {query[:100]}")
        
        # Step 1: Search
        search_results = await search_engine.search(query, max_results=10)
        if not search_results:
            return {
                "success": False,
                "error": "No search results found",
                "query": query
            }
        
        # Step 2: Scrape
        urls = [r["url"] for r in search_results if r.get("url")]
        scraped = await scraper.scrape_multiple(urls[:7])  # Top 7 sources
        valid_sources = [s for s in scraped if s["status"] == "success" and s["content"]]
        
        if not valid_sources:
            return {
                "success": False,
                "error": "Could not extract content from sources",
                "sources": search_results
            }
        
        # Step 3: Extract claims from combined content
        combined_content = "\n\n".join([s["content"][:5000] for s in valid_sources])
        claims = await llm.extract_claims(combined_content)
        
        # Step 4: Verify claims
        claims_verification = None
        if claims:
            claims_verification = await verifier.verify_multiple(claims, valid_sources)
        
        # Step 5: Synthesize
        synthesis = await llm.synthesize_research(
            query=query,
            sources=valid_sources,
            claims_verification=claims_verification
        )
        
        # Build final report
        report = {
            "success": True,
            "query": query,
            "summary": synthesis.get("summary", ""),
            "detailed_answer": synthesis.get("detailed_answer", ""),
            "sources": [
                {
                    "title": s.get("title", "Source"),
                    "url": s["url"],
                    "site": s.get("metadata", {}).get("site_name", "")
                }
                for s in valid_sources
            ],
            "key_claims": synthesis.get("key_claims", []),
            "consensus": synthesis.get("consensus_areas"),
            "controversy": synthesis.get("controversial_areas"),
            "source_diversity": synthesis.get("source_diversity_score", 0),
            "overall_confidence": synthesis.get("overall_confidence", 0),
            "caveats": synthesis.get("caveats", ""),
            "claims_verification": claims_verification
        }
        
        logger.info(f"Research complete: {len(valid_sources)} sources, {len(claims or [])} claims")
        return report
    
    async def analyze_text(self, text: str) -> dict[str, Any]:
        """Analyze text content (summary, key points, sentiment)."""
        analysis = await llm.analyze(text, mode="summarize")
        
        # Also extract claims for fact-check
        claims = await llm.extract_claims(text)
        
        return {
            "analysis": analysis,
            "claims": claims,
            "word_count": len(text.split()),
            "char_count": len(text)
        }
    
    async def analyze_url(self, url: str) -> dict[str, Any]:
        """Analyze URL content."""
        # Scrape
        result = await scraper.scrape(url)
        if result["status"] != "success":
            return {
                "success": False,
                "error": result.get("error", "Failed to scrape"),
                "url": url
            }
        
        # Analyze content
        content = result["content"]
        analysis = await llm.analyze(content, mode="url", context={
            "metadata": result.get("metadata", {})
        })
        
        # Extract and verify claims
        claims = await llm.extract_claims(content)
        verification = None
        if claims:
            # Search for additional sources to verify
            search_results = await search_engine.search(
                f"{result.get('title', '')} {claims[0][:100]}",
                max_results=5
            )
            sources = await scraper.scrape_multiple(
                [r["url"] for r in search_results if r.get("url")]
            )
            verification = await verifier.verify_multiple(claims, sources)
        
        return {
            "success": True,
            "url": url,
            "title": result.get("title", ""),
            "analysis": analysis,
            "claims": claims,
            "verification": verification,
            "metadata": result.get("metadata", {})
        }
    
    async def analyze_news(self, topic: str) -> dict[str, Any]:
        """Analyze news on a topic."""
        # Search news
        news_results = await search_engine.search_news(topic, max_results=10)
        if not news_results:
            return {
                "success": False,
                "error": "No news found",
                "topic": topic
            }
        
        # Scrape articles
        urls = [r["url"] for r in news_results if r.get("url")]
        scraped = await scraper.scrape_multiple(urls[:5])
        valid_articles = [s for s in scraped if s["status"] == "success"]
        
        # Analyze
        combined = "\n\n---\n\n".join([
            f"Article: {a.get('title', 'Unknown')}\n{a['content'][:3000]}"
            for a in valid_articles
        ])
        
        analysis = await llm.analyze(combined, mode="news", context={
            "sources": news_results[:5]
        })
        
        # Calculate source diversity
        sites = set(a.get("metadata", {}).get("site_name", "") for a in valid_articles)
        diversity_score = min(100, len(sites) * 25)
        
        return {
            "success": True,
            "topic": topic,
            "analysis": analysis,
            "articles": [
                {
                    "title": a.get("title", ""),
                    "url": a["url"],
                    "site": a.get("metadata", {}).get("site_name", "")
                }
                for a in valid_articles
            ],
            "source_diversity_score": diversity_score,
            "article_count": len(valid_articles)
        }


analyzer = AnalysisOrchestrator()
