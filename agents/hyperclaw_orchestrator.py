"""
HYPERCLAW ORCHESTRATOR
OpenClaw + Hermes Integration Module

This module orchestrates the collaboration between:
- OpenClaw: Execution engine (file ops, trading, deployment)
- Hermes: Validation engine (Red Team, Devil's Advocate, Bias Detection)

Pipeline:
1. OpenClaw proposes an action
2. Hermes validates (finds flaws, risks, biases)
3. If approved: OpenClaw executes
4. If rejected: Back to step 1 with corrections
5. Feedback loop: Results feed back to both agents

All decisions are logged to the Obsidian vault for audit trail.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class HyperClawDecision:
    """A decision in the HyperClaw pipeline"""
    decision_id: str
    timestamp: float
    proposed_by: str  # 'openclaw' or 'hermes'
    action_type: str  # 'trade', 'deploy', 'config', 'revenue', 'risk'
    action_details: Dict[str, Any]
    
    # Validation
    hermes_validation: Optional[Dict] = None
    hermes_status: str = 'pending'  # pending, approved, rejected, needs_work
    hermes_feedback: str = ''
    
    # Execution
    execution_status: str = 'pending'  # pending, executed, failed
    execution_result: Optional[Dict] = None
    execution_error: str = ''
    
    # Feedback loop
    feedback_applied: bool = False
    iteration: int = 1
    max_iterations: int = 3


class HyperClawOrchestrator:
    """
    HyperClaw: OpenClaw + Hermes Coordination System
    
    Ensures every decision is validated before execution.
    Every action is logged to the Cognitive Nexus vault.
    """
    
    def __init__(self, vault_path: str = '/root/obsidian-vault/Cognitive Nexus'):
        self.vault_path = vault_path
        self.decisions: List[HyperClawDecision] = []
        self.active = False
        
        # Subsystems
        self.openclaw_available = self._check_openclaw()
        self.hermes_available = self._check_hermes()
        
        # Callbacks
        self.on_decision: Optional[Callable] = None
        self.on_execution: Optional[Callable] = None
        
    def _check_openclaw(self) -> bool:
        """Check if OpenClaw is available"""
        try:
            # Check for openclaw CLI or environment
            return os.path.exists('/usr/lib/node_modules/openclaw') or os.path.exists('/root/.openclaw')
        except:
            return False
            
    def _check_hermes(self) -> bool:
        """Check if Hermes vault is available"""
        try:
            return os.path.exists(self.vault_path)
        except:
            return False
            
    async def initialize(self):
        """Initialize the orchestrator"""
        logger.info("🔥 HYPERCLAW ORCHESTRATOR INITIALIZING...")
        
        status = {
            'openclaw': self.openclaw_available,
            'hermes': self.hermes_available,
            'vault': self.vault_path
        }
        
        if not self.openclaw_available:
            logger.warning("⚠️ OpenClaw not detected - some features may be limited")
        if not self.hermes_available:
            logger.warning("⚠️ Hermes vault not detected - validation will be simulated")
            
        logger.info(f"✅ HyperClaw ready: {status}")
        return status
        
    async def propose_action(self, action_type: str, action_details: Dict) -> HyperClawDecision:
        """
        Propose an action and run it through the HyperClaw pipeline.
        
        Pipeline:
        1. Create decision
        2. Hermes validation
        3. If approved: Execute
        4. If rejected: Log and return
        """
        decision_id = f"hyperclaw_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.decisions)}"
        
        decision = HyperClawDecision(
            decision_id=decision_id,
            timestamp=datetime.now().timestamp(),
            proposed_by='openclaw',
            action_type=action_type,
            action_details=action_details
        )
        
        self.decisions.append(decision)
        logger.info(f"📝 Decision proposed: {decision_id} | {action_type}")
        
        # Step 2: Hermes Validation
        await self._hermes_validate(decision)
        
        if decision.hermes_status == 'approved':
            # Step 3: Execute
            await self._execute_decision(decision)
        elif decision.hermes_status == 'rejected':
            logger.warning(f"❌ Decision rejected by Hermes: {decision.hermes_feedback}")
        elif decision.hermes_status == 'needs_work':
            logger.info(f"🔄 Decision needs work: {decision.hermes_feedback}")
            # Could trigger iteration here
            
        # Step 5: Log to vault
        await self._log_to_vault(decision)
        
        return decision
        
    async def _hermes_validate(self, decision: HyperClawDecision):
        """
        Hermes validation: Red Team analysis
        
        Checks for:
        - Logical gaps
        - Security flaws
        - Bias and unsupported assumptions
        - Risk factors
        - Conflict with existing decisions
        """
        logger.info(f"🔍 Hermes validating: {decision.decision_id}")
        
        validation = {
            'logical_gaps': [],
            'security_flaws': [],
            'biases': [],
            'risk_factors': [],
            'conflicts': [],
            'score': 0.0,
            'verdict': 'pending'
        }
        
        # Action-specific validation
        if decision.action_type == 'trade':
            validation = await self._validate_trade(decision, validation)
        elif decision.action_type == 'deploy':
            validation = await self._validate_deploy(decision, validation)
        elif decision.action_type == 'revenue':
            validation = await self._validate_revenue(decision, validation)
        elif decision.action_type == 'risk':
            validation = await self._validate_risk(decision, validation)
        elif decision.action_type == 'config':
            validation = await self._validate_config(decision, validation)
            
        # Calculate overall score
        issues = (
            len(validation['logical_gaps']) +
            len(validation['security_flaws']) * 2 +  # Security issues weighted 2x
            len(validation['biases']) +
            len(validation['risk_factors']) +
            len(validation['conflicts']) * 2
        )
        
        validation['score'] = max(0, 100 - issues * 10)
        
        # Determine verdict
        if validation['score'] >= 80 and len(validation['security_flaws']) == 0:
            validation['verdict'] = 'approved'
        elif validation['score'] >= 50:
            validation['verdict'] = 'needs_work'
        else:
            validation['verdict'] = 'rejected'
            
        # Apply to decision
        decision.hermes_validation = validation
        decision.hermes_status = validation['verdict']
        decision.hermes_feedback = self._format_feedback(validation)
        
        logger.info(f"🔍 Hermes verdict: {validation['verdict']} | Score: {validation['score']}/100")
        
    async def _validate_trade(self, decision: HyperClawDecision, validation: Dict) -> Dict:
        """Validate a trading decision"""
        details = decision.action_details
        
        # Check for logical gaps
        if not details.get('stop_loss'):
            validation['logical_gaps'].append('No stop loss defined')
        if not details.get('take_profit'):
            validation['logical_gaps'].append('No take profit defined')
        if details.get('size', 0) > 0.1:  # >10% of bankroll
            validation['risk_factors'].append('Position size > 10% of bankroll')
            
        # Check for security flaws
        if details.get('slippage', 0) > 0.01:  # >1%
            validation['security_flaws'].append('Slippage > 1% - sandwich risk')
        if not details.get('contract_verified'):
            validation['security_flaws'].append('Contract not verified')
            
        # Check for bias
        if details.get('fomo_indicator', 0) > 0.7:
            validation['biases'].append('FOMO detected - high momentum bias')
        if details.get('recent_losses', 0) > 2:
            validation['biases'].append('Revenge trading risk after recent losses')
            
        # Check for conflicts
        similar_decisions = [d for d in self.decisions if d.action_type == 'trade' and d.execution_status == 'executed']
        if len(similar_decisions) > 5:  # Too many recent trades
            validation['conflicts'].append('High trading frequency - overtrading risk')
            
        return validation
        
    async def _validate_deploy(self, decision: HyperClawDecision, validation: Dict) -> Dict:
        """Validate a deployment decision"""
        details = decision.action_details
        
        if not details.get('tested'):
            validation['security_flaws'].append('Not tested before deployment')
        if not details.get('rollback_plan'):
            validation['logical_gaps'].append('No rollback plan')
            
        return validation
        
    async def _validate_revenue(self, decision: HyperClawDecision, validation: Dict) -> Dict:
        """Validate a revenue strategy decision"""
        details = decision.action_details
        
        if details.get('capital_required', 0) > 0.5:
            validation['risk_factors'].append('High capital requirement')
        if details.get('time_to_profit', 0) > 30:  # >30 days
            validation['risk_factors'].append('Long time to profitability')
            
        # Check for unrealistic expectations
        if details.get('expected_roi', 0) > 10:  # >1000%
            validation['biases'].append('Unrealistic ROI expectation - likely scam or rug')
            
        return validation
        
    async def _validate_risk(self, decision: HyperClawDecision, validation: Dict) -> Dict:
        """Validate a risk management decision"""
        details = decision.action_details
        
        if details.get('new_stop_loss', 0) > 0.3:  # >30%
            validation['risk_factors'].append('Stop loss too wide - will not protect capital')
        if details.get('new_position_size', 0) > 0.2:  # >20%
            validation['risk_factors'].append('Position size too large')
            
        return validation
        
    async def _validate_config(self, decision: HyperClawDecision, validation: Dict) -> Dict:
        """Validate a configuration change"""
        details = decision.action_details
        
        if 'rpc_endpoint' in str(details) and 'http' not in str(details.get('rpc_endpoint', '')):
            validation['security_flaws'].append('Invalid RPC endpoint')
        if 'private_key' in str(details) or 'secret' in str(details).lower():
            validation['security_flaws'].append('Potential secret exposure in config')
            
        return validation
        
    def _format_feedback(self, validation: Dict) -> str:
        """Format validation feedback"""
        feedback = []
        
        if validation['logical_gaps']:
            feedback.append(f"Logical gaps: {', '.join(validation['logical_gaps'])}")
        if validation['security_flaws']:
            feedback.append(f"Security flaws: {', '.join(validation['security_flaws'])}")
        if validation['biases']:
            feedback.append(f"Biases: {', '.join(validation['biases'])}")
        if validation['risk_factors']:
            feedback.append(f"Risks: {', '.join(validation['risk_factors'])}")
        if validation['conflicts']:
            feedback.append(f"Conflicts: {', '.join(validation['conflicts'])}")
            
        return '; '.join(feedback) if feedback else 'No issues found'
        
    async def _execute_decision(self, decision: HyperClawDecision):
        """Execute an approved decision"""
        logger.info(f"⚡ Executing: {decision.decision_id}")
        
        try:
            # Execute based on action type
            if decision.action_type == 'trade':
                result = await self._execute_trade(decision.action_details)
            elif decision.action_type == 'deploy':
                result = await self._execute_deploy(decision.action_details)
            elif decision.action_type == 'revenue':
                result = await self._execute_revenue(decision.action_details)
            elif decision.action_type == 'config':
                result = await self._execute_config(decision.action_details)
            else:
                result = {'status': 'unknown', 'message': 'Unknown action type'}
                
            decision.execution_status = 'executed'
            decision.execution_result = result
            
            logger.info(f"✅ Executed: {decision.decision_id} | {result}")
            
        except Exception as e:
            decision.execution_status = 'failed'
            decision.execution_error = str(e)
            logger.error(f"❌ Execution failed: {decision.decision_id} | {e}")
            
    async def _execute_trade(self, details: Dict) -> Dict:
        """Execute a trade (via OpenClaw trading engine)"""
        # Delegate to execution engine
        from .execution_engine import ZeroLatencyExecutionEngine, ExecutionConfig
        
        # This would be a real execution in production
        return {'status': 'simulated', 'message': 'Trade execution simulated'}
        
    async def _execute_deploy(self, details: Dict) -> Dict:
        """Execute a deployment"""
        # Deploy via OpenClaw
        return {'status': 'simulated', 'message': 'Deployment simulated'}
        
    async def _execute_revenue(self, details: Dict) -> Dict:
        """Execute a revenue strategy"""
        # Start revenue engine
        return {'status': 'simulated', 'message': 'Revenue strategy started'}
        
    async def _execute_config(self, details: Dict) -> Dict:
        """Apply configuration change"""
        # Apply config
        return {'status': 'simulated', 'message': 'Config applied'}
        
    async def _log_to_vault(self, decision: HyperClawDecision):
        """Log decision to Obsidian vault"""
        try:
            # Create log entry
            log_entry = {
                'decision_id': decision.decision_id,
                'timestamp': decision.timestamp,
                'action_type': decision.action_type,
                'proposed_by': decision.proposed_by,
                'hermes_status': decision.hermes_status,
                'hermes_score': decision.hermes_validation.get('score', 0) if decision.hermes_validation else 0,
                'execution_status': decision.execution_status,
                'iteration': decision.iteration
            }
            
            # Write to vault
            log_path = os.path.join(self.vault_path, 'decisions', f"{decision.decision_id}.json")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            with open(log_path, 'w') as f:
                json.dump(log_entry, f, indent=2)
                
            logger.info(f"📝 Logged to vault: {decision.decision_id}")
            
        except Exception as e:
            logger.error(f"Failed to log to vault: {e}")
            
    def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        total = len(self.decisions)
        approved = len([d for d in self.decisions if d.hermes_status == 'approved'])
        rejected = len([d for d in self.decisions if d.hermes_status == 'rejected'])
        executed = len([d for d in self.decisions if d.execution_status == 'executed'])
        failed = len([d for d in self.decisions if d.execution_status == 'failed'])
        
        return {
            'total_decisions': total,
            'approved': approved,
            'rejected': rejected,
            'executed': executed,
            'failed': failed,
            'approval_rate': approved / total if total > 0 else 0,
            'execution_rate': executed / approved if approved > 0 else 0,
            'openclaw_available': self.openclaw_available,
            'hermes_available': self.hermes_available,
        }
        
    async def run_zero_to_revenue(self):
        """Run the full zero-to-revenue pipeline with HyperClaw validation"""
        logger.info("🚀 Starting Zero-to-Revenue with HyperClaw validation...")
        
        # Propose revenue strategy
        decision = await self.propose_action('revenue', {
            'strategy': 'zero_to_revenue',
            'capital_required': 0,
            'expected_roi': 5.0,  # 500% realistic
            'time_to_profit': 7,  # 7 days
            'phases': 3
        })
        
        if decision.hermes_status == 'approved':
            # Start the zero-to-revenue engine
            from .zero_to_revenue import ZeroToRevenueEngine
            
            engine = ZeroToRevenueEngine("wallet", 0.0)
            await engine.start()
            
            return engine.get_report()
        else:
            logger.warning(f"Zero-to-revenue strategy rejected: {decision.hermes_feedback}")
            return {'status': 'rejected', 'reason': decision.hermes_feedback}


# ─── MAIN ───
async def main():
    """Run HyperClaw orchestrator"""
    orchestrator = HyperClawOrchestrator()
    await orchestrator.initialize()
    
    # Test: Propose a trading decision
    decision = await orchestrator.propose_action('trade', {
        'mint': 'SOL',
        'direction': 'BUY',
        'size': 0.01,
        'stop_loss': 0.15,
        'take_profit': 0.50,
        'slippage': 0.005,
        'contract_verified': True
    })
    
    print(f"Decision: {decision}")
    print(f"Stats: {orchestrator.get_stats()}")


if __name__ == "__main__":
    asyncio.run(main())