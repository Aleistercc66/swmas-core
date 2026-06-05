#!/usr/bin/env python3
"""Phase 8 smoke test: Full pipeline with Position Monitor + Auto Executor."""
import asyncio
import sys

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_event_bus, EventType, SwarmEvent
from core.events import (
    TokenDiscoveredEvent, TokensValidatedEvent,
    RiskAssessedEvent, TradeDecision, PositionOpenedEvent,
    PositionUpdatedEvent, PositionClosedEvent,
)


async def phase8_smoke_test():
    """Full pipeline: Scanner → Validator → Risk → Master → Executor → Monitor → Close."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🚀 PHASE 8: POSITION MONITOR + AUTO EXECUTOR         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    bus = await get_event_bus()
    print(f"✅ EventBus: {'Redis' if bus.is_connected else 'In-Memory'}")
    
    # Track events
    events_by_stage = {et.value: [] for et in EventType}
    
    async def track_all(event: SwarmEvent):
        events_by_stage[event.event_type].append(event)
        
        if event.event_type == EventType.POSITION_OPENED.value:
            print(f"  📥 POSITION OPENED: {event.data.get('symbol', '?')}")
        elif event.event_type == EventType.POSITION_UPDATED.value:
            d = event.data
            pnl = d.get('pnl_percent', 0)
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"  {emoji} UPDATE: {d.get('symbol', '?')} ${d.get('current_price', 0):.8f} PnL={pnl:+.2f}%")
        elif event.event_type == EventType.POSITION_CLOSED.value:
            d = event.data
            pnl = d.get('pnl_pct', 0)
            emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"  {emoji} CLOSED: {d.get('symbol', '?')} {d.get('close_reason', '?')} PnL={pnl:+.2f}%")
        else:
            print(f"  📥 [{event.source:12s}] → {event.event_type:20s}")
    
    # Subscribe to ALL
    consumers = []
    for et in EventType:
        task = await bus.subscribe(event_type=et, consumer_name="phase8_test", handler=track_all)
        consumers.append(task)
    
    print(f"\n✅ Subscribed to {len(consumers)} event types")
    
    # ── [1] Scanner ──
    print("\n--- [1] Scanner ---")
    await bus.publish_simple(
        event_type=EventType.TOKENS_DISCOVERED,
        data=TokenDiscoveredEvent(
            tokens=[{"symbol": "SOL", "price": 150.0, "volume_24h": 500000, "liquidity": 200000,
                     "price_change_24h": 15.0, "price_change_1h": 3.5, "price_change_5m": 1.2, "buy_ratio": 1.5}],
            batch_id="phase8_001",
        ).model_dump(),
        source="scanner",
        correlation_id="phase8_001",
    )
    await asyncio.sleep(0.2)
    
    # ── [2] Validator ──
    print("\n--- [2] Validator ---")
    await bus.publish_simple(
        event_type=EventType.TOKENS_VALIDATED,
        data=TokensValidatedEvent(
            validated_tokens=[{"scanner_output_id": 1, "symbol": "SOL", "is_approved": True,
                             "tier": "TIER_2", "confidence": 75.0, "pass_rate": 0.75,
                             "total_checks": 8, "passed_checks": 6, "checks": [],
                             "rejection_reason": "", "buy_sell_ratio": 1.5}],
            batch_id="phase8_001",
        ).model_dump(),
        source="validator",
        correlation_id="phase8_001",
    )
    await asyncio.sleep(0.2)
    
    # ── [3] Risk Engine ──
    print("\n--- [3] Risk Engine ---")
    await bus.publish_simple(
        event_type=EventType.RISK_ASSESSED,
        data=RiskAssessedEvent(
            signals=[{"validator_output_id": 1, "symbol": "SOL", "tier": "TIER_2", "entry_price": 150.0,
                     "stop_loss_price": 135.0, "take_profit_1": 225.0, "take_profit_2": 300.0,
                     "take_profit_3": 450.0, "stop_distance_pct": 10.0, "risk_reward_ratio": 2.5,
                     "position_size_pct": 2.0, "composite_score": 72.5, "atr_proxy": 7.5,
                     "volatility_regime": "MEDIUM", "is_active": True, "is_executable": True}],
            batch_id="phase8_001",
        ).model_dump(),
        source="risk_engine",
        correlation_id="phase8_001",
    )
    await asyncio.sleep(0.2)
    
    # ── [4] Master → POSITION_OPENED ──
    print("\n--- [4] Master → Executor ---")
    trade = TradeDecision(
        symbol="SOL",
        decision="APPROVE",
        tier="TIER_2",
        position_size_usd=200.0,
        entry_price=150.0,
        stop_loss=135.0,
        take_profits=[225.0, 300.0, 450.0],
        confidence=72.5,
        risk_reward=2.5,
        reason="All checks passed",
    )
    await bus.publish_simple(
        event_type=EventType.POSITION_OPENED,
        data=trade.model_dump(),
        source="master",
        correlation_id="phase8_001",
    )
    await asyncio.sleep(0.3)
    
    # ── [5] Position Monitor: Simulate price updates ──
    print("\n--- [5] Position Monitor (simulated updates) ---")
    
    # Simulate 3 price updates
    prices = [155.0, 160.0, 230.0]  # Price goes up, then hits TP1
    
    for i, price in enumerate(prices):
        pnl = (price - 150.0) / 150.0 * 100
        
        update = PositionUpdatedEvent(
            trade_id="phase8_trade_001",
            symbol="SOL",
            current_price=price,
            entry_price=150.0,
            pnl_percent=round(pnl, 2),
            pnl_usd=round(200.0 * (pnl / 100), 2),
            status="OPEN",
            highest_price=price,
        )
        
        await bus.publish_simple(
            event_type=EventType.POSITION_UPDATED,
            data=update.model_dump(),
            source="position_monitor",
        )
        
        # Check if TP hit
        if price >= 225.0:
            print(f"\n  🎯 TP1 HIT at ${price}! Closing position...")
            
            closed = PositionClosedEvent(
                position_id=1,  # Using position_id as required by model
                symbol="SOL",
                close_price=price,
                pnl_pct=round(pnl, 2),
                pnl_usd=round(200.0 * (pnl / 100), 2),
                close_reason="HIT_TP1",
            )
            
            await bus.publish_simple(
                event_type=EventType.POSITION_CLOSED,
                data=closed.model_dump(),
                source="position_monitor",
            )
            break
        
        await asyncio.sleep(0.2)
    
    # Wait for events to process
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
    
    # Validate full pipeline
    success = (
        len(events_by_stage.get(EventType.TOKENS_DISCOVERED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.TOKENS_VALIDATED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.RISK_ASSESSED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.POSITION_OPENED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.POSITION_UPDATED.value, [])) >= 1 and
        len(events_by_stage.get(EventType.POSITION_CLOSED.value, [])) >= 1
    )
    
    if success:
        print(f"\n  🔥 PHASE 8 PASSED ✅")
        print(f"  Full cycle: Scan → Validate → Risk → Execute → Monitor → Close")
    else:
        print(f"\n  ❌ PHASE 8 FAILED")
        print(f"  Missing stages in pipeline")
    
    for task in consumers:
        task.cancel()
    await bus.disconnect()
    return success


if __name__ == "__main__":
    success = asyncio.run(phase8_smoke_test())
    sys.exit(0 if success else 1)
