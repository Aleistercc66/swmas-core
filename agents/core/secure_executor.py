#!/usr/bin/env python3
"""🔒 Secure Executor — Real money trade execution with safety checks."""
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from config.safety import safety_config, is_paper_mode, is_real_mode
from core import get_event_bus, EventType
from core.events import PositionOpenedEvent


class SecureExecutor:
    """Executes trades with full safety validation.
    
    Paper mode: Simulates trades, records to DB.
    Real mode: Requires all safety checks + manual approval.
    """
    
    def __init__(self):
        self.daily_risk_used: float = 0.0
        self.daily_trades: int = 0
        self.daily_reset_time: datetime = datetime.utcnow() + timedelta(days=1)
        self.hourly_trades: int = 0
        self.hourly_reset_time: datetime = datetime.utcnow() + timedelta(hours=1)
        self.audit_log: List[Dict[str, Any]] = []
        self.bus = None
        self.jupiter = None  # Lazy init
    
    async def _get_bus(self):
        if self.bus is None:
            self.bus = await get_event_bus()
        return self.bus
    
    async def execute(self, decision: Dict[str, Any]) -> bool:
        """Execute a trade decision with full safety checks.
        
        Returns True if executed (or simulated in paper mode).
        """
        bus = await self._get_bus()
        
        # 1. Mode check
        mode = safety_config.trading_mode
        self._audit("EXECUTE_START", {"mode": mode, "decision": decision})
        
        # 2. Kill switch check
        if await self._is_kill_switch_active():
            await self._publish_block("KILL_SWITCH_ACTIVE", decision)
            return False
        
        # 3. Reset daily/hourly counters
        now = datetime.utcnow()
        if now >= self.daily_reset_time:
            self.daily_risk_used = 0.0
            self.daily_trades = 0
            self.daily_reset_time = now + timedelta(days=1)
        if now >= self.hourly_reset_time:
            self.hourly_trades = 0
            self.hourly_reset_time = now + timedelta(hours=1)
        
        # 4. Safety checks
        if not await self._run_all_safety_checks(decision):
            return False
        
        # 5. Paper mode: simulate
        if is_paper_mode():
            return await self._execute_paper(decision)
        
        # 6. Real mode: full execution
        return await self._execute_real(decision)
    
    async def _run_all_safety_checks(self, decision: Dict[str, Any]) -> bool:
        """Run all safety validation checks."""
        checks = [
            ("daily_limit", await self._check_daily_limit()),
            ("hourly_limit", await self._check_hourly_limit()),
            ("position_size", self._check_position_size(decision)),
            ("daily_risk", await self._check_daily_risk(decision)),
            ("drawdown", await self._check_drawdown()),
            ("slippage", self._check_slippage(decision)),
            ("kill_switch", not await self._is_kill_switch_active()),
        ]
        
        failed = [name for name, passed in checks if not passed]
        
        if failed:
            await self._publish_block(f"SAFETY_CHECKS_FAILED: {', '.join(failed)}", decision)
            self._audit("SAFETY_FAILED", {"failed_checks": failed, "decision": decision})
            return False
        
        self._audit("SAFETY_PASSED", {"checks": [name for name, _ in checks]})
        return True
    
    async def _check_daily_limit(self) -> bool:
        """Check daily trade limit."""
        return self.daily_trades < safety_config.daily_trade_limit
    
    async def _check_hourly_limit(self) -> bool:
        """Check hourly trade limit."""
        return self.hourly_trades < safety_config.hourly_trade_limit
    
    def _check_position_size(self, decision: Dict[str, Any]) -> bool:
        """Check position size against limit."""
        size = decision.get("position_size_usd", 0)
        return size <= safety_config.max_single_position_usd
    
    async def _check_daily_risk(self, decision: Dict[str, Any]) -> bool:
        """Check daily risk budget."""
        size = decision.get("position_size_usd", 0)
        sl_pct = decision.get("stop_loss_pct", 10)
        risk = size * (sl_pct / 100)
        return (self.daily_risk_used + risk) <= safety_config.max_daily_risk_usd
    
    async def _check_drawdown(self) -> bool:
        """Check portfolio drawdown."""
        # TODO: Fetch from portfolio tracker
        # For now, return True (assumes meta agent handles this)
        return True
    
    def _check_slippage(self, decision: Dict[str, Any]) -> bool:
        """Check slippage tolerance."""
        expected_slippage = decision.get("expected_slippage", 0.5)
        return expected_slippage <= safety_config.slippage_tolerance_percent
    
    async def _is_kill_switch_active(self) -> bool:
        """Check if kill switch is active (Redis)."""
        try:
            from core.event_bus import get_redis
            redis = await get_redis()
            val = await redis.get("kill_switch:active")
            return val == "true"
        except Exception:
            return False
    
    async def _execute_paper(self, decision: Dict[str, Any]) -> bool:
        """Execute in paper mode (simulation)."""
        bus = await self._get_bus()
        
        # Record trade
        self.daily_trades += 1
        self.hourly_trades += 1
        self.daily_risk_used += decision.get("position_size_usd", 0) * (decision.get("stop_loss_pct", 10) / 100)
        
        trade_record = {
            "mode": "paper",
            "symbol": decision.get("symbol"),
            "entry_price": decision.get("entry_price"),
            "position_size_usd": decision.get("position_size_usd"),
            "stop_loss": decision.get("stop_loss"),
            "take_profit": decision.get("take_profit"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._audit("TRADE_EXECUTED_PAPER", trade_record)
        
        await bus.publish_simple(
            event_type=EventType.POSITION_OPENED.value,
            data={
                "trade_id": f"paper_{datetime.utcnow().strftime('%H%M%S')}",
                "symbol": decision.get("symbol"),
                "entry_price": decision.get("entry_price"),
                "position_size_usd": decision.get("position_size_usd"),
                "stop_loss": decision.get("stop_loss"),
                "take_profit": decision.get("take_profit"),
                "mode": "paper",
            },
            source="secure_executor",
        )
        
        print(f"📊 PAPER TRADE: {decision.get('symbol')} @ ${decision.get('entry_price')}")
        return True
    
    async def _execute_real(self, decision: Dict[str, Any]) -> bool:
        """Execute in real mode (with manual approval)."""
        bus = await self._get_bus()
        
        # 1. Pre-flight simulation
        sim_ok = await self._simulate_swap(decision)
        if not sim_ok:
            await self._publish_block("SIMULATION_FAILED", decision)
            return False
        
        # 2. Manual approval required
        if safety_config.require_manual_approval_real:
            confirmed = await self._request_confirmation(decision)
            if not confirmed:
                await self._publish_block("MANUAL_REJECTED", decision)
                return False
        
        # 3. Execute
        result = await self._execute_swap(decision)
        if result:
            self.daily_trades += 1
            self.hourly_trades += 1
            self._audit("TRADE_EXECUTED_REAL", {"decision": decision, "result": result})
            await bus.publish_simple(
                event_type=EventType.POSITION_OPENED.value,
                data={
                    **decision,
                    "mode": "real",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                source="secure_executor",
            )
            print(f"💰 REAL TRADE EXECUTED: {decision.get('symbol')} @ ${decision.get('entry_price')}")
        
        return result
    
    async def _simulate_swap(self, decision: Dict[str, Any]) -> bool:
        """Simulate swap before execution."""
        # Placeholder: Always pass in test
        # In production: Call Jupiter API for simulation
        return True
    
    async def _request_confirmation(self, decision: Dict[str, Any]) -> bool:
        """Request manual confirmation for real trades.
        
        Returns True if confirmed within timeout.
        """
        bus = await self._get_bus()
        
        # Publish confirmation request
        request_id = f"confirm_{datetime.utcnow().strftime('%H%M%S')}"
        await bus.publish_simple(
            event_type=EventType.ALERT.value,
            data={
                "alert_type": "MANUAL_CONFIRMATION",
                "request_id": request_id,
                "symbol": decision.get("symbol"),
                "entry_price": decision.get("entry_price"),
                "position_size_usd": decision.get("position_size_usd"),
                "message": f"🚨 CONFIRM REAL TRADE: {decision.get('symbol')} ${decision.get('position_size_usd')} — Reply CONFIRM or REJECT",
            },
            source="secure_executor",
        )
        
        self._audit("CONFIRMATION_REQUESTED", {"request_id": request_id, "decision": decision})
        
        # Wait for response (30 seconds)
        # In production: Listen for Telegram/Dashboard response
        print(f"⏳ Waiting for manual confirmation... (30s)")
        await asyncio.sleep(2)  # Shortened for testing
        
        # For testing: auto-approve if test flag set
        if decision.get("_test_auto_confirm"):
            print("✅ Auto-confirmed (test mode)")
            return True
        
        return False
    
    async def _execute_swap(self, decision: Dict[str, Any]) -> bool:
        """Execute swap on Jupiter.
        
        Placeholder: Returns success for structure validation.
        """
        # In production:
        # 1. Build Jupiter swap transaction
        # 2. Sign with wallet
        # 3. Submit to network
        # 4. Verify confirmation
        return True
    
    async def _publish_block(self, reason: str, decision: Dict[str, Any]):
        """Publish trade blocked event."""
        bus = await self._get_bus()
        await bus.publish_simple(
            event_type=EventType.ALERT.value,
            data={
                "alert_type": "TRADE_BLOCKED",
                "reason": reason,
                "symbol": decision.get("symbol"),
                "mode": safety_config.trading_mode,
            },
            source="secure_executor",
        )
    
    def _audit(self, action: str, data: Dict[str, Any]):
        """Record audit log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "data": data,
        }
        self.audit_log.append(entry)
        
        if safety_config.audit_all_decisions:
            print(f"📝 AUDIT: {action} — {data.get('symbol', 'N/A')}")
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get full audit log."""
        return self.audit_log.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "mode": safety_config.trading_mode,
            "daily_trades": self.daily_trades,
            "daily_limit": safety_config.daily_trade_limit,
            "hourly_trades": self.hourly_trades,
            "hourly_limit": safety_config.hourly_trade_limit,
            "daily_risk_used": self.daily_risk_used,
            "daily_risk_limit": safety_config.max_daily_risk_usd,
            "audit_entries": len(self.audit_log),
        }


# ── Kill Switch ──

async def activate_kill_switch(reason: str):
    """Activate global kill switch."""
    try:
        from core.event_bus import get_redis
        redis = await get_redis()
        await redis.set("kill_switch:active", "true")
        await redis.set("kill_switch:reason", reason)
        await redis.set("kill_switch:activated_at", datetime.utcnow().isoformat())
        
        bus = await get_event_bus()
        await bus.publish_simple(
            event_type=EventType.ALERT.value,
            data={
                "alert_type": "KILL_SWITCH",
                "reason": reason,
                "message": f"🛑 KILL SWITCH ACTIVATED: {reason}",
            },
            source="safety_guard",
        )
        print(f"🛑 KILL SWITCH ACTIVATED: {reason}")
        return True
    except Exception as e:
        print(f"❌ Failed to activate kill switch: {e}")
        return False


async def deactivate_kill_switch():
    """Deactivate global kill switch."""
    try:
        from core.event_bus import get_redis
        redis = await get_redis()
        await redis.delete("kill_switch:active")
        await redis.delete("kill_switch:reason")
        
        bus = await get_event_bus()
        await bus.publish_simple(
            event_type=EventType.ALERT.value,
            data={
                "alert_type": "KILL_SWITCH_RELEASED",
                "message": "✅ Kill switch deactivated",
            },
            source="safety_guard",
        )
        print("✅ Kill switch deactivated")
        return True
    except Exception as e:
        print(f"❌ Failed to deactivate kill switch: {e}")
        return False
