import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import os

logger = logging.getLogger(__name__)

class DashboardServer:
    """
    WebSocket Dashboard Server
    
    Serves real-time revenue data to the HTML dashboard
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.state: Dict = {
            'total_earned': 0.0,
            'monthly_projection': 113.59,
            'yearly_projection': 1363.10,
            'apr': 0.25,
            'capital': 409.99,
            'sol_balance': 20.50,
            'usd_value': 409.99,
            'phase': 1,
            'progress_pct': 200.0,
            'yield_earnings': 0.0006,
            'airdrop_earnings': 0.925,
            'mev_earnings': 0.10,
            'social_earnings': 0.0,
            'cycle': 1,
            'last_cycle': '09:15:00',
            'wallet': 'wallet_0x...',
            'log': 'Engine started'
        }
        self.running = False
        
    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register new client"""
        self.clients.add(websocket)
        logger.info(f"📊 New dashboard client connected. Total: {len(self.clients)}")
        
        # Send current state immediately
        await self.send_state(websocket)
        
    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister client"""
        self.clients.discard(websocket)
        logger.info(f"📊 Client disconnected. Total: {len(self.clients)}")
        
    async def send_state(self, websocket: websockets.WebSocketServerProtocol):
        """Send current state to a client"""
        try:
            await websocket.send(json.dumps(self.state))
        except Exception as e:
            logger.error(f"Failed to send state: {e}")
            
    async def broadcast(self):
        """Broadcast state to all clients"""
        if not self.clients:
            return
            
        message = json.dumps(self.state)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)
                
        # Remove disconnected clients
        for client in disconnected:
            self.clients.discard(client)
            
    async def update_state(self, updates: Dict):
        """Update state and broadcast"""
        self.state.update(updates)
        self.state['last_update'] = datetime.now().isoformat()
        await self.broadcast()
        
    async def handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get('type') == 'ping':
                    await websocket.send(json.dumps({'type': 'pong'}))
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            await self.unregister(websocket)
            
    async def start(self):
        """Start dashboard server"""
        self.running = True
        logger.info(f"📊 Dashboard server starting on ws://{self.host}:{self.port}")
        
        # Start WebSocket server
        async with websockets.serve(self.handler, self.host, self.port):
            logger.info(f"📊 Dashboard server running on http://{self.host}:{self.port}")
            logger.info(f"📊 Open dashboard.html in browser to view")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
    async def stop(self):
        """Stop dashboard server"""
        self.running = False
        logger.info("📊 Dashboard server stopped")


# ─── MAIN ───
async def main():
    """Run dashboard server"""
    server = DashboardServer()
    await server.start()


if __name__ == '__main__':
    asyncio.run(main())
