"""
AI Engine with RAG (Retrieval-Augmented Generation) and Image Sensing
"""
import json
import re
import base64
import logging
import math
import hashlib
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from PIL import Image
    import io
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

try:
    import numpy as np
    import faiss
    import pickle
    RAG_VECTOR_DB_AVAILABLE = True
except ImportError:
    RAG_VECTOR_DB_AVAILABLE = False
    np = None
    logger.warning("FAISS/numpy not available. RAG will use simple text-based search.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class RAGEngine:
    """Retrieval-Augmented Generation engine for enhanced context"""
    
    def __init__(self):
        self.vector_db = None
        self.documents = []
        self.embeddings_cache = {}
        self.embedding_model = None
        self.init_rag()
    
    def init_rag(self):
        """Initialize RAG system"""
        if not Config.RAG_ENABLED:
            return
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            if Config.VECTOR_DB_PATH.exists():
                self.load_vector_db()
            elif RAG_VECTOR_DB_AVAILABLE:
                self.create_vector_db()
        except Exception as e:
            logger.warning(f"RAG initialization failed: {e}")
    
    def create_vector_db(self):
        """Create a new vector database"""
        if RAG_VECTOR_DB_AVAILABLE:
            # Create a simple FAISS index (flat L2)
            self.vector_db = faiss.IndexFlatL2(384)  # 384 dim for sentence-transformers
    
    def load_vector_db(self):
        """Load existing vector database"""
        try:
            with open(Config.VECTOR_DB_PATH, 'rb') as f:
                data = pickle.load(f)
                self.vector_db = data.get('index') if RAG_VECTOR_DB_AVAILABLE else None
                self.documents = data.get('documents', [])
        except Exception as e:
            logger.error(f"Failed to load vector DB: {e}")
            if RAG_VECTOR_DB_AVAILABLE:
                self.create_vector_db()
    
    def save_vector_db(self):
        """Save vector database"""
        try:
            with open(Config.VECTOR_DB_PATH, 'wb') as f:
                pickle.dump({
                    'index': self.vector_db if RAG_VECTOR_DB_AVAILABLE else None,
                    'documents': self.documents
                }, f)
        except Exception as e:
            logger.error(f"Failed to save vector DB: {e}")
    
    def get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding for text using sentence-transformers or deterministic hashing fallback."""
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        if np is None:
            # Fallback: return None if numpy not available
            return None

        normalized = " ".join(text.lower().split())
        if self.embedding_model is not None:
            try:
                embedding = self.embedding_model.encode(normalized, normalize_embeddings=True).astype("float32")
                self.embeddings_cache[text] = embedding
                return embedding
            except Exception as e:
                logger.warning(f"Sentence transformer embedding failed, using fallback: {e}")

        # Deterministic hashed term embedding fallback.
        embedding = np.zeros(384, dtype="float32")
        for token in re.findall(r"\b[a-z0-9_]+\b", normalized):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % 384
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            embedding[index] += sign

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        self.embeddings_cache[text] = embedding
        return embedding
    
    def add_document(self, text: str, metadata: Dict = None):
        """Add document to RAG database"""
        if not Config.RAG_ENABLED:
            return
        
        embedding = self.get_embedding(text)
        if embedding is not None and self.vector_db:
            self.vector_db.add(embedding.reshape(1, -1))
        self.documents.append({
            'text': text,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        self.save_vector_db()
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        if not Config.RAG_ENABLED:
            return []
        
        results = []
        query_embedding = self.get_embedding(query) if self.vector_db else None
        if query_embedding is not None and self.vector_db and self.documents:
            try:
                distances, indices = self.vector_db.search(query_embedding.reshape(1, -1), min(k * 2, len(self.documents)))
                for distance, index in zip(distances[0], indices[0]):
                    if index < 0 or index >= len(self.documents):
                        continue
                    doc = dict(self.documents[index])
                    doc["_score"] = float(1 / (1 + distance))
                    results.append(doc)
            except Exception as e:
                logger.warning(f"Vector search failed, using lexical search: {e}")

        query_terms = set(re.findall(r"\b[a-z0-9_]+\b", query.lower()))
        lexical = []
        for doc in self.documents[-200:]:
            text = doc.get("text", "").lower()
            overlap = sum(1 for term in query_terms if term in text)
            if overlap:
                item = dict(doc)
                item["_score"] = item.get("_score", 0) + overlap + min(len(text), 500) / 1000
                lexical.append(item)

        merged = {}
        for doc in results + lexical:
            key = f"{doc.get('timestamp')}::{doc.get('text', '')[:80]}"
            if key not in merged or doc.get("_score", 0) > merged[key].get("_score", 0):
                merged[key] = doc

        ranked = sorted(merged.values(), key=lambda item: item.get("_score", 0), reverse=True)
        return ranked[:k]


class AIEngine:
    """AI Engine with RAG and vision capabilities"""
    
    def __init__(self):
        self.conversation_history = []
        self.rag_engine = RAGEngine()
        self.load_conversation_history()
        from jarvis_ai.learning import LearningEngine
        self.learning_engine = LearningEngine(self)
    
    def load_conversation_history(self):
        """Load conversation history from file"""
        try:
            if Config.CONVERSATION_FILE.exists():
                with open(Config.CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = data.get("messages", [])[-20:]
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
    def encode_image(image_path: str) -> Optional[str]:
        """Encode image to base64 for API"""
        try:
            if not IMAGE_AVAILABLE:
                return None
            
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None
    
    @staticmethod
    def query_groq(system_prompt: str, user_prompt: str, 
                   model_preference: Optional[str] = None,
                   conversation_context: List[Dict] = None,
                   image_path: Optional[str] = None,
                   use_vision: bool = False) -> str:
        """Query Groq API with fallback support, conversation context, and image support"""
        if not Config.GROQ_KEY:
            return "❌ Missing GROQ_API_KEY. Set it in your environment before running."
        headers = {
            "Authorization": f"Bearer {Config.GROQ_KEY}",
            "Content-Type": "application/json"
        }
        
        # Select models based on whether we need vision
        if use_vision and image_path:
            models = [m for m in Config.IMAGE_MODELS if m in Config.MODELS] + Config.MODELS
        else:
            models = Config.MODELS.copy()
        
        if model_preference and model_preference in models:
            models.remove(model_preference)
            models.insert(0, model_preference)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_context:
            messages.extend(conversation_context[-10:])
        
        # Add image if provided and vision is enabled
        user_message_content = user_prompt
        if use_vision and image_path and IMAGE_AVAILABLE:
            base64_image = AIEngine.encode_image(image_path)
            if base64_image:
                user_message_content = [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
        
        messages.append({"role": "user", "content": user_message_content})
        
        failed_models = []
        for model in models:
            try:
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 4000,
                    "top_p": 0.9,
                }
                
                logger.debug(f"Trying model: {model}")
                response = requests.post(Config.API_URL, headers=headers, json=data, timeout=Config.API_TIMEOUT)
                response.raise_for_status()
                
                result = response.json()
                if "choices" in result and result["choices"]:
                    logger.info(f"✅ Successfully used model: {model}")
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"Model {model} returned empty choices")
                    failed_models.append(model)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Model {model} timed out")
                failed_models.append(model)
                continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error(f"❌ Authentication failed (401) - Invalid or expired API key")
                    error_msg = "❌ Authentication failed. Please check your Groq API key.\n"
                    error_msg += "Set GROQ_API_KEY environment variable or update jarvis_ai/config.py"
                    return error_msg
                elif e.response.status_code == 404:
                    logger.warning(f"Model {model} not found (404)")
                elif e.response.status_code == 429:
                    logger.warning(f"Model {model} rate limited (429)")
                else:
                    logger.warning(f"Model {model} HTTP error: {e.response.status_code}")
                failed_models.append(model)
                continue
            except Exception as e:
                logger.warning(f"Model {model} failed: {str(e)[:100]}")
                failed_models.append(model)
                continue
        
        error_msg = f"❌ All {len(models)} AI models failed."
        if failed_models:
            error_msg += f"\n\nMost common issues:"
            error_msg += f"\n1. Invalid API key - Get a free key from: https://console.groq.com/keys"
            error_msg += f"\n2. Set environment variable: export GROQ_API_KEY='your_key_here'"
            error_msg += f"\n3. Or update jarvis_ai/config.py with your key"
        error_msg += "\n\nCheck your connection and API key."
        return error_msg
    
    def chat(self, user_input: str, system_context: str = None, image_path: Optional[str] = None) -> str:
        """Chat with AI using advanced conversation context, RAG, and optional image"""
        
        # Get RAG context
        rag_context = ""
        if Config.RAG_ENABLED:
            relevant_docs = self.rag_engine.search(user_input, k=3)
            if relevant_docs:
                rag_context = "\n\nRelevant context from memory:\n"
                for doc in relevant_docs:
                    rag_context += f"- {doc['text'][:200]}\n"
        
        # Get system state
        system_state = self._get_system_context()
        
        system_prompt = f"""You are BenX, an ultra-advanced AI personal assistant with complete control over the user's Linux system.

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
- Image analysis and understanding (vision capabilities)
- And much more...

CURRENT SYSTEM STATE:
{system_state}

{rag_context}

CONTEXT AWARENESS:
- Remember what the user has asked before
- Understand implicit requests (e.g., "make it louder" means increase volume)
- Recognize follow-up questions and references to previous topics
- Understand user intent even if phrasing is unclear
- Be proactive - suggest helpful actions when relevant

{system_context if system_context else ""}

Remember: You're not just executing commands - you're understanding the user's needs and helping them achieve their goals intelligently."""
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Use vision if image is provided
        use_vision = image_path is not None
        
        # Get response
        response = self.query_groq(
            system_prompt,
            user_input,
            conversation_context=self.conversation_history,
            image_path=image_path,
            use_vision=use_vision
        )
        
        # Add response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        self.save_conversation_history()
        
        # Store in RAG for future reference
        if Config.RAG_ENABLED:
            self.rag_engine.add_document(
                f"Q: {user_input}\nA: {response}",
                metadata={"type": "conversation", "timestamp": datetime.now().isoformat()}
            )
        
        return response
    
    def analyze_image(self, image_path: str, question: str = "What is in this image?") -> str:
        """Analyze an image using vision models"""
        if not IMAGE_AVAILABLE:
            return "❌ Image processing not available. Install: pip install Pillow"
        
        system_prompt = """You are BenX's vision assistant. Analyze images and provide detailed descriptions, answer questions about images, and extract information from visual content.

Be thorough, accurate, and descriptive. Identify:
- Objects, people, text, UI elements
- Context and scene understanding
- Actions that can be performed
- Any important details"""
        
        return self.query_groq(
            system_prompt,
            question,
            image_path=image_path,
            use_vision=True
        )
    
    def _get_system_context(self) -> str:
        """Get current system state for context"""
        try:
            import psutil
            context_parts = []
            
            try:
                battery = psutil.sensors_battery()
                if battery:
                    context_parts.append(f"Battery: {battery.percent}% ({'Charging' if battery.power_plugged else 'Discharging'})")
            except:
                pass
            
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                context_parts.append(f"CPU: {cpu:.1f}%, Memory: {memory.percent:.1f}%")
            except:
                pass
            
            context_parts.append(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            
            return "\n".join(context_parts) if context_parts else "System state: Normal"
        except:
            return "System state: Available"
    
    @staticmethod
    def interpret_command(text: str, conversation_context: List[Dict] = None, learning_engine=None) -> str:
        """Convert natural language to JSON command"""
        from jarvis_ai.learning import LearningEngine
        
        # Check learned patterns first
        if learning_engine:
            learned = learning_engine.apply_learned_pattern(text)
            if learned:
                logger.info(f"Using learned pattern for command interpretation")
                return learned
        
        system_prompt = """You are BenX's command interpreter. Your job is to understand user intent and convert it to precise JSON commands.

THINKING PROCESS:
1. Analyze the user's intent deeply - what do they REALLY want?
2. Consider context from conversation (e.g., "make it louder" after volume discussion)
3. Extract all relevant parameters (numbers, paths, app names, etc.)
4. Choose the most appropriate command
5. Handle variations and synonyms intelligently

OUTPUT FORMAT:
Output ONLY valid JSON in this exact format:
{"command": "action_name", "app": "app_name", "value": number, "path": "file_path", "query": "search_term", "text": "content", "process": "process_name", "dest": "destination_path", "package": "package_name", "city": "city_name", "url": "url", "ssid": "wifi_name", "instruction": "automation_instruction", "contact": "contact_name_or_number", "name": "task_or_symbol_name", "category": "memory_category", "repeat": "once|daily|weekly|monthly", "when": "YYYY-MM-DD HH:MM", "snippet_type": "react_component|fastapi_route|flask_route|test_file|plugin_template|cli_command", "framework": "framework_name", "dry_run": false}

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
- create_pdf: "create pdf", "make pdf", "generate pdf"
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
- get_time: "time", "current time", "what time is it"
- open_url: "open website", "browse to", "go to"
- take_screenshot: "screenshot", "capture screen", "snapshot"
- analyze_screen: "analyze screen", "what's on screen", "screen analysis"
- analyze_image: "analyze image", "what's in this image", "describe image"
- read_screen_text: "read screen", "extract text", "OCR screen"
- automate: "automate", "do this", "perform automation", "execute automation"
- search_github: "search github", "find on github", "github search", "look for on github", "how many repositories does USER have", "github profile stats", "repo count for USER"
- open_whatsapp_contact: "whatsapp", "message on whatsapp", "open whatsapp contact", "whatsapp contact"
- preview_automation: "preview automation", "show automation steps", "dry run automation"
- pause_automation: "pause automation"
- resume_automation: "resume automation"
- screen_aware_click: "click the button that says", "click text on screen"
- schedule_task: "schedule", "remind me at", "every morning", "every night", "schedule automation"
- list_scheduled_tasks: "list scheduled tasks", "show reminders"
- cancel_scheduled_task: "cancel scheduled task", "remove reminder"

DEVELOPER:
- analyze_project: "analyze project", "inspect repo", "what kind of project is this", "analyze this repository", "analyze all code", "summarize this codebase", "what is in this repo"
- search_code: "find in code", "search code", "find all uses"
- find_symbol: "find symbol", "where is this class used", "where is this function used"
- list_todos: "list todos", "show fixmes"
- find_dead_code: "find dead code", "unused code candidates"
- generate_snippet: "create react component", "create fastapi route", "create test file", "create plugin template", "create cli command template"
- remember_developer_note: "remember this convention", "remember preferred command", "remember recurring fix", "remember how this repo is run"
- recall_developer_memory: "show developer memory", "what do you remember about this project"

PACKAGES:
- install_package: "install", "add package" (system packages)
- install_python_package: "install python package", "pip install", "install with pip" (Python packages)
- update_system: "update", "upgrade system"
- check_updates: "check updates", "available updates"

PROJECT ORCHESTRATION (NEW - High Priority):
- create_project: "create project", "build project", "new project", "create a full project", "make a project", "generate project"
- modify_project: "add feature", "add login page", "add component", "add page", "add endpoint"
- refactor_project: "refactor", "restructure", "refactor folder structure", "reorganize", "change structure"
- fix_project_bug: "fix bug", "fix bug in", "debug", "fix error in", "fix issue in"
- modify_project: "change backend", "migrate", "change from X to Y", "switch to", "convert to"

PROJECT TASK DETECTION:
- If user says "create", "build", "new project", "full project" → create_project
- If user says "add", "create" + feature/page/component → modify_project
- If user says "refactor", "restructure", "reorganize" → refactor_project
- If user says "fix bug", "fix error", "debug" + file → fix_project_bug
- If user says "change", "migrate", "convert" + framework/backend → modify_project
- These are PROJECT tasks and should be prioritized over regular file operations

COMMAND VS QUESTION:
- COMMANDS (execute actions): "create", "open", "install", "delete", "move", "copy", "automate", "set", "increase", "decrease", "kill", "play", "pause", "analyze"
- QUESTIONS (conversation): "what", "how", "why", "when", "where", "explain", "tell me about", "describe"
- Questions about a local repository, codebase, or project structure should use analyze_project.
- Questions about GitHub users, repository counts, or GitHub profile stats should use search_github.
- If it's clearly a QUESTION or CONVERSATION (not a command), return: {"command":"none"}
- Be AGGRESSIVE about recognizing commands - prefer action over conversation
- Only return {"command":"none"} if it's CLEARLY a question with no action intent

IMPORTANT:
- Extract numbers intelligently ("eighty" = 80, "half" = 50)
- Handle paths with ~ expansion
- Be smart about app name variations (chrome/chromium, code/vscode)
- If unsure about a parameter, use reasonable defaults
- For automation requests, capture the full instruction in the "instruction" field"""
        
        context_messages = []
        if conversation_context:
            context_messages = conversation_context[-5:]
        
        try:
            return AIEngine.query_groq(system_prompt, text, conversation_context=context_messages)
        except Exception as e:
            logger.error(f"Command interpretation failed: {e}")
            return json.dumps({"command": "none"})
