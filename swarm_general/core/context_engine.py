"""
🧠 CONTEXT ENGINE
Manages session state, memory, and context for all swarm operations
Provides short-term, long-term, and episodic memory
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger('ContextEngine')

class ContextEngine:
    """Manages context and memory for the swarm"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
        # Memory stores
        self.short_term: Dict[str, Any] = {}  # Active session memory
        self.long_term: Dict[str, Any] = {}   # Persistent knowledge
        self.episodic: List[Dict] = []        # Event/timeline memory
        
        # User contexts
        self.user_contexts: Dict[str, Dict] = {}
        
        # Load existing memory
        self._load_memory()
        
        logger.info("🧠 Context Engine initialized")
    
    def _get_memory_path(self) -> Path:
        """Get path for memory storage"""
        return Path(__file__).parent.parent / 'memory'
    
    def _load_memory(self):
        """Load persisted memory"""
        memory_dir = self._get_memory_path()
        memory_dir.mkdir(exist_ok=True)
        
        # Load long-term memory
        lt_file = memory_dir / 'long_term.json'
        if lt_file.exists():
            try:
                with open(lt_file) as f:
                    self.long_term = json.load(f)
                logger.info(f"📚 Loaded long-term memory: {len(self.long_term)} entries")
            except Exception as e:
                logger.error(f"❌ Error loading long-term memory: {e}")
        
        # Load episodic memory
        ep_file = memory_dir / 'episodic.json'
        if ep_file.exists():
            try:
                with open(ep_file) as f:
                    self.episodic = json.load(f)
                logger.info(f"📖 Loaded episodic memory: {len(self.episodic)} events")
            except Exception as e:
                logger.error(f"❌ Error loading episodic memory: {e}")
        
        # Load user contexts
        uc_file = memory_dir / 'user_contexts.json'
        if uc_file.exists():
            try:
                with open(uc_file) as f:
                    self.user_contexts = json.load(f)
                logger.info(f"👤 Loaded user contexts: {len(self.user_contexts)} users")
            except Exception as e:
                logger.error(f"❌ Error loading user contexts: {e}")
    
    def _save_memory(self):
        """Persist memory to disk"""
        memory_dir = self._get_memory_path()
        memory_dir.mkdir(exist_ok=True)
        
        try:
            with open(memory_dir / 'long_term.json', 'w') as f:
                json.dump(self.long_term, f, indent=2)
            
            with open(memory_dir / 'episodic.json', 'w') as f:
                json.dump(self.episodic[-1000:], f, indent=2)  # Keep last 1000
            
            with open(memory_dir / 'user_contexts.json', 'w') as f:
                json.dump(self.user_contexts, f, indent=2)
            
            logger.debug("💾 Memory saved")
        except Exception as e:
            logger.error(f"❌ Error saving memory: {e}")
    
    # Short-term memory operations
    def set_short_term(self, key: str, value: Any, ttl: int = 3600):
        """Set short-term memory with TTL"""
        self.short_term[key] = {
            'value': value,
            'set_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
        }
    
    def get_short_term(self, key: str) -> Optional[Any]:
        """Get short-term memory if not expired"""
        entry = self.short_term.get(key)
        if not entry:
            return None
        
        expires = datetime.fromisoformat(entry['expires_at'])
        if datetime.now() > expires:
            del self.short_term[key]
            return None
        
        return entry['value']
    
    def clear_short_term(self):
        """Clear all short-term memory"""
        self.short_term.clear()
        logger.info("🧹 Short-term memory cleared")
    
    # Long-term memory operations
    def remember(self, key: str, value: Any, category: str = 'general'):
        """Store in long-term memory"""
        if category not in self.long_term:
            self.long_term[category] = {}
        
        self.long_term[category][key] = {
            'value': value,
            'stored_at': datetime.now().isoformat(),
            'access_count': 0
        }
        
        # Auto-save periodically
        if len(self.long_term[category]) % 10 == 0:
            self._save_memory()
        
        logger.debug(f"📝 Remembered: {key} ({category})")
    
    def recall(self, key: str, category: str = None) -> Optional[Any]:
        """Recall from long-term memory"""
        if category:
            entry = self.long_term.get(category, {}).get(key)
        else:
            # Search across categories
            entry = None
            for cat_data in self.long_term.values():
                if key in cat_data:
                    entry = cat_data[key]
                    break
        
        if entry:
            entry['access_count'] += 1
            entry['last_accessed'] = datetime.now().isoformat()
            return entry['value']
        
        return None
    
    def search_memory(self, query: str, category: str = None) -> List[Dict]:
        """Search memory by keyword"""
        results = []
        query_lower = query.lower()
        
        categories = [category] if category else self.long_term.keys()
        
        for cat in categories:
            if cat not in self.long_term:
                continue
            
            for key, entry in self.long_term[cat].items():
                value_str = str(entry['value']).lower()
                if query_lower in key.lower() or query_lower in value_str:
                    results.append({
                        'key': key,
                        'category': cat,
                        'value': entry['value'],
                        'relevance': self._calculate_relevance(query_lower, key, value_str)
                    })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:10]
    
    def _calculate_relevance(self, query: str, key: str, value: str) -> float:
        """Calculate relevance score for search"""
        score = 0.0
        
        # Exact key match is highest
        if query == key.lower():
            score += 1.0
        elif query in key.lower():
            score += 0.5
        
        # Value matches
        if query in value:
            score += 0.3
        
        return score
    
    # Episodic memory operations
    def record_event(self, event_type: str, details: Dict, importance: int = 5):
        """Record an event in episodic memory"""
        event = {
            'id': f"evt_{int(time.time())}_{len(self.episodic)}",
            'type': event_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'importance': importance  # 1-10
        }
        
        self.episodic.append(event)
        
        # Keep only important events if too many
        if len(self.episodic) > 2000:
            self.episodic = sorted(
                self.episodic,
                key=lambda x: (x['importance'], x['timestamp']),
                reverse=True
            )[:1000]
        
        logger.debug(f"📅 Recorded event: {event_type} (importance: {importance})")
    
    def get_recent_events(self, count: int = 10, event_type: str = None) -> List[Dict]:
        """Get recent events"""
        events = self.episodic
        
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        return sorted(events, key=lambda x: x['timestamp'], reverse=True)[:count]
    
    def get_events_by_timeframe(self, hours: int = 24) -> List[Dict]:
        """Get events from last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            e for e in self.episodic
            if datetime.fromisoformat(e['timestamp']) > cutoff
        ]
    
    # User context operations
    def get_user_context(self, user_id: str) -> Dict:
        """Get or create user context"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'preferences': {},
                'history': [],
                'active_tasks': [],
                'stats': {
                    'tasks_submitted': 0,
                    'tasks_completed': 0
                }
            }
        
        return self.user_contexts[user_id]
    
    def update_user_context(self, user_id: str, updates: Dict):
        """Update user context"""
        context = self.get_user_context(user_id)
        context.update(updates)
        context['last_updated'] = datetime.now().isoformat()
        
        # Save periodically
        self._save_memory()
    
    def add_user_history(self, user_id: str, entry: Dict):
        """Add to user history"""
        context = self.get_user_context(user_id)
        entry['timestamp'] = datetime.now().isoformat()
        context['history'].append(entry)
        
        # Keep last 100 entries
        if len(context['history']) > 100:
            context['history'] = context['history'][-100:]
    
    # Context assembly for agents
    def build_context(self, task: Dict, agent_type: str) -> Dict:
        """Build execution context for an agent"""
        user_id = task.get('context', {}).get('user_id', 'default')
        
        context = {
            'task': task,
            'agent_type': agent_type,
            'user': self.get_user_context(user_id),
            'short_term': self.short_term,
            'relevant_memory': self._get_relevant_memory(task),
            'recent_events': self.get_recent_events(5),
            'swarm_status': self.orchestrator.get_status(),
            'timestamp': datetime.now().isoformat()
        }
        
        return context
    
    def _get_relevant_memory(self, task: Dict) -> List[Dict]:
        """Get memory relevant to the task"""
        description = task.get('description', '')
        
        # Search for relevant entries
        results = self.search_memory(description[:50])
        
        return results[:5]
    
    # Maintenance
    def cleanup(self):
        """Clean up expired entries"""
        # Clean short-term
        expired = []
        for key, entry in self.short_term.items():
            expires = datetime.fromisoformat(entry['expires_at'])
            if datetime.now() > expires:
                expired.append(key)
        
        for key in expired:
            del self.short_term[key]
        
        logger.info(f"🧹 Cleaned up {len(expired)} expired short-term entries")
        
        # Save to disk
        self._save_memory()
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            'short_term_entries': len(self.short_term),
            'long_term_categories': len(self.long_term),
            'long_term_total': sum(len(v) for v in self.long_term.values()),
            'episodic_events': len(self.episodic),
            'user_contexts': len(self.user_contexts),
            'memory_size_kb': self._estimate_size()
        }
    
    def _estimate_size(self) -> int:
        """Estimate memory size in KB"""
        try:
            total = json.dumps({
                'short_term': self.short_term,
                'long_term': self.long_term,
                'episodic': self.episodic,
                'user_contexts': self.user_contexts
            })
            return len(total.encode('utf-8')) // 1024
        except:
            return 0
