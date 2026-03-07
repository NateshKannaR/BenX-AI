"""
Command Executor - Execute parsed commands
"""
import json
import logging
import os
from datetime import datetime, timedelta
from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.command_engine import CommandEngine
from jarvis_ai.screen_analyzer import ScreenAnalyzer
from jarvis_ai.automation import AutomationEngine
from jarvis_ai.project_orchestrator import ProjectOrchestrator
from jarvis_ai.config import Config
from jarvis_ai.plugin_manager import PluginManager
from jarvis_ai.scheduler import Scheduler
from jarvis_ai.developer_assistant import DeveloperAssistant

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Execute commands parsed from natural language"""

    _plugin_manager = None
    _scheduler = None
    _developer_assistant = None

    CONFIRM_ACTIONS = {
        "delete_file",
        "shutdown",
        "restart",
        "suspend",
        "kill_process",
        "install_package",
        "update_system",
        "move_file",
        "copy_file",
    }

    FILE_ACTIONS = {
        "open_folder",
        "list_files",
        "search_files",
        "read_file",
        "create_file",
        "write_file",
        "delete_file",
        "create_directory",
        "move_file",
        "copy_file",
        "create_pdf",
        "open_file",
    }

    @staticmethod
    def _confirm_action(prompt: str, confirm_cb=None) -> bool:
        if confirm_cb:
            try:
                return bool(confirm_cb(prompt))
            except Exception:
                pass
        try:
            answer = input(f"{prompt} [y/N]: ").strip().lower()
            return answer in {"y", "yes"}
        except Exception:
            return False

    @staticmethod
    def _is_path_allowed(path: str) -> bool:
        if not path:
            return True
        expanded = os.path.realpath(os.path.expanduser(path))
        for root in Config.ALLOWED_ROOTS:
            root_path = os.path.realpath(os.path.expanduser(root))
            if expanded == root_path or expanded.startswith(root_path + os.sep):
                return True
        return False

    @staticmethod
    def _extract_paths(action: str, obj: dict) -> list:
        paths = []
        if action in {"open_folder", "list_files", "read_file", "create_file", "write_file", "delete_file", "create_directory", "open_file"}:
            paths.append(obj.get("path", ""))
        if action in {"search_files"}:
            paths.append(obj.get("path", ""))
        if action in {"move_file", "copy_file"}:
            paths.append(obj.get("path", ""))
            paths.append(obj.get("dest", ""))
        if action in {"create_pdf"}:
            paths.append(obj.get("path", ""))
        return [p for p in paths if p]

    @staticmethod
    def _get_plugin_manager() -> PluginManager:
        if CommandExecutor._plugin_manager is None:
            CommandExecutor._plugin_manager = PluginManager()
            CommandExecutor._plugin_manager.load_plugins()
        return CommandExecutor._plugin_manager

    @staticmethod
    def _get_scheduler() -> Scheduler:
        if CommandExecutor._scheduler is None:
            CommandExecutor._scheduler = Scheduler()
        return CommandExecutor._scheduler

    @staticmethod
    def _get_developer_assistant() -> DeveloperAssistant:
        if CommandExecutor._developer_assistant is None:
            CommandExecutor._developer_assistant = DeveloperAssistant()
        return CommandExecutor._developer_assistant
    
    @staticmethod
    def execute(cmd_json: str, ai_engine: AIEngine = None, user_input: str = "", confirm_cb=None) -> str:
        """Execute a JSON command"""
        try:
            # Check if this is a project task (before parsing JSON)
            if ai_engine:
                # Initialize orchestrator if not exists
                if not hasattr(ai_engine, 'project_orchestrator'):
                    ai_engine.project_orchestrator = ProjectOrchestrator(ai_engine)
                
                if ai_engine.project_orchestrator.is_project_task(user_input):
                    logger.info(f"Detected project task: {user_input}")
                    # Get current working directory or project path
                    import os
                    base_path = os.getcwd()
                    result = ai_engine.project_orchestrator.handle_project_request(user_input, base_path)
                    return result
            
            # Apply learned patterns
            if ai_engine and ai_engine.learning_engine:
                learned_cmd = ai_engine.learning_engine.apply_learned_pattern(user_input)
                if learned_cmd:
                    logger.info(f"Using learned pattern for: {user_input}")
                    cmd_json = learned_cmd
            
            obj = json.loads(cmd_json)
            action = obj.get("command", "none")
            
            if action == "none":
                return None  # Question, not command

            plugin_manager = CommandExecutor._get_plugin_manager()
            plugin_handler = plugin_manager.get_handler(action)
            if plugin_handler:
                return plugin_handler(obj, ai_engine, user_input)

            if Config.REQUIRE_CONFIRMATION and action in CommandExecutor.CONFIRM_ACTIONS:
                prompt = f"Confirm action '{action}' for: {user_input}"
                if not CommandExecutor._confirm_action(prompt, confirm_cb=confirm_cb):
                    return "⚠️ Action cancelled."

            if action in CommandExecutor.FILE_ACTIONS:
                paths = CommandExecutor._extract_paths(action, obj)
                if paths and any(not CommandExecutor._is_path_allowed(p) for p in paths):
                    prompt = "This action targets a path outside allowed roots. Continue?"
                    if Config.REQUIRE_CONFIRMATION and not CommandExecutor._confirm_action(prompt, confirm_cb=confirm_cb):
                        return "⚠️ Action cancelled."
            
            # Command mapping
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
                "analyze_screen": lambda: CommandExecutor._analyze_screen_with_ai(ai_engine),
                "analyze_image": lambda: CommandExecutor._analyze_image(ai_engine, obj.get("path", "")),
                "read_screen_text": lambda: CommandEngine.read_screen_text(),
                "automate": lambda: CommandExecutor._execute_automation(obj.get("instruction", user_input), ai_engine),
                "preview_automation": lambda: CommandExecutor._preview_automation(obj.get("instruction", user_input), ai_engine),
                "pause_automation": lambda: CommandExecutor._pause_automation(ai_engine),
                "resume_automation": lambda: CommandExecutor._resume_automation(ai_engine),
                "screen_aware_click": lambda: CommandExecutor._screen_aware_click(obj.get("text", obj.get("query", obj.get("name", ""))), ai_engine),
                "search_github": lambda: CommandEngine.search_github(obj.get("query", "")),
                "open_whatsapp_contact": lambda: CommandEngine.open_whatsapp_contact(obj.get("contact", "")),
                "schedule_task": lambda: CommandExecutor._schedule_task(obj, user_input, ai_engine),
                "list_scheduled_tasks": lambda: CommandExecutor._list_scheduled_tasks(),
                "cancel_scheduled_task": lambda: CommandExecutor._cancel_scheduled_task(obj.get("name", obj.get("text", ""))),
                
                # Project Orchestration
                "create_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "modify_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "refactor_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "fix_project_bug": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),

                # Developer Assistance
                "analyze_project": lambda: CommandExecutor._analyze_project(obj, user_input),
                "search_code": lambda: CommandExecutor._search_code(obj),
                "find_symbol": lambda: CommandExecutor._find_symbol(obj),
                "list_todos": lambda: CommandExecutor._list_todos(obj),
                "find_dead_code": lambda: CommandExecutor._find_dead_code(obj),
                "generate_snippet": lambda: CommandExecutor._generate_snippet(obj),
                "remember_developer_note": lambda: CommandExecutor._remember_developer_note(obj, user_input),
                "recall_developer_memory": lambda: CommandExecutor._recall_developer_memory(obj),
                
                # Packages
                "install_package": lambda: CommandEngine.install_package(obj.get("package", "")),
                "install_python_package": lambda: CommandEngine.install_python_package(obj.get("package", "")),
                "update_system": lambda: CommandEngine.update_system(),
                "check_updates": lambda: CommandEngine.check_updates(),
            }
            
            if action in command_map:
                result = command_map[action]()
                
                # Self-reflect and learn
                if ai_engine and ai_engine.learning_engine:
                    corrected = ai_engine.learning_engine.self_reflect(user_input, action, result)
                    if corrected:
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
                if ai_engine and ai_engine.learning_engine:
                    ai_engine.learning_engine.learn_from_failure(user_input, action, error_msg)
                return error_msg
                
        except json.JSONDecodeError:
            return None  # Treat as question if JSON parsing fails
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            error_msg = f"❌ Execution error: {str(e)}"
            if ai_engine and ai_engine.learning_engine:
                ai_engine.learning_engine.learn_from_failure(user_input, "unknown", error_msg, str(e))
            return error_msg
    
    @staticmethod
    def _analyze_screen_with_ai(ai_engine: AIEngine) -> str:
        """Analyze screen with AI vision"""
        if not ai_engine:
            from jarvis_ai.command_engine import CommandEngine
            return CommandEngine.take_screenshot()
        
        from jarvis_ai.command_engine import CommandEngine
        result = CommandEngine.take_screenshot()
        if "❌" in result:
            return result
        
        try:
            from PIL import Image
            import pyautogui
            
            img = Image.open(CommandExecutor._get_screenshot_path())
            screen_width, screen_height = pyautogui.size()
            
            # Use AI vision for analysis
            analysis = ai_engine.analyze_image(
                CommandExecutor._get_screenshot_path(),
                "Analyze this screen. Describe what you see, including applications, UI elements, text, and actionable items."
            )
            
            return f"📸 Screen Analysis:\n{analysis}"
        except Exception as e:
            return f"❌ Screen analysis error: {str(e)}"
    
    @staticmethod
    def _analyze_image(ai_engine: AIEngine, image_path: str) -> str:
        """Analyze an image file"""
        if not ai_engine:
            return "❌ AI engine required for image analysis"
        
        if not image_path:
            return "❌ No image path specified"
        
        import os
        path = os.path.expanduser(image_path)
        if not os.path.exists(path):
            return f"❌ Image not found: {path}"
        
        return ai_engine.analyze_image(path, "What is in this image? Describe it in detail.")
    
    @staticmethod
    def _execute_automation(instruction: str, ai_engine: AIEngine) -> str:
        """Execute automation"""
        if not ai_engine:
            return "❌ AI engine required for automation"
        
        automation_engine = CommandExecutor._get_automation_engine(ai_engine)
        return automation_engine.automate(instruction)

    @staticmethod
    def _preview_automation(instruction: str, ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        automation_engine = CommandExecutor._get_automation_engine(ai_engine)
        plan = automation_engine.understand_automation(instruction)
        return automation_engine.preview_automation(plan)

    @staticmethod
    def _pause_automation(ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        return CommandExecutor._get_automation_engine(ai_engine).pause()

    @staticmethod
    def _resume_automation(ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        return CommandExecutor._get_automation_engine(ai_engine).resume()

    @staticmethod
    def _screen_aware_click(target: str, ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        return CommandExecutor._get_automation_engine(ai_engine).screen_aware_click(target)
    
    @staticmethod
    def _get_screenshot_path() -> str:
        from jarvis_ai.config import Config
        return Config.SCREENSHOT_PATH

    @staticmethod
    def _get_automation_engine(ai_engine: AIEngine) -> AutomationEngine:
        if not hasattr(ai_engine, "automation_engine"):
            ai_engine.automation_engine = AutomationEngine(ai_engine)
        return ai_engine.automation_engine

    @staticmethod
    def _schedule_task(obj: dict, user_input: str, ai_engine: AIEngine) -> str:
        scheduler = CommandExecutor._get_scheduler()
        scheduler.start(lambda command_text: CommandExecutor._execute_scheduled_command(command_text, ai_engine))
        when_text = obj.get("when", "")
        repeat = obj.get("repeat", "once")
        command = obj.get("instruction") or obj.get("text") or user_input
        name = obj.get("name") or command[:40]

        when = CommandExecutor._parse_schedule_time(when_text, repeat)
        if when is None:
            return "❌ Could not understand schedule time. Use 'YYYY-MM-DD HH:MM' or phrases like 'daily'."
        return scheduler.schedule_task(name, command, when, repeat)

    @staticmethod
    def _list_scheduled_tasks() -> str:
        return CommandExecutor._get_scheduler().list_tasks()

    @staticmethod
    def _cancel_scheduled_task(name: str) -> str:
        if not name:
            return "❌ No scheduled task name provided"
        return CommandExecutor._get_scheduler().cancel_task(name)

    @staticmethod
    def _execute_scheduled_command(command_text: str, ai_engine: AIEngine = None):
        logger.info(f"Scheduled task triggered: {command_text}")
        if not ai_engine:
            return
        cmd_json = ai_engine.interpret_command(
            command_text,
            conversation_context=ai_engine.conversation_history,
            learning_engine=ai_engine.learning_engine,
        )
        try:
            CommandExecutor.execute(cmd_json, ai_engine, command_text)
        except Exception as exc:
            logger.error(f"Scheduled command execution failed: {exc}")

    @staticmethod
    def _parse_schedule_time(when_text: str, repeat: str):
        if when_text:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%H:%M"):
                try:
                    parsed = datetime.strptime(when_text, fmt)
                    if fmt == "%H:%M":
                        now = datetime.now()
                        parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                        if parsed <= now:
                            parsed = parsed + timedelta(days=1)
                    return parsed
                except ValueError:
                    continue
        now = datetime.now()
        if repeat == "daily":
            scheduled = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += timedelta(days=1)
            return scheduled
        if repeat == "weekly":
            return now + timedelta(days=7)
        if repeat == "monthly":
            return now + timedelta(days=30)
        return None

    @staticmethod
    def _analyze_project(obj: dict, user_input: str) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        base_path = obj.get("path", ".")
        request = obj.get("query") or user_input
        return assistant.analyze_project(base_path, request)

    @staticmethod
    def _search_code(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.search_code(obj.get("query", obj.get("text", "")), obj.get("path", "."))

    @staticmethod
    def _find_symbol(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.find_symbol(obj.get("name", obj.get("query", obj.get("text", ""))), obj.get("path", "."))

    @staticmethod
    def _list_todos(obj: dict) -> str:
        return CommandExecutor._get_developer_assistant().list_todos(obj.get("path", "."))

    @staticmethod
    def _find_dead_code(obj: dict) -> str:
        return CommandExecutor._get_developer_assistant().find_dead_code_candidates(obj.get("path", "."))

    @staticmethod
    def _generate_snippet(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.generate_snippet(
            obj.get("snippet_type", obj.get("name", "")).lower(),
            obj.get("text", obj.get("query", "Example")),
            obj.get("framework", ""),
        )

    @staticmethod
    def _remember_developer_note(obj: dict, user_input: str) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        note = obj.get("text") or user_input
        category = obj.get("category") or "project_conventions"
        return assistant.memory.remember(category, note)

    @staticmethod
    def _recall_developer_memory(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.memory.recall(obj.get("category"))
    
    @staticmethod
    def _handle_project_task(ai_engine: AIEngine, user_input: str, base_path: str) -> str:
        """Handle project orchestration tasks"""
        if not ai_engine:
            return "❌ AI engine required for project tasks"
        
        if not hasattr(ai_engine, 'project_orchestrator'):
            ai_engine.project_orchestrator = ProjectOrchestrator(ai_engine)
        
        return ai_engine.project_orchestrator.handle_project_request(user_input, base_path)
