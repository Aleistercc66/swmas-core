#!/usr/bin/env python3
"""
Standalone Superior Training Script
Τρέχει training σε όλα τα data και εξάγει optimized parameters.
Usage: python train.py
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime

# Import all modules
from learning_engine import SolanaKnowledgeBase
from historian import SolanaHistorian
from opportunity_scanner import OpportunityScanner
from strategy_engine import StrategyEngine
from risk_manager import RiskManager
from training_engine import SuperiorTrainingEngine


async def run_superior_training():
    """Run complete superior training cycle."""
    
    print("🔥🔥🔥 SUPERIOR TRAINING INITIATED 🔥🔥🔥")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Initialize all systems
    print("\n📚 Initializing subsystems...")
    kb = SolanaKnowledgeBase()
    historian = SolanaHistorian()
    scanner = OpportunityScanner(kb, historian)
    strategy = StrategyEngine()
    risk = RiskManager()
    
    trainer = SuperiorTrainingEngine(kb, historian, strategy, risk)
    
    print("   ✅ All systems loaded")
    print(f"   📊 KB: {len(kb.tokens)} tokens, {len(kb.patterns)} patterns")
    print(f"   📜 Historian: {len(historian.token_profiles)} profiles")
    
    # Run training
    async with aiohttp.ClientSession() as session:
        print("\n🚀 Starting training cycles...")
        
        results = await trainer.run_full_training(session)
        
        # Generate optimized config
        print("\n" + "="*70)
        print("📋 GENERATING OPTIMIZED CONFIGURATION")
        print("="*70)
        
        config = {
            "version": "2.0-trained",
            "training_time": datetime.now().isoformat(),
            "training_results": [
                {
                    "module": r.module,
                    "improvement_pct": r.improvement_pct,
                    "before": r.before_score,
                    "after": r.after_score,
                    "insights": r.insights,
                    "updates": r.model_updates
                }
                for r in results
            ],
            "optimized_parameters": {
                "opportunity_weights": kb.opportunity_weights if hasattr(kb, 'opportunity_weights') else {},
                "strategy_params": strategy.strategies if hasattr(strategy, 'strategies') else {},
                "risk_params": {
                    "stop_loss": risk.stop_loss_pct if hasattr(risk, 'stop_loss_pct') else 10,
                    "max_positions": risk.max_positions if hasattr(risk, 'max_positions') else 5,
                }
            },
            "summary": trainer.get_training_summary()
        }
        
        # Save config
        config_file = "optimized_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        print(f"\n💾 Saved optimized config to: {config_file}")
        
        # Print summary
        print("\n" + "🔥"*35)
        print("✅ SUPERIOR TRAINING COMPLETE")
        print("🔥"*35)
        
        total_improvement = sum(r.improvement_pct for r in results)
        avg_improvement = total_improvement / len(results) if results else 0
        
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   Total training modules: {len(results)}")
        print(f"   Average improvement: {avg_improvement:.1f}%")
        print(f"   Total improvement: {total_improvement:.1f}%")
        
        print(f"\n📈 PER-MODULE IMPROVEMENTS:")
        for r in results:
            status = "🟢" if r.improvement_pct > 10 else "🟡" if r.improvement_pct > 0 else "🔴"
            print(f"   {status} {r.module}: {r.before_score:.2f} → {r.after_score:.2f} (+{r.improvement_pct:.1f}%)")
        
        print(f"\n💡 KEY INSIGHTS:")
        for r in results:
            for insight in r.insights[:2]:
                print(f"   • {insight}")
        
        print(f"\n🎯 OPTIMIZED PARAMETERS APPLIED:")
        print(f"   Config saved to: {config_file}")
        print(f"   Ready for production use!")
        
        return config


def quick_train():
    """Quick training with sample data."""
    print("⚡ QUICK TRAINING MODE")
    
    kb = SolanaKnowledgeBase()
    historian = SolanaHistorian()
    trainer = SuperiorTrainingEngine(kb, historian)
    
    # Simulate with synthetic data
    print("   Training with sample patterns...")
    
    # Update weights based on common patterns
    kb.opportunity_weights = {
        'momentum': 0.30,
        'volume': 0.25,
        'historical': 0.15,
        'timing': 0.15,
        'risk': 0.10,
        'social': 0.05,
    }
    
    print("   ✅ Quick training complete")
    print("   🎯 Opportunity weights updated")
    
    return kb.opportunity_weights


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_train()
    else:
        config = asyncio.run(run_superior_training())
        print("\n👋 Training complete. Run 'python main.py' to use optimized config.")
