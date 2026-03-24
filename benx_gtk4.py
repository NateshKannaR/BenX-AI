#!/usr/bin/env python3
"""
BenX GTK4 - Native Wayland version with screen recording exclusion
Use this ONLY if you want GTK4 UI specifically.

For the beautiful tkinter UI, use: python benx.py
"""
import sys
import signal
import logging
from pathlib import Path

# CRITICAL: Load GTK4 BEFORE anything else
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

# Setup logging
from jarvis_ai.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BenX:
    """Main BenX application with GTK4"""
    
    def __init__(self):
        self.running = True
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nBenX: Shutting down gracefully... 👋")
        self.running = False
        sys.exit(0)
    
    def save_command(self, command: str):
        """Save command to history"""
        from datetime import datetime
        try:
            with open(Config.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()}: {command}\n")
        except Exception as e:
            logger.warning(f"Failed to save command: {e}")
    
    def run(self):
        """Main application loop"""
        print("🎯 Starting BenX with GTK4 UI (Native Wayland)...")
        try:
            # Import directly to avoid __init__.py loading other GUI modules
            from jarvis_ai.gui import benx_gtk4 as gtk4_module
            app = gtk4_module.create_gtk4_ui(self)
            app.run_app()
        except Exception as e:
            logger.error(f"GTK4 startup failed: {e}")
            print(f"❌ GTK4 failed to start: {e}")
            print("")
            print("💡 TIP: For the beautiful tkinter UI, use: python benx.py")
            sys.exit(1)


def main():
    """Main entry point"""
    try:
        jarvis = BenX()
        jarvis.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
