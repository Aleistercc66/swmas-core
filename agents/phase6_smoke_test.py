#!/usr/bin/env python3
"""Phase 6 smoke test: Event-driven pipeline test."""
import asyncio
import sys
sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType, SwarmEvent
from core.events import TokenDiscoveredEvent, TokensValidatedEvent, RiskAssessedEvent

async def phase6_smoke_test():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🔥 PHASE 6: EVENT-DRIVEN AGENT CONVERSION TEST         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    bus = await get_event_bus()
    print(f"✅ EventBus: {'Redis' if bus.is_connected else 'In-Memory'}")
    
    events_received = {et.value: [] for et in EventType}
    
    async def monitor_handler(event: SwarmEvent):
        events_received[event.event_type].append(event)
        print(f"  📥 [{event.source:12s}] → {event.event_type:20s}")
    
    consumers = []
    for et in EventType:
        task = await bus.subscribe(event_type=et, consumer_name=f"phase6_test", handler=monitor_handler)
        consumers.append(task)
    
    print(f"\n✅ Subscribed to {len(consumers)} event types")
    
    # Step 1: Scanner
    print("\n--- Step 1: Scanner publishes TOKENS_DISCOVERED ---")
    scanner_event = TokenDiscoveredEvent(
        tokens=[
            {"symbol": "TEST_SOL", "price": 150.0, "volume_24h": 500000, "liquidity": 200000,
             "price_change_24h": 15.0, "price_change_1h": 3.5, "price_change_5m": 1.2, "buy_ratio": 1.5},
            {"symbol": "TEST_BONK", "price": 0.00001, "volume_24h": 100000, "liquidity": 75000,
             "price_change_24h": 25.0, "price_change_1h": 5.0, "price_change_5m": 2.0, "buy_ratio": 2.0},
        ],
        batch_id="phase6_test_001",
    )
    await bus.publish_simple(event_type=EventType.TOKENS_DISCOVERED, data=scanner_event.model_dump(), source="scanner", correlation_id="phase6_test_001")
    print(f"📤 Published: {len(scanner_event.tokens)} tokens")
    await asyncio.sleep(0.5)
    
    # Step 2: Validator
    print("\n--- Step 2: Validator publishes TOKENS_VALIDATED ---")
    validated_event = TokensValidatedEvent(
        validated_tokens=[
            {"scanner_output_id": 1, "symbol": "TEST_SOL", "is_approved": True, "tier": "TIER_2", "confidence": 75.0,
             "pass_rate": 0.75, "total_checks": 8, "passed_checks": 6, "checks": [], "rejection_reason": "", "buy_sell_ratio": 1.5},
            {"scanner_output_id": 2, "symbol": "TEST_BONK", "is_approved": True, "tier": "TIER_1", "confidence": 90.0,
             "pass_rate": 0.875, "total_checks": 8, "passed_checks": 7, "checks": [], "rejection_reason": "", "buy_sell_ratio": 2.0},
        ],
        batch_id="phase6_test_001",
    )
    await bus.publish_simple(event_type=EventType.TOKENS_VALIDATED, data=validated_event.model_dump(), source="validator", correlation_id="phase6_test_001")
    print(f"📤 Published: {validated_event.approved_count} approved")
    await asyncio.sleep(0.5)
    
    # Step 3: Risk Engine
    print("\n--- Step 3: Risk Engine publishes RISK_ASSESSED ---")
    risk_event = RiskAssessedEvent(
        signals=[
            {"validator_output_id": 1, "symbol": "TEST_SOL", "tier": "TIER_2", "entry_price": 150.0, "stop_loss_price": 135.0,
             "take_profit_1": 225.0, "take_profit_2": 300.0, "take_profit_3": 450.0, "stop_distance_pct": 10.0,
             "risk_reward_ratio": 2.5, "position_size_pct": 2.0, "composite_score": 72.5, "atr_proxy": 7.5,
             "volatility_regime": "MEDIUM", "is_active": True, "is_executable": True},
            {"validator_output_id": 2, "symbol": "TEST_BONK", "tier": "TIER_1", "entry_price": 0.00001, "stop_loss_price": 0.000008,
             "take_profit_1": 0.000015, "take_profit_2": 0.00002, "take_profit_3": 0.00003, "stop_distance_pct": 20.0,
             "risk_reward_ratio": 3.0, "position_size_pct": 1.5, "composite_score": 85.0, "atr_proxy": 12.5,
             "volatility_regime": "HIGH", "is_active": True, "is_executable": True},
        ],
        batch_id="phase6_test_001",
    )
    await bus.publish_simple(event_type=EventType.RISK_ASSESSED, data=risk_event.model_dump(), source="risk_engine", correlation_id="phase6_test_001")
    print(f"📤 Published: {risk_event.high_quality_count} high-quality signals")
    await asyncio.sleep(1.0)
    
    # Results
    print(f"\n{'═' * 60}")
    print("║                    📊 RESULTS                              ║")
    print(f"{'═' * 60}")
    
    total = 0
    for et, events in events_received.items():
        count = len(events)
        total += count
        if count > 0:
            print(f"  ✅ {et:20s}: {count} events")
    
    print(f"\n  📈 Total: {total}")
    
    success = (
        len(events_received.get(EventType.TOKENS_DISCOVERED.value, [])) >= 1 and
        len(events_received.get(EventType.TOKENS_VALIDATED.value, [])) >= 1 and
        len(events_received.get(EventType.RISK_ASSESSED.value, [])) >= 1
    )
    
    if success:
        print(f"\n  🔥 PHASE 6 PASSED ✅")
    else:
        print(f"\n  ❌ PHASE 6 FAILED")
    
    for task in consumers:
        task.cancel()
    await bus.disconnect()
    return success

if __name__ == "__main__":
    success = asyncio.run(phase6_smoke_test())
    sys.exit(0 if success else 1)
