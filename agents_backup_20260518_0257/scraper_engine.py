#!/usr/bin/env python3
"""
🕷️ ADVANCED SCRAPER ENGINE — Layer 2 Enrichment
Playwright + BeautifulSoup for DexScreener, GMGN, Photon, BullX
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
from datetime import datetime

class CryptoScraperEngine:
    """Browser-based scraper for crypto platforms"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.results = []
        
    async def init_browser(self):
        """Initialize stealth browser"""
        self.playwright = await async_playwright().start()
        
        # Stealth context with anti-detection
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York"
        )
        
        # Inject stealth script
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
    async def scrape_dexscreener(self, chain="solana", min_volume=10000):
        """Scrape DexScreener for trending pairs"""
        page = await self.context.new_page()
        
        try:
            url = f"https://dexscreener.com/{chain}?minLiq=25000&minVol={min_volume}&maxAge=24"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000)  # Wait for JS to load
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            pairs = []
            # DexScreener uses specific classes — adjust as needed
            pair_elements = soup.find_all('div', class_='ds-dex-table-row')
            
            for elem in pair_elements[:20]:  # Top 20
                try:
                    symbol = elem.find('span', class_='symbol').text.strip()
                    price = elem.find('span', class_='price').text.strip()
                    volume = elem.find('span', class_='volume').text.strip()
                    
                    pairs.append({
                        "symbol": symbol,
                        "price": price,
                        "volume_24h": volume,
                        "source": "dexscreener_scrape",
                        "timestamp": datetime.now().isoformat()
                    })
                except:
                    continue
                    
            print(f"[SCRAPER] DexScreener: {len(pairs)} pairs scraped")
            return pairs
            
        finally:
            await page.close()
            
    async def scrape_gmgn(self, timeframe="1h"):
        """Scrape GMGN.ai for trending tokens"""
        page = await self.context.new_page()
        
        try:
            url = f"https://gmgn.ai/?tab={timeframe}"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            tokens = []
            # GMGN specific selectors
            token_rows = soup.find_all('tr', class_='token-row')
            
            for row in token_rows[:15]:
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        tokens.append({
                            "symbol": cells[0].text.strip(),
                            "price": cells[1].text.strip(),
                            "change": cells[2].text.strip(),
                            "volume": cells[3].text.strip(),
                            "source": "gmgn_scrape",
                            "timestamp": datetime.now().isoformat()
                        })
                except:
                    continue
                    
            print(f"[SCRAPER] GMGN: {len(tokens)} tokens scraped")
            return tokens
            
        finally:
            await page.close()
            
    async def scrape_photon(self):
        """Scrape Photon for momentum signals"""
        page = await self.context.new_page()
        
        try:
            url = "https://photon-sol.tinyastro.io/"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            # Photon is heavily JS-rendered — may need more work
            
            print(f"[SCRAPER] Photon: page loaded")
            return []
            
        finally:
            await page.close()
            
    async def save_results(self, data, filename):
        """Save scraped data to shared state"""
        filepath = f"/root/.openclaw/workspace/agents/tmp_state/{filename}.json"
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "count": len(data),
                "data": data
            }, f, indent=2)
            
    async def run(self):
        """Main scraper loop"""
        print("[SCRAPER ENGINE] Initializing browser...")
        await self.init_browser()
        
        while True:
            try:
                print("\n[SCRAPER] Starting scrape round...")
                
                # Scrape multiple sources
                dex_data = await self.scrape_dexscreener("solana")
                await self.save_results(dex_data, "dexscreener_scraped")
                
                gmgn_data = await self.scrape_gmgn("1h")
                await self.save_results(gmgn_data, "gmgn_scraped")
                
                print(f"[SCRAPER] Round complete. Sleeping 60s...")
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"[SCRAPER ERROR] {e}")
                await asyncio.sleep(30)
                
    async def close(self):
        """Clean up"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

if __name__ == "__main__":
    scraper = CryptoScraperEngine()
    try:
        asyncio.run(scraper.run())
    except KeyboardInterrupt:
        print("\n[SCRAPER] Shutting down...")
        asyncio.run(scraper.close())
