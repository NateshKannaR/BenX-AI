"""
BenX Agent Orchestrator - True agentic loop (ReAct pattern).
Thought → Action → Observation → Thought → ... → finish()
"""
import json
import logging
import os
import re
import subprocess
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 18

TOOLS_SCHEMA = """
AVAILABLE TOOLS (call exactly one per turn):

shell(cmd)                     - Run ANY bash command. Most powerful tool.
read_file(path)                - Read a file
write_file(path, content)      - Write/overwrite a file
append_file(path, content)     - Append to a file
list_files(path)               - List directory
search_files(path, query)      - Find files matching query
ai_think(prompt)               - Use AI to reason, write, analyze, summarize, generate code
open_app(app)                  - Open an application
open_url(url)                  - Open URL in browser
browser_scrape(url, selector)  - Scrape webpage (selector optional)
browser_search(query)          - Search the web
email_inbox(count)             - Read inbox (count optional, default 5)
email_read(index)              - Read email body (1=latest)
email_send(to, subject, body)  - Send email
notify(title, body, urgency)   - Desktop notification (urgency: low/normal/critical)
screenshot()                   - Take screenshot
system_info()                  - CPU/memory/disk/battery
workspace_state()              - All open windows and workspaces
bluetooth_list()               - List paired bluetooth devices
bluetooth_connect(device)      - Connect bluetooth device
git(cmd)                       - Run git command
python_run(code)               - Execute Python and return output
remember(key, value)           - Save a fact to long-term memory
recall(key)                    - Retrieve a saved fact
finish(answer)                 - DONE. Call when goal is fully accomplished.
"""

REACT_SYSTEM = """You are BenX, an advanced AI agent with full control over a Linux system.
You reason step by step and call tools to accomplish goals autonomously.

RESPONSE FORMAT (strict - every turn):
Thought: <your reasoning about what to do next>
Action: <tool_name>(<params>)

RULES:
- ONE action per response, nothing else after Action line
- Use observations from previous steps to decide next action
- On tool failure: try a different approach, don't give up
- When goal is fully done: finish(<clear answer summarizing what was done>)
- Be decisive - make reasonable assumptions, don't ask for clarification
- shell() can do almost anything on Linux - prefer it for system tasks
- ai_think() for writing, analysis, code generation, summarization
- Chain tools naturally: search → read → write → notify
- If you already have enough info, go straight to finish()
""" + TOOLS_SCHEMA


class AgentOrchestrator:
    """ReAct agentic loop: Thought → Action → Observation → repeat → finish"""

    def __init__(self, ai_engine, executor_cls):
        self.ai = ai_engine
        self.executor_cls = executor_cls
        self.on_step_cb: Optional[Callable] = None

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, user_goal: str, confirm_cb=None) -> Optional[str]:
        """Run agentic loop. Returns answer or None (caller uses simple path)."""
        if not self._needs_agent(user_goal):
            return None

        self._notify(f"🤖 Agent: {user_goal[:70]}")

        # Inject live system context into the first message
        sys_ctx = self._get_system_context()
        user_facts = self._get_user_facts()

        scratchpad: List[Dict] = [{
            "role": "user",
            "content": (
                f"SYSTEM CONTEXT:\n{sys_ctx}\n\n"
                f"USER FACTS:\n{user_facts}\n\n"
                f"GOAL: {user_goal}\n\n"
                "Start working. Think step by step."
            )
        }]

        for iteration in range(MAX_ITERATIONS):
            raw = self._call_ai(scratchpad)
            if not raw:
                break

            thought, tool_name, tool_params = self._parse_react(raw)

            if thought:
                self._notify(f"💭 {thought[:120]}")

            if tool_name == "finish":
                self._notify("✅ Done")
                answer = tool_params.get("answer", raw)
                self._store_in_memory(user_goal, answer)
                return answer

            self._notify(f"🔧 {tool_name}({self._params_preview(tool_params)})")
            observation = self._execute_tool(tool_name, tool_params, confirm_cb)
            self._notify(f"👁️ {str(observation)[:150]}")

            scratchpad.append({"role": "assistant", "content": raw})
            scratchpad.append({
                "role": "user",
                "content": (
                    f"Observation: {observation}\n\n"
                    "Continue. If goal is done → finish(answer). Otherwise next action."
                )
            })

            # Compress scratchpad if getting long to save tokens
            if len(scratchpad) > 24:
                scratchpad = self._compress_scratchpad(scratchpad)

        return self._emergency_finish(user_goal, scratchpad)

    # ── AI call ───────────────────────────────────────────────────────────────

    def _call_ai(self, scratchpad: List[Dict]) -> str:
        try:
            context = scratchpad[-22:]
            last = context[-1]["content"]
            history = context[:-1]
            return self.ai.query_groq(
                REACT_SYSTEM, last,
                conversation_context=history,
                task_type="reason"
            )
        except Exception as e:
            logger.error(f"Agent AI call failed: {e}")
            return ""

    # ── Parse ReAct ───────────────────────────────────────────────────────────

    def _parse_react(self, raw: str) -> tuple:
        thought = ""
        tool_name = "finish"
        tool_params = {"answer": raw}

        tm = re.search(r"Thought:\s*(.+?)(?=Action:|$)", raw, re.DOTALL | re.IGNORECASE)
        if tm:
            thought = tm.group(1).strip()

        # Match Action: tool_name(anything including newlines)
        am = re.search(r"Action:\s*(\w+)\s*\((.*?)\)\s*$", raw, re.DOTALL | re.IGNORECASE)
        if am:
            tool_name = am.group(1).strip().lower()
            tool_params = self._parse_params(tool_name, am.group(2).strip() if am.group(2) else "")
        else:
            # Fallback: any tool call in the text
            fb = re.search(r"\b(\w+)\s*\(([^)]*)\)", raw)
            if fb and fb.group(1).lower() in self._known_tools():
                tool_name = fb.group(1).strip().lower()
                tool_params = self._parse_params(tool_name, fb.group(2).strip())

        return thought, tool_name, tool_params

    def _known_tools(self):
        return {
            "shell", "read_file", "write_file", "append_file", "list_files",
            "search_files", "ai_think", "open_app", "open_url", "browser_scrape",
            "browser_search", "email_inbox", "email_read", "email_send", "notify",
            "screenshot", "system_info", "workspace_state", "bluetooth_list",
            "bluetooth_connect", "git", "python_run", "remember", "recall", "finish"
        }

    def _parse_params(self, tool_name: str, raw: str) -> dict:
        if not raw.strip():
            return {}
        try:
            if raw.strip().startswith("{"):
                return json.loads(raw)
        except Exception:
            pass

        PARAM_MAPS = {
            "shell": ["cmd"], "read_file": ["path"],
            "write_file": ["path", "content"], "append_file": ["path", "content"],
            "list_files": ["path"], "search_files": ["path", "query"],
            "ai_think": ["prompt"], "open_app": ["app"], "open_url": ["url"],
            "browser_scrape": ["url", "selector"], "browser_search": ["query"],
            "email_inbox": ["count"], "email_read": ["index"],
            "email_send": ["to", "subject", "body"],
            "notify": ["title", "body", "urgency"],
            "bluetooth_connect": ["device"], "git": ["cmd"],
            "python_run": ["code"], "remember": ["key", "value"],
            "recall": ["key"], "finish": ["answer"],
        }
        param_names = PARAM_MAPS.get(tool_name, ["value"])
        parts = self._split_params(raw)
        return {
            (param_names[i] if i < len(param_names) else f"arg{i}"): part.strip().strip("\"'")
            for i, part in enumerate(parts)
        }

    def _split_params(self, raw: str) -> List[str]:
        parts, current, depth, in_quote = [], [], 0, None
        for ch in raw:
            if ch in ('"', "'") and in_quote is None:
                in_quote = ch; current.append(ch)
            elif ch == in_quote:
                in_quote = None; current.append(ch)
            elif ch in ("(", "[", "{") and not in_quote:
                depth += 1; current.append(ch)
            elif ch in (")", "]", "}") and not in_quote:
                depth -= 1; current.append(ch)
            elif ch == "," and depth == 0 and not in_quote:
                parts.append("".join(current).strip()); current = []
            else:
                current.append(ch)
        if current:
            parts.append("".join(current).strip())
        return parts

    # ── Tool execution ────────────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, params: dict, confirm_cb=None) -> str:
        try:
            if tool_name == "shell":
                return self._shell(params.get("cmd", ""))
            elif tool_name == "read_file":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.read_file(params.get("path", ""), lines=300)
            elif tool_name == "write_file":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.write_file(params.get("path", ""), params.get("content", ""))
            elif tool_name == "append_file":
                path = os.path.expanduser(params.get("path", ""))
                with open(path, "a", encoding="utf-8") as f:
                    f.write(params.get("content", "") + "\n")
                return f"✅ Appended to {path}"
            elif tool_name == "list_files":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.list_files(params.get("path", "."))
            elif tool_name == "search_files":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.search_files(params.get("query", ""), params.get("path", "."))
            elif tool_name == "ai_think":
                return self.ai.query_groq(
                    "You are BenX. Think carefully and provide a thorough, accurate response.",
                    params.get("prompt", ""), task_type="reason"
                )
            elif tool_name == "open_app":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.open_app(params.get("app", ""))
            elif tool_name == "open_url":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.open_url(params.get("url", ""))
            elif tool_name == "browser_scrape":
                from jarvis_ai.browser_automation import BrowserAutomation
                return BrowserAutomation.scrape(params.get("url", ""), params.get("selector", "body"))
            elif tool_name == "browser_search":
                from jarvis_ai.browser_automation import BrowserAutomation
                return BrowserAutomation.search_and_scrape(params.get("query", ""))
            elif tool_name == "email_inbox":
                from jarvis_ai.email_manager import EmailManager
                return EmailManager.read_inbox(int(params.get("count", 5)))
            elif tool_name == "email_read":
                from jarvis_ai.email_manager import EmailManager
                return EmailManager.read_email_body(int(params.get("index", 1)))
            elif tool_name == "email_send":
                from jarvis_ai.email_manager import EmailManager
                return EmailManager.send(params.get("to", ""), params.get("subject", ""), params.get("body", ""))
            elif tool_name == "notify":
                from jarvis_ai.notification_sender import NotificationSender
                return NotificationSender.send(params.get("title", "BenX"), params.get("body", ""), params.get("urgency", "normal"))
            elif tool_name == "screenshot":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.take_screenshot()
            elif tool_name == "system_info":
                from jarvis_ai.command_engine import CommandEngine
                return CommandEngine.system_info()
            elif tool_name == "workspace_state":
                from jarvis_ai.workspace_monitor import WorkspaceMonitor
                return WorkspaceMonitor.full_state_summary()
            elif tool_name == "bluetooth_list":
                from jarvis_ai.bluetooth_manager import BluetoothManager
                return BluetoothManager.list_paired()
            elif tool_name == "bluetooth_connect":
                from jarvis_ai.bluetooth_manager import BluetoothManager
                return BluetoothManager.connect(params.get("device", ""))
            elif tool_name == "git":
                return self._shell(f"git {params.get('cmd', 'status')}")
            elif tool_name == "python_run":
                return self._run_python(params.get("code", ""))
            elif tool_name == "remember":
                self._save_fact(params.get("key", ""), params.get("value", ""))
                return f"✅ Remembered: {params.get('key')} = {params.get('value')}"
            elif tool_name == "recall":
                return self._load_fact(params.get("key", ""))
            elif tool_name == "finish":
                return params.get("answer", "Done.")
            else:
                cmd_json = json.dumps({"command": tool_name, **params})
                result = self.executor_cls.execute(cmd_json, self.ai, tool_name, confirm_cb)
                return result or "✅ Done"
        except Exception as e:
            return f"❌ {tool_name} failed: {e}"

    def _shell(self, cmd: str) -> str:
        if not cmd:
            return "❌ Empty command"
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=45,
                env={**os.environ, "TERM": "xterm"}
            )
            out = (r.stdout + r.stderr).strip()
            return out[:4000] if out else "✅ Done (no output)"
        except subprocess.TimeoutExpired:
            return "❌ Timed out after 45s"
        except Exception as e:
            return f"❌ Shell error: {e}"

    def _run_python(self, code: str) -> str:
        if not code:
            return "❌ No code"
        try:
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(code, {"__builtins__": __builtins__})  # noqa
            return buf.getvalue().strip() or "✅ Executed (no output)"
        except Exception as e:
            return f"❌ Python error: {e}"

    # ── Memory helpers ────────────────────────────────────────────────────────

    def _save_fact(self, key: str, value: str):
        try:
            from jarvis_ai.config import Config
            facts_file = Config.BENX_DIR / "user_facts.json"
            facts = {}
            if facts_file.exists():
                facts = json.loads(facts_file.read_text())
            facts[key.lower().strip()] = value
            facts_file.write_text(json.dumps(facts, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save fact: {e}")

    def _load_fact(self, key: str) -> str:
        try:
            from jarvis_ai.config import Config
            facts_file = Config.BENX_DIR / "user_facts.json"
            if facts_file.exists():
                facts = json.loads(facts_file.read_text())
                val = facts.get(key.lower().strip())
                return f"{key} = {val}" if val else f"No fact stored for '{key}'"
        except Exception:
            pass
        return f"No fact stored for '{key}'"

    def _get_user_facts(self) -> str:
        try:
            from jarvis_ai.config import Config
            facts_file = Config.BENX_DIR / "user_facts.json"
            if facts_file.exists():
                facts = json.loads(facts_file.read_text())
                if facts:
                    return "\n".join(f"  {k}: {v}" for k, v in list(facts.items())[:10])
        except Exception:
            pass
        return "  (none stored yet)"

    def _store_in_memory(self, goal: str, answer: str):
        try:
            if hasattr(self.ai, "rag_engine"):
                self.ai.rag_engine.add_document(
                    f"Agent task: {goal}\nResult: {answer[:300]}",
                    metadata={"type": "agent_result"}
                )
        except Exception:
            pass

    # ── Context ───────────────────────────────────────────────────────────────

    def _get_system_context(self) -> str:
        parts = []
        try:
            import psutil
            from datetime import datetime
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            parts.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            parts.append(f"CPU: {cpu:.1f}%  Memory: {mem.percent:.1f}%  Disk: {disk.percent:.1f}%")
            bat = psutil.sensors_battery()
            if bat:
                parts.append(f"Battery: {bat.percent:.0f}% ({'charging' if bat.power_plugged else 'discharging'})")
        except Exception:
            pass
        try:
            from jarvis_ai.workspace_monitor import WorkspaceMonitor
            parts.append(WorkspaceMonitor.full_state_summary())
        except Exception:
            pass
        return "\n".join(parts) if parts else "System context unavailable"

    # ── Needs agent detection ─────────────────────────────────────────────────

    def _needs_agent(self, goal: str) -> bool:
        g = goal.strip().lower()

        # Definitely simple — skip agent
        simple = [
            r"^(open|launch|start)\s+\w+(\s+\w+)?$",
            r"^(volume|brightness)\s+\d+",
            r"^(mute|unmute|lock|shutdown|restart|suspend|hibernate)$",
            r"^set (volume|brightness) to \d+",
            r"^(play|pause|next|previous)(\s+music|\s+track)?$",
            r"^(what time|what's the time|current time)",
            r"^(battery|disk usage|system info|network status)$",
            r"^(list|show) (wifi|bluetooth|processes|apps)$",
            r"^take (a )?screenshot$",
            r"^(hello|hi|hey|thanks|thank you)",
        ]
        for pat in simple:
            if re.match(pat, g):
                return False

        # Definitely needs agent
        agent_signals = [
            "and then", "after that", "then ", " and ",
            "create a", "build a", "set up", "configure", "install and",
            "research", "find and", "search and",
            "write a", "generate", "make a", "organize",
            "fix", "debug", "refactor", "improve", "optimize",
            "send.*email", "notify.*when", "monitor",
            "download", "scrape", "extract",
            "analyze", "summarize", "compare",
            "check.*and", "read.*and", "scan",
            "deploy", "test", "run", "execute",
            "backup", "restore", "migrate",
            "find all", "list all", "show all",
            "what's in", "what is in",
            "help me", "can you",
        ]
        if any(s in g for s in agent_signals):
            return True

        # Long requests are usually complex
        return len(goal.split()) > 8

    # ── Scratchpad compression ────────────────────────────────────────────────

    def _compress_scratchpad(self, scratchpad: List[Dict]) -> List[Dict]:
        """Keep first message + last 12 messages to save context."""
        if len(scratchpad) <= 14:
            return scratchpad
        first = scratchpad[0]
        recent = scratchpad[-12:]
        summary_msg = {
            "role": "user",
            "content": f"[Earlier steps compressed. Continuing from step {len(scratchpad)//2}...]"
        }
        return [first, summary_msg] + recent

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _params_preview(self, params: dict) -> str:
        if not params:
            return ""
        parts = [f"{k}={str(v)[:35]!r}" for k, v in list(params.items())[:2]]
        return ", ".join(parts)

    def _emergency_finish(self, goal: str, scratchpad: List[Dict]) -> str:
        observations = [
            m["content"] for m in scratchpad
            if m["role"] == "user" and m["content"].startswith("Observation:")
        ]
        summary = "\n".join(observations[-6:])
        try:
            return self.ai.query_groq(
                "You are BenX. Summarize what was accomplished. Be concise and clear.",
                f"Goal: {goal}\n\nLast observations:\n{summary}",
                task_type="chat"
            )
        except Exception:
            return f"⚠️ Reached step limit.\n{summary[:600]}"

    def _notify(self, message: str):
        logger.info(message)
        if self.on_step_cb:
            try:
                self.on_step_cb(message)
            except Exception:
                pass
