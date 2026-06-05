#!/usr/bin/env python3
"""
🚀 ORCHESTRATOR v5.0 — Advanced Multi-Layer Architecture
Combines: WebSockets + Scraping + RPC + AI Analysis
"""
import asyncio
import json
import sys
from datetime import datetime
sys.path.insert(0, '/root/.openclaw/workspace/agents')

from solana_rpc_monitor import SolanaRPCMonitor
from pump_portal_monitor import PumpPortalMonitor
from scraper_engine import CryptoScraperEngine
from ai_evaluation_layer import AIEvaluationLayer
from anti_detection import AntiDetectionLayer

class AdvancedOrchestrator:
    """Orchestrate all advanced data sources"""
    
    def __init__(self):
        self.ai_layer = AIEvaluationLayer()
        self.anti_detect = AntiDetectionLayer()
        self.running = False
        
    async def run_all(self):
        """Run all advanced monitors in parallel"""
        print("[ORCHESTRATOR v5.0] Starting Advanced Architecture")
        print("=" * 60)
        print("Components:")
        print("  🔥 Solana RPC Monitor (<1s latency)")
        print("  🚀 Pump Portal WebSocket (instant launches)")
        print("  🕷️ Scraper Engine (DexScreener, GMGN)")
        print("  🧠 AI Evaluation Layer (scam/rug detection)")
        print("  🛡️ Anti-Detection (stealth mode)")
        print("=" * 60)
        
        self.running = True
        
        # Start all monitors
        tasks = [
            asyncio.create_task(self.run_rpc_monitor()),
            asyncio.create_task(self.run_pump_monitor()),
            asyncio.create_task(self.run_scraper()),
            asyncio.create_task(self.run_ai_analysis_loop()),
        ]
        
        await asyncio.gather(*tasks)
        
    async def run_rpc_monitor(self):
        """Run Solana RPC monitor"""
        monitor = SolanaRPCMonitor()
        try:
            await monitor.run()
        except Exception as e:
            print(f"[RPC MONITOR ERROR] {e}")
            await asyncio.sleep(10)
            
    async def run_pump_monitor(self):
        """Run Pump Portal monitor"""
        monitor = PumpPortalMonitor()
        try:
            await monitor.run()
        except Exception as e:
            print(f"[PUMP MONITOR ERROR] {e}")
            await asyncio.sleep(10)
            
    async def run_scraper(self):
        """Run scraper engine"""
        scraper = CryptoScraperEngine()
        try:
            await scraper.run()
        except Exception as e:
            print(f"[SCRAPER ERROR] {e}")
            await asyncio.sleep(30)
            
    async def run_ai_analysis_loop(self):
        """Continuous AI analysis of collected data"""
        while self.running:
            try:
                # Load latest data
                data_sources = [
                    "scanner_output.json",
                    "dexscreener_scraped.json",
                    "gmgn_scraped.json"
                ]
                
                all_tokens = []
                for source in data_sources:
                    try:
                        with open(f"/root/.openclaw/workspace/agents/tmp_state/{source}") as f:
                            data = json.load(f)
                            if "pairs" in data:
                                all_tokens.extend(data["pairs"])
                            elif "data" in data:
                                all_tokens.extend(data["data"])
                    except:
                        pass
                        
                if all_tokens:
                    # Analyze top tokens
                    analyses = self.ai_layer.batch_analyze(all_tokens[:10])
                    
                    for analysis in analyses:
                        if analysis["overall_score"] >= 70:
                            print(f"\n🔥 [AI HIGH SCORE] {analysis['symbol']}: {analysis['overall_score']}/100")
                            print(f"   Recommendation: {analysis['recommendation']}")
                            
                        self.ai_layer.save_analysis(analysis)
                        
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                print(f"[AI LOOP ERROR] {e}")
                await asyncio.sleep(30)
                
    def stop(self):
        """Stop all monitors"""
        self.running = False
        print("[ORCHESTRATOR] Stopping...")

if __name__ == "__main__":
    orchestrator = AdvancedOrchestrator()
    
    try:
        asyncio.run(orchestrator.run_all())
    except KeyboardInterrupt:
        print("\n[ORCHESTRATOR] Shutdown complete")
        orchestrator.stop()
