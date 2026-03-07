#!/usr/bin/env python3
"""
BenX - Advanced AI Assistant with RAG and Image Sensing
Main entry point
"""
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path

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

# Check GUI availability
try:
    from jarvis_ai.gui.jarvis_ui import JarvisUI, GUI_AVAILABLE
except ImportError:
    GUI_AVAILABLE = False
    logger.warning("GUI not available")


class BenX:
    """Main BenX application"""
    
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
        print("\n\nBenX: Shutting down gracefully... 👋")
        self.running = False
        if self.gui and self.gui.root:
            try:
                self.gui.root.quit()
            except:
                pass
    
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
            print("🎯 Starting BenX with JARVIS UI...")
            try:
                from jarvis_ai.gui.jarvis_ui import JarvisUI
                self.gui = JarvisUI(self)
                self.gui.run()
            except Exception as e:
                logger.error(f"GUI startup failed: {e}")
                print(f"⚠️  GUI failed to start: {e}")
                print("Falling back to CLI mode...")
                self.run_cli()
        else:
            self.run_cli()
    
    def run_cli(self):
        """Run in CLI mode"""
        print("=" * 60)
        print("🎯 BenX - Advanced Assistant with RAG & Image Sensing")
        print("=" * 60)
        print("\nType 'help' for commands or just speak naturally!")
        print("Examples: 'open chrome', 'volume 80', 'what's the weather'")
        print("=" * 60 + "\n")
        
        logger.info("BenX started (CLI mode)")
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.executor import CommandExecutor
        
        ai_engine = AIEngine()
        
        while self.running:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                self.save_command(user_input)
                user_lower = user_input.lower()
                
                if user_lower in ["exit", "quit", "bye"]:
                    print("BenX: Goodbye! Have a great day! 👋")
                    break
                
                print("🧠 Understanding...")
                json_cmd = ai_engine.interpret_command(
                    user_input,
                    conversation_context=ai_engine.conversation_history,
                    learning_engine=ai_engine.learning_engine
                )
                result = CommandExecutor.execute(json_cmd, ai_engine, user_input)
                
                if result is None:
                    print("🧠 Thinking deeply...")
                    response = ai_engine.chat(user_input)
                    print(f"BenX: {response}\n")
                else:
                    print(f"BenX: {result}\n")
                    
            except EOFError:
                print("\nBenX: Input closed. Goodbye! 👋")
                break
            except KeyboardInterrupt:
                print("\nBenX: Interrupted. Goodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                print(f"BenX: ❌ Unexpected error: {str(e)}\n")


def main():
    """Main entry point"""
    try:
        use_gui = "--no-gui" not in sys.argv
        
        jarvis = BenX(use_gui=use_gui)
        jarvis.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
