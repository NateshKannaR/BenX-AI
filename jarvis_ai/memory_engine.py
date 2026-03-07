"""
Advanced Memory Engine - Context-aware long-term memory
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryEngine:
    """Advanced memory system with context awareness"""
    
    def __init__(self, memory_file: Path):
        self.memory_file = memory_file
        self.short_term = []  # Last 50 interactions
        self.long_term = defaultdict(list)  # Categorized memories
        self.facts = {}  # User facts (name, preferences, etc.)
        self.load_memory()
    
    def load_memory(self):
        """Load memory from disk"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.short_term = data.get('short_term', [])[-50:]
                    self.long_term = defaultdict(list, data.get('long_term', {}))
                    self.facts = data.get('facts', {})
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
    
    def save_memory(self):
        """Save memory to disk"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump({
                    'short_term': self.short_term[-50:],
                    'long_term': dict(self.long_term),
                    'facts': self.facts
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def remember(self, user_input: str, response: str, category: str = 'general'):
        """Store interaction in memory"""
        memory = {
            'timestamp': datetime.now().isoformat(),
            'user': user_input,
            'assistant': response,
            'category': category
        }
        self.short_term.append(memory)
        self.long_term[category].append(memory)
        self.save_memory()
    
    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall relevant memories"""
        query_lower = query.lower()
        relevant = []
        
        for memory in reversed(self.short_term):
            if query_lower in memory['user'].lower() or query_lower in memory['assistant'].lower():
                relevant.append(memory)
                if len(relevant) >= limit:
                    break
        
        return relevant
    
    def learn_fact(self, key: str, value: str):
        """Learn a fact about the user"""
        self.facts[key] = {
            'value': value,
            'learned_at': datetime.now().isoformat()
        }
        self.save_memory()
    
    def get_fact(self, key: str) -> Optional[str]:
        """Retrieve a learned fact"""
        fact = self.facts.get(key)
        return fact['value'] if fact else None
    
    def get_context_summary(self) -> str:
        """Get summary of recent context"""
        if not self.short_term:
            return "No recent context"
        
        recent = self.short_term[-5:]
        summary = "Recent context:\n"
        for mem in recent:
            summary += f"- User: {mem['user'][:50]}...\n"
        
        return summary
