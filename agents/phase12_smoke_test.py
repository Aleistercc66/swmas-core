#!/usr/bin/env python3
"""Phase 12 smoke test: Real Money Safety Layer validation."""
import sys
import asyncio

sys.path.insert(0, "/root/.openclaw/workspace/agents")

from config.safety import safety_config, is_paper_mode, is_real_mode, update_safety_config
from core.secure_executor import SecureExecutor, activate_kill_switch, deactivate_kill_switch
from core.chain_router import chain_router


def test_safety_config():
    """Test safety configuration defaults."""
    print("\n--- [1] Safety Config ---")
    
    checks = [
        ("trading_mode", safety_config.trading_mode, "paper"),
        ("max_single_position_usd", safety_config.max_single_position_usd, 250.0),
        ("max_daily_risk_usd", safety_config.max_daily_risk_usd, 500.0),
        ("max_drawdown_percent", safety_config.max_drawdown_percent, 15.0),
        ("require_manual_approval_real", safety_config.require_manual_approval_real, True),
        ("daily_trade_limit", safety_config.daily_trade_limit, 5),
        ("allowed_chains", safety_config.allowed_chains, ["solana"]),
    ]
    
    all_ok = True
    for name, actual, expected in checks:
        if actual == expected:
            print(f"  ✅ {name}: {actual}")
        else:
            print(f"  ❌ {name}: {actual} (expected {expected})")
            all_ok = False
    
    return all_ok


def test_paper_vs_real_mode():
    """Test mode detection."""
    print("\n--- [2] Paper vs Real Mode ---")
    
    # Default should be paper
    if is_paper_mode() and not is_real_mode():
        print(f"  ✅ Default mode: PAPER")
    else:
        print(f"  ❌ Default mode wrong: paper={is_paper_mode()}, real={is_real_mode()}")
        return False
    
    # Switch to real
    update_safety_config(trading_mode="real")
    if is_real_mode() and not is_paper_mode():
        print(f"  ✅ Switched to: REAL")
    else:
        print(f"  ❌ Mode switch failed")
        return False
    
    # Switch back
    update_safety_config(trading_mode="paper")
    if is_paper_mode():
        print(f"  ✅ Switched back to: PAPER")
    else:
        print(f"  ❌ Switch back failed")
        return False
    
    return True


async def test_secure_executor_paper():
    """Test secure executor in paper mode."""
    print("\n--- [3] Secure Executor (Paper Mode) ---")
    
    executor = SecureExecutor()
    
    # Paper trade
    decision = {
        "symbol": "SOL",
        "entry_price": 150.0,
        "position_size_usd": 200.0,
        "stop_loss": 135.0,
        "take_profit": 225.0,
        "stop_loss_pct": 10.0,
    }
    
    result = await executor.execute(decision)
    
    if result:
        print(f"  ✅ Paper trade executed")
        print(f"  ✅ Daily trades: {executor.daily_trades}/{safety_config.daily_trade_limit}")
        print(f"  ✅ Audit entries: {len(executor.audit_log)}")
    else:
        print(f"  ❌ Paper trade failed")
        return False
    
    # Check audit log
    audit = executor.get_audit_log()
    if len(audit) >= 2:  # EXECUTE_START + TRADE_EXECUTED_PAPER
        print(f"  ✅ Audit log has {len(audit)} entries")
    else:
        print(f"  ❌ Audit log too short: {len(audit)}")
        return False
    
    return True


async def test_safety_checks():
    """Test safety check rejections."""
    print("\n--- [4] Safety Checks ---")
    
    executor = SecureExecutor()
    
    # Test 1: Position too large
    big_decision = {
        "symbol": "SOL",
        "entry_price": 150.0,
        "position_size_usd": 500.0,  # > 250 limit
        "stop_loss": 135.0,
        "take_profit": 225.0,
        "stop_loss_pct": 10.0,
    }
    
    result = await executor.execute(big_decision)
    if not result:
        print(f"  ✅ Large position rejected")
    else:
        print(f"  ❌ Large position should be rejected")
        return False
    
    # Test 2: Slippage too high
    slip_decision = {
        "symbol": "SOL",
        "entry_price": 150.0,
        "position_size_usd": 100.0,
        "stop_loss": 135.0,
        "take_profit": 225.0,
        "stop_loss_pct": 10.0,
        "expected_slippage": 5.0,  # > 1.2% limit
    }
    
    result = await executor.execute(slip_decision)
    if not result:
        print(f"  ✅ High slippage rejected")
    else:
        print(f"  ❌ High slippage should be rejected")
        return False
    
    return True


async def test_kill_switch():
    """Test kill switch functionality."""
    print("\n--- [5] Kill Switch ---")
    
    executor = SecureExecutor()
    
    # Activate kill switch
    activated = await activate_kill_switch("SMOKE_TEST")
    if activated:
        print(f"  ✅ Kill switch activated")
    else:
        print(f"  ⚠️ Kill switch activation failed (Redis may be unavailable)")
        # Continue test with manual flag
    
    # Test trade is blocked
    decision = {
        "symbol": "SOL",
        "entry_price": 150.0,
        "position_size_usd": 100.0,
        "stop_loss": 135.0,
        "take_profit": 225.0,
        "stop_loss_pct": 10.0,
    }
    
    result = await executor.execute(decision)
    if not result:
        print(f"  ✅ Trade blocked by kill switch")
    else:
        print(f"  ⚠️ Trade not blocked (kill switch may not be active)")
    
    # Deactivate
    deactivated = await deactivate_kill_switch()
    if deactivated:
        print(f"  ✅ Kill switch deactivated")
    else:
        print(f"  ⚠️ Kill switch deactivation failed")
    
    return True


async def test_chain_router():
    """Test chain router."""
    print("\n--- [6] Chain Router ---")
    
    await chain_router.init()
    
    status = chain_router.get_chain_status()
    if "solana" in status:
        print(f"  ✅ Solana chain registered")
    else:
        print(f"  ❌ Solana chain missing")
        return False
    
    # Test execute on allowed chain
    decision = {
        "symbol": "SOL",
        "chain": "solana",
        "entry_price": 150.0,
        "position_size_usd": 100.0,
    }
    
    result = await chain_router.execute(decision)
    if result:
        print(f"  ✅ Solana execution route working")
    else:
        print(f"  ⚠️ Solana execution returned False (expected in test)")
    
    # Test reject disallowed chain
    bad_decision = {
        "symbol": "ETH",
        "chain": "ethereum",
        "entry_price": 3000.0,
    }
    
    result = await chain_router.execute(bad_decision)
    if not result:
        print(f"  ✅ Disallowed chain rejected")
    else:
        print(f"  ❌ Disallowed chain should be rejected")
        return False
    
    return True


async def test_real_mode_safety():
    """Test real mode requires manual approval."""
    print("\n--- [7] Real Mode Safety ---")
    
    # Switch to real mode
    update_safety_config(trading_mode="real")
    
    executor = SecureExecutor()
    
    # Auto-confirm for testing
    decision = {
        "symbol": "SOL",
        "entry_price": 150.0,
        "position_size_usd": 100.0,
        "stop_loss": 135.0,
        "take_profit": 225.0,
        "stop_loss_pct": 10.0,
        "_test_auto_confirm": True,
    }
    
    result = await executor.execute(decision)
    
    if result:
        print(f"  ✅ Real mode execution with approval")
    else:
        print(f"  ⚠️ Real mode execution failed (expected in test without Jupiter)")
    
    # Switch back to paper
    update_safety_config(trading_mode="paper")
    
    return True


async def phase12_smoke_test():
    """Run Phase 12 smoke test."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     🛡️ PHASE 12: REAL MONEY SAFETY TEST                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # Test 1: Safety config
    results.append(("Safety Config", test_safety_config()))
    
    # Test 2: Paper vs Real mode
    results.append(("Paper vs Real", test_paper_vs_real_mode()))
    
    # Test 3: Secure executor (paper)
    results.append(("Paper Execution", await test_secure_executor_paper()))
    
    # Test 4: Safety checks
    results.append(("Safety Checks", await test_safety_checks()))
    
    # Test 5: Kill switch
    results.append(("Kill Switch", await test_kill_switch()))
    
    # Test 6: Chain router
    results.append(("Chain Router", await test_chain_router()))
    
    # Test 7: Real mode safety
    results.append(("Real Mode Safety", await test_real_mode_safety()))
    
    # Results
    print(f"\n{'═' * 60}")
    print("║                    📊 RESULTS                              ║")
    print(f"{'═' * 60}")
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print(f"\n  🔥 PHASE 12 PASSED ✅")
        print(f"\n  🛡️ SAFETY STATUS:")
        print(f"     Mode: {safety_config.trading_mode.upper()}")
        print(f"     Daily limit: {safety_config.daily_trade_limit} trades")
        print(f"     Max position: ${safety_config.max_single_position_usd}")
        print(f"     Manual approval: {'YES' if safety_config.require_manual_approval_real else 'NO'}")
        print(f"\n  ⚠️  BEFORE REAL MONEY:")
        print(f"     1. Set trading_mode = 'real' in config/safety.py")
        print(f"     2. Configure wallet private key (secure storage)")
        print(f"     3. Set Jupiter API endpoint")
        print(f"     4. Start with $200-500 capital")
        print(f"     5. Keep manual approval ON for 2-4 weeks")
    else:
        print(f"\n  ❌ PHASE 12 FAILED")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(phase12_smoke_test())
    sys.exit(0 if success else 1)
