"""
Configuration settings for BenX
"""
import os
from pathlib import Path
from typing import List

class Config:
    """Configuration class for BenX"""
    
    # API Configuration
    # IMPORTANT: Never commit your API key to GitHub!
    # Set your API key as an environment variable:
    # export GROQ_API_KEY='your_key_here'
    GROQ_KEY = os.getenv("GROQ_API_KEY", os.getenv("GROQ_KEY", "")).strip()
    
    # ── Model routing: task-type → best model ──────────────────────
    MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "groq/compound",
        "groq/compound-mini",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "moonshotai/kimi-k2-instruct",
    ]

    # Ordered fallback lists per task type
    MODEL_ROUTES = {
        "vision":  ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile", "groq/compound"],
        "code":    ["qwen/qwen3-32b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
        "chat":    ["llama-3.3-70b-versatile", "groq/compound", "llama-3.1-8b-instant"],
        "fast":    ["llama-3.1-8b-instant", "groq/compound-mini", "llama-3.3-70b-versatile"],
        "reason":  ["openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct", "llama-3.3-70b-versatile"],
    }

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    API_TIMEOUT = 120

    # Email (IMAP/SMTP)
    EMAIL_ADDRESS  = os.getenv("BENX_EMAIL", "").strip()
    EMAIL_PASSWORD = os.getenv("BENX_EMAIL_PASSWORD", "").strip()
    EMAIL_IMAP     = os.getenv("BENX_IMAP", "imap.gmail.com").strip()
    EMAIL_SMTP     = os.getenv("BENX_SMTP", "smtp.gmail.com").strip()
    EMAIL_SMTP_PORT = int(os.getenv("BENX_SMTP_PORT", "587"))

    # Safety/permissions
    # If True, require explicit confirmation for privileged or destructive actions.
    REQUIRE_CONFIRMATION = True
    # If True, prompt before running sudo-level commands.
    PROMPT_FOR_SUDO = True
    # Limit file operations to these roots unless explicitly overridden.
    ALLOWED_ROOTS = [
        str(Path.home()),
    ]
    
    # RAG Configuration
    RAG_ENABLED = True
    RAG_EMBEDDINGS_MODEL = "text-embedding-3-small"  # For text embeddings
    VECTOR_DB_PATH = None  # Will be set in __init__
    MAX_CONTEXT_LENGTH = 128000  # Maximum context window
    
    # Image processing - vision models (may not be available)
    IMAGE_MODELS = [
        "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 Scout - vision capable
        "llama-3.3-70b-versatile",  # Fallback to best text model
        "groq/compound",  # Compound model
    ]
    MAX_IMAGE_SIZE = 2048  # Max image dimension for processing
    IMAGE_CACHE_DIR = None  # Will be set in __init__
    
    # Paths
    HOME = Path.home()
    BENX_DIR = HOME / ".benx"
    LOG_FILE = BENX_DIR / "benx.log"
    HISTORY_FILE = BENX_DIR / "history.txt"
    CONVERSATION_FILE = BENX_DIR / "conversation.json"
    SCREENSHOT_PATH = "/tmp/benx_screen.png"
    SCREEN_ANALYSIS_PATH = BENX_DIR / "screen_analysis.json"
    LEARNING_FILE = BENX_DIR / "learning.json"
    DEVELOPER_MEMORY_FILE = BENX_DIR / "developer_memory.json"
    SCHEDULE_FILE = BENX_DIR / "scheduled_tasks.json"
    AUTOMATION_STATE_FILE = BENX_DIR / "automation_state.json"
    RAG_DATA_DIR = BENX_DIR / "rag_data"
    
    # Create directories
    BENX_DIR.mkdir(exist_ok=True)
    RAG_DATA_DIR.mkdir(exist_ok=True)
    
    # Initialize paths (using .pkl extension for vector DB)
    VECTOR_DB_PATH = RAG_DATA_DIR / "vector_db.pkl"
    IMAGE_CACHE_DIR = RAG_DATA_DIR / "images"
    IMAGE_CACHE_DIR.mkdir(exist_ok=True)
    
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
    
    # GUI Settings (Advanced control center)
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 820
    WINDOW_OPACITY = 0.97  # Semi-transparent floating effect
    FONT_FAMILY = "Rajdhani"
    HEADING_FONT_FAMILY = "Orbitron"
    THEME_COLOR = "#0b1720"  # Deep panel
    ACCENT_COLOR = "#20d9ff"  # Neon cyan
    ACCENT_COLOR_2 = "#2be2a4"  # Neon green
    TEXT_COLOR = "#d3f0ff"  # Light text
    BG_COLOR = "#060c10"  # App background
    SECONDARY_COLOR = "#0c222c"  # Secondary background
    GLASS_COLOR = "#0c1f27"  # Glass panel
    GLASS_COLOR_DARK = "#08161c"  # Glass panel deep
    GLASS_BORDER = "#173640"  # Glass border
    GLASS_HIGHLIGHT = "#1fd9ff"  # Glass highlight
    SUCCESS_COLOR = "#34d399"  # Green
    ERROR_COLOR = "#f87171"  # Red
    WARNING_COLOR = "#fbbf24"  # Yellow


