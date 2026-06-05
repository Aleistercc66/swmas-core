#!/usr/bin/env python3
"""
🛡️ ANTI-DETECTION LAYER
Proxy rotation, header rotation, stealth mode
"""
import random
import requests
from typing import Dict, List

class AntiDetectionLayer:
    """Provides stealth capabilities for web scraping"""
    
    def __init__(self):
        self.proxies = self._load_proxies()
        self.current_proxy = None
        self.request_count = 0
        
    def _load_proxies(self) -> List[str]:
        """Load proxy list (free tier or paid)"""
        # Free proxy sources — rotate frequently
        return [
            # Format: "http://user:pass@host:port"
            # Add your proxies here or load from file
        ]
        
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.8",
        "en;q=0.7",
    ]
    
    def get_random_headers(self) -> Dict[str, str]:
        """Generate randomized request headers"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
    def rotate_proxy(self) -> str:
        """Rotate to new proxy"""
        if not self.proxies:
            return None
        self.current_proxy = random.choice(self.proxies)
        return self.current_proxy
        
    def make_request(self, url: str, method="GET", **kwargs) -> requests.Response:
        """Make stealth request with rotation"""
        headers = self.get_random_headers()
        
        # Rotate proxy every 10 requests
        if self.request_count % 10 == 0:
            self.rotate_proxy()
        self.request_count += 1
        
        proxies = {}
        if self.current_proxy:
            proxies = {
                "http": self.current_proxy,
                "https": self.current_proxy
            }
            
        # Add random delay between requests
        import time
        time.sleep(random.uniform(0.5, 2.0))
        
        return requests.request(
            method=method,
            url=url,
            headers={**headers, **kwargs.get("headers", {})},
            proxies=proxies,
            timeout=kwargs.get("timeout", 30),
            **{k: v for k, v in kwargs.items() if k not in ["headers", "timeout"]}
        )

class StealthSession:
    """Persistent stealth session with cookie rotation"""
    
    def __init__(self):
        self.anti_detect = AntiDetectionLayer()
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """Configure session for stealth"""
        self.session.headers.update(self.anti_detect.get_random_headers())
        
    def get(self, url: str, **kwargs):
        """Stealth GET request"""
        self.session.headers.update(self.anti_detect.get_random_headers())
        return self.session.get(url, **kwargs)
        
    def post(self, url: str, **kwargs):
        """Stealth POST request"""
        self.session.headers.update(self.anti_detect.get_random_headers())
        return self.session.post(url, **kwargs)

if __name__ == "__main__":
    # Test
    stealth = AntiDetectionLayer()
    print("[ANTI-DETECTION] Layer initialized")
    print(f"   Proxies: {len(stealth.proxies)}")
    print(f"   User agents: {len(stealth.USER_AGENTS)}")
    
    # Test request
    try:
        resp = stealth.make_request("https://api.dexscreener.com/latest/dex/search/?q=SOL")
        print(f"   Test request: {resp.status_code}")
    except Exception as e:
        print(f"   Test failed: {e}")
