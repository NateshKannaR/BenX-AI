"""
Learning Engine - Self-improvement system that learns from failures and corrections
"""
import json
import re
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

class LearningEngine:
    """Self-improvement system that learns from failures and corrections"""
    
    def __init__(self, ai_engine):
        self.ai_engine = ai_engine
        self.learned_patterns = {}
        self.corrections = []
        self.load_learning()
    
    def load_learning(self):
        """Load learned patterns and corrections"""
        try:
            if Config.LEARNING_FILE.exists():
                with open(Config.LEARNING_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learned_patterns = self._sanitize_patterns(data.get("patterns", {}))
                    self.corrections = data.get("corrections", [])[-50:]  # Keep last 50
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")
            self.learned_patterns = {}
            self.corrections = []
    
    def save_learning(self):
        """Save learned patterns and corrections"""
        try:
            with open(Config.LEARNING_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "patterns": self.learned_patterns,
                    "corrections": self.corrections[-50:],
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save learning data: {e}")

    def _is_valid_command_json(self, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        stripped = text.strip()
        if not stripped.startswith("{"):
            return False
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return False
        return isinstance(obj, dict) and isinstance(obj.get("command"), str) and bool(obj.get("command"))

    def _sanitize_patterns(self, patterns: dict) -> dict:
        sanitized = {}
        for key, value in (patterns or {}).items():
            if not isinstance(value, dict):
                continue
            candidate = value.get("correct_command")
            if self._is_valid_command_json(candidate):
                sanitized[key] = value
            else:
                logger.info(f"Discarding invalid learned pattern for: {key}")
        return sanitized
    
    def learn_from_failure(self, user_input: str, command: str, result: str, error: str = None):
        """Learn from a failed command execution or user correction"""
        is_correction = any(word in user_input.lower() for word in 
                          ["no", "wrong", "incorrect", "instead", "should", "correction", "fix", "improve"])
        
        if "❌" not in result and not error and not is_correction:
            return
        
        try:
            system_prompt = """You are BenX's self-improvement analyzer. When a command fails, analyze why and suggest how to fix it.

Analyze:
1. What went wrong?
2. Why did it fail?
3. What should have been done instead?
4. How can this be prevented in the future?

Return a JSON object with: {"problem": "...", "solution": "...", "pattern": "..."}"""

            correction_type = "User Correction" if is_correction else "Command Failure"
            
            analysis_prompt = f"""{correction_type} Analysis:

User Input: "{user_input}"
Command Attempted: "{command}"
Result: "{result}"
Error: "{error if error else 'N/A'}"

Analyze what went wrong and what the correct approach should be. Extract:
1. The problem (what was wrong)
2. The solution (what should be done instead)
3. A pattern to recognize this situation in the future

Return JSON with problem, solution, and pattern."""

            analysis = self.ai_engine.query_groq(system_prompt, analysis_prompt)
            
            json_match = re.search(r'\{[^}]+\}', analysis)
            if json_match:
                try:
                    learned = json.loads(json_match.group(0))
                    correction = {
                        "timestamp": datetime.now().isoformat(),
                        "user_input": user_input,
                        "command": command,
                        "result": result,
                        "error": error,
                        "problem": learned.get("problem", ""),
                        "solution": learned.get("solution", ""),
                        "pattern": learned.get("pattern", "")
                    }
                    self.corrections.append(correction)
                    
                    pattern = learned.get("pattern", "")
                    solution = learned.get("solution", "")
                    if pattern and self._is_valid_command_json(solution):
                        self.learned_patterns[user_input.lower()] = {
                            "correct_command": solution,
                            "pattern": pattern,
                            "learned_at": datetime.now().isoformat()
                        }
                    elif pattern:
                        logger.info(f"Skipping non-command learning output for: {user_input}")
                    
                    self.save_learning()
                    logger.info(f"Learned from failure: {user_input} -> {learned.get('solution', '')}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Learning analysis failed: {e}")
    
    def apply_learned_pattern(self, user_input: str) -> Optional[str]:
        """Apply learned patterns to improve command interpretation"""
        user_lower = user_input.lower()
        
        if user_lower in self.learned_patterns:
            pattern = self.learned_patterns[user_lower]
            logger.info(f"Applying learned pattern: {user_input}")
            corrected = pattern.get("correct_command", None)
            return corrected if self._is_valid_command_json(corrected) else None
        
        for pattern_key, pattern_data in self.learned_patterns.items():
            if pattern_key in user_lower or user_lower in pattern_key:
                logger.info(f"Applying learned pattern (partial): {user_input}")
                corrected = pattern_data.get("correct_command", None)
                return corrected if self._is_valid_command_json(corrected) else None
        
        return None
    
    def self_reflect(self, user_input: str, command: str, result: str):
        """Self-reflect on execution and improve"""
        if "❌" in result or "failed" in result.lower() or "error" in result.lower():
            self.learn_from_failure(user_input, command, result)
            
            corrected = self.apply_learned_pattern(user_input)
            if corrected:
                logger.info(f"Auto-correcting based on learned pattern: {corrected}")
                return corrected
        
        return None
    
    def get_improvement_suggestions(self) -> str:
        """Get suggestions for improvement based on learned patterns"""
        if not self.corrections:
            return "No corrections recorded yet."
        
        recent = self.corrections[-5:]
        suggestions = []
        for corr in recent:
            if corr.get("solution"):
                suggestions.append(f"- {corr['user_input']}: {corr['solution']}")
        
        return "\n".join(suggestions) if suggestions else "No suggestions available."










