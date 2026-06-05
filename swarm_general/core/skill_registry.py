"""
🛠️ SKILL REGISTRY
Manages skills ecosystem for the swarm
Discovers, loads, tracks, and evolves skills
"""

import importlib
import logging
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger('SkillRegistry')

class SkillRegistry:
    """Registry for swarm skills"""
    
    # Built-in skill catalog
    SKILL_CATALOG = {
        # Research Skills
        'web_search': {'category': 'research', 'level': 1, 'description': 'Search the web for information'},
        'deep_research': {'category': 'research', 'level': 2, 'description': 'Deep research with synthesis'},
        'osint_gather': {'category': 'research', 'level': 2, 'description': 'Open source intelligence gathering'},
        'data_scrape': {'category': 'research', 'level': 1, 'description': 'Scrape data from websites'},
        'fact_check': {'category': 'research', 'level': 2, 'description': 'Verify facts and sources'},
        
        # Content Skills
        'write_text': {'category': 'content', 'level': 1, 'description': 'Write text content'},
        'write_code': {'category': 'content', 'level': 2, 'description': 'Write code in various languages'},
        'edit_text': {'category': 'content', 'level': 1, 'description': 'Edit and improve text'},
        'summarize': {'category': 'content', 'level': 1, 'description': 'Summarize long content'},
        'translate': {'category': 'content', 'level': 1, 'description': 'Translate between languages'},
        'creative_write': {'category': 'content', 'level': 2, 'description': 'Creative writing'},
        'generate_doc': {'category': 'content', 'level': 1, 'description': 'Generate documentation'},
        
        # Automation Skills
        'schedule_task': {'category': 'automation', 'level': 1, 'description': 'Schedule future tasks'},
        'run_script': {'category': 'automation', 'level': 2, 'description': 'Execute scripts'},
        'api_call': {'category': 'automation', 'level': 1, 'description': 'Make API calls'},
        'webhook_trigger': {'category': 'automation', 'level': 2, 'description': 'Trigger webhooks'},
        'file_operation': {'category': 'automation', 'level': 1, 'description': 'File read/write/operations'},
        'workflow_orchestrate': {'category': 'automation', 'level': 3, 'description': 'Orchestrate complex workflows'},
        
        # Monitoring Skills
        'ping_check': {'category': 'monitoring', 'level': 1, 'description': 'Check if service is alive'},
        'log_monitor': {'category': 'monitoring', 'level': 1, 'description': 'Monitor logs'},
        'metric_collect': {'category': 'monitoring', 'level': 2, 'description': 'Collect metrics'},
        'alert_send': {'category': 'monitoring', 'level': 1, 'description': 'Send alerts'},
        'health_report': {'category': 'monitoring', 'level': 2, 'description': 'Generate health reports'},
        'anomaly_detect': {'category': 'monitoring', 'level': 3, 'description': 'Detect anomalies'},
        
        # Communication Skills
        'telegram_send': {'category': 'communication', 'level': 1, 'description': 'Send Telegram messages'},
        'email_send': {'category': 'communication', 'level': 1, 'description': 'Send emails'},
        'discord_send': {'category': 'communication', 'level': 1, 'description': 'Send Discord messages'},
        'broadcast': {'category': 'communication', 'level': 2, 'description': 'Broadcast to multiple channels'},
        'meeting_schedule': {'category': 'communication', 'level': 2, 'description': 'Schedule meetings'},
        'reminder_set': {'category': 'communication', 'level': 1, 'description': 'Set reminders'},
        
        # Analysis Skills
        'data_analyze': {'category': 'analysis', 'level': 2, 'description': 'Analyze datasets'},
        'chart_create': {'category': 'analysis', 'level': 2, 'description': 'Create charts and visualizations'},
        'report_generate': {'category': 'analysis', 'level': 2, 'description': 'Generate analytical reports'},
        'statistical_test': {'category': 'analysis', 'level': 3, 'description': 'Run statistical tests'},
        'predict_model': {'category': 'analysis', 'level': 3, 'description': 'Predictive modeling'},
        'trend_analyze': {'category': 'analysis', 'level': 2, 'description': 'Analyze trends'},
        
        # Problem Solving Skills
        'debug_code': {'category': 'problem_solving', 'level': 2, 'description': 'Debug code'},
        'error_analyze': {'category': 'problem_solving', 'level': 2, 'description': 'Analyze errors'},
        'fix_suggest': {'category': 'problem_solving', 'level': 2, 'description': 'Suggest fixes'},
        'optimize_code': {'category': 'problem_solving', 'level': 3, 'description': 'Optimize code'},
        'root_cause': {'category': 'problem_solving', 'level': 3, 'description': 'Root cause analysis'},
        'workaround_find': {'category': 'problem_solving', 'level': 2, 'description': 'Find workarounds'},
        
        # Learning Skills
        'skill_learn': {'category': 'learning', 'level': 1, 'description': 'Learn new skills'},
        'pattern_learn': {'category': 'learning', 'level': 2, 'description': 'Learn patterns from data'},
        'knowledge_update': {'category': 'learning', 'level': 1, 'description': 'Update knowledge base'},
        'strategy_evolve': {'category': 'learning', 'level': 3, 'description': 'Evolve strategies'},
        'cross_domain': {'category': 'learning', 'level': 3, 'description': 'Cross-domain knowledge transfer'},
        'self_assess': {'category': 'learning', 'level': 2, 'description': 'Self-assess performance'},
    }
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.skills: Dict[str, Any] = {}
        self.skill_usage: Dict[str, int] = {}
        self.skill_success: Dict[str, Dict] = {}
        self.skill_levels: Dict[str, int] = {}
        
        # Load skills
        self._load_all_skills()
        
        logger.info(f"🛠️ Skill Registry initialized with {len(self.skills)} skills")
    
    def _load_all_skills(self):
        """Load all available skills"""
        # Load built-in catalog
        for skill_name, config in self.SKILL_CATALOG.items():
            self.skills[skill_name] = {
                **config,
                'name': skill_name,
                'loaded': True,
                'source': 'built-in',
                'discovered_at': datetime.now().isoformat()
            }
            self.skill_levels[skill_name] = config.get('level', 1)
            self.skill_usage[skill_name] = 0
            self.skill_success[skill_name] = {'success': 0, 'fail': 0}
        
        # Discover additional skills from skills directory
        self._discover_skills()
    
    def _discover_skills(self):
        """Discover skills from the skills directory"""
        skills_dir = Path(__file__).parent.parent / 'skills'
        if not skills_dir.exists():
            return
        
        for skill_file in skills_dir.glob('*.py'):
            skill_name = skill_file.stem
            if skill_name not in self.skills and not skill_name.startswith('_'):
                self.skills[skill_name] = {
                    'name': skill_name,
                    'category': 'discovered',
                    'level': 1,
                    'description': f'Discovered skill: {skill_name}',
                    'loaded': False,
                    'source': 'discovered',
                    'path': str(skill_file),
                    'discovered_at': datetime.now().isoformat()
                }
                self.skill_levels[skill_name] = 1
                self.skill_usage[skill_name] = 0
                self.skill_success[skill_name] = {'success': 0, 'fail': 0}
    
    def get_skill(self, skill_name: str) -> Optional[Dict]:
        """Get skill by name"""
        return self.skills.get(skill_name)
    
    def list_skills(self, category: str = None, min_level: int = None) -> List[Dict]:
        """List skills with optional filtering"""
        result = []
        for name, skill in self.skills.items():
            if category and skill.get('category') != category:
                continue
            if min_level and skill.get('level', 0) < min_level:
                continue
            result.append(skill)
        return result
    
    def find_skills_for_task(self, task_description: str) -> List[str]:
        """Find relevant skills for a task"""
        task_lower = task_description.lower()
        matches = []
        
        for skill_name, skill in self.skills.items():
            # Check if skill keywords match task
            desc = skill.get('description', '').lower()
            category = skill.get('category', '').lower()
            
            if any(word in task_lower for word in desc.split()):
                matches.append(skill_name)
            elif category in task_lower:
                matches.append(skill_name)
        
        # Sort by usage (most used first)
        matches.sort(key=lambda s: self.skill_usage.get(s, 0), reverse=True)
        
        return matches[:5]  # Top 5 matches
    
    def use_skill(self, skill_name: str, success: bool = True):
        """Record skill usage"""
        if skill_name not in self.skill_usage:
            self.skill_usage[skill_name] = 0
        
        self.skill_usage[skill_name] += 1
        
        if skill_name not in self.skill_success:
            self.skill_success[skill_name] = {'success': 0, 'fail': 0}
        
        if success:
            self.skill_success[skill_name]['success'] += 1
        else:
            self.skill_success[skill_name]['fail'] += 1
        
        # Check for level up
        self._check_level_up(skill_name)
    
    def _check_level_up(self, skill_name: str):
        """Check if skill should level up"""
        usage = self.skill_usage.get(skill_name, 0)
        current_level = self.skill_levels.get(skill_name, 1)
        success_rate = self._get_success_rate(skill_name)
        
        # Level up conditions
        level_thresholds = {
            1: {'min_usage': 5, 'min_success_rate': 0.6},
            2: {'min_usage': 20, 'min_success_rate': 0.7},
            3: {'min_usage': 50, 'min_success_rate': 0.8},
        }
        
        if current_level in level_thresholds:
            threshold = level_thresholds[current_level]
            if usage >= threshold['min_usage'] and success_rate >= threshold['min_success_rate']:
                new_level = current_level + 1
                self.skill_levels[skill_name] = new_level
                self.skills[skill_name]['level'] = new_level
                logger.info(f"⬆️ Skill {skill_name} leveled up to {new_level}!")
    
    def _get_success_rate(self, skill_name: str) -> float:
        """Get success rate for a skill"""
        stats = self.skill_success.get(skill_name, {'success': 0, 'fail': 0})
        total = stats['success'] + stats['fail']
        if total == 0:
            return 1.0
        return stats['success'] / total
    
    def get_skill_stats(self, skill_name: str) -> Optional[Dict]:
        """Get statistics for a skill"""
        if skill_name not in self.skills:
            return None
        
        return {
            'name': skill_name,
            'usage_count': self.skill_usage.get(skill_name, 0),
            'success_rate': self._get_success_rate(skill_name),
            'current_level': self.skill_levels.get(skill_name, 1),
            'details': self.skills[skill_name]
        }
    
    def add_skill(self, skill_name: str, config: Dict):
        """Add a new skill to the registry"""
        if skill_name in self.skills:
            logger.warning(f"⚠️ Skill {skill_name} already exists, updating")
        
        self.skills[skill_name] = {
            **config,
            'name': skill_name,
            'loaded': True,
            'source': 'manual',
            'added_at': datetime.now().isoformat()
        }
        self.skill_levels[skill_name] = config.get('level', 1)
        self.skill_usage[skill_name] = 0
        self.skill_success[skill_name] = {'success': 0, 'fail': 0}
        
        logger.info(f"➕ Added skill: {skill_name}")
    
    def remove_skill(self, skill_name: str) -> bool:
        """Remove a skill from the registry"""
        if skill_name not in self.skills:
            return False
        
        del self.skills[skill_name]
        del self.skill_levels[skill_name]
        del self.skill_usage[skill_name]
        del self.skill_success[skill_name]
        
        logger.info(f"➖ Removed skill: {skill_name}")
        return True
    
    def get_top_skills(self, count: int = 10) -> List[Dict]:
        """Get most used skills"""
        sorted_skills = sorted(
            self.skill_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {
                'name': name,
                'usage': usage,
                'level': self.skill_levels.get(name, 1),
                'success_rate': self._get_success_rate(name)
            }
            for name, usage in sorted_skills[:count]
        ]
    
    def export_skills(self) -> str:
        """Export skills to JSON"""
        export_data = {
            'skills': self.skills,
            'levels': self.skill_levels,
            'usage': self.skill_usage,
            'success': self.skill_success,
            'exported_at': datetime.now().isoformat()
        }
        return json.dumps(export_data, indent=2)
    
    def get_category_stats(self) -> Dict:
        """Get statistics by category"""
        categories = {}
        for skill in self.skills.values():
            cat = skill.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'count': 0, 'total_usage': 0, 'avg_level': 0}
            categories[cat]['count'] += 1
            categories[cat]['total_usage'] += self.skill_usage.get(skill['name'], 0)
            categories[cat]['avg_level'] += self.skill_levels.get(skill['name'], 1)
        
        # Calculate averages
        for cat in categories:
            if categories[cat]['count'] > 0:
                categories[cat]['avg_level'] /= categories[cat]['count']
                categories[cat]['avg_level'] = round(categories[cat]['avg_level'], 2)
        
        return categories
