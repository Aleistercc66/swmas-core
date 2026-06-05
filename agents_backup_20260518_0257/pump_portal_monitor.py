#!/usr/bin/env python3
"""
🔥 PUMP PORTAL WEBSOCKET — Real-time Pump.fun Token Launches
Captures new launches BEFORE they appear on DexScreener
"""
import asyncio
import websockets
import json
from datetime import datetime

# Pump.fun WebSocket endpoints
PUMP_FUN_WS = "wss://pumpportal.fun/api/data"

class PumpPortalMonitor:
    """Monitor Pump.fun for new token launches via WebSocket"""
    
    def __init__(self):
        self.new_launches = []
        self.active_tokens = {}
        
    async def subscribe_to_new_tokens(self):
        """Subscribe to new token creation events on Pump.fun"""
        async with websockets.connect(PUMP_FUN_WS) as ws:
            # Subscribe to new token events
            subscribe_msg = {
                "method": "subscribeNewToken",
                "params": []
            }
            await ws.send(json.dumps(subscribe_msg))
            print("[PUMP PORTAL] Subscribed to new token events")
            
            # Also subscribe to trades for tracking
            trade_msg = {
                "method": "subscribeTokenTrade",
                "params": []
            }
            await ws.send(json.dumps(trade_msg))
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(msg)
                    self.process_message(data)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await ws.send(json.dumps({"method": "ping"}))
                    
    def process_message(self, data):
        """Process incoming WebSocket messages"""
        msg_type = data.get("type", "")
        
        if msg_type == "newToken":
            self.handle_new_token(data)
        elif msg_type == "trade":
            self.handle_trade(data)
            
    def handle_new_token(self, data):
        """Handle new token launch"""
        token = {
            "symbol": data.get("symbol", "???"),
            "name": data.get("name", "???"),
            "mint": data.get("mint", ""),
            "creator": data.get("creator", ""),
            "timestamp": datetime.now().isoformat(),
            "initial_liquidity": data.get("initialLiquidity", 0),
            "initial_price": data.get("initialPrice", 0)
        }
        
        self.new_launches.append(token)
        
        print(f"\n🚀 [PUMP FUN] NEW TOKEN LAUNCHED!")
        print(f"   Symbol: {token['symbol']}")
        print(f"   Name: {token['name']}")
        print(f"   Mint: {token['mint'][:20]}...")
        print(f"   Time: {token['timestamp']}")
        
        # Alert via Telegram (hook into existing system)
        self.send_alert(token)
        
    def handle_trade(self, data):
        """Handle trade events for tracking volume"""
        mint = data.get("mint", "")
        if mint in self.active_tokens:
            self.active_tokens[mint]["volume"] += data.get("solAmount", 0)
            self.active_tokens[mint]["trades"] += 1
            
    def send_alert(self, token):
        """Send alert to Telegram integration"""
        # This will hook into our existing alert system
        alert_data = {
            "type": "PUMP_FUN_LAUNCH",
            "token": token,
            "urgency": "HIGH",
            "timestamp": datetime.now().isoformat()
        }
        
        # Write to shared state for other agents to pick up
        import json
        with open("/root/.openclaw/workspace/agents/tmp_state/pump_fun_launches.json", "a") as f:
            f.write(json.dumps(alert_data) + "\n")
            
    async def run(self):
        """Main monitoring loop"""
        print("[PUMP PORTAL MONITOR] Starting...")
        print("   Endpoint: Pump.fun WebSocket")
        print("   Monitoring: New token launches, trades")
        
        while True:
            try:
                await self.subscribe_to_new_tokens()
            except Exception as e:
                print(f"[PUMP PORTAL ERROR] {e} — reconnecting in 5s...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    monitor = PumpPortalMonitor()
    asyncio.run(monitor.run())
