#!/usr/bin/env python3
"""🧠 Knowledge Base — Vector store for swarm memory & RAG."""
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("knowledge_base")

# Try to import langchain; fallback to simple in-memory if not available
try:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available — using in-memory fallback")


class KnowledgeBase:
    """Vector-based knowledge store for swarm events and decisions."""
    
    def __init__(self, persist_dir: str = "./knowledge_db"):
        self.persist_dir = persist_dir
        self.vectorstore = None
        self.embeddings = None
        self._fallback_memory: List[Dict[str, Any]] = []
        self._initialized = False
        
        if LANGCHAIN_AVAILABLE:
            self._init_chroma()
        else:
            logger.info("Using in-memory knowledge store")
    
    def _init_chroma(self):
        """Initialize ChromaDB with OpenAI embeddings."""
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            
            # Check for API key
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROK_API_KEY")
            if not api_key:
                logger.warning("No LLM API key found — using in-memory fallback")
                return
            
            self.embeddings = OpenAIEmbeddings()
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )
            self._initialized = True
            logger.info(f"✅ ChromaDB initialized at {self.persist_dir}")
            
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            self.vectorstore = None
    
    def add_event(self, event_type: str, data: Dict[str, Any], summary: str = "") -> bool:
        """Store an event in the knowledge base."""
        doc = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "summary": summary or f"Event {event_type}",
        }
        text = json.dumps(doc, default=str)
        
        if self.vectorstore:
            try:
                self.vectorstore.add_texts(
                    texts=[text],
                    metadatas=[{"type": event_type, "timestamp": doc["timestamp"]}],
                )
                return True
            except Exception as e:
                logger.error(f"Vector store add failed: {e}")
        
        # Fallback: in-memory
        self._fallback_memory.append(doc)
        if len(self._fallback_memory) > 1000:
            self._fallback_memory = self._fallback_memory[-500:]
        return True
    
    def query(self, question: str, k: int = 5) -> List[Dict[str, Any]]:
        """Query knowledge base for relevant events."""
        if self.vectorstore:
            try:
                results = self.vectorstore.similarity_search(question, k=k)
                return [
                    {
                        "content": r.page_content,
                        "metadata": r.metadata,
                    }
                    for r in results
                ]
            except Exception as e:
                logger.error(f"Vector query failed: {e}")
        
        # Fallback: simple keyword search in memory
        question_lower = question.lower()
        matches = []
        for doc in reversed(self._fallback_memory):
            text = json.dumps(doc, default=str).lower()
            if any(word in text for word in question_lower.split()):
                matches.append(doc)
                if len(matches) >= k:
                    break
        return matches
    
    def get_recent_events(self, event_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events from memory."""
        events = self._fallback_memory
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        return events[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base stats."""
        return {
            "initialized": self._initialized,
            "vectorstore": self.vectorstore is not None,
            "memory_size": len(self._fallback_memory),
            "persist_dir": self.persist_dir,
        }
