"""
BenX Memory Engine - Persistent user facts + smart recall
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryEngine:
    def __init__(self, memory_file: Path):
        self.memory_file = memory_file
        self.facts_file = memory_file.parent / "user_facts.json"
        self.short_term = []
        self.long_term = defaultdict(list)
        self.facts = {}
        self.load_memory()

    def load_memory(self):
        try:
            if self.memory_file.exists():
                data = json.loads(self.memory_file.read_text())
                self.short_term = data.get("short_term", [])[-100:]
                self.long_term = defaultdict(list, data.get("long_term", {}))
        except Exception as e:
            logger.error(f"Memory load failed: {e}")
        try:
            if self.facts_file.exists():
                self.facts = json.loads(self.facts_file.read_text())
        except Exception:
            self.facts = {}

    def save_memory(self):
        try:
            self.memory_file.write_text(json.dumps({
                "short_term": self.short_term[-100:],
                "long_term": dict(self.long_term),
            }, indent=2))
        except Exception as e:
            logger.error(f"Memory save failed: {e}")

    def save_facts(self):
        try:
            self.facts_file.write_text(json.dumps(self.facts, indent=2))
        except Exception as e:
            logger.error(f"Facts save failed: {e}")

    def remember(self, user_input: str, response: str, category: str = "general"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": response,
            "category": category
        }
        self.short_term.append(entry)
        self.long_term[category].append(entry)
        # Auto-extract facts from conversation
        self._auto_extract_facts(user_input)
        self.save_memory()

    def _auto_extract_facts(self, text: str):
        """Auto-detect user facts from natural language."""
        import re
        patterns = [
            (r"my name is (\w+)", "user_name"),
            (r"i(?:'m| am) (\w+)", "user_name"),
            (r"call me (\w+)", "user_name"),
            (r"i(?:'m| am) a[n]? ([\w\s]+)", "user_role"),
            (r"i work (?:at|for|in) ([\w\s]+)", "workplace"),
            (r"i(?:'m| am) (?:from|in|at) ([\w\s]+)", "location"),
            (r"i prefer ([\w\s]+)", "preference"),
            (r"i use ([\w\s]+) for", "tool_preference"),
            (r"my (?:email|mail) is ([\w@.]+)", "email"),
            (r"my project is ([\w\s/~.]+)", "current_project"),
        ]
        t = text.lower()
        for pattern, key in patterns:
            m = re.search(pattern, t)
            if m:
                val = m.group(1).strip()
                if len(val) > 1 and val not in ("a", "an", "the"):
                    self.facts[key] = val
                    self.save_facts()

    def learn_fact(self, key: str, value: str):
        self.facts[key.lower().strip()] = value
        self.save_facts()

    def get_fact(self, key: str) -> Optional[str]:
        return self.facts.get(key.lower().strip())

    def recall(self, query: str, limit: int = 5):
        q = query.lower()
        return [
            m for m in reversed(self.short_term)
            if q in m.get("user", "").lower() or q in m.get("assistant", "").lower()
        ][:limit]

    def get_user_facts_summary(self) -> str:
        if not self.facts:
            return ""
        lines = ["Known about user:"]
        for k, v in self.facts.items():
            lines.append(f"  - {k.replace('_', ' ')}: {v}")
        return "\n".join(lines)

    def get_context_summary(self) -> str:
        if not self.short_term:
            return ""
        recent = self.short_term[-3:]
        lines = ["Recent context:"]
        for m in recent:
            lines.append(f"  - {m['user'][:60]}")
        return "\n".join(lines)
