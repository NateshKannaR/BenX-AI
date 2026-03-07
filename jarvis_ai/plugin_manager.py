"""
Plugin Manager - Lightweight command extension system.
"""
import importlib
import logging
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class PluginManager:
    """Load plugins from jarvis_ai/plugins and register command handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._loaded = False

    def register_command(self, command: str, handler: Callable):
        if not command or not callable(handler):
            return
        self._handlers[command] = handler

    def get_handler(self, command: str) -> Optional[Callable]:
        return self._handlers.get(command)

    def load_plugins(self):
        if self._loaded:
            return
        self._loaded = True

        plugins_dir = Path(__file__).parent / "plugins"
        if not plugins_dir.exists():
            return

        for path in plugins_dir.glob("*.py"):
            if path.name.startswith("_") or path.name == "__init__.py":
                continue
            module_name = f"jarvis_ai.plugins.{path.stem}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    module.register(self)
            except Exception as e:
                logger.warning(f"Plugin load failed: {module_name}: {e}")
