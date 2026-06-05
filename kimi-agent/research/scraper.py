"""Async web scraper for Kimi Telegram Agent."""
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class WebScraper:
    """Async web scraper with content extraction."""
    
    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_length = settings.MAX_SCRAPE_CONTENT_LENGTH
        self.ua = UserAgent()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a webpage and extract content.
        
        Returns:
            Dict with title, content, metadata, and status
        """
        headers = {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Extract title
                title = self._extract_title(soup)
                
                # Extract main content
                content = self._extract_content(soup)
                
                # Extract metadata
                metadata = self._extract_metadata(soup, url)
                
                logger.info(f"Scraped {url[:80]}: {len(content)} chars")
                
                return {
                    "url": url,
                    "title": title,
                    "content": content[:self.max_length],
                    "metadata": metadata,
                    "status": "success",
                    "status_code": response.status_code
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error scraping {url}: {e.response.status_code}")
            return {
                "url": url,
                "title": "",
                "content": "",
                "metadata": {},
                "status": "error",
                "error": f"HTTP {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "title": "",
                "content": "",
                "metadata": {},
                "status": "error",
                "error": str(e)
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try various title sources
        for selector in [
            "h1",
            "title",
            ".article-title",
            "[property='og:title']",
            "meta[name='twitter:title']"
        ]:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == "meta":
                    return elem.get("content", "").strip()
                return elem.get_text().strip()
        
        return "Untitled"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content area
        content_selectors = [
            "article",
            "main",
            ".article-content",
            ".post-content",
            ".entry-content",
            "[role='main']",
            ".content",
            "#content",
            "body"
        ]
        
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                # Clean up whitespace
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                content = "\n".join(lines)
                if len(content) > 200:  # Ensure we got meaningful content
                    return content
        
        # Fallback: get all text
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract page metadata."""
        metadata = {"url": url}
        
        # Open Graph
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        for tag in og_tags:
            prop = tag.get("property", "").replace("og:", "")
            metadata[f"og_{prop}"] = tag.get("content", "")
        
        # Twitter cards
        twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            metadata[f"twitter_{name}"] = tag.get("content", "")
        
        # Description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            metadata["description"] = desc.get("content", "")
        
        # Author
        author = soup.find("meta", attrs={"name": "author"})
        if author:
            metadata["author"] = author.get("content", "")
        
        # Published time
        published = soup.find("meta", property="article:published_time")
        if published:
            metadata["published_time"] = published.get("content", "")
        
        # Site name
        site = soup.find("meta", property="og:site_name")
        if site:
            metadata["site_name"] = site.get("content", "")
        
        return metadata
    
    async def scrape_multiple(
        self,
        urls: list[str],
        max_concurrent: int = 5
    ) -> list[dict[str, Any]]:
        """Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of scrape results
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(url: str) -> dict[str, Any]:
            async with semaphore:
                return await self.scrape(url)
        
        tasks = [scrape_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Scraping task failed: {r}")
            else:
                valid_results.append(r)
        
        return valid_results


scraper = WebScraper()
