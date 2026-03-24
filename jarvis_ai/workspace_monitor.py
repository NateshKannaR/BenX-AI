"""
Workspace Monitor - Full Hyprland workspace awareness for BenX
"""
import json
import logging
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _hyprctl(cmd: str) -> Optional[dict | list]:
    try:
        result = subprocess.run(
            ["hyprctl", cmd, "-j"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"hyprctl {cmd} failed: {e}")
    return None


def _hyprctl_dispatch(cmd: str) -> bool:
    try:
        result = subprocess.run(
            ["hyprctl", "dispatch"] + cmd.split(),
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"hyprctl dispatch {cmd} failed: {e}")
        return False


class WorkspaceMonitor:
    """Full Hyprland workspace state - what's open, where, and what's focused"""

    @staticmethod
    def get_all_workspaces() -> List[Dict]:
        return _hyprctl("workspaces") or []

    @staticmethod
    def get_all_clients() -> List[Dict]:
        return _hyprctl("clients") or []

    @staticmethod
    def get_active_window() -> Optional[Dict]:
        return _hyprctl("activewindow")

    @staticmethod
    def get_active_workspace_id() -> int:
        aw = WorkspaceMonitor.get_active_window()
        if aw:
            return aw.get("workspace", {}).get("id", -1)
        return -1

    @staticmethod
    def get_workspace_map() -> Dict[int, List[Dict]]:
        """Returns {workspace_id: [client, ...]} mapping"""
        clients = WorkspaceMonitor.get_all_clients()
        ws_map: Dict[int, List[Dict]] = {}
        for client in clients:
            ws_id = client.get("workspace", {}).get("id", -1)
            ws_map.setdefault(ws_id, []).append(client)
        return ws_map

    @staticmethod
    def full_state_summary() -> str:
        """Human-readable full workspace state for AI context"""
        workspaces = WorkspaceMonitor.get_all_workspaces()
        ws_map = WorkspaceMonitor.get_workspace_map()
        active_ws_id = WorkspaceMonitor.get_active_workspace_id()
        active_win = WorkspaceMonitor.get_active_window()

        lines = ["🖥️ WORKSPACE STATE:"]

        for ws in sorted(workspaces, key=lambda w: w.get("id", 0)):
            ws_id = ws.get("id")
            ws_name = ws.get("name", str(ws_id))
            monitor = ws.get("monitor", "?")
            is_active = "◀ ACTIVE" if ws_id == active_ws_id else ""
            clients = ws_map.get(ws_id, [])

            lines.append(f"\n  Workspace {ws_name} [{monitor}] {is_active}")
            if clients:
                for c in clients:
                    title = c.get("title", "?")
                    cls = c.get("class", "?")
                    floating = " [floating]" if c.get("floating") else ""
                    fullscreen = " [fullscreen]" if c.get("fullscreen") else ""
                    lines.append(f"    • [{cls}] {title}{floating}{fullscreen}")
            else:
                lines.append("    (empty)")

        if active_win:
            lines.append(f"\n🎯 FOCUSED: [{active_win.get('class','?')}] {active_win.get('title','?')} (WS {active_ws_id})")

        return "\n".join(lines)

    # ── Control methods ──────────────────────────────────────────────

    @staticmethod
    def switch_workspace(ws_id: int) -> str:
        if _hyprctl_dispatch(f"workspace {ws_id}"):
            return f"✅ Switched to workspace {ws_id}"
        return f"❌ Failed to switch to workspace {ws_id}"

    @staticmethod
    def move_window_to_workspace(ws_id: int) -> str:
        if _hyprctl_dispatch(f"movetoworkspace {ws_id}"):
            return f"✅ Moved active window to workspace {ws_id}"
        return f"❌ Failed to move window to workspace {ws_id}"

    @staticmethod
    def focus_window_by_title(title: str) -> str:
        clients = WorkspaceMonitor.get_all_clients()
        for c in clients:
            if title.lower() in c.get("title", "").lower() or title.lower() in c.get("class", "").lower():
                addr = c.get("address", "")
                if _hyprctl_dispatch(f"focuswindow address:{addr}"):
                    ws_id = c.get("workspace", {}).get("id")
                    _hyprctl_dispatch(f"workspace {ws_id}")
                    return f"✅ Focused [{c.get('class')}] {c.get('title')} on workspace {ws_id}"
        return f"❌ No window matching '{title}' found"

    @staticmethod
    def close_active_window() -> str:
        if _hyprctl_dispatch("killactive"):
            return "✅ Closed active window"
        return "❌ Failed to close window"

    @staticmethod
    def toggle_fullscreen() -> str:
        if _hyprctl_dispatch("fullscreen 0"):
            return "✅ Toggled fullscreen"
        return "❌ Failed to toggle fullscreen"

    @staticmethod
    def toggle_float() -> str:
        if _hyprctl_dispatch("togglefloating"):
            return "✅ Toggled floating"
        return "❌ Failed to toggle floating"

    @staticmethod
    def find_app_workspace(app_name: str) -> str:
        # Self-referential: user asking about BenX itself
        SELF_ALIASES = {"you", "yourself", "benx", "this", "current_app", "self", "this app", "ben"}
        if app_name.lower().strip() in SELF_ALIASES or not app_name.strip():
            app_name = "benx"

        clients = WorkspaceMonitor.get_all_clients()
        matches = [
            c for c in clients
            if app_name.lower() in c.get("title", "").lower()
            or app_name.lower() in c.get("class", "").lower()
        ]
        if not matches:
            return f"❌ '{app_name}' is not open in any workspace"
        lines = [f"🔍 '{app_name}' found in:"]
        for c in matches:
            ws_id = c.get("workspace", {}).get("id", "?")
            lines.append(f"  • Workspace {ws_id}: [{c.get('class')}] {c.get('title')}")
        return "\n".join(lines)

    @staticmethod
    def list_workspaces_summary() -> str:
        return WorkspaceMonitor.full_state_summary()
