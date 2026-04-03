"""
Type Text in Specific Workspace Terminal - Advanced Automation
For BenX: switch WS, focus konsole/alacritty/terminal, type text
"""
import os
import time
import subprocess
from typing import Optional
from jarvis_ai.workspace_monitor import WorkspaceMonitor
from jarvis_ai.config import Config

def type_in_ws_terminal(workspace: int, text: str) -> str:
    """Switch to WS, focus terminal, type text"""
    if not text:
        return "❌ No text to type"
    
    # 1. Switch to workspace
    ws_result = WorkspaceMonitor.switch_workspace(workspace)
    if "❌" in ws_result:
        return f"❌ Workspace switch failed: {ws_result}"
    
    time.sleep(0.3)  # Compositor settle
    
    # 2. Focus terminal (konsole/alacritty/kitty)
    terminals = ["konsole", "alacritty", "kitty", "gnome-terminal", "xfce4-terminal"]
    for term in terminals:
        focus_result = WorkspaceMonitor.focus_window_by_title(term)
        if "✅" in focus_result:
            break
    else:
        return "❌ No terminal found in WS - open konsole first"
    
    time.sleep(0.2)
    
    # 3. Type text
    import shutil
    if shutil.which("wtype"):
        r = subprocess.run(["wtype", text], capture_output=True, timeout=10)
        if r.returncode == 0:
            return f"✅ Typed '{text}' in WS{workspace} terminal"
        return f"❌ wtype failed: {r.stderr.decode()[:80]}"
    if shutil.which("xdotool"):
        r = subprocess.run(["xdotool", "type", "--clearmodifiers", text], capture_output=True, timeout=10)
        if r.returncode == 0:
            return f"✅ Typed '{text}' in WS{workspace} terminal"
        return f"❌ xdotool failed: {r.stderr.decode()[:80]}"
    return "❌ No typing tool - install wtype: sudo pacman -S wtype" 
    
def send_keys_to_ws_terminal(workspace: int, keys: str) -> str:
    """Send keys/keystrokes to WS terminal"""
    ws_result = WorkspaceMonitor.switch_workspace(workspace)
    if "❌" in ws_result:
        return f"❌ WS switch failed"
    
    time.sleep(0.3)
    
    terminals = ["konsole", "alacritty"]
    for term in terminals:
        if "✅" in WorkspaceMonitor.focus_window_by_title(term):
            break
    else:
        return "❌ No terminal in WS"
    
    time.sleep(0.2)
    
    import shutil
    if shutil.which("wtype"):
        r = subprocess.run(["wtype", "-k", keys], capture_output=True, timeout=10)
        return f"✅ Sent '{keys}' to WS{workspace} terminal" if r.returncode == 0 else f"❌ Key send failed: {r.stderr.decode()[:80]}"
    return "❌ No wtype tool - install: sudo pacman -S wtype" 

if __name__ == "__main__":
    print(type_in_ws_terminal(1, "ls -la"))

