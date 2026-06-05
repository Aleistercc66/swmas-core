#!/usr/bin/env python3
"""
⚡ SOLANA RPC MONITOR — Layer 1 Fast Data
Direct blockchain reads for <1 sec latency
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
HELIUS_WS = "wss://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY"  # Optional, use public if no key

class SolanaRPCMonitor:
    """Monitor Solana blockchain for new token launches, Raydium pools, etc."""
    
    def __init__(self):
        self.recent_mints = []
        self.active_pools = []
        self.new_launches = []
        
    async def subscribe_to_logs(self, program_id="675kPX9MHTjS2zt1D7aW4rBcakCskpXDTXRaJ9pJu2qK"):  # Raydium AMM
        """Subscribe to Raydium program logs for new pools"""
        async with websockets.connect(HELIUS_WS if HELIUS_WS else SOLANA_RPC.replace("https", "wss")) as ws:
            # Subscribe to logs mentioning Raydium
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [program_id]},
                    {"commitment": "confirmed"}
                ]
            }
            await ws.send(json.dumps(subscribe_msg))
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    
                    if 'params' in data:
                        log_data = data['params']['result']['value']
                        self.process_log(log_data)
                        
                except asyncio.TimeoutError:
                    print("[SOLANA RPC] Ping")
                    await ws.send(json.dumps({"jsonrpc":"2.0","id":999,"method":"ping"}))
                    
    def process_log(self, log_data):
        """Process new log entries"""
        logs = log_data.get('logs', [])
        signature = log_data.get('signature', '')
        
        for log in logs:
            if 'initialize2' in log or 'CreatePool' in log:
                print(f"\n🔥 [SOLANA] NEW POOL DETECTED!")
                print(f"   Signature: {signature[:50]}...")
                self.new_launches.append({
                    "signature": signature,
                    "timestamp": datetime.now().isoformat(),
                    "source": "raydium"
                })
                
    def get_recent_transactions(self, limit=50):
        """Poll RPC for recent transactions"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                "675kPX9MHTjS2zt1D7aW4rBcakCskpXDTXRaJ9pJu2qK",  # Raydium
                {"limit": limit}
            ]
        }
        
        try:
            resp = requests.post(SOLANA_RPC, json=payload, timeout=5)
            data = resp.json()
            return data.get('result', [])
        except Exception as e:
            print(f"[RPC ERROR] {e}")
            return []

    async def run(self):
        """Main loop — RPC polling + WebSocket"""
        print("[SOLANA RPC MONITOR] Starting...")
        print(f"   RPC: {SOLANA_RPC}")
        print("   Monitoring: Raydium pools, new launches")
        
        # Start WebSocket listener
        ws_task = asyncio.create_task(self.subscribe_to_logs())
        
        # Poll RPC every 5 seconds as backup
        while True:
            await asyncio.sleep(5)
            txs = self.get_recent_transactions(10)
            if txs:
                print(f"[RPC POLL] {len(txs)} recent Raydium txs")

if __name__ == "__main__":
    monitor = SolanaRPCMonitor()
    asyncio.run(monitor.run())
