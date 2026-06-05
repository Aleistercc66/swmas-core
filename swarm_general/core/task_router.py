"""
🎯 TASK ROUTER
Intelligent task routing system for the General Purpose Swarm
Routes tasks to the most appropriate agent based on multiple factors
"""

import logging
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger('TaskRouter')

class TaskRouter:
    """Routes tasks to appropriate agents"""
    
    # Task type keywords for routing
    ROUTING_MAP = {
        'ResearchAgent': {
            'keywords': [
                'research', 'find', 'search', 'investigate', 'discover', 'explore',
                'look up', 'gather', 'collect', 'survey', 'study', 'analyze data',
                'osint', 'intelligence', 'reconnaissance', 'due diligence',
                'background check', 'verify', 'fact check', 'validate',
                'market research', 'competitive analysis', 'trend',
                'what is', 'how does', 'why is', 'who is', 'when did',
                'news', 'article', 'information', 'source', 'reference',
                'document', 'paper', 'report', 'study', 'whitepaper'
            ],
            'domains': ['research', 'intelligence', 'osint', 'investigation'],
            'confidence_threshold': 0.6
        },
        'ContentAgent': {
            'keywords': [
                'write', 'create', 'draft', 'compose', 'generate', 'produce',
                'code', 'program', 'script', 'develop', 'build',
                'design', 'concept', 'visual', 'media', 'content',
                'article', 'blog', 'post', 'copy', 'text', 'story',
                'email', 'letter', 'message', 'announcement', 'update',
                'documentation', 'readme', 'guide', 'tutorial', 'manual',
                'script', 'automation', 'workflow', 'bot', 'tool',
                'edit', 'revise', 'proofread', 'improve', 'polish',
                'translate', 'localize', 'adapt', 'rewrite', 'summarize',
                'creative', 'artistic', 'copywriting', 'marketing'
            ],
            'domains': ['content', 'creation', 'writing', 'coding', 'creative'],
            'confidence_threshold': 0.6
        },
        'AutomationAgent': {
            'keywords': [
                'automate', 'schedule', 'cron', 'routine', 'repetitive',
                'workflow', 'pipeline', 'process', 'streamline', 'optimize',
                'integrate', 'connect', 'sync', 'bridge', 'link',
                'deploy', 'setup', 'configure', 'install', 'provision',
                'monitor', 'watch', 'track', 'log', 'record',
                'execute', 'run', 'perform', 'batch', 'bulk',
                'script', 'macro', 'bot', 'daemon', 'service',
                'trigger', 'event', 'condition', 'rule', 'policy',
                'backup', 'sync', 'migrate', 'transfer', 'copy'
            ],
            'domains': ['automation', 'workflow', 'integration', 'devops'],
            'confidence_threshold': 0.6
        },
        'MonitorAgent': {
            'keywords': [
                'monitor', 'watch', 'track', 'observe', 'check',
                'alert', 'notify', 'warn', 'ping', 'status',
                'health', 'performance', 'metrics', 'statistics', 'analytics',
                'uptime', 'downtime', 'availability', 'response time',
                'error', 'exception', 'bug', 'issue', 'problem',
                'detect', 'identify', 'spot', 'notice', 'catch',
                'dashboard', 'visualization', 'graph', 'chart', 'report',
                'heartbeat', 'pulse', 'alive', 'dead', 'status check',
                'log', 'event', 'audit', 'trail', 'history'
            ],
            'domains': ['monitoring', 'alerting', 'observability', 'tracking'],
            'confidence_threshold': 0.6
        },
        'CommsAgent': {
            'keywords': [
                'send', 'message', 'notify', 'inform', 'contact',
                'telegram', 'discord', 'email', 'slack', 'whatsapp',
                'announce', 'broadcast', 'share', 'distribute', 'publish',
                'coordinate', 'organize', 'schedule meeting', 'arrange',
                'remind', 'prompt', 'nudge', 'follow up', 'check in',
                'communicate', 'talk', 'chat', 'discuss', 'converse',
                'forward', 'relay', 'route', 'pass', 'transfer',
                'respond', 'reply', 'answer', 'acknowledge', 'confirm',
                'group', 'channel', 'room', 'forum', 'community'
            ],
            'domains': ['communication', 'messaging', 'coordination', 'notifications'],
            'confidence_threshold': 0.6
        },
        'AnalysisAgent': {
            'keywords': [
                'analyze', 'evaluate', 'assess', 'examine', 'inspect',
                'compare', 'contrast', 'benchmark', 'rank', 'score',
                'calculate', 'compute', 'model', 'simulate', 'predict',
                'forecast', 'project', 'estimate', 'trend', 'pattern',
                'data', 'statistics', 'metrics', 'kpi', 'indicator',
                'report', 'summary', 'review', 'audit', 'deep dive',
                'insight', 'finding', 'conclusion', 'recommendation', 'suggestion',
                'risk', 'opportunity', 'threat', 'strength', 'weakness',
                'decision', 'choice', 'option', 'alternative', 'scenario'
            ],
            'domains': ['analysis', 'evaluation', 'modeling', 'forecasting'],
            'confidence_threshold': 0.6
        },
        'SolverAgent': {
            'keywords': [
                'fix', 'repair', 'solve', 'resolve', 'troubleshoot',
                'debug', 'diagnose', 'investigate', 'root cause', 'error',
                'broken', 'not working', 'failed', 'crash', 'bug',
                'issue', 'problem', 'challenge', 'obstacle', 'blocker',
                'stuck', 'blocked', "can't", 'unable', 'impossible',
                'optimize', 'improve', 'enhance', 'upgrade', 'refactor',
                'convert', 'transform', 'migrate', 'upgrade', 'update',
                'hack', 'workaround', 'patch', 'hotfix', 'solution',
                'emergency', 'critical', 'urgent', 'asap', 'now'
            ],
            'domains': ['problem_solving', 'debugging', 'repair', 'optimization'],
            'confidence_threshold': 0.6
        },
        'LearnAgent': {
            'keywords': [
                'learn', 'study', 'train', 'practice', 'improve skill',
                'new skill', 'capability', 'ability', 'competence',
                'tutorial', 'course', 'lesson', 'guide', 'how to',
                'teach', 'explain', 'demonstrate', 'show', 'walkthrough',
                'adapt', 'evolve', 'upgrade', 'level up', 'progress',
                'memorize', 'remember', 'recall', 'store', 'save',
                'pattern', 'rule', 'heuristic', 'strategy', 'tactic',
                'knowledge base', 'wiki', 'documentation', 'reference',
                'best practice', 'standard', 'convention', 'pattern',
                'research new', 'explore new', 'discover new', 'investigate new'
            ],
            'domains': ['learning', 'adaptation', 'skill_building', 'evolution'],
            'confidence_threshold': 0.6
        }
    }
    
    # Special compound routing
    COMPOUND_ROUTES = {
        ('research', 'content'): 'ResearchAgent',  # Research then write
        ('monitor', 'alert'): 'MonitorAgent',      # Monitor with alerts
        ('analysis', 'research'): 'AnalysisAgent', # Analysis with research
        ('automation', 'monitor'): 'AutomationAgent', # Auto monitoring
    }
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.routing_history = []
        logger.info("🎯 Task Router initialized")
    
    def route(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a task to the most appropriate agent
        
        Returns:
            {
                'agent_type': str,
                'confidence': float,
                'reasoning': str,
                'fallback': str,
                'estimated_time': int
            }
        """
        task_type = task.get('type', '').lower()
        description = task.get('description', '').lower()
        direction = task.get('direction', '').lower()
        
        # Combine all text for analysis
        task_text = f"{task_type} {description} {direction}"
        
        # Calculate scores for each agent type
        scores = {}
        reasoning = {}
        
        for agent_type, config in self.ROUTING_MAP.items():
            score = self._calculate_score(task_text, config)
            scores[agent_type] = score
            reasoning[agent_type] = self._generate_reason(task_text, config, score)
        
        # Sort by score
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent = sorted_agents[0][0]
        best_score = sorted_agents[0][1]
        
        # Check if we need compound routing
        if best_score < 0.5 and len(sorted_agents) > 1:
            # Low confidence on primary, check compound
            top_two = (sorted_agents[0][0].replace('Agent', '').lower(), 
                      sorted_agents[1][0].replace('Agent', '').lower())
            if top_two in self.COMPOUND_ROUTES:
                best_agent = self.COMPOUND_ROUTES[top_two]
                best_score = 0.7  # Boost confidence for compound
        
        # Fallback if confidence too low
        fallback = sorted_agents[1][0] if len(sorted_agents) > 1 else 'ResearchAgent'
        
        result = {
            'agent_type': best_agent,
            'confidence': round(best_score, 2),
            'reasoning': reasoning[best_agent],
            'fallback': fallback,
            'estimated_time': self._estimate_time(best_agent, task),
            'all_scores': {k: round(v, 2) for k, v in sorted_agents[:3]}
        }
        
        # Log routing decision
        self.routing_history.append({
            'task_id': task.get('id'),
            'routed_to': best_agent,
            'confidence': best_score,
            'text_preview': task_text[:100]
        })
        
        logger.info(f"🎯 Routed to {best_agent} (confidence: {best_score:.2f})")
        return result
    
    def _calculate_score(self, text: str, config: Dict) -> float:
        """Calculate routing score based on keyword matching"""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Keyword matching
        keyword_hits = sum(1 for kw in config['keywords'] if kw.lower() in text_lower)
        keyword_score = min(keyword_hits / 3, 1.0)  # Normalize, cap at 3 hits
        
        # Domain matching
        domain_hits = sum(1 for domain in config['domains'] if domain in text_lower)
        domain_score = min(domain_hits / 1, 0.5)  # Domains are worth less
        
        # Similarity matching for longer phrases
        similarity_scores = []
        for kw in config['keywords']:
            if len(kw) > 5:  # Only for longer keywords
                similarity = SequenceMatcher(None, text_lower, kw.lower()).ratio()
                if similarity > 0.7:
                    similarity_scores.append(similarity)
        
        similarity_score = max(similarity_scores) if similarity_scores else 0
        
        # Combined score with weights
        score = (keyword_score * 0.5 + domain_score * 0.2 + similarity_score * 0.3)
        
        return min(score, 1.0)
    
    def _generate_reason(self, text: str, config: Dict, score: float) -> str:
        """Generate human-readable routing reason"""
        hits = [kw for kw in config['keywords'] if kw.lower() in text.lower()]
        
        if hits:
            return f"Matched keywords: {', '.join(hits[:3])}"
        else:
            return f"Semantic similarity score: {score:.2f}"
    
    def _estimate_time(self, agent_type: str, task: Dict) -> int:
        """Estimate task execution time in seconds"""
        base_times = {
            'ResearchAgent': 120,
            'ContentAgent': 90,
            'AutomationAgent': 60,
            'MonitorAgent': 30,
            'CommsAgent': 15,
            'AnalysisAgent': 100,
            'SolverAgent': 180,
            'LearnAgent': 300
        }
        
        base = base_times.get(agent_type, 60)
        
        # Adjust based on complexity indicators
        desc = task.get('description', '')
        if any(w in desc.lower() for w in ['deep', 'comprehensive', 'thorough', 'detailed']):
            base *= 2
        if any(w in desc.lower() for w in ['quick', 'simple', 'brief', 'fast']):
            base = int(base * 0.5)
        
        return base
    
    def get_stats(self) -> Dict:
        """Get routing statistics"""
        if not self.routing_history:
            return {'total_routed': 0}
        
        from collections import Counter
        agent_counts = Counter([r['routed_to'] for r in self.routing_history])
        
        return {
            'total_routed': len(self.routing_history),
            'agent_distribution': dict(agent_counts),
            'avg_confidence': sum(r['confidence'] for r in self.routing_history) / len(self.routing_history)
        }
