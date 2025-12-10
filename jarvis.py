#!/usr/bin/env python3
"""
Jarvis Enhanced - Advanced AI Assistant with Modal GUI
A comprehensive AI-powered assistant with system integration, voice commands, and advanced modal interface
"""

import os
import sys
import json
import logging
import shlex
import subprocess
import time
import psutil
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import threading
import signal
import queue
import re

# GUI imports
GUI_AVAILABLE = False
tk = None
ttk = None
scrolledtext = None
messagebox = None

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    # Test if tkinter actually works (not just imported)
    test_root = tk.Tk()
    test_root.withdraw()  # Hide test window
    test_root.destroy()
    GUI_AVAILABLE = True
except ImportError as e:
    GUI_AVAILABLE = False
    print(f"⚠️  Warning: tkinter not available. GUI features disabled.")
    print(f"   Error: {str(e)}")
    print(f"   To enable GUI, install: sudo pacman -S tk (Arch Linux)")
    print(f"   Or run in CLI mode: python3 jarvis.py --no-gui")
except Exception as e:
    GUI_AVAILABLE = False
    print(f"⚠️  Warning: tkinter not available. GUI features disabled.")
    print(f"   Error: {str(e)}")
    print(f"   To enable GUI, install: sudo pacman -S tk (Arch Linux)")

# Voice imports (optional)
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# OCR and Screen Understanding imports (optional)
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Automation imports (optional)
try:
    import pyautogui
    AUTOMATION_AVAILABLE = True
    pyautogui.FAILSAFE = True  # Enable failsafe (move mouse to corner to abort)
    pyautogui.PAUSE = 0.5  # Small pause between actions
except ImportError:
    AUTOMATION_AVAILABLE = False

# ==================== CONFIGURATION ====================

class Config:
    # API Configuration
    GROQ_KEY = ""
    
    # Models with priority order (using best models for understanding)
    MODELS = [
        "llama-3.3-70b-specdec",  # Best for reasoning
        "llama-3.1-70b-versatile",  # Best for understanding
        "llama-3.1-8b-instant",  # Fast fallback
        "gemma2-9b-it",
        "qwen2.5-7b"
    ]
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    API_TIMEOUT = 45  # Increased for complex reasoning
    
    # Paths
    HOME = Path.home()
    JARVIS_DIR = HOME / ".jarvis"
    LOG_FILE = JARVIS_DIR / "jarvis.log"
    HISTORY_FILE = JARVIS_DIR / "history.txt"
    CONVERSATION_FILE = JARVIS_DIR / "conversation.json"
    SCREENSHOT_PATH = "/tmp/jarvis_screen.png"
    SCREEN_ANALYSIS_PATH = JARVIS_DIR / "screen_analysis.json"
    LEARNING_FILE = JARVIS_DIR / "learning.json"
    
    # Create directories
    JARVIS_DIR.mkdir(exist_ok=True)
    
    # System tools with fallbacks
    TOOLS = {
        "screenshot": ["grim", "maim", "scrot", "gnome-screenshot"],
        "volume": ["pamixer", "amixer", "pactl"],
        "brightness": ["brightnessctl", "xbacklight", "light"],
        "network": ["nmcli", "iwconfig"],
        "media": ["playerctl", "mpc"],
        "file_manager": ["xdg-open", "nautilus", "thunar", "dolphin"],
        "window_manager": ["hyprctl", "wmctrl", "xdotool"]
    }
    
    # Limits
    MAX_VOLUME = 100
    MIN_VOLUME = 0
    MAX_BRIGHTNESS = 100
    MIN_BRIGHTNESS = 0
    
    # GUI Settings
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 700
    THEME_COLOR = "#1e1e2e"  # Dark theme
    ACCENT_COLOR = "#89b4fa"
    TEXT_COLOR = "#cdd6f4"
    BG_COLOR = "#11111b"

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== UTILITIES ====================

def run_cmd(cmd: str, shell: bool = False, timeout: int = 30) -> Tuple[bool, str]:
    """Execute command safely with timeout"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        
        output = result.stdout.strip() if result.stdout else ""
        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Command failed"
            return False, error
        return True, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"

def find_tool(tools: List[str]) -> Optional[str]:
    """Find first available tool from list"""
    for tool in tools:
        success, _ = run_cmd(f"which {tool}")
        if success:
            return tool
    return None

def safe_open_app(app: str) -> bool:
    """Safely open application in background"""
    try:
        env = os.environ.copy()
        process = subprocess.Popen(
            [app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, start_new_session=True, env=env
        )
        time.sleep(0.2)
        return process.poll() is None
    except:
        return False

# ==================== LEARNING ENGINE ====================

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
                    self.learned_patterns = data.get("patterns", {})
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
    
    def learn_from_failure(self, user_input: str, command: str, result: str, error: str = None):
        """Learn from a failed command execution or user correction"""
        # Always learn if user explicitly corrects, even if no error
        is_correction = any(word in user_input.lower() for word in ["no", "wrong", "incorrect", "instead", "should", "correction", "fix", "improve"])
        
        if "❌" not in result and not error and not is_correction:
            return  # Not a failure or correction
        
        # Use Groq to analyze what went wrong and how to fix it
        try:
            system_prompt = """You are Jarvis's self-improvement analyzer. When a command fails, analyze why and suggest how to fix it.

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
            
            # Try to extract JSON
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
                    
                    # Extract pattern for future use
                    pattern = learned.get("pattern", "")
                    if pattern:
                        self.learned_patterns[user_input.lower()] = {
                            "correct_command": learned.get("solution", ""),
                            "pattern": pattern,
                            "learned_at": datetime.now().isoformat()
                        }
                    
                    self.save_learning()
                    logger.info(f"Learned from failure: {user_input} -> {learned.get('solution', '')}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Learning analysis failed: {e}")
    
    def apply_learned_pattern(self, user_input: str) -> Optional[str]:
        """Apply learned patterns to improve command interpretation"""
        user_lower = user_input.lower()
        
        # Check exact match
        if user_lower in self.learned_patterns:
            pattern = self.learned_patterns[user_lower]
            logger.info(f"Applying learned pattern: {user_input}")
            return pattern.get("correct_command", None)
        
        # Check partial matches
        for pattern_key, pattern_data in self.learned_patterns.items():
            if pattern_key in user_lower or user_lower in pattern_key:
                logger.info(f"Applying learned pattern (partial): {user_input}")
                return pattern_data.get("correct_command", None)
        
        return None
    
    def self_reflect(self, user_input: str, command: str, result: str):
        """Self-reflect on execution and improve"""
        # If result indicates failure, learn from it
        if "❌" in result or "failed" in result.lower() or "error" in result.lower():
            self.learn_from_failure(user_input, command, result)
            
            # Try to auto-correct using learned patterns
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

# ==================== AI INTEGRATION ====================

class AIEngine:
    def __init__(self):
        self.conversation_history = []
        self.load_conversation_history()
        self.learning_engine = LearningEngine(self)
    
    def load_conversation_history(self):
        """Load conversation history from file"""
        try:
            if Config.CONVERSATION_FILE.exists():
                with open(Config.CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = data.get("messages", [])[-20:]  # Keep last 20 messages
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
            self.conversation_history = []
    
    def save_conversation_history(self):
        """Save conversation history to file"""
        try:
            with open(Config.CONVERSATION_FILE, 'w', encoding='utf-8') as f:
                json.dump({"messages": self.conversation_history[-50:]}, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save conversation history: {e}")
    
    @staticmethod
    def query_groq(system_prompt: str, user_prompt: str, model_preference: Optional[str] = None, 
                   conversation_context: List[Dict] = None) -> str:
        """Query Groq API with fallback support and conversation context"""
        headers = {
            "Authorization": f"Bearer {Config.GROQ_KEY}",
            "Content-Type": "application/json"
        }
        
        models = Config.MODELS.copy()
        if model_preference and model_preference in models:
            models.remove(model_preference)
            models.insert(0, model_preference)
        
        # Build messages with conversation context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_context:
            messages.extend(conversation_context[-10:])  # Last 10 messages for context
        
        # Add current user prompt
        messages.append({"role": "user", "content": user_prompt})
        
        for model in models:
            try:
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.8,  # More creative and understanding
                    "max_tokens": 4000,  # More detailed responses
                    "top_p": 0.9,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.1
                }
                
                response = requests.post(Config.API_URL, headers=headers, json=data, timeout=Config.API_TIMEOUT)
                response.raise_for_status()
                
                result = response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"]
                    
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        
        return "❌ All AI models failed. Check your connection."
    
    def chat(self, user_input: str, system_context: str = None) -> str:
        """Chat with AI using advanced conversation context and reasoning"""
        
        # Get system state for context
        system_state = self._get_system_context()
        
        system_prompt = f"""You are Jarvis, an ultra-advanced AI personal assistant with complete control over the user's Linux system.

PERSONALITY & COMMUNICATION:
- Be extremely intelligent, helpful, and understanding
- Understand context deeply - remember previous conversations and adapt
- Be conversational, natural, and friendly but professional
- Show personality - be witty when appropriate, empathetic when needed
- Think step-by-step before responding to complex queries
- If you're unsure, ask clarifying questions rather than guessing

CAPABILITIES:
You have complete system control including:
- Applications (open, manage, monitor)
- System settings (volume, brightness, power)
- File operations (create, read, write, search, manage)
- Process management (monitor, kill, find)
- Network management (WiFi, connections)
- Media control (music, videos)
- System monitoring (CPU, memory, disk, battery)
- Package management (install, update)
- And much more...

CURRENT SYSTEM STATE:
{system_state}

CONTEXT AWARENESS:
- Remember what the user has asked before
- Understand implicit requests (e.g., "make it louder" means increase volume)
- Recognize follow-up questions and references to previous topics
- Understand user intent even if phrasing is unclear
- Be proactive - suggest helpful actions when relevant

REASONING APPROACH:
1. Analyze the user's request deeply
2. Consider context from conversation history
3. Determine if it's a question, command, or conversation
4. If it's a command, think about what they really want to achieve
5. Provide intelligent, helpful responses

{system_context if system_context else ""}

Remember: You're not just executing commands - you're understanding the user's needs and helping them achieve their goals intelligently."""
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Get response with extended context
        response = self.query_groq(
            system_prompt, 
            user_input,
            conversation_context=self.conversation_history
        )
        
        # Add response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        self.save_conversation_history()
        
        return response
    
    def _get_system_context(self) -> str:
        """Get current system state for context"""
        try:
            context_parts = []
            
            # Battery
            try:
                battery = psutil.sensors_battery()
                if battery:
                    context_parts.append(f"Battery: {battery.percent}% ({'Charging' if battery.power_plugged else 'Discharging'})")
            except:
                pass
            
            # CPU/Memory
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                context_parts.append(f"CPU: {cpu:.1f}%, Memory: {memory.percent:.1f}%")
            except:
                pass
            
            # Current time
            context_parts.append(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            
            return "\n".join(context_parts) if context_parts else "System state: Normal"
        except:
            return "System state: Available"
    
    @staticmethod
    def _fallback_command_match(text: str, context: str = "") -> str:
        """Fallback command matching when AI fails"""
        text_lower = text.lower()
        
        # Direct command patterns
        if "create" in text_lower and "pdf" in text_lower:
            # Extract path
            path_match = re.search(r'(?:at|in|to|with)\s+([^\s]+)', text_lower)
            path = path_match.group(1) if path_match else "~/Downloads/output.pdf"
            if not path.endswith('.pdf'):
                path = os.path.join(path, "output.pdf") if os.path.isdir(os.path.expanduser(path)) else f"{path}.pdf"
            
            # Try to find data file in context
            data_file_match = re.search(r'([/\\~][^\s\n]+\.(txt|json))', context)
            content = ""
            if data_file_match:
                data_file = data_file_match.group(1)
                try:
                    with open(os.path.expanduser(data_file), 'r') as f:
                        content = f.read()
                except:
                    content = "Data from file"
            else:
                # Look for JSON or data in context
                json_match = re.search(r'\{[^}]+\}', context)
                if json_match:
                    content = json_match.group(0)
                else:
                    content = "Mock data"
            
            return json.dumps({"command": "create_pdf", "content": content, "path": path})
        
        if "open" in text_lower and ("that" in text_lower or "it" in text_lower or "file" in text_lower):
            # Try to find file in context
            file_match = re.search(r'([/\\~][^\s\n]+\.(pdf|txt|doc|docx))', context)
            if file_match:
                return json.dumps({"command": "open_file", "path": file_match.group(1)})
            return json.dumps({"command": "open_folder", "path": "~/Downloads"})
        
        if "create" in text_lower and "file" in text_lower:
            path_match = re.search(r'(?:at|in|to)\s+([^\s]+)', text_lower)
            path = path_match.group(1) if path_match else "~/Downloads/file.txt"
            return json.dumps({"command": "create_file", "path": path, "text": "Mock data"})
        
        # Default: return none to trigger chat mode
        return json.dumps({"command": "none"})
    
    @staticmethod
    def interpret_command(text: str, conversation_context: List[Dict] = None, learning_engine=None) -> str:
        """Convert natural language to JSON command with advanced understanding"""
        # Check learned patterns first
        if learning_engine:
            learned = learning_engine.apply_learned_pattern(text)
            if learned:
                logger.info(f"Using learned pattern for command interpretation")
                return learned
        
        system_prompt = """You are Jarvis AI's command interpreter. Your job is to understand user intent and convert it to precise JSON commands.

THINKING PROCESS:
1. Analyze the user's intent deeply - what do they REALLY want?
2. Consider context from conversation (e.g., "make it louder" after volume discussion)
3. Extract all relevant parameters (numbers, paths, app names, etc.)
4. Choose the most appropriate command
5. Handle variations and synonyms intelligently

OUTPUT FORMAT:
Output ONLY valid JSON in this exact format:
{"command": "action_name", "app": "app_name", "value": number, "path": "file_path", "query": "search_term", "text": "content", "process": "process_name", "dest": "destination_path", "package": "package_name", "city": "city_name", "url": "url", "ssid": "wifi_name"}

SUPPORTED COMMANDS (with intelligent synonyms):
APPLICATIONS:
- open_app: "open", "launch", "start", "run" + app name
- list_apps: "list apps", "show running", "what's open"

AUDIO:
- set_volume: "volume X", "set volume to X", "make it X percent"
- increase_volume: "louder", "turn up", "increase volume", "volume up"
- decrease_volume: "quieter", "turn down", "decrease volume", "volume down"
- mute_volume: "mute", "silence", "turn off sound"
- get_volume: "what's the volume", "current volume"

DISPLAY:
- set_brightness: "brightness X", "set brightness to X"
- increase_brightness: "brighter", "increase brightness", "brighten"
- decrease_brightness: "dimmer", "decrease brightness", "darken"

FILES:
- open_folder: "open folder", "show directory", "browse"
- list_files: "list files", "show files", "what's in", "contents of"
- search_files: "find file", "search for", "look for file"
- read_file: "read", "show", "display", "open file"
- create_file: "create file", "make file", "new file", "write file"
- write_file: "write to", "save to", "update file"
- delete_file: "delete", "remove", "erase"
- create_directory: "create folder", "make directory", "mkdir"
- move_file: "move", "relocate"
- copy_file: "copy", "duplicate"
- create_pdf: "create pdf", "make pdf", "generate pdf", "pdf with"
- open_file: "open file", "open that file", "open that", "open it"

PROCESSES:
- kill_process: "kill", "stop", "close", "terminate" + process name
- list_processes: "list processes", "show processes", "what's running"
- find_process: "find process", "search process"

SYSTEM:
- lock_screen: "lock", "lock screen"
- shutdown: "shutdown", "turn off", "power off"
- restart: "restart", "reboot", "reset"
- suspend: "suspend", "sleep", "hibernate"
- battery: "battery", "power", "charge status"
- system_info: "system info", "system status", "system stats"
- disk_usage: "disk usage", "disk space", "storage"

NETWORK:
- connect_wifi: "connect to wifi", "join network"
- list_wifi: "list wifi", "show networks", "available wifi"
- network_status: "network status", "connection status"

MEDIA:
- play_music: "play", "resume"
- pause_music: "pause", "stop music"
- next_track: "next", "skip"
- previous_track: "previous", "back"
- get_media_info: "what's playing", "current song"

UTILITIES:
- get_clipboard: "clipboard", "what's copied"
- set_clipboard: "copy to clipboard", "save to clipboard"
- get_weather: "weather", "forecast"
- open_url: "open website", "browse to", "go to"
- take_screenshot: "screenshot", "capture screen", "snapshot"
- analyze_screen: "analyze screen", "what's on screen", "screen analysis"
- read_screen_text: "read screen", "extract text", "OCR screen"
- automate: "automate", "do this", "perform automation", "execute automation"

PACKAGES:
- install_package: "install", "add package" (system packages)
- install_python_package: "install python package", "pip install", "install with pip" (Python packages)
- update_system: "update", "upgrade system"
- check_updates: "check updates", "available updates"

INTELLIGENT UNDERSTANDING:
- "make it louder" → increase_volume
- "turn it up" → increase_volume (context-dependent)
- "open my documents" → open_folder with path expansion
- "kill that app" → kill_process (if recent context mentions app)
- "what's running?" → list_processes
- "create a note" → create_file with sensible default name
- "show me files" → list_files
- "search for python files" → search_files with query
- "automate opening chrome and searching for python" → automate with instruction
- "analyze what's on my screen" → analyze_screen
- "read text from screen" → read_screen_text
- "install that" → install_python_package (extract package names from recent error messages)
- "install pytesseract Pillow opencv-python" → install_python_package with all packages
- "create pdf" or "create a pdf" → create_pdf command
- "open that file" or "open that" → open_file (extract file path from recent context)
- If user says "install" after an error mentioning packages, extract package names from error
- If user says "open that" after mentioning a file, extract file path from context

EXAMPLES:
"open chrome" → {"command":"open_app","app":"chrome"}
"volume 80" → {"command":"set_volume","value":80}
"make it louder" → {"command":"increase_volume","value":10}
"create file notes.txt with my todo list" → {"command":"create_file","path":"notes.txt","text":"my todo list"}
"kill firefox" → {"command":"kill_process","process":"firefox"}
"what's the weather in New York?" → {"command":"none"} (this is a question, not a command)
"open my downloads folder" → {"command":"open_folder","path":"~/Downloads"}

AUTOMATION COMMANDS:
- automate: Use when user wants to automate a task. Include full instruction in "instruction" field.
  Examples:
  - "automate opening chrome and searching for python" → {"command":"automate","instruction":"open chrome, search for python"}
  - "do this: click the button, type hello, press enter" → {"command":"automate","instruction":"click the button, type hello, press enter"}

CONTEXT AWARENESS:
- If user says "install that" or "install it", look at recent conversation/errors for package names
- Extract Python package names from error messages:
  * "Install: pip install pytesseract Pillow opencv-python" → extract "pytesseract Pillow opencv-python"
  * "pip install X Y Z" → extract "X Y Z"
  * "❌ OCR not available. Install: pip install pytesseract Pillow" → extract "pytesseract Pillow"
- Understand "install" can mean Python packages if context suggests it (error messages, "pip", "python package", etc.)
- When user says "install" after an error mentioning packages, use install_python_package command

COMMAND VS QUESTION:
- COMMANDS (execute actions): "create", "open", "install", "delete", "move", "copy", "automate", "set", "increase", "decrease", "kill", "play", "pause"
- QUESTIONS (conversation): "what", "how", "why", "when", "where", "explain", "tell me about", "describe"
- If user says "create X", "open Y", "install Z" → these are COMMANDS, not questions
- Be AGGRESSIVE about recognizing commands - prefer action over conversation
- Only return {"command":"none"} if it's CLEARLY a question with no action intent

IMPORTANT:
- If it's clearly a QUESTION or CONVERSATION (not a command), return: {"command":"none"}
- Extract numbers intelligently ("eighty" = 80, "half" = 50)
- Handle paths with ~ expansion
- Be smart about app name variations (chrome/chromium, code/vscode)
- If unsure about a parameter, use reasonable defaults
- For automation requests, capture the full instruction in the "instruction" field
- For "install that/it", extract package names from recent error messages or conversation context
- When user says "create pdf with that data" → extract data from context and create PDF"""
        
        # Add recent conversation context for better understanding
        context_messages = []
        if conversation_context:
            context_messages = conversation_context[-5:]  # Last 5 messages for context
        
        # Enhanced context: Extract packages/files from recent context
        enhanced_prompt = text
        recent_context = "\n".join([str(msg.get("content", "")) for msg in context_messages[-3:]])
        
        if "install" in text.lower():
            # Extract packages from error messages
            patterns = [
                r'Install:?\s*(?:pip install\s+)?([^\n]+?)(?:\n|$)',  # "Install: pip install X Y Z"
                r'pip install\s+([^\n]+?)(?:\n|$)',  # "pip install X Y Z"
                r'Install\s+([^\n]+?)(?:\n|$)',  # "Install X Y Z"
            ]
            
            packages_found = []
            for pattern in patterns:
                matches = re.findall(pattern, recent_context, re.IGNORECASE)
                for match in matches:
                    match = re.sub(r'pip install\s*', '', match, flags=re.IGNORECASE)
                    pkgs = [p.strip() for p in re.split(r'[,\s\n]+', match) if p.strip() and p.lower() not in ['pip', 'install']]
                    packages_found.extend(pkgs)
            
            if packages_found:
                packages_str = " ".join(set(packages_found))
                enhanced_prompt = f"{text} (packages to install: {packages_str})"
        
        if "open" in text.lower() and ("that" in text.lower() or "it" in text.lower()):
            # Extract file paths from recent context
            file_patterns = [
                r'([/\\~][^\s\n]+\.(pdf|txt|doc|docx|png|jpg|jpeg|gif|mp4|mp3|zip|tar|gz))',  # File paths
                r'File path[:\s]+([^\n]+)',  # "File path: /path/to/file"
                r'Created[:\s]+([^\n]+\.(pdf|txt|doc))',  # "Created: file.pdf"
                r'([^\s]+\.pdf)',  # Just .pdf files
            ]
            
            files_found = []
            for pattern in file_patterns:
                matches = re.findall(pattern, recent_context, re.IGNORECASE)
                for match in matches:
                    file_path = match[0] if isinstance(match, tuple) else match
                    if os.path.exists(os.path.expanduser(file_path)):
                        files_found.append(file_path)
            
            if files_found:
                file_path = files_found[-1]  # Use most recent
                enhanced_prompt = f"{text} (file to open: {file_path})"
        
        try:
            try:
            return AIEngine.query_groq(system_prompt, enhanced_prompt, conversation_context=context_messages)
        except Exception as e:
            logger.error(f"Command interpretation failed: {e}")
            # Fallback: Try direct command matching
            return AIEngine._fallback_command_match(text, recent_context)
        except Exception as e:
            logger.error(f"Command interpretation failed: {e}")
            # Fallback: Try direct command matching
            return AIEngine._fallback_command_match(text, recent_context)

# ==================== COMMAND ENGINE ====================

class CommandEngine:
    
    # Application Management
    @staticmethod
    def open_app(app: str) -> str:
        if not app:
            return "❌ No application specified"
        
        app_mappings = {
            "chrome": "chromium", "firefox": "firefox", "code": "code",
            "terminal": os.getenv("TERMINAL", "alacritty"),
            "calculator": "gnome-calculator", "files": "nautilus",
            "editor": os.getenv("EDITOR", "nano"), "browser": "firefox"
        }
        
        app_name = app_mappings.get(app.lower(), app)
        
        if safe_open_app(app_name):
            return f"✅ Opened {app_name}"
        
        # Try with xdg-open
        success, _ = run_cmd(f"xdg-open {shlex.quote(app_name)}")
        return f"✅ Opened {app_name}" if success else f"❌ Could not open {app}"
    
    @staticmethod
    def list_running_apps() -> str:
        try:
            apps = {}
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name not in apps:
                        apps[name] = proc.info['pid']
                except:
                    continue
            
            result = "📱 Running Applications:\n"
            for name, pid in sorted(list(apps.items())[:20]):
                result += f"  • {name} (PID: {pid})\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Audio Control
    @staticmethod
    def set_volume(level: int) -> str:
        level = max(Config.MIN_VOLUME, min(Config.MAX_VOLUME, level))
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --set-volume {level}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {level}%")
        elif tool == "pactl":
            success, _ = run_cmd(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
        else:
            return f"❌ Unsupported tool: {tool}"
        
        return f"✅ Volume set to {level}%" if success else "❌ Failed to set volume"
    
    @staticmethod
    def increase_volume(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --increase {amount}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {amount}%+")
        else:
            return "❌ Volume control failed"
        
        return f"✅ Volume increased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def decrease_volume(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --decrease {amount}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {amount}%-")
        else:
            return "❌ Volume control failed"
        
        return f"✅ Volume decreased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def mute_volume() -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        success, _ = run_cmd(f"{tool} --toggle-mute" if tool == "pamixer" else "amixer set Master toggle")
        return "✅ Volume toggled" if success else "❌ Failed"
    
    @staticmethod
    def get_volume() -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, output = run_cmd("pamixer --get-volume")
        else:
            success, output = run_cmd("amixer get Master | grep -oP '\\[\\K[0-9]+(?=%\\])' | head -1", shell=True)
        
        return f"🔊 Volume: {output}%" if success else "❌ Failed to get volume"
    
    # Brightness Control
    @staticmethod
    def set_brightness(level: int) -> str:
        level = max(Config.MIN_BRIGHTNESS, min(Config.MAX_BRIGHTNESS, level))
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set {level}%")
        elif tool == "light":
            success, _ = run_cmd(f"light -S {level}")
        elif tool == "xbacklight":
            success, _ = run_cmd(f"xbacklight -set {level}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness set to {level}%" if success else "❌ Failed"
    
    @staticmethod
    def increase_brightness(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set +{amount}%")
        elif tool == "light":
            success, _ = run_cmd(f"light -A {amount}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness increased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def decrease_brightness(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set {amount}%-")
        elif tool == "light":
            success, _ = run_cmd(f"light -U {amount}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness decreased by {amount}%" if success else "❌ Failed"
    
    # File Operations
    @staticmethod
    def open_folder(path: str) -> str:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"❌ Path does not exist: {path}"
        
        tool = find_tool(Config.TOOLS["file_manager"])
        if tool:
            success = safe_open_app(f"{tool} {shlex.quote(path)}")
        else:
            success, _ = run_cmd(f"xdg-open {shlex.quote(path)}")
        
        return f"✅ Opened {path}" if success else f"❌ Failed to open {path}"
    
    @staticmethod
    def list_files(path: str = ".") -> str:
        path = os.path.expanduser(path)
        try:
            files = list(Path(path).iterdir())
            if not files:
                return f"📁 Empty directory: {path}"
            
            result = f"📁 Files in {path}:\n"
            for item in sorted(files)[:30]:
                icon = "📁" if item.is_dir() else "📄"
                size = item.stat().st_size if item.is_file() else 0
                result += f"  {icon} {item.name} ({size} bytes)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def search_files(query: str, path: str = ".") -> str:
        if not query:
            return "❌ No search query"
        
        path = os.path.expanduser(path)
        try:
            matches = list(Path(path).rglob(f"*{query}*"))[:20]
            if not matches:
                return f"🔍 No files found matching '{query}'"
            
            result = f"🔍 Found {len(matches)} files:\n"
            for match in matches:
                result += f"  📄 {match}\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def read_file(path: str, lines: int = 50) -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
                preview = ''.join(content[:lines])
                
                result = f"📄 {path} ({len(content)} lines):\n"
                result += "─" * 50 + "\n" + preview
                if len(content) > lines:
                    result += f"\n... ({len(content) - lines} more lines)"
                return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_file(path: str, text: str = "") -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return f"✅ Created file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def write_file(path: str, text: str = "") -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return f"✅ Wrote to file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def delete_file(path: str) -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                return f"✅ Deleted directory: {path}"
            else:
                os.remove(path)
                return f"✅ Deleted file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_directory(path: str) -> str:
        if not path:
            return "❌ No path specified"
        
        path = os.path.expanduser(path)
        try:
            os.makedirs(path, exist_ok=True)
            return f"✅ Created directory: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def move_file(source: str, dest: str) -> str:
        if not source or not dest:
            return "❌ Source and destination required"
        
        source = os.path.expanduser(source)
        dest = os.path.expanduser(dest)
        try:
            import shutil
            shutil.move(source, dest)
            return f"✅ Moved {source} to {dest}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def copy_file(source: str, dest: str) -> str:
        if not source or not dest:
            return "❌ Source and destination required"
        
        source = os.path.expanduser(source)
        dest = os.path.expanduser(dest)
        try:
            import shutil
            shutil.copy2(source, dest)
            return f"✅ Copied {source} to {dest}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_pdf(content: str, output_path: str) -> str:
        """Create a PDF file from text content"""
        try:
            # Try reportlab first
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                
                output_path = os.path.expanduser(output_path)
                os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
                
                c = canvas.Canvas(output_path, pagesize=letter)
                width, height = letter
                
                # Split content into lines and write
                y = height - 50
                for line in content.split('\n'):
                    if y < 50:
                        c.showPage()
                        y = height - 50
                    c.drawString(50, y, line[:100])  # Limit line length
                    y -= 20
                
                c.save()
                return f"✅ Created PDF: {output_path}"
            except ImportError:
                # Fallback: Use weasyprint or fpdf
                try:
                    from weasyprint import HTML
                    html_content = f"<pre>{content}</pre>"
                    HTML(string=html_content).write_pdf(output_path)
                    return f"✅ Created PDF: {output_path}"
                except ImportError:
                    try:
                        from fpdf import FPDF
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", size=12)
                        for line in content.split('\n'):
                            pdf.cell(200, 10, txt=line[:100], ln=1)
                        pdf.output(output_path)
                        return f"✅ Created PDF: {output_path}"
                    except ImportError:
                        # Last resort: use system tools
                        temp_file = "/tmp/jarvis_temp.txt"
                        with open(temp_file, 'w') as f:
                            f.write(content)
                        success, _ = run_cmd(f"pandoc {temp_file} -o {output_path}", timeout=30)
                        if success:
                            return f"✅ Created PDF: {output_path}"
                        return "❌ PDF creation failed. Install: pip install reportlab (or weasyprint/fpdf/pandoc)"
        except Exception as e:
            return f"❌ PDF creation error: {str(e)}"
    
    # Process Management
    @staticmethod
    def kill_process(process_name: str) -> str:
        if not process_name:
            return "❌ No process specified"
        
        try:
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        proc.kill()
                        killed.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed:
                return f"✅ Killed: {', '.join(killed)}"
            return f"❌ Process '{process_name}' not found"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def list_processes() -> str:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc.info['cpu_percent'] = proc.cpu_percent(interval=0.1)
                    processes.append(proc.info)
                except:
                    continue
            
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            result = "🖥️ Top Processes:\n"
            for proc in processes[:15]:
                result += f"  • {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']:.1f}%, Mem: {proc['memory_percent']:.1f}%)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def find_process(query: str) -> str:
        if not query:
            return "❌ No query specified"
        
        try:
            matches = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if query.lower() in proc.info['name'].lower():
                        matches.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except:
                    continue
            
            if matches:
                result = f"🔍 Found {len(matches)} processes:\n"
                for match in matches[:10]:
                    result += f"  • {match}\n"
                return result
            return f"❌ No processes found matching '{query}'"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # System Control
    @staticmethod
    def lock_screen() -> str:
        success, _ = run_cmd("loginctl lock-session")
        return "✅ Screen locked" if success else "❌ Failed to lock screen"
    
    @staticmethod
    def shutdown() -> str:
        success, _ = run_cmd("shutdown now")
        return "✅ Shutting down..." if success else "❌ Failed to shutdown"
    
    @staticmethod
    def restart() -> str:
        success, _ = run_cmd("reboot")
        return "✅ Restarting..." if success else "❌ Failed to restart"
    
    @staticmethod
    def suspend() -> str:
        success, _ = run_cmd("systemctl suspend")
        return "✅ Suspending..." if success else "❌ Failed to suspend"
    
    @staticmethod
    def battery() -> str:
        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = "🔌 Charging" if battery.power_plugged else "🔋 Battery"
                time_left = f" ({battery.secsleft // 3600}h {(battery.secsleft % 3600) // 60}m)" if battery.secsleft > 0 else ""
                return f"{plugged}: {percent}%{time_left}"
            return "❌ Battery info not available"
        except:
            return "❌ Battery info not available"
    
    @staticmethod
    def system_info() -> str:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            result = "💻 System Information:\n"
            result += f"  CPU: {psutil.cpu_count()} cores, {cpu_percent:.1f}% usage\n"
            result += f"  Memory: {memory.percent:.1f}% used ({memory.used/1024**3:.1f}GB/{memory.total/1024**3:.1f}GB)\n"
            result += f"  Disk: {disk.percent:.1f}% used ({disk.used/1024**3:.1f}GB/{disk.total/1024**3:.1f}GB)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def disk_usage(path: str = "/") -> str:
        try:
            disk = psutil.disk_usage(path)
            result = f"💾 Disk Usage for {path}:\n"
            result += f"  Total: {disk.total/1024**3:.2f} GB\n"
            result += f"  Used: {disk.used/1024**3:.2f} GB ({disk.percent:.1f}%)\n"
            result += f"  Free: {disk.free/1024**3:.2f} GB\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Network
    @staticmethod
    def connect_wifi(ssid: str) -> str:
        if not ssid:
            return "❌ No SSID specified"
        success, _ = run_cmd(f"nmcli device wifi connect {shlex.quote(ssid)}")
        return f"✅ Connected to {ssid}" if success else f"❌ Failed to connect to {ssid}"
    
    @staticmethod
    def list_wifi() -> str:
        success, output = run_cmd("nmcli device wifi list")
        return f"📶 WiFi Networks:\n{output}" if success else "❌ Failed to list networks"
    
    @staticmethod
    def network_status() -> str:
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_io_counters()
            
            result = "🌐 Network Status:\n"
            result += f"  Bytes sent: {stats.bytes_sent / 1024**2:.2f} MB\n"
            result += f"  Bytes received: {stats.bytes_recv / 1024**2:.2f} MB\n"
            result += f"  Interfaces: {', '.join(interfaces.keys())}\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Media Control
    @staticmethod
    def play_music() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} play")
        return "✅ Playing music" if success else "❌ Failed to play"
    
    @staticmethod
    def pause_music() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} pause")
        return "✅ Music paused" if success else "❌ Failed to pause"
    
    @staticmethod
    def next_track() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} next")
        return "✅ Next track" if success else "❌ Failed"
    
    @staticmethod
    def previous_track() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} previous")
        return "✅ Previous track" if success else "❌ Failed"
    
    @staticmethod
    def get_media_info() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, output = run_cmd(f"{tool} metadata")
        return f"🎵 {output}" if success else "❌ Failed to get media info"
    
    # Utilities
    @staticmethod
    def get_clipboard() -> str:
        success, output = run_cmd("xclip -selection clipboard -o")
        return f"📋 Clipboard: {output[:200]}" if success else "❌ Failed to read clipboard"
    
    @staticmethod
    def set_clipboard(text: str) -> str:
        if not text:
            return "❌ No text specified"
        success, _ = run_cmd(f"echo {shlex.quote(text)} | xclip -selection clipboard", shell=True)
        return "✅ Clipboard updated" if success else "❌ Failed to update clipboard"
    
    @staticmethod
    def get_weather(city: str = "") -> str:
        if not city:
            success, city = run_cmd("curl -s ipinfo.io/city")
            city = city.strip() if success else "your location"
        
        success, output = run_cmd(f"curl -s 'wttr.in/{shlex.quote(city)}?format=3'")
        return f"🌤️ Weather: {output}" if success else "❌ Failed to get weather"
    
    @staticmethod
    def open_url(url: str) -> str:
        if not url:
            return "❌ No URL specified"
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
        return f"✅ Opened {url}" if success else f"❌ Failed to open {url}"
    
    @staticmethod
    def open_file(path: str) -> str:
        """Open a file with default application"""
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"❌ File does not exist: {path}"
        
        success, _ = run_cmd(f"xdg-open {shlex.quote(path)}")
        return f"✅ Opened {path}" if success else f"❌ Failed to open {path}"
    
    @staticmethod
    def take_screenshot() -> str:
        tool = find_tool(Config.TOOLS["screenshot"])
        if not tool:
            return "❌ No screenshot tool found"
        
        path = Config.SCREENSHOT_PATH
        success, _ = run_cmd(f"{tool} {path}")
        return f"✅ Screenshot saved to {path}" if success else "❌ Failed to take screenshot"
    
    @staticmethod
    def analyze_screen() -> str:
        """Take screenshot and analyze it with OCR and AI"""
        if not OCR_AVAILABLE:
            return "❌ OCR not available. Install: pip install pytesseract Pillow opencv-python"
        
        # Take screenshot first
        result = CommandEngine.take_screenshot()
        if "❌" in result:
            return result
        
        try:
            # Load and process image
            img = Image.open(Config.SCREENSHOT_PATH)
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(img)
            
            # Get screen dimensions
            screen_width, screen_height = pyautogui.size() if AUTOMATION_AVAILABLE else (1920, 1080)
            
            # Analyze with AI
            analysis = ScreenAnalyzer.analyze_with_ai(img, ocr_text, screen_width, screen_height)
            
            return f"📸 Screen Analysis:\n{analysis}"
        except Exception as e:
            return f"❌ Screen analysis error: {str(e)}"
    
    @staticmethod
    def read_screen_text() -> str:
        """Extract text from screen using OCR"""
        if not OCR_AVAILABLE:
            return "❌ OCR not available. Install: pip install pytesseract Pillow"
        
        # Take screenshot first
        result = CommandEngine.take_screenshot()
        if "❌" in result:
            return result
        
        try:
            img = Image.open(Config.SCREENSHOT_PATH)
            text = pytesseract.image_to_string(img)
            
            if not text.strip():
                return "📄 No text found on screen"
            
            return f"📄 Screen Text:\n{text[:1000]}"  # Limit to 1000 chars
        except Exception as e:
            return f"❌ OCR error: {str(e)}"
    
    # Package Management
    @staticmethod
    def install_package(package: str) -> str:
        if not package:
            return "❌ No package specified"
        
        # Try different package managers
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -S {shlex.quote(package)} --noconfirm", timeout=300)
                elif manager == "pacman":
                    success, output = run_cmd(f"sudo pacman -S {shlex.quote(package)} --noconfirm", timeout=300)
                elif manager == "apt":
                    success, output = run_cmd(f"sudo apt install -y {shlex.quote(package)}", timeout=300)
                else:
                    success, output = run_cmd(f"sudo {manager} install -y {shlex.quote(package)}", timeout=300)
                
                return f"✅ Installed {package}" if success else f"❌ Failed to install {package}"
        
        return "❌ No package manager found"
    
    @staticmethod
    def update_system() -> str:
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -Syu --noconfirm", timeout=600)
                elif manager == "pacman":
                    success, output = run_cmd(f"sudo pacman -Syu --noconfirm", timeout=600)
                elif manager == "apt":
                    success, output = run_cmd(f"sudo apt update && sudo apt upgrade -y", timeout=600)
                else:
                    success, output = run_cmd(f"sudo {manager} update -y", timeout=600)
                
                return f"✅ System updated" if success else f"❌ Failed to update system"
        
        return "❌ No package manager found"
    
    @staticmethod
    def check_updates() -> str:
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -Qu")
                elif manager == "pacman":
                    success, output = run_cmd(f"pacman -Qu")
                elif manager == "apt":
                    success, output = run_cmd(f"apt list --upgradable")
                else:
                    success, output = run_cmd(f"{manager} check-update")
                
                return f"📦 Updates available:\n{output[:500]}" if success else "✅ System is up to date"
        
        return "❌ No package manager found"
    
    @staticmethod
    def install_python_package(packages: str) -> str:
        """Install Python packages using pip"""
        if not packages:
            return "❌ No packages specified"
        
        # Parse multiple packages (comma or space separated)
        package_list = [p.strip() for p in re.split(r'[, ]+', packages) if p.strip()]
        if not package_list:
            return "❌ No valid packages found"
        
        # Try pip3 first, then pip
        pip_cmd = None
        for cmd in ["pip3", "pip"]:
            success, _ = run_cmd(f"which {cmd}")
            if success:
                pip_cmd = cmd
                break
        
        if not pip_cmd:
            return "❌ pip not found. Install pip first."
        
        # Install packages
        packages_str = " ".join([shlex.quote(p) for p in package_list])
        success, output = run_cmd(f"{pip_cmd} install {packages_str}", timeout=300)
        
        if success:
            return f"✅ Installed Python packages: {', '.join(package_list)}"
        else:
            return f"❌ Failed to install packages. Error: {output[:200]}"

# ==================== SCREEN ANALYZER ====================

class ScreenAnalyzer:
    @staticmethod
    def analyze_with_ai(image: Image.Image, ocr_text: str, screen_width: int, screen_height: int) -> str:
        """Analyze screen using AI with OCR text"""
        try:
            system_prompt = """You are Jarvis's screen analyzer. Analyze the screen content based on OCR text and provide:
1. What applications/windows are visible
2. What text/buttons/UI elements are present
3. Current state/context of the screen
4. What actions might be possible

Be concise and descriptive."""

            analysis_prompt = f"""Screen Analysis Request:

Screen Dimensions: {screen_width}x{screen_height}
OCR Text Extracted:
{ocr_text[:2000]}

Analyze this screen and describe:
- What is currently displayed?
- What applications or windows are visible?
- What UI elements (buttons, text fields, menus) can be seen?
- What is the current context/state?
- What actions might be possible on this screen?

Provide a clear, structured analysis."""

            return AIEngine.query_groq(system_prompt, analysis_prompt)
        except Exception as e:
            return f"Screen analysis: OCR found {len(ocr_text)} characters. Error: {str(e)}"
    
    @staticmethod
    def find_text_on_screen(text: str) -> Optional[Tuple[int, int]]:
        """Find text on screen and return coordinates"""
        if not OCR_AVAILABLE or not AUTOMATION_AVAILABLE:
            return None

        try:
            # Take screenshot
            CommandEngine.take_screenshot()
            img = Image.open(Config.SCREENSHOT_PATH)

            # Use pytesseract to find text with bounding boxes
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            # Search for the text
            for i, word in enumerate(data['text']):
                if text.lower() in word.lower():
                    x = data['left'][i] + data['width'][i] // 2
                    y = data['top'][i] + data['height'][i] // 2
                    return (x, y)

            return None
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return None

# ==================== AUTOMATION ENGINE ====================

class AutomationEngine:
    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
        self.automation_history = []
        self.status_callback = None  # For GUI status updates

    def understand_automation(self, user_instruction: str) -> str:
        """Use Groq AI to understand automation steps from user instruction"""
        system_prompt = """You are Jarvis's automation planner. The user will describe an automation task.
Your job is to break it down into step-by-step automation actions.

AVAILABLE AUTOMATION ACTIONS:
- click(x, y) - Click at coordinates
- click_text("text") - Find and click text on screen (use OCR to locate)
- type("text") - Type text
- press("key") - Press a key (e.g., "Enter", "Tab", "Ctrl+C", "Ctrl+V", "Alt+Tab")
- scroll(direction, amount) - Scroll (up/down/left/right)
- wait(seconds) - Wait for specified seconds
- screenshot() - Take screenshot
- read_screen() - Read text from screen
- analyze_screen() - Analyze screen to understand current state
- hotkey("key1+key2") - Press key combination (e.g., "Ctrl+C", "Alt+F4")

OUTPUT FORMAT:
Return a JSON array of actions. Each action is an object with:
{"action": "action_name", "params": {...}, "description": "what this does"}

Example:
User: "Open Chrome, search for Python, click the first result"
Output:
[
  {"action": "open_app", "params": {"app": "chrome"}, "description": "Open Chrome browser"},
  {"action": "wait", "params": {"seconds": 2}, "description": "Wait for Chrome to load"},
  {"action": "click_text", "params": {"text": "search"}, "description": "Click search bar"},
  {"action": "type", "params": {"text": "Python"}, "description": "Type Python"},
  {"action": "press", "params": {"key": "Enter"}, "description": "Press Enter to search"},
  {"action": "wait", "params": {"seconds": 2}, "description": "Wait for results"},
  {"action": "click_text", "params": {"text": "first result"}, "description": "Click first search result"}
]

SMART AUTOMATION GUIDELINES:
- Break down complex tasks into simple steps
- Add wait times between actions (1-3 seconds)
- Be specific about what to click or interact with
- Consider screen state and timing
- If user's instruction is vague, infer reasonable defaults:
  * "open browser" → assume Chrome/Firefox
  * "search for X" → assume search bar, then type X, then Enter
  * "click button" → use analyze_screen first to find button
- For ambiguous instructions, add analyze_screen steps to understand context
- Use analyze_screen() before clicking if the target is unclear
- Return ONLY valid JSON array"""

        prompt = f"""User wants to automate: "{user_instruction}"

Break this down into step-by-step automation actions. Return a JSON array of actions."""

        try:
            response = self.ai_engine.query_groq(system_prompt, prompt)
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json_match.group(0)
            return response
        except Exception as e:
            return f'[{{"action": "error", "params": {{"message": "{str(e)}"}}, "description": "Failed to plan automation"}}]'

    def execute_automation(self, automation_plan: str) -> str:
        """Execute automation plan step by step"""
        if not AUTOMATION_AVAILABLE:
            return "❌ Automation not available. Install: pip install pyautogui"

        try:
            steps = json.loads(automation_plan)
            results = []

            for i, step in enumerate(steps, 1):
                action = step.get("action", "")
                params = step.get("params", {})
                description = step.get("description", "")

                logger.info(f"Automation step {i}: {action} - {description}")

                try:
                    if action == "click":
                        x, y = params.get("x", 0), params.get("y", 0)
                        pyautogui.click(x, y)
                        results.append(f"✅ Step {i}: Clicked at ({x}, {y})")

                    elif action == "click_text":
                        text = params.get("text", "")
                        coords = ScreenAnalyzer.find_text_on_screen(text)
                        if coords:
                            pyautogui.click(coords[0], coords[1])
                            results.append(f"✅ Step {i}: Clicked '{text}' at {coords}")
                        else:
                            # Smart recovery: Use Groq to figure out alternative approach
                            results.append(f"⚠️ Step {i}: Could not find '{text}' on screen. Trying smart recovery...")
                            recovery = self._smart_recovery(f"Could not find text '{text}' on screen. What should I do?", i, steps)
                            if recovery:
                                results.append(f"💡 Step {i} Recovery: {recovery}")
                                # Try to execute recovery action if it's a simple command
                                if "click" in recovery.lower() or "type" in recovery.lower() or "press" in recovery.lower():
                                    # Let Groq plan a recovery step
                                    recovery_plan = self.understand_automation(f"Recovery: {recovery}")
                                    if recovery_plan and recovery_plan != automation_plan:
                                        recovery_result = self.execute_automation(recovery_plan)
                                        results.append(f"🔄 Recovery attempt: {recovery_result[:200]}")
                            else:
                                results.append(f"❌ Step {i}: Could not find '{text}' on screen")

                    elif action == "type":
                        text = params.get("text", "")
                        pyautogui.write(text, interval=0.1)
                        results.append(f"✅ Step {i}: Typed '{text}'")

                    elif action == "press":
                        key = params.get("key", "")
                        pyautogui.press(key)
                        results.append(f"✅ Step {i}: Pressed '{key}'")

                    elif action == "hotkey":
                        keys = params.get("keys", params.get("key", ""))
                        if "+" in keys:
                            key_list = keys.split("+")
                            pyautogui.hotkey(*[k.strip().lower() for k in key_list])
                        else:
                            pyautogui.press(keys)
                        results.append(f"✅ Step {i}: Pressed hotkey '{keys}'")

                    elif action == "analyze_screen":
                        result = CommandEngine.analyze_screen()
                        results.append(f"✅ Step {i}: {result[:200]}")

                    elif action == "scroll":
                        direction = params.get("direction", "down")
                        amount = params.get("amount", 3)
                        if direction == "down":
                            pyautogui.scroll(-amount)
                        elif direction == "up":
                            pyautogui.scroll(amount)
                        results.append(f"✅ Step {i}: Scrolled {direction}")

                    elif action == "wait":
                        seconds = params.get("seconds", 1)
                        time.sleep(seconds)
                        results.append(f"✅ Step {i}: Waited {seconds}s")

                    elif action == "screenshot":
                        result = CommandEngine.take_screenshot()
                        results.append(f"✅ Step {i}: {result}")

                    elif action == "read_screen":
                        result = CommandEngine.read_screen_text()
                        results.append(f"✅ Step {i}: {result[:100]}")

                    elif action == "open_app":
                        app = params.get("app", "")
                        result = CommandEngine.open_app(app)
                        results.append(f"✅ Step {i}: {result}")

                    else:
                        results.append(f"⚠️ Step {i}: Unknown action '{action}'")

                except Exception as e:
                    # Smart recovery: Use Groq to figure out what to do when error occurs
                    error_msg = str(e)
                    results.append(f"⚠️ Step {i}: Error - {error_msg}. Trying smart recovery...")
                    recovery = self._smart_recovery(f"Automation step {i} failed with error: {error_msg}. What should I do?", i, steps)
                    if recovery:
                        results.append(f"💡 Step {i} Recovery: {recovery}")
                        # Don't break - try to continue with recovery
                    else:
                        results.append(f"❌ Step {i}: Error - {error_msg}")
                        # Only break on critical errors
                        if "critical" in error_msg.lower() or "fatal" in error_msg.lower():
                            break

            return "\n".join(results)

        except json.JSONDecodeError as e:
            return f"❌ Invalid automation plan format: {str(e)}"
        except Exception as e:
            return f"❌ Automation error: {str(e)}"

    def _smart_recovery(self, problem: str, current_step: int, all_steps: List[Dict]) -> Optional[str]:
        """Use Groq to figure out how to recover from automation problems"""
        try:
            system_prompt = """You are Jarvis's automation recovery assistant. When automation fails, suggest what to do next.

Provide concise, actionable recovery steps. Examples:
- "Take screenshot and analyze screen to find alternative elements"
- "Try clicking at coordinates (x, y) instead"
- "Wait 2 seconds and retry"
- "Skip this step and continue"
- "Use keyboard shortcut Alt+F4 instead"

Be practical and specific."""

            context = f"""Current automation step: {current_step}
Problem: {problem}
Remaining steps: {len(all_steps) - current_step}

What should I do to recover?"""

            recovery = self.ai_engine.query_groq(system_prompt, context)
            return recovery[:300] if recovery else None
        except Exception as e:
            logger.error(f"Recovery planning error: {e}")
            return None

    def automate(self, user_instruction: str) -> str:
        """Complete automation workflow: understand -> execute"""
        # Get automation plan from AI
        plan = self.understand_automation(user_instruction)

        # Execute the plan
        result = self.execute_automation(plan)

        return f"🤖 Automation Plan:\n{plan}\n\n📋 Execution Results:\n{result}"

# ==================== COMMAND EXECUTOR ====================

class CommandExecutor:
    @staticmethod
    def execute(cmd_json: str, ai_engine: AIEngine = None, user_input: str = "") -> str:
        try:
            # Apply learned patterns before execution
            if ai_engine and ai_engine.learning_engine:
                learned_cmd = ai_engine.learning_engine.apply_learned_pattern(user_input)
                if learned_cmd:
                    logger.info(f"Using learned pattern for: {user_input}")
                    cmd_json = learned_cmd
            
            obj = json.loads(cmd_json)
            action = obj.get("command", "none")
            
            if action == "none":
                return None  # Return None to indicate it's a question, not a command
            
            # Map commands to methods
            command_map = {
                # Applications
                "open_app": lambda: CommandEngine.open_app(obj.get("app", "")),
                "list_apps": lambda: CommandEngine.list_running_apps(),
                
                # Audio
                "set_volume": lambda: CommandEngine.set_volume(obj.get("value", 50)),
                "increase_volume": lambda: CommandEngine.increase_volume(obj.get("value", 5)),
                "decrease_volume": lambda: CommandEngine.decrease_volume(obj.get("value", 5)),
                "mute_volume": lambda: CommandEngine.mute_volume(),
                "get_volume": lambda: CommandEngine.get_volume(),
                
                # Brightness
                "set_brightness": lambda: CommandEngine.set_brightness(obj.get("value", 50)),
                "increase_brightness": lambda: CommandEngine.increase_brightness(obj.get("value", 5)),
                "decrease_brightness": lambda: CommandEngine.decrease_brightness(obj.get("value", 5)),
                
                # Files
                "open_folder": lambda: CommandEngine.open_folder(obj.get("path", "~")),
                "list_files": lambda: CommandEngine.list_files(obj.get("path", ".")),
                "search_files": lambda: CommandEngine.search_files(obj.get("query", ""), obj.get("path", ".")),
                "read_file": lambda: CommandEngine.read_file(obj.get("path", ""), obj.get("lines", 50)),
                "create_file": lambda: CommandEngine.create_file(obj.get("path", ""), obj.get("text", "")),
                "write_file": lambda: CommandEngine.write_file(obj.get("path", ""), obj.get("text", "")),
                "delete_file": lambda: CommandEngine.delete_file(obj.get("path", "")),
                "create_directory": lambda: CommandEngine.create_directory(obj.get("path", "")),
                "move_file": lambda: CommandEngine.move_file(obj.get("path", ""), obj.get("dest", "")),
                "copy_file": lambda: CommandEngine.copy_file(obj.get("path", ""), obj.get("dest", "")),
                "create_pdf": lambda: CommandEngine.create_pdf(obj.get("content", obj.get("text", "")), obj.get("path", "")),
                "open_file": lambda: CommandEngine.open_file(obj.get("path", "")),
                
                # Processes
                "kill_process": lambda: CommandEngine.kill_process(obj.get("process", "")),
                "list_processes": lambda: CommandEngine.list_processes(),
                "find_process": lambda: CommandEngine.find_process(obj.get("query", "")),
                
                # System
                "lock_screen": lambda: CommandEngine.lock_screen(),
                "shutdown": lambda: CommandEngine.shutdown(),
                "restart": lambda: CommandEngine.restart(),
                "suspend": lambda: CommandEngine.suspend(),
                "battery": lambda: CommandEngine.battery(),
                "system_info": lambda: CommandEngine.system_info(),
                "disk_usage": lambda: CommandEngine.disk_usage(obj.get("path", "/")),
                
                # Network
                "connect_wifi": lambda: CommandEngine.connect_wifi(obj.get("ssid", "")),
                "list_wifi": lambda: CommandEngine.list_wifi(),
                "network_status": lambda: CommandEngine.network_status(),
                
                # Media
                "play_music": lambda: CommandEngine.play_music(),
                "pause_music": lambda: CommandEngine.pause_music(),
                "next_track": lambda: CommandEngine.next_track(),
                "previous_track": lambda: CommandEngine.previous_track(),
                "get_media_info": lambda: CommandEngine.get_media_info(),
                
                # Utilities
                "get_clipboard": lambda: CommandEngine.get_clipboard(),
                "set_clipboard": lambda: CommandEngine.set_clipboard(obj.get("text", "")),
                "get_weather": lambda: CommandEngine.get_weather(obj.get("city", "")),
                "open_url": lambda: CommandEngine.open_url(obj.get("url", "")),
                "take_screenshot": lambda: CommandEngine.take_screenshot(),
                "analyze_screen": lambda: CommandEngine.analyze_screen(),
                "read_screen_text": lambda: CommandEngine.read_screen_text(),
                "automate": lambda: CommandExecutor._execute_automation(obj.get("instruction", user_input), ai_engine),
                
                # Packages
                "install_package": lambda: CommandEngine.install_package(obj.get("package", "")),
                "install_python_package": lambda: CommandEngine.install_python_package(obj.get("package", "")),
                "update_system": lambda: CommandEngine.update_system(),
                "check_updates": lambda: CommandEngine.check_updates(),
            }
            
            if action in command_map:
                result = command_map[action]()
                
                # Self-reflect and learn from failures
                if ai_engine and ai_engine.learning_engine:
                    corrected = ai_engine.learning_engine.self_reflect(user_input, action, result)
                    if corrected:
                        # Try the corrected command
                        try:
                            corrected_obj = json.loads(corrected)
                            corrected_action = corrected_obj.get("command", "")
                            if corrected_action in command_map:
                                logger.info(f"Retrying with learned correction")
                                result = command_map[corrected_action]()
                        except:
                            pass
                
                return result
            else:
                error_msg = f"❌ Unknown command: {action}"
                # Learn from unknown command
                if ai_engine and ai_engine.learning_engine:
                    ai_engine.learning_engine.learn_from_failure(user_input, action, error_msg)
                return error_msg
                
        except json.JSONDecodeError:
            return None  # Treat as question if JSON parsing fails
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            error_msg = f"❌ Execution error: {str(e)}"
            # Learn from exception
            if ai_engine and ai_engine.learning_engine:
                ai_engine.learning_engine.learn_from_failure(user_input, "unknown", error_msg, str(e))
            return error_msg
    
    @staticmethod
    def _execute_automation(instruction: str, ai_engine: AIEngine) -> str:
        """Execute automation with AI engine"""
        if not ai_engine:
            return "❌ AI engine required for automation"
        
        if not AUTOMATION_AVAILABLE:
            return "❌ Automation not available. Install: pip install pyautogui"
        
        automation_engine = AutomationEngine(ai_engine)
        return automation_engine.automate(instruction)

# ==================== VOICE HANDLING ====================

class VoiceHandler:
    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        
        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 4000
            except Exception as e:
                logger.warning(f"Voice recognition setup failed: {e}")
        
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                logger.warning(f"TTS setup failed: {e}")
    
    def listen(self) -> Optional[str]:
        """Listen for voice input"""
        if not self.recognizer:
            return None
        
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            try:
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error(f"Voice recognition error: {e}")
                return None
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return None
    
    def speak(self, text: str):
        """Speak text using TTS"""
        if not self.tts_engine:
            return
        
        try:
            # Run in thread to avoid blocking
            def _speak():
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            thread = threading.Thread(target=_speak, daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"TTS error: {e}")

# ==================== ADVANCED MODAL GUI ====================

class JarvisGUI:
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        self.ai_engine = AIEngine()
        self.voice_handler = VoiceHandler()
        self.root = None
        self.setup_gui()
        self.processing = False
    
    def setup_gui(self):
        """Setup the advanced modal GUI"""
        self.root = tk.Tk()
        self.root.title("Jarvis - AI Personal Assistant")
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.configure(bg=Config.BG_COLOR)
        
        # Center window
        self.center_window()
        
        # Make window always on top and modal-like
        self.root.attributes('-topmost', True)
        self.root.attributes('-type', 'dialog')
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=Config.BG_COLOR)
        style.configure('TLabel', background=Config.BG_COLOR, foreground=Config.TEXT_COLOR)
        style.configure('TButton', background=Config.ACCENT_COLOR, foreground='white')
        style.map('TButton', background=[('active', '#74c7ec')])
        
        # Header
        header_frame = tk.Frame(self.root, bg=Config.THEME_COLOR, height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎯 Jarvis AI Assistant",
            font=("Arial", 20, "bold"),
            bg=Config.THEME_COLOR,
            fg=Config.ACCENT_COLOR
        )
        title_label.pack(pady=20)
        
        # Status bar
        self.status_label = tk.Label(
            header_frame,
            text="Ready",
            font=("Arial", 10),
            bg=Config.THEME_COLOR,
            fg=Config.TEXT_COLOR
        )
        self.status_label.pack()
        
        # Main content area
        content_frame = tk.Frame(self.root, bg=Config.BG_COLOR)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat display area
        chat_frame = tk.Frame(content_frame, bg=Config.BG_COLOR)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        chat_label = tk.Label(
            chat_frame,
            text="Conversation:",
            font=("Arial", 12, "bold"),
            bg=Config.BG_COLOR,
            fg=Config.TEXT_COLOR,
            anchor='w'
        )
        chat_label.pack(fill=tk.X, pady=(0, 5))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg=Config.THEME_COLOR,
            fg=Config.TEXT_COLOR,
            insertbackground=Config.ACCENT_COLOR,
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Input area
        input_frame = tk.Frame(content_frame, bg=Config.BG_COLOR)
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.input_entry = tk.Entry(
            input_frame,
            font=("Arial", 12),
            bg=Config.THEME_COLOR,
            fg=Config.TEXT_COLOR,
            insertbackground=Config.ACCENT_COLOR,
            relief=tk.FLAT,
            borderwidth=2,
            highlightthickness=1,
            highlightbackground=Config.ACCENT_COLOR,
            highlightcolor=Config.ACCENT_COLOR
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_entry.bind('<Return>', lambda e: self.process_input())
        self.input_entry.focus()
        
        # Buttons frame
        buttons_frame = tk.Frame(input_frame, bg=Config.BG_COLOR)
        buttons_frame.pack(side=tk.RIGHT)
        
        self.send_button = tk.Button(
            buttons_frame,
            text="Send",
            font=("Arial", 11, "bold"),
            bg=Config.ACCENT_COLOR,
            fg="white",
            relief=tk.FLAT,
            padx=20,
            pady=5,
            cursor="hand2",
            command=self.process_input
        )
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        self.voice_button = tk.Button(
            buttons_frame,
            text="🎤",
            font=("Arial", 14),
            bg="#a6e3a1" if VOICE_AVAILABLE else "#45475a",
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.voice_input,
            state=tk.NORMAL if VOICE_AVAILABLE else tk.DISABLED
        )
        self.voice_button.pack(side=tk.LEFT, padx=5)
        
        # Quick actions frame
        quick_frame = tk.Frame(content_frame, bg=Config.BG_COLOR)
        quick_frame.pack(fill=tk.X, pady=(10, 0))
        
        quick_label = tk.Label(
            quick_frame,
            text="Quick Actions:",
            font=("Arial", 10),
            bg=Config.BG_COLOR,
            fg=Config.TEXT_COLOR,
            anchor='w'
        )
        quick_label.pack(side=tk.LEFT)
        
        quick_actions = [
            ("System Info", "system info"),
            ("Battery", "battery status"),
            ("Weather", "what's the weather"),
            ("Screenshot", "take screenshot")
        ]
        
        for text, command in quick_actions:
            btn = tk.Button(
                quick_frame,
                text=text,
                font=("Arial", 9),
                bg=Config.THEME_COLOR,
                fg=Config.TEXT_COLOR,
                relief=tk.FLAT,
                padx=10,
                pady=3,
                cursor="hand2",
                command=lambda c=command: self.quick_action(c)
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # Welcome message
        self.add_message("Jarvis", "Hello! I'm Jarvis, your AI personal assistant. How can I help you today?", "assistant")
        
        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def add_message(self, sender: str, message: str, role: str = "user"):
        """Add message to chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Color coding
        if role == "assistant":
            tag = "assistant"
            self.chat_display.tag_config(tag, foreground=Config.ACCENT_COLOR, font=("Arial", 11, "bold"))
        else:
            tag = "user"
            self.chat_display.tag_config(tag, foreground="#f9e2af", font=("Arial", 11))
        
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n", "normal")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def update_status(self, status: str):
        """Update status label"""
        self.status_label.config(text=status)
        self.root.update_idletasks()
    
    def process_input(self):
        """Process user input"""
        if self.processing:
            return
        
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Add user message
        self.add_message("You", user_input, "user")
        
        # Process in thread to avoid blocking
        self.processing = True
        self.send_button.config(state=tk.DISABLED)
        self.update_status("Processing...")
        
        thread = threading.Thread(target=self._process_input_thread, args=(user_input,), daemon=True)
        thread.start()
    
    def _process_input_thread(self, user_input: str):
        """Process input in background thread with advanced understanding"""
        try:
            # Save command
            self.jarvis.save_command(user_input)
            
            # Use advanced interpretation with conversation context
            self.update_status("Understanding...")
            json_cmd = self.ai_engine.interpret_command(
                user_input, 
                conversation_context=self.ai_engine.conversation_history,
                learning_engine=self.ai_engine.learning_engine
            )
            
            result = CommandExecutor.execute(json_cmd, self.ai_engine, user_input)
            
            if result is None:
                # It's a question or conversation, use advanced chat mode
                self.update_status("Thinking deeply...")
                try:
                    response = self.ai_engine.chat(user_input)
                    self.root.after(0, self._show_response, response, "assistant")
                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    self.root.after(0, self._show_response, f"❌ AI service unavailable. Error: {str(e)}", "assistant")
            else:
                # It's a command - execute and show result directly
                self.root.after(0, self._show_response, result, "assistant")
                
                # Check if user is correcting Jarvis (e.g., "no, do X instead" or "that's wrong")
                if any(word in user_input.lower() for word in ["no", "wrong", "incorrect", "instead", "should", "correction"]):
                    # User is providing correction - learn from it
                    if self.ai_engine.learning_engine:
                        correction_context = f"User correction: '{user_input}' after result: '{result}'. Learn from this."
                        self.ai_engine.learning_engine.learn_from_failure(
                            user_input, 
                            json_cmd if isinstance(json_cmd, str) else str(json_cmd),
                            result,
                            "User correction"
                        )
        
        except Exception as e:
            logger.error(f"Processing error: {e}")
            error_msg = f"❌ Error: {str(e)}"
            self.root.after(0, self._show_response, error_msg, "assistant")
            
            # Try to get AI help for the error
            try:
                help_msg = self.ai_engine.chat(
                    f"I encountered an error: {str(e)}. Help the user understand what happened.",
                    system_context="Explain the error in user-friendly terms and suggest solutions."
                )
                if help_msg and len(help_msg) < 300:
                    self.root.after(0, self._show_response, help_msg, "assistant")
            except Exception:
                pass
        finally:
            self.processing = False
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.update_status("Ready"))
    
    def _show_response(self, response: str, role: str):
        """Show response in GUI"""
        self.add_message("Jarvis", response, role)
        
        # Speak response if TTS available
        if self.voice_handler.tts_engine and len(response) < 500:
            self.voice_handler.speak(response)
    
    def voice_input(self):
        """Handle voice input"""
        if not VOICE_AVAILABLE:
            messagebox.showinfo("Voice", "Voice recognition not available. Install speech_recognition package.")
            return
        
        self.update_status("Listening...")
        self.voice_button.config(text="🔴", bg="#f38ba8")
        self.root.update()
        
        def _listen():
            text = self.voice_handler.listen()
            if text:
                self.root.after(0, lambda: self.input_entry.insert(0, text))
                self.root.after(0, lambda: self.process_input())
            self.root.after(0, lambda: self.voice_button.config(text="🎤", bg="#a6e3a1"))
            self.root.after(0, lambda: self.update_status("Ready"))
        
        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
    
    def quick_action(self, command: str):
        """Execute quick action"""
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, command)
        self.process_input()
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit Jarvis?"):
            self.root.destroy()
            self.jarvis.running = False
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

# ==================== JARVIS MAIN CLASS ====================

class Jarvis:
    def __init__(self, use_gui: bool = True):
        self.running = True
        self.use_gui = use_gui and GUI_AVAILABLE
        self.setup_signal_handlers()
        self.gui = None
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nJarvis: Shutting down gracefully... 👋")
        self.running = False
        if self.gui and self.gui.root:
            self.gui.root.quit()
    
    def save_command(self, command: str):
        """Save command to history"""
        try:
            with open(Config.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()}: {command}\n")
        except Exception as e:
            logger.warning(f"Failed to save command: {e}")
    
    def run(self):
        """Main application loop"""
        if self.use_gui:
            print("🎯 Starting Jarvis with Advanced Modal GUI...")
            self.gui = JarvisGUI(self)
            self.gui.run()
        else:
            # Fallback to CLI mode
            print("=" * 60)
            print("🎯 Jarvis Enhanced - AI Assistant Ready")
            print("=" * 60)
            print("\nType 'help' for commands or just speak naturally!")
            print("Examples: 'open chrome', 'volume 80', 'what's the weather'")
            print("=" * 60 + "\n")
            
            logger.info("Jarvis Enhanced started (CLI mode)")
            ai_engine = AIEngine()
            
            while self.running:
                try:
                    user_input = input("You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    self.save_command(user_input)
                    user_lower = user_input.lower()
                    
                    # Handle special commands
                    if user_lower in ["exit", "quit", "bye"]:
                        print("Jarvis: Goodbye! Have a great day! 👋")
                        break
                    
                    # Process input with advanced understanding
                    print("🧠 Understanding...")
                    json_cmd = ai_engine.interpret_command(
                        user_input,
                        conversation_context=ai_engine.conversation_history,
                        learning_engine=ai_engine.learning_engine
                    )
                    result = CommandExecutor.execute(json_cmd, ai_engine, user_input)
                    
                    if result is None:
                        # It's a question or conversation
                        print("🧠 Thinking deeply...")
                        response = ai_engine.chat(user_input)
                        print(f"Jarvis: {response}\n")
                    else:
                        # It's a command
                        print(f"Jarvis: {result}\n")
                        
                        # Provide intelligent feedback
                        if "❌" not in result:
                            feedback = ai_engine.chat(
                                f"User requested: '{user_input}'. I executed: '{result}'. Provide brief confirmation.",
                                system_context="Give a brief, natural confirmation."
                            )
                            if feedback and len(feedback) < 200:
                                print(f"Jarvis: {feedback}\n")
                    
                except EOFError:
                    print("\nJarvis: Input closed. Goodbye! 👋")
                    break
                except KeyboardInterrupt:
                    print("\nJarvis: Interrupted. Goodbye! 👋")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    print(f"Jarvis: ❌ Unexpected error: {str(e)}\n")

# ==================== MAIN ENTRY POINT ====================

def main():
    """Main entry point"""
    try:
        # Check for GUI flag
        use_gui = "--no-gui" not in sys.argv
        
        jarvis = Jarvis(use_gui=use_gui)
        jarvis.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
