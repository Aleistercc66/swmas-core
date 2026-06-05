#!/usr/bin/env python3
"""📊 Event Bus Monitor — watch all streams and show stats."""
import asyncio
import sys
import time

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType, SwarmEvent
from core.event_bus import EventBus


async def monitor_all_streams():
    """Monitor all event streams."""
    bus = await get_event_bus()
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          📊 EVENT BUS MONITOR — Phase 6 Smoke Test           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\nRedis: {'✅ Connected' if bus.is_connected else '⚠️ Fallback'}")
    print(f"Streams prefix: {bus.prefix}")
    print()
    
    # Check all stream info
    for event_type in EventType:
        try:
            info = await bus.get_stream_info(event_type)
            stream_name = f"{bus.prefix}:stream:{event_type.value}"
            
            bar = "█" * min(info["length"] // 2, 20)
            
            print(f"  {event_type.value:20s} | Length: {info['length']:4d} {bar:20s} | Groups: {info['groups']}")
        except Exception as e:
            print(f"  {event_type.value:20s} | Error: {e}")
    
    # Subscribe to all events
    received_count = {et.value: 0 for et in EventType}
    
    async def track_event(event: SwarmEvent):
        received_count[event.event_type] += 1
        timestamp = event.timestamp.split("T")[1][:8] if "T" in event.timestamp else "??:??:??"
        print(f"\n  [{timestamp}] 🔥 {event.source:12s} → {event.event_type:20s} | {event.correlation_id or 'no-id'}")
    
    # Start consumers for all event types
    tasks = []
    for event_type in EventType:
        task = await bus.subscribe(
            event_type=event_type,
            consumer_name=f"monitor_{event_type.value}",
            handler=track_event,
        )
        tasks.append(task)
    
    print(f"\n✅ Monitoring {len(tasks)} streams...")
    print("Press Ctrl+C to stop\n")
    
    # Stats loop
    try:
        while True:
            await asyncio.sleep(5)
            print(f"\n{'─' * 60}")
            print(f"📈 STATS (last 5s)")
            total = sum(received_count.values())
            print(f"   Total events: {total}")
            for et, count in received_count.items():
                if count > 0:
                    print(f"   • {et:20s}: {count}")
            print(f"{'─' * 60}\n")
    except asyncio.CancelledError:
        pass
    
    # Cleanup
    for task in tasks:
        task.cancel()
    
    await bus.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(monitor_all_streams())
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
