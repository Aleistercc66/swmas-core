"""Web search engine with multiple provider support."""
import logging
from typing import Any

import httpx
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class SearchEngine:
    """Multi-provider web search engine."""
    
    def __init__(self):
        self.max_results = settings.MAX_SEARCH_RESULTS
        self.timeout = settings.REQUEST_TIMEOUT
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_duckduckgo(
        self,
        query: str,
        max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Search using DuckDuckGo (no API key needed)."""
        max_results = max_results or self.max_results
        
        try:
            with DDGS() as ddgs:
                results = ddgs.text(
                    query,
                    max_results=max_results,
                    region="wt-wt",
                    safesearch="off"
                )
                
                formatted = []
                for r in results:
                    formatted.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source": "duckduckgo"
                    })
                
                logger.info(f"DuckDuckGo search '{query[:50]}...': {len(formatted)} results")
                return formatted
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def search_bing(
        self,
        query: str,
        max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Search using Bing API (requires API key)."""
        if not settings.BING_API_KEY:
            return []
        
        max_results = max_results or self.max_results
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": settings.BING_API_KEY},
                params={
                    "q": query,
                    "count": max_results,
                    "mkt": "en-US"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            formatted = []
            for r in data.get("webPages", {}).get("value", []):
                formatted.append({
                    "title": r.get("name", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "source": "bing"
                })
            
            logger.info(f"Bing search '{query[:50]}...': {len(formatted)} results")
            return formatted
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def search_google(
        self,
        query: str,
        max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Search using Google Custom Search (requires API key + CSE ID)."""
        if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
            return []
        
        max_results = max_results or self.max_results
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.GOOGLE_API_KEY,
                    "cx": settings.GOOGLE_CSE_ID,
                    "q": query,
                    "num": min(max_results, 10)
                }
            )
            response.raise_for_status()
            data = response.json()
            
            formatted = []
            for r in data.get("items", []):
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                    "source": "google"
                })
            
            logger.info(f"Google search '{query[:50]}...': {len(formatted)} results")
            return formatted
    
    async def search(
        self,
        query: str,
        max_results: int | None = None,
        providers: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Search using available providers.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            providers: List of providers to use (duckduckgo, bing, google)
        
        Returns:
            List of search results with deduplication
        """
        providers = providers or ["duckduckgo"]
        all_results = []
        seen_urls = set()
        
        for provider in providers:
            try:
                if provider == "duckduckgo":
                    results = await self.search_duckduckgo(query, max_results)
                elif provider == "bing":
                    results = await self.search_bing(query, max_results)
                elif provider == "google":
                    results = await self.search_google(query, max_results)
                else:
                    continue
                
                for r in results:
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
            except Exception as e:
                logger.error(f"Search provider {provider} failed: {e}")
        
        # Sort by source diversity priority
        source_priority = {"google": 1, "bing": 2, "duckduckgo": 3}
        all_results.sort(key=lambda x: source_priority.get(x.get("source"), 99))
        
        return all_results[:max_results or self.max_results]
    
    async def search_news(
        self,
        query: str,
        max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Search for news articles."""
        news_query = f"{query} news latest"
        
        # Try DuckDuckGo news
        try:
            with DDGS() as ddgs:
                results = ddgs.news(
                    news_query,
                    max_results=max_results or self.max_results,
                    region="wt-wt"
                )
                
                formatted = []
                for r in results:
                    formatted.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("body", ""),
                        "source": r.get("source", "news"),
                        "date": r.get("date", "")
                    })
                
                logger.info(f"News search '{query[:50]}...': {len(formatted)} results")
                return formatted
        except Exception as e:
            logger.error(f"News search failed: {e}")
            # Fallback to regular search
            return await self.search(news_query, max_results)


search_engine = SearchEngine()
