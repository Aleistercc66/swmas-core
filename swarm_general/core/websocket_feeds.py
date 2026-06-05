#!/usr/bin/env python3
"""
📡 WEBSOCKET REAL-TIME DATA FEEDS
Συνεχής streaming από DexScreener και άλλες πηγές.
"""
import asyncio
import websockets
import json
import logging
import time
from typing import Dict, List, Callable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('WebSocketFeeds')

class WebSocketDataFeeds:
    """
    Real-time data feeds μέσω WebSocket.
    Συνδέεται σε Helius RPC για Solana data.
    """
    
    def __init__(self):
        self.connections: Dict[str, any] = {}
        self.subscribers: List[Callable] = []
        self.is_running = False
        self.reconnect_delay = 5
        self.data_buffer: List[Dict] = []
        self.buffer_size = 1000
        
        # Helius RPC WebSocket (free tier)
        self.helius_ws_url = "wss://mainnet.helius-rpc.com/?api-key=demo"
        
    async def start(self):
        """Ξεκινάει όλα τα WebSocket connections"""
        self.is_running = True
        
        logger.info("📡 WebSocket Feeds starting...")
        
        # Start connections σε parallel
        tasks = [
            asyncio.create_task(self._helius_solana_stream()),
            asyncio.create_task(self._dexscreener_simulated_stream()),
            asyncio.create_task(self._monitor_health())
        ]
        
        await asyncio.gather(*tasks)
    
    async def _helius_solana_stream(self):
        """Helius Solana RPC stream για transactions"""
        # Skip if using demo key — it will 401 forever
        if "demo" in self.helius_ws_url:
            logger.warning("⚠️ Helius demo key detected — WebSocket disabled. Set a real API key to enable.")
            await asyncio.sleep(3600)  # sleep long, don't spam
            return
        logger.info("🔗 Connecting to Helius Solana RPC...")
        
        while self.is_running:
            try:
                async with websockets.connect(self.helius_ws_url) as ws:
                    logger.info("✅ Helius WebSocket connected")
                    
                    # Subscribe to account changes (for token accounts)
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "accountSubscribe",
                        "params": [
                            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token program
                            {"commitment": "confirmed"}
                        ]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            
                            # Process transaction data
                            if 'params' in data:
                                await self._process_solana_update(data['params'])
                                
                        except json.JSONDecodeError:
                            pass
                            
            except Exception as e:
                logger.error(f"Helius connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _dexscreener_simulated_stream(self):
        """Simulated real-time stream (DexScreener δεν έχει official WebSocket)"""
        logger.info("📊 Starting DexScreener simulated stream...")
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            while self.is_running:
                try:
                    # Poll για updates κάθε 10 δευτερόλεπτα (simulated real-time)
                    async with session.get(
                        "https://api.dexscreener.com/token-profiles/latest/v1",
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check for new tokens
                            await self._check_new_tokens(data)
                            
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"DexScreener poll error: {e}")
                    await asyncio.sleep(5)
    
    async def _check_new_tokens(self, tokens: List[Dict]):
        """Ελέγχει για νέα tokens"""
        current_time = time.time()
        
        for token in tokens[:20]:  # Check top 20
            addr = token.get('tokenAddress', '')
            
            if addr and addr not in self.data_buffer:
                # New token detected!
                logger.info(f"🆕 NEW TOKEN: {addr[:20]}...")
                
                # Add to buffer
                self.data_buffer.append({
                    'address': addr,
                    'chain': token.get('chainId', ''),
                    'timestamp': current_time,
                    'type': 'new_token'
                })
                
                # Notify subscribers
                await self._notify_subscribers({
                    'type': 'new_token',
                    'data': token,
                    'timestamp': current_time
                })
        
        # Trim buffer
        if len(self.data_buffer) > self.buffer_size:
            self.data_buffer = self.data_buffer[-self.buffer_size:]
    
    async def _process_solana_update(self, data: Dict):
        """Επεξεργάζεται Solana updates"""
        # Extract transaction info
        try:
            result = data.get('result', {})
            value = result.get('value', {})
            
            # Check for large transactions
            if 'lamports' in value:
                lamports = value['lamports']
                sol = lamports / 1e9
                
                if sol > 100:  # Large transaction
                    logger.info(f"🐋 LARGE SOLANA TX: {sol:.2f} SOL")
                    
                    await self._notify_subscribers({
                        'type': 'large_tx',
                        'chain': 'solana',
                        'amount': sol,
                        'timestamp': time.time()
                    })
                    
        except Exception as e:
            logger.error(f"Error processing Solana update: {e}")
    
    async def _monitor_health(self):
        """Monitor health των connections"""
        while self.is_running:
            active_connections = len([c for c in self.connections.values() if c])
            
            logger.info(
                f"📡 WebSocket Health | "
                f"Active: {active_connections} | "
                f"Buffer: {len(self.data_buffer)} | "
                f"Subscribers: {len(self.subscribers)}"
            )
            
            await asyncio.sleep(60)
    
    async def _notify_subscribers(self, data: Dict):
        """Ειδοποιεί όλους τους subscribers"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")
    
    def subscribe(self, callback: Callable):
        """Προσθέτει subscriber"""
        self.subscribers.append(callback)
        logger.info(f"📡 New subscriber added. Total: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable):
        """Αφαιρεί subscriber"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_buffer(self) -> List[Dict]:
        """Επιστρέφει data buffer"""
        return self.data_buffer[-100:]  # Last 100
    
    async def stop(self):
        """Σταματάει όλα τα feeds"""
        self.is_running = False
        
        # Close connections
        for name, ws in self.connections.items():
            if ws:
                await ws.close()
                
        logger.info("🛑 WebSocket Feeds stopped")


# Simulated WebSocket for testing
class SimulatedWebSocketFeed:
    """Simulated feed για testing χωρίς real connections"""
    
    def __init__(self):
        self.is_running = False
        self.subscribers = []
        
    async def start(self):
        """Ξεκινάει simulated stream"""
        self.is_running = True
        
        logger.info("🎮 Simulated WebSocket feed started")
        
        # Generate simulated data
        while self.is_running:
            # Simulate new token detection
            if time.time() % 60 < 10:  # Every minute
                await self._generate_simulated_data()
                
            await asyncio.sleep(10)
    
    async def _generate_simulated_data(self):
        """Παράγει simulated data"""
        import random
        
        token = {
            'type': 'new_token',
            'address': f"simulated_{random.randint(1000, 9999)}",
            'chain': 'solana',
            'price': random.uniform(0.0001, 1.0),
            'volume': random.uniform(10000, 1000000),
            'timestamp': time.time()
        }
        
        logger.info(f"🎮 Simulated: New token {token['address']}")
        
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(token)
            except:
                pass
    
    def subscribe(self, callback):
        self.subscribers.append(callback)
    
    async def stop(self):
        self.is_running = False


async def main():
    """Main entry"""
    feeds = WebSocketDataFeeds()
    
    # Add test subscriber
    def on_data(data):
        print(f"📡 Received: {data.get('type')}")
    
    feeds.subscribe(on_data)
    
    try:
        await feeds.start()
    except KeyboardInterrupt:
        await feeds.stop()

if __name__ == '__main__':
    asyncio.run(main())
