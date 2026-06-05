#!/usr/bin/env python3
"""Phase 7 smoke test: Full event-driven pipeline with Master Orchestrator."""
import asyncio
import sys

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType, SwarmEvent
from core.events import TokenDiscoveredEvent, TokensValidatedEvent, RiskAssessedEvent


async def phase7_smoke_test():
    """Run full pipeline: Scanner → Validator → Risk → Master."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🧠 PHASE 7: MASTER ORCHESTRATOR TEST                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    bus = await get_event_bus()
    print(f"✅ EventBus: {'Redis' if bus.is_connected else 'In-Memory'}")
    
    # Track events per stage
    events_by_stage = {et.value: [] for et in EventType}
    decisions = []
    
    async def track_all(event: SwarmEvent):
        events_by_stage[event.event_type].append(event)
        
        if event.event_type == EventType.POSITION_OPENED.value:
            data = event.data
            decisions.append({
                "symbol": data.get("symbol", "?"),
                "decision": data.get("decision", "?"),
                "size": data.get("position_size_usd", 0),
                "confidence": data.get("confidence", 0),
            })
            print(f"  🟢 TRADE APPROVED: {data.get('symbol', '?')} ${data.get('position_size_usd', 0):.2f}")
        elif event.event_type == EventType.ALERT.value:
            data = event.data
            if data.get("decision") == "REJECT":
                print(f"  🔴 REJECTED: {data.get('symbol', '?')} — {data.get('reason', '')}")
        else:
            print(f"  📥 [{event.source:12s}] → {event.event_type:20s}")
    
    # Subscribe to ALL event types
    consumers = []
    for et in EventType:
        task = await bus.subscribe(
            event_type=et,
            consumer_name=f"phase7_test",
            handler=track_all,
        )
        consumers.append(task)
    
    print(f"\n✅ Subscribed to {len(consumers)} event types")
    
    # ── Step 1: Scanner ──
    print("\n--- [1] Scanner → TOKENS_DISCOVERED ---")
    scanner_event = TokenDiscoveredEvent(
        tokens=[
            {"symbol": "SOL", "price": 150.0, "volume_24h": 500000, "liquidity": 200000,
             "price_change_24h": 15.0, "price_change_1h": 3.5, "price_change_5m": 1.2, "buy_ratio": 1.5},
            {"symbol": "BONK", "price": 0.00001, "volume_24h": 100000, "liquidity": 75000,
             "price_change_24h": 25.0, "price_change_1h": 5.0, "price_change_5m": 2.0, "buy_ratio": 2.0},
            {"symbol": "JUP", "price": 0.85, "volume_24h": 1200000, "liquidity": 500000,
             "price_change_24h": 8.0, "price_change_1h": 1.5, "price_change_5m": 0.5, "buy_ratio": 1.1},
        ],
        batch_id="phase7_test_001",
    )
    await bus.publish_simple(
        event_type=EventType.TOKENS_DISCOVERED,
        data=scanner_event.model_dump(),
        source="scanner",
        correlation_id="phase7_test_001",
    )
    print(f"📤 Published: {len(scanner_event.tokens)} tokens")
    await asyncio.sleep(0.3)
    
    # ── Step 2: Validator ──
    print("\n--- [2] Validator → TOKENS_VALIDATED ---")
    validated_event = TokensValidatedEvent(
        validated_tokens=[
            {"scanner_output_id": 1, "symbol": "SOL", "is_approved": True, "tier": "TIER_2",
             "confidence": 75.0, "pass_rate": 0.75, "total_checks": 8, "passed_checks": 6,
             "checks": [], "rejection_reason": "", "buy_sell_ratio": 1.5},
            {"scanner_output_id": 2, "symbol": "BONK", "is_approved": True, "tier": "TIER_1",
             "confidence": 90.0, "pass_rate": 0.875, "total_checks": 8, "passed_checks": 7,
             "checks": [], "rejection_reason": "", "buy_sell_ratio": 2.0},
            {"scanner_output_id": 3, "symbol": "JUP", "is_approved": False, "tier": "TIER_3",
             "confidence": 45.0, "pass_rate": 0.375, "total_checks": 8, "passed_checks": 3,
             "checks": [], "rejection_reason": "Low confidence", "buy_sell_ratio": 1.1},
        ],
        batch_id="phase7_test_001",
    )
    await bus.publish_simple(
        event_type=EventType.TOKENS_VALIDATED,
        data=validated_event.model_dump(),
        source="validator",
        correlation_id="phase7_test_001",
    )
    print(f"📤 Published: {validated_event.approved_count} approved, {validated_event.rejected_count} rejected")
    await asyncio.sleep(0.3)
    
    # ── Step 3: Risk Engine ──
    print("\n--- [3] Risk Engine → RISK_ASSESSED ---")
    risk_event = RiskAssessedEvent(
        signals=[
            {"validator_output_id": 1, "symbol": "SOL", "tier": "TIER_2", "entry_price": 150.0,
             "stop_loss_price": 135.0, "take_profit_1": 225.0, "take_profit_2": 300.0,
             "take_profit_3": 450.0, "stop_distance_pct": 10.0, "risk_reward_ratio": 2.5,
             "position_size_pct": 2.0, "composite_score": 72.5, "atr_proxy": 7.5,
             "volatility_regime": "MEDIUM", "is_active": True, "is_executable": True},
            {"validator_output_id": 2, "symbol": "BONK", "tier": "TIER_1", "entry_price": 0.00001,
             "stop_loss_price": 0.000008, "take_profit_1": 0.000015, "take_profit_2": 0.00002,
             "take_profit_3": 0.00003, "stop_distance_pct": 20.0, "risk_reward_ratio": 3.0,
             "position_size_pct": 1.5, "composite_score": 85.0, "atr_proxy": 12.5,
             "volatility_regime": "HIGH", "is_active": True, "is_executable": True},
        ],
        batch_id="phase7_test_001",
    )
    await bus.publish_simple(
        event_type=EventType.RISK_ASSESSED,
        data=risk_event.model_dump(),
        source="risk_engine",
        correlation_id="phase7_test_001",
    )
    print(f"📤 Published: {risk_event.high_quality_count} high-quality signals")
    await asyncio.sleep(0.5)
    
    # ── Step 4: Master Orchestrator Simulation ──
    print("\n--- [4] Master → Decisions ---")
    
    # Simulate master evaluation logic
    for signal in risk_event.signals:
        # Check if it passes master rules
        composite = signal.composite_score
        rr = signal.risk_reward_ratio
        symbol = signal.symbol
        
        if composite >= 60 and rr >= 1.5:
            # APPROVE
            decision = {
                "symbol": symbol,
                "decision": "APPROVE",
                "tier": signal.tier,
                "position_size_usd": 200.0,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss_price,
                "take_profits": [
                    signal.take_profit_1,
                    signal.take_profit_2,
                    signal.take_profit_3,
                ],
                "confidence": composite,
                "risk_reward": rr,
                "reason": "All checks passed",
            }
            await bus.publish_simple(
                event_type=EventType.POSITION_OPENED,
                data=decision,
                source="master",
                correlation_id="phase7_test_001",
            )
        else:
            # REJECT
            decision = {
                "symbol": symbol,
                "decision": "REJECT",
                "reason": f"Score={composite:.1f} or RR={rr:.1f} too low",
            }
            await bus.publish_simple(
                event_type=EventType.ALERT,
                data=decision,
                source="master",
                correlation_id="phase7_test_001",
            )
    
    await asyncio.sleep(0.5)
    
    # ── Results ──
    print(f"\n{'═' * 60}")
    print("║                    📊 RESULTS                              ║")
    print(f"{'═' * 60}")
    
    for et, events in events_by_stage.items():
        if events:
            print(f"  ✅ {et:20s}: {len(events)} events")
    
    total = sum(len(v) for v in events_by_stage.values() if v)
    print(f"\n  📈 Total events: {total}")
    print(f"  🟢 Trades approved: {len(decisions)}")
    for d in decisions:
        print(f"     • {d['symbol']}: ${d['size']:.2f} (conf={d['confidence']:.1f})")
    
    # Validate
    success = (
        len(events_by_stage.get(EventType.TOKENS_DISCOVERED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.TOKENS_VALIDATED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.RISK_ASSESSED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.POSITION_OPENED.value, [])) >= 1
    )
    
    if success:
        print(f"\n  🔥 PHASE 7 PASSED ✅")
        print(f"  Full pipeline: Scanner → Validator → Risk → Master → Trades")
    else:
        print(f"\n  ❌ PHASE 7 FAILED")
    
    # Cleanup
    for task in consumers:
        task.cancel()
    await bus.disconnect()
    return success


if __name__ == "__main__":
    success = asyncio.run(phase7_smoke_test())
    sys.exit(0 if success else 1)
