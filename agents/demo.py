"""
Quick test/demo script for Master Blockchain Trading Agent
Shows all components in action without real trades
"""

import asyncio
import json
from datetime import datetime
from blockchain_analyzer import BlockchainAnalyzer, TokenMetrics
from exchange_manager import StrategyLearner, MarketData
from risk_portfolio import RiskManager, RiskLevel

async def demo_blockchain_analysis():
    """Demo on-chain analysis"""
    print("\n" + "="*60)
    print("🔍 BLOCKCHAIN ANALYZER DEMO")
    print("="*60)
    
    async with BlockchainAnalyzer() as analyzer:
        # Analyze SOL
        print("\n📊 Analyzing SOL...")
        metrics = await analyzer.analyze_token("So11111111111111111111111111111111111111112")
        
        print(f"""
Symbol: {metrics.symbol}
Price: ${metrics.price:.4f}
Market Cap: ${metrics.market_cap:,.0f}
Liquidity: ${metrics.liquidity:,.0f}
Volume 24h: ${metrics.volume_24h:,.0f}
Holders: {metrics.holders:,}
Whale Txns 24h: {metrics.whale_transactions_24h}
Contract Risk: {metrics.contract_risk_score}/100
        """)
        
        # Scan opportunities
        print("🔍 Scanning for opportunities...")
        opportunities = await analyzer.scan_opportunities()
        
        if opportunities:
            print(f"\n✅ Found {len(opportunities)} opportunities:")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"""
{i}. {opp['token'].symbol}
   Score: {opp['score']:.0f}/100
   Risk: {opp['risk_level']}
   Signals:
""")
                for signal in opp['signals'][:3]:
                    print(f"      • {signal}")
        else:
            print("⚠️  No high-confidence opportunities found (expected without real API keys)")

async def demo_strategy_learning():
    """Demo strategy learning"""
    print("\n" + "="*60)
    print("🧠 STRATEGY LEARNER DEMO")
    print("="*60)
    
    learner = StrategyLearner()
    
    # Create dummy market data for different regimes
    print("\n📈 Testing different market regimes...")
    
    # Uptrend data
    uptrend_data = []
    price = 100
    for i in range(50):
        price *= 1.002  # Small consistent gains
        uptrend_data.append(MarketData(
            symbol="SOL",
            price=price,
            volume_24h=1000000 + i * 1000,
            high_24h=price * 1.05,
            low_24h=price * 0.95,
            change_24h=price * 0.02,
            change_24h_pct=2.0
        ))
    
    signal = learner.generate_signal(uptrend_data)
    print(f"""
Uptrend Market:
  Signal: {signal['signal'].upper()}
  Strategy: {signal['strategy']}
  Regime: {signal['regime']}
  Confidence: {signal['confidence']:.0f}%
  Reason: {signal['reason']}
""")
    
    # Volatile data
    volatile_data = []
    price = 100
    for i in range(20):
        price *= (1 + (0.05 if i % 2 == 0 else -0.03))  # Up/down swings
        volatile_data.append(MarketData(
            symbol="SOL",
            price=price,
            volume_24h=5000000,
            high_24h=price * 1.1,
            low_24h=price * 0.9,
            change_24h=price * (0.05 if i % 2 == 0 else -0.03),
            change_24h_pct=(5.0 if i % 2 == 0 else -3.0)
        ))
    
    signal = learner.generate_signal(volatile_data)
    print(f"""
Volatile Market:
  Signal: {signal['signal'].upper()}
  Strategy: {signal['strategy']}
  Regime: {signal['regime']}
  Confidence: {signal['confidence']:.0f}%
  Reason: {signal['reason']}
""")

async def demo_risk_management():
    """Demo risk management"""
    print("\n" + "="*60)
    print("💰 RISK & PORTFOLIO MANAGEMENT DEMO")
    print("="*60)
    
    # Test different risk levels
    for level in [RiskLevel.MODERATE, RiskLevel.AGGRESSIVE, RiskLevel.DEGEN]:
        risk = RiskManager(level)
        risk.portfolio.total_equity = 100000
        risk.portfolio.available_cash = 100000
        
        print(f"\n🎯 Risk Level: {level.value.upper()}")
        print(f"   Max position size: {risk.risk_params['max_position_size_pct']}%")
        print(f"   Stop loss: {risk.risk_params['stop_loss_pct']}%")
        print(f"   Max leverage: {risk.risk_params['leverage_max']}x")
        
        # Calculate position
        sizing = risk.calculate_position_size(
            symbol="SOL",
            entry_price=150.0,
            stop_loss=142.5,
            portfolio_value=100000,
            confidence=75
        )
        
        print(f"""
   Position sizing:
     Quantity: {sizing['quantity']:.4f} SOL
     Value: ${sizing['position_value']:,.2f}
     Risk: ${sizing['risk_amount']:,.2f} ({sizing['risk_pct']:.2f}%)
     Kelly: {sizing['kelly_fraction']:.2%}
""")
        
        # Show stop levels
        stops = risk.set_stop_levels(150.0, 'long')
        print(f"""
   Stop levels:
     Stop Loss: ${stops['stop_loss']:.2f}
     TP1: ${stops['take_profit_1']:.2f} (+{risk.risk_params['take_profit_1_pct']}%)
     TP2: ${stops['take_profit_2']:.2f} (+{risk.risk_params['take_profit_2_pct']}%)
     TP3: ${stops['take_profit_3']:.2f} (+{risk.risk_params['take_profit_3_pct']}%)
""")

async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("🔥 MASTER BLOCKCHAIN TRADING AGENT - DEMO")
    print("="*60)
    print("\nThis demo shows all components working together.")
    print("(Note: Some features need API keys to show full data)")
    
    try:
        await demo_blockchain_analysis()
    except Exception as e:
        print(f"⚠️  Blockchain demo skipped: {e}")
    
    await demo_strategy_learning()
    await demo_risk_management()
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETE!")
    print("="*60)
    print("""
Next steps:
1. Add API keys to .env file
2. Run: pip install -r requirements.txt
3. Run: python master_agent.py

The agent will:
  • Learn market patterns every hour
  • Scan for opportunities every 5 minutes
  • Execute trades with risk management
  • Send Telegram alerts
""")

if __name__ == "__main__":
    asyncio.run(main())
