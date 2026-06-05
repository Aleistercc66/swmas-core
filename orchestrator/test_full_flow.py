#!/usr/bin/env python3
"""Full flow test simulating Telegram bot"""
import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/orchestrator')

from core.wallet_commands import WalletCommandHandler

class MockUpdate:
    def __init__(self):
        self.effective_user = MockUser()
        self.message = MockMessage()

class MockUser:
    def __init__(self):
        self.id = 158923136

class MockMessage:
    def __init__(self):
        self.text = "/portfolio"
        self.responses = []
    
    async def reply_text(self, text, parse_mode=None):
        self.responses.append((text, parse_mode))
        print(f"📤 BOT RESPONSE: {text[:200]}...")

class MockContext:
    def __init__(self):
        self.args = []

async def test():
    handler = WalletCommandHandler()
    await handler.initialize()
    
    update = MockUpdate()
    context = MockContext()
    
    print("🔍 Testing /portfolio command...")
    try:
        await handler.cmd_portfolio(update, context)
        print(f"\n✅ Command completed! {len(update.message.responses)} responses sent")
        for i, (text, mode) in enumerate(update.message.responses):
            print(f"\nResponse {i+1}:")
            print(text[:500])
    except Exception as e:
        print(f"\n❌ COMMAND FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
