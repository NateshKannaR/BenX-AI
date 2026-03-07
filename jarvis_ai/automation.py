"""
Automation Engine - AI-powered task automation with safety controls.
"""
import json
import logging
import threading
import time
from typing import Callable, Dict, List, Optional

from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.config import Config
from jarvis_ai.screen_analyzer import ScreenAnalyzer

logger = logging.getLogger(__name__)

try:
    import pyautogui

    AUTOMATION_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5
except ImportError:
    AUTOMATION_AVAILABLE = False


class AutomationEngine:
    """AI-powered automation engine with dry-run and step safety."""

    RISKY_ACTIONS = {"click", "click_text", "type", "press", "hotkey", "drag"}

    def __init__(self, ai_engine: AIEngine):
        self.ai_engine = ai_engine
        self.automation_history = []
        self.paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.confirm_callback: Optional[Callable[[str], bool]] = None

    def understand_automation(self, user_instruction: str) -> str:
        """Use AI to convert a user request into a structured automation plan."""
        system_prompt = """You are BenX's automation planner. Break down user tasks into safe, step-by-step automation actions.

Available actions:
- click(x,y)
- click_text(text)
- type(text)
- press(key)
- scroll(direction, amount)
- wait(seconds)
- screenshot()
- analyze_screen()
- hotkey(keys)
- drag(x1,y1,x2,y2,duration)
- screen_aware_click(target_text)

Rules:
- Keep plans minimal and safe.
- Use click_text or screen_aware_click before raw click coordinates whenever possible.
- Include a short human-readable description for every step.
- Return ONLY valid JSON array.
"""

        prompt = f"""User wants to automate: "{user_instruction}"

Return ONLY a valid JSON array like:
[{{"action":"click_text","params":{{"text":"Login"}},"description":"Click the Login button"}}]
"""
        return self.ai_engine.query_groq(system_prompt, prompt)

    def preview_automation(self, automation_plan: str) -> str:
        actions = self._parse_actions(automation_plan)
        if not isinstance(actions, list):
            return "❌ Invalid automation plan format"

        lines = ["🔎 Automation Preview:"]
        for index, action_obj in enumerate(actions, start=1):
            action = action_obj.get("action", "unknown")
            params = action_obj.get("params", {})
            desc = action_obj.get("description", f"Step {index}")
            risk = " [confirm]" if self._is_risky_action(action, params) else ""
            lines.append(f"{index}. {desc} -> {action} {params}{risk}")
        return "\n".join(lines)

    def set_confirm_callback(self, confirm_callback: Optional[Callable[[str], bool]]):
        self.confirm_callback = confirm_callback

    def pause(self) -> str:
        self.paused = True
        self.pause_event.clear()
        return "⏸️ Automation paused"

    def resume(self) -> str:
        self.paused = False
        self.pause_event.set()
        return "▶️ Automation resumed"

    def execute_automation(
        self,
        automation_plan: str,
        dry_run: bool = False,
        require_confirmation: bool = True,
        confirm_callback: Optional[Callable[[str], bool]] = None,
    ) -> str:
        """Execute automation plan with safety options."""
        if not AUTOMATION_AVAILABLE and not dry_run:
            return "❌ Automation not available. Install: pip install pyautogui"

        actions = self._parse_actions(automation_plan)
        if not isinstance(actions, list):
            return "❌ Invalid automation plan format"

        if confirm_callback is not None:
            self.confirm_callback = confirm_callback

        results = [self.preview_automation(automation_plan)]

        for i, action_obj in enumerate(actions, start=1):
            self.pause_event.wait()

            action = action_obj.get("action", "")
            params = action_obj.get("params", {})
            desc = action_obj.get("description", f"Step {i}")

            if require_confirmation and self._is_risky_action(action, params):
                approved = self._confirm_step(f"{desc} ({action} {params})")
                if not approved:
                    results.append(f"⚠️ Step {i}: Skipped by user confirmation")
                    continue

            if dry_run:
                results.append(f"🧪 Step {i}: Dry run only -> {desc}")
                continue

            try:
                outcome = self._execute_action(i, action, params)
                results.append(outcome if outcome else f"✅ Step {i}: {desc}")
                time.sleep(0.2)
            except Exception as exc:
                results.append(f"❌ Step {i} failed: {str(exc)}")
                break

        return "\n".join(results)

    def automate(
        self,
        instruction: str,
        dry_run: bool = False,
        require_confirmation: bool = True,
        confirm_callback: Optional[Callable[[str], bool]] = None,
    ) -> str:
        """Full automation workflow."""
        if not AUTOMATION_AVAILABLE and not dry_run:
            return "❌ Automation not available. Install: pip install pyautogui"

        plan = self.understand_automation(instruction)
        result = self.execute_automation(
            plan,
            dry_run=dry_run,
            require_confirmation=require_confirmation,
            confirm_callback=confirm_callback,
        )

        self.automation_history.append({
            "instruction": instruction,
            "plan": plan,
            "result": result,
            "dry_run": dry_run,
        })
        self._save_state()
        return f"🤖 Automation Result:\n{result}"

    def screen_aware_click(self, target_text: str) -> str:
        if not target_text:
            return "❌ No target text provided"
        coords = ScreenAnalyzer.find_text_on_screen(target_text)
        if not coords:
            return f"❌ Could not find '{target_text}' on screen"
        x, y = coords
        pyautogui.click(x, y)
        return f"✅ Clicked '{target_text}' at ({x}, {y})"

    def _execute_action(self, index: int, action: str, params: Dict) -> str:
        if action == "click":
            x, y = params.get("x", 0), params.get("y", 0)
            pyautogui.click(x, y)
            return f"✅ Step {index}: Clicked at ({x}, {y})"

        if action == "click_text":
            text = params.get("text", "")
            coords = ScreenAnalyzer.find_text_on_screen(text)
            if not coords:
                return f"❌ Step {index} failed: Could not find text '{text}'"
            pyautogui.click(coords[0], coords[1])
            return f"✅ Step {index}: Clicked text '{text}'"

        if action == "screen_aware_click":
            target = params.get("target_text") or params.get("text", "")
            return self.screen_aware_click(target).replace("✅", f"✅ Step {index}:")

        if action == "type":
            text = params.get("text", "")
            pyautogui.typewrite(text)
            return f"✅ Step {index}: Typed '{text[:50]}'"

        if action == "press":
            key = params.get("key", "")
            pyautogui.press(key.lower())
            return f"✅ Step {index}: Pressed '{key}'"

        if action == "wait":
            seconds = params.get("seconds", 1)
            time.sleep(seconds)
            return f"✅ Step {index}: Waited {seconds}s"

        if action == "scroll":
            direction = params.get("direction", "down")
            amount = int(params.get("amount", 3))
            pyautogui.scroll(-amount if direction == "down" else amount)
            return f"✅ Step {index}: Scrolled {direction}"

        if action == "hotkey":
            keys = params.get("keys", "")
            key_list = [key.strip().lower() for key in keys.split("+") if key.strip()]
            pyautogui.hotkey(*key_list)
            return f"✅ Step {index}: Pressed hotkey {keys}"

        if action == "drag":
            x1 = params.get("x1", 0)
            y1 = params.get("y1", 0)
            x2 = params.get("x2", 0)
            y2 = params.get("y2", 0)
            duration = float(params.get("duration", 0.5))
            pyautogui.moveTo(x1, y1)
            pyautogui.dragTo(x2, y2, duration=duration, button="left")
            return f"✅ Step {index}: Dragged from ({x1}, {y1}) to ({x2}, {y2})"

        if action == "screenshot":
            from jarvis_ai.command_engine import CommandEngine

            return f"✅ Step {index}: {CommandEngine.take_screenshot()}"

        if action == "analyze_screen":
            from jarvis_ai.command_engine import CommandEngine

            screenshot_result = CommandEngine.take_screenshot()
            if "❌" in screenshot_result:
                return f"❌ Step {index}: {screenshot_result}"
            analysis = self.ai_engine.analyze_image(
                Config.SCREENSHOT_PATH,
                "Read this UI and summarize the next likely action for the user.",
            )
            return f"✅ Step {index}: Screen analyzed\n{analysis}"

        return f"⚠️ Step {index}: Unknown action '{action}'"

    def _parse_actions(self, automation_plan: str):
        try:
            actions = json.loads(automation_plan)
            return actions if isinstance(actions, list) else None
        except json.JSONDecodeError:
            return None

    def _is_risky_action(self, action: str, params: Dict) -> bool:
        if action in self.RISKY_ACTIONS:
            return True
        if action == "scroll" and abs(int(params.get("amount", 0))) > 10:
            return True
        return False

    def _confirm_step(self, prompt: str) -> bool:
        if self.confirm_callback:
            try:
                return bool(self.confirm_callback(prompt))
            except Exception:
                logger.warning("Automation confirmation callback failed")
        try:
            answer = input(f"Confirm automation step: {prompt} [y/N]: ").strip().lower()
            return answer in {"y", "yes"}
        except Exception:
            return False

    def _save_state(self):
        try:
            payload = {
                "paused": self.paused,
                "history": self.automation_history[-20:],
            }
            with open(Config.AUTOMATION_STATE_FILE, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save automation state: {exc}")
