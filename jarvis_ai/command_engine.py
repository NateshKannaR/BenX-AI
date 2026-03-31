"""
Command Engine - System command execution
"""
import os
import re
import shlex
import logging
import psutil
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from jarvis_ai.config import Config
from jarvis_ai.utils import run_cmd, find_tool, safe_open_app

logger = logging.getLogger(__name__)

# Check optional dependencies
try:
    from PIL import Image
    import pytesseract
    import os
    # Set TESSDATA_PREFIX if not already set
    if 'TESSDATA_PREFIX' not in os.environ:
        os.environ['TESSDATA_PREFIX'] = '/usr/share/tessdata/'
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pyautogui
    AUTOMATION_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5
except ImportError:
    AUTOMATION_AVAILABLE = False

class CommandEngine:
    """System command execution engine"""

    GITHUB_QUERY_STOPWORDS = {
        "github", "repo", "repos", "repository", "repositories", "how", "many",
        "does", "do", "have", "has", "user", "users", "account", "profile",
        "on", "in", "for", "the", "a", "an", "of", "find", "search", "count",
        "number", "show", "me", "public", "stats", "stat",
    }

    @staticmethod
    def _normalize_phone_number(contact: str) -> str:
        if not contact:
            return ""

        trimmed = contact.strip()
        prefix = "+" if trimmed.startswith("+") else ""
        digits = re.sub(r"\D", "", trimmed)
        if len(digits) < 8:
            return ""
        return f"{prefix}{digits}" if prefix else digits

    @staticmethod
    def _looks_like_phone_number(contact: str) -> bool:
        return bool(CommandEngine._normalize_phone_number(contact))

    @staticmethod
    def _press_enter_after_delay(delay_seconds: float = 8.0) -> None:
        if not AUTOMATION_AVAILABLE:
            return

        def _send():
            try:
                import time
                time.sleep(delay_seconds)
                pyautogui.press("enter")
            except Exception as exc:
                logger.warning(f"WhatsApp auto-send failed: {exc}")

        import threading
        threading.Thread(target=_send, daemon=True).start()

    @staticmethod
    def _github_api_get(path: str):
        url = f"https://api.github.com{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "BenX-AI",
        }
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            url,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _github_profile_page_get(username: str) -> str:
        url = f"https://github.com/{urllib.parse.quote(username)}?tab=repositories"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "BenX-AI",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")

    @staticmethod
    def _extract_repo_count_from_profile_html(html: str) -> int | None:
        patterns = [
            r'href="/[^"/?]+[?]?tab=repositories"[^>]*>\s*Repositories\s*<span[^>]*>([\d,]+)</span>',
            r'count[^>]*>\s*([\d,]+)\s*</span>\s*repositories',
            r'"public_repos":\s*([0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_github_username(query: str) -> str:
        if not query:
            return ""

        text = query.strip()
        lower = text.lower()

        url_match = re.search(r"github\.com/([a-zA-Z0-9-]{1,39})", text, re.IGNORECASE)
        if url_match:
            return url_match.group(1)

        explicit_match = re.search(
            r"(?:for|user|username|account|profile)\s+([a-zA-Z0-9-]{1,39})\b",
            lower,
            re.IGNORECASE,
        )
        if explicit_match and explicit_match.group(1) not in CommandEngine.GITHUB_QUERY_STOPWORDS:
            return explicit_match.group(1)

        candidates = re.findall(r"\b[a-zA-Z0-9-]{1,39}\b", lower)
        filtered = [token for token in candidates if token not in CommandEngine.GITHUB_QUERY_STOPWORDS]
        return filtered[-1] if filtered else ""

    @staticmethod
    def _looks_like_github_user_question(query: str) -> bool:
        lowered = (query or "").lower()
        markers = (
            "repository", "repositories", "repo", "repos", "profile",
            "followers", "following", "github user", "github account",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def github_user_summary(username: str) -> str:
        if not username:
            return "❌ No GitHub username specified"

        try:
            data = CommandEngine._github_api_get(f"/users/{username}")
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                try:
                    html = CommandEngine._github_profile_page_get(username)
                    repo_count = CommandEngine._extract_repo_count_from_profile_html(html)
                    if repo_count is not None:
                        return (
                            f"GitHub user {username} has {repo_count} public repositories.\n"
                            f"Profile: https://github.com/{username}?tab=repositories\n"
                            f"Note: API access was rate-limited, so this count came from the public profile page."
                        )
                except Exception:
                    pass
                return (
                    f"❌ GitHub API rate-limited or forbidden for '{username}' (HTTP 403).\n"
                    f"Set `GITHUB_TOKEN` to improve reliability, or open: https://github.com/{username}?tab=repositories"
                )
            if exc.code == 404:
                return f"❌ GitHub user '{username}' not found"
            return f"❌ GitHub request failed: HTTP {exc.code}"
        except Exception as exc:
            return f"❌ GitHub request failed: {str(exc)}"

        login = data.get("login", username)
        public_repos = data.get("public_repos", 0)
        followers = data.get("followers", 0)
        following = data.get("following", 0)
        profile_url = data.get("html_url", f"https://github.com/{login}")
        name = data.get("name") or login

        return (
            f"GitHub user {name} ({login}) has {public_repos} public repositories, "
            f"{followers} followers, and follows {following} users.\n"
            f"Profile: {profile_url}"
        )

    @staticmethod
    def _try_open_commands(commands) -> bool:
        """Try launcher commands in order until one succeeds."""
        for command in commands:
            if safe_open_app(command):
                return True
        return False
    
    @staticmethod
    def open_app(app: str) -> str:
        if not app:
            return "❌ No application specified"
        
        app_mappings = {
            "chrome": "chromium", "firefox": "firefox", "code": "code",
            "terminal": os.getenv("TERMINAL", "alacritty"),
            "calculator": "gnome-calculator", "files": "nautilus",
            "editor": os.getenv("EDITOR", "nano"), "browser": "firefox"
        }
        
        normalized_app = app.lower().strip()
        app_name = app_mappings.get(normalized_app, app)

        if normalized_app in {"whatsapp", "whats app"}:
            whatsapp_commands = [
                ["whatsapp"],
                ["whatsapp-for-linux"],
                ["flatpak", "run", "io.github.mimbrero.WhatsAppDesktop"],
                ["flatpak", "run", "com.rtosta.zapzap"],
            ]
            if CommandEngine._try_open_commands(whatsapp_commands):
                return "✅ Opened WhatsApp"

            success, _ = run_cmd("xdg-open https://web.whatsapp.com")
            if success:
                return "✅ Opened WhatsApp Web"
            return "❌ Could not open WhatsApp"

        if safe_open_app(app_name):
            return f"✅ Opened {app_name}"

        success, _ = run_cmd(f"xdg-open {shlex.quote(app_name)}")
        return f"✅ Opened {app_name}" if success else f"❌ Could not open {app}"
    
    @staticmethod
    def list_running_apps() -> str:
        try:
            apps = {}
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name not in apps:
                        apps[name] = proc.info['pid']
                except:
                    continue
            
            result = "📱 Running Applications:\n"
            for name, pid in sorted(list(apps.items())[:20]):
                result += f"  • {name} (PID: {pid})\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Audio Control
    @staticmethod
    def set_volume(level: int) -> str:
        level = max(Config.MIN_VOLUME, min(Config.MAX_VOLUME, level))
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --set-volume {level}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {level}%")
        elif tool == "pactl":
            success, _ = run_cmd(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
        else:
            return f"❌ Unsupported tool: {tool}"
        
        return f"✅ Volume set to {level}%" if success else "❌ Failed to set volume"
    
    @staticmethod
    def increase_volume(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --increase {amount}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {amount}%+")
        else:
            return "❌ Volume control failed"
        
        return f"✅ Volume increased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def decrease_volume(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, _ = run_cmd(f"pamixer --decrease {amount}")
        elif tool == "amixer":
            success, _ = run_cmd(f"amixer set Master {amount}%-")
        else:
            return "❌ Volume control failed"
        
        return f"✅ Volume decreased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def mute_volume() -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        success, _ = run_cmd(f"{tool} --toggle-mute" if tool == "pamixer" else "amixer set Master toggle")
        return "✅ Volume toggled" if success else "❌ Failed"
    
    @staticmethod
    def get_volume() -> str:
        tool = find_tool(Config.TOOLS["volume"])
        if not tool:
            return "❌ No volume control found"
        
        if tool == "pamixer":
            success, output = run_cmd("pamixer --get-volume")
        else:
            success, output = run_cmd("amixer get Master | grep -oP '\\[\\K[0-9]+(?=%\\])' | head -1", shell=True)
        
        return f"🔊 Volume: {output}%" if success else "❌ Failed to get volume"
    
    # Brightness Control
    @staticmethod
    def set_brightness(level: int) -> str:
        level = max(Config.MIN_BRIGHTNESS, min(Config.MAX_BRIGHTNESS, level))
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set {level}%")
        elif tool == "light":
            success, _ = run_cmd(f"light -S {level}")
        elif tool == "xbacklight":
            success, _ = run_cmd(f"xbacklight -set {level}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness set to {level}%" if success else "❌ Failed"
    
    @staticmethod
    def increase_brightness(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set +{amount}%")
        elif tool == "light":
            success, _ = run_cmd(f"light -A {amount}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness increased by {amount}%" if success else "❌ Failed"
    
    @staticmethod
    def decrease_brightness(amount: int = 5) -> str:
        tool = find_tool(Config.TOOLS["brightness"])
        if not tool:
            return "❌ No brightness control found"
        
        if tool == "brightnessctl":
            success, _ = run_cmd(f"brightnessctl set {amount}%-")
        elif tool == "light":
            success, _ = run_cmd(f"light -U {amount}")
        else:
            return "❌ Brightness control failed"
        
        return f"✅ Brightness decreased by {amount}%" if success else "❌ Failed"
    
    # File Operations
    @staticmethod
    def open_folder(path: str) -> str:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"❌ Path does not exist: {path}"
        
        tool = find_tool(Config.TOOLS["file_manager"])
        if tool:
            success = safe_open_app([tool, path])
        else:
            success, _ = run_cmd(f"xdg-open {shlex.quote(path)}")
        
        return f"✅ Opened {path}" if success else f"❌ Failed to open {path}"
    
    @staticmethod
    def list_files(path: str = ".") -> str:
        path = os.path.expanduser(path)
        try:
            files = list(Path(path).iterdir())
            if not files:
                return f"📁 Empty directory: {path}"
            
            result = f"📁 Files in {path}:\n"
            for item in sorted(files)[:30]:
                icon = "📁" if item.is_dir() else "📄"
                size = item.stat().st_size if item.is_file() else 0
                result += f"  {icon} {item.name} ({size} bytes)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def search_files(query: str, path: str = ".") -> str:
        if not query:
            return "❌ No search query"
        
        path = os.path.expanduser(path)
        try:
            matches = list(Path(path).rglob(f"*{query}*"))[:20]
            if not matches:
                return f"🔍 No files found matching '{query}'"
            
            result = f"🔍 Found {len(matches)} files:\n"
            for match in matches:
                result += f"  📄 {match}\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def read_file(path: str, lines: int = 50) -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
                preview = ''.join(content[:lines])
                
                result = f"📄 {path} ({len(content)} lines):\n"
                result += "─" * 50 + "\n" + preview
                if len(content) > lines:
                    result += f"\n... ({len(content) - lines} more lines)"
                return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_file(path: str, text: str = "") -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return f"✅ Created file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def write_file(path: str, text: str = "") -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return f"✅ Wrote to file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def delete_file(path: str) -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                return f"✅ Deleted directory: {path}"
            else:
                os.remove(path)
                return f"✅ Deleted file: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_directory(path: str) -> str:
        if not path:
            return "❌ No path specified"
        
        path = os.path.expanduser(path)
        try:
            os.makedirs(path, exist_ok=True)
            return f"✅ Created directory: {path}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def move_file(source: str, dest: str) -> str:
        if not source or not dest:
            return "❌ Source and destination required"
        
        source = os.path.expanduser(source)
        dest = os.path.expanduser(dest)
        try:
            import shutil
            shutil.move(source, dest)
            return f"✅ Moved {source} to {dest}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def copy_file(source: str, dest: str) -> str:
        if not source or not dest:
            return "❌ Source and destination required"
        
        source = os.path.expanduser(source)
        dest = os.path.expanduser(dest)
        try:
            import shutil
            shutil.copy2(source, dest)
            return f"✅ Copied {source} to {dest}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def create_pdf(content: str, output_path: str) -> str:
        """Create a PDF using pure Python stdlib — no dependencies needed."""
        import struct, zlib, time

        if not output_path:
            output_path = os.path.expanduser("~/benx_output.pdf")
        output_path = os.path.expanduser(output_path)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        # ── page geometry ──────────────────────────────────────────────────────
        PW, PH   = 595, 842          # A4 points
        MARGIN   = 50
        LINE_H   = 14
        FONT_SZ  = 11
        MAX_W    = PW - 2 * MARGIN   # ~495 pts  ≈ 82 chars at 6pt/char
        CHARS_PER_LINE = MAX_W // (FONT_SZ * 0.55)  # rough estimate

        # ── word-wrap lines ────────────────────────────────────────────────────
        def wrap(text: str) -> list:
            out = []
            for raw in text.split("\n"):
                if not raw.strip():
                    out.append("")
                    continue
                words, cur = raw.split(), ""
                for w in words:
                    if len(cur) + len(w) + 1 <= CHARS_PER_LINE:
                        cur = (cur + " " + w).lstrip()
                    else:
                        if cur:
                            out.append(cur)
                        cur = w
                if cur:
                    out.append(cur)
            return out

        lines = wrap(content)

        # ── build PDF pages ────────────────────────────────────────────────────
        def _page_stream(page_lines):
            ops = []
            ops.append(f"BT")
            ops.append(f"/F1 {FONT_SZ} Tf")
            y = PH - MARGIN
            for ln in page_lines:
                safe = ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                ops.append(f"{MARGIN} {y} Td" if y == PH - MARGIN else f"0 -{LINE_H} Td")
                ops.append(f"({safe}) Tj")
                y -= LINE_H
            ops.append("ET")
            return "\n".join(ops).encode()

        lines_per_page = (PH - 2 * MARGIN) // LINE_H
        pages = [lines[i:i + lines_per_page] for i in range(0, max(len(lines), 1), lines_per_page)]

        # ── assemble PDF objects ───────────────────────────────────────────────
        buf = bytearray()
        offsets = []

        def add(obj_id, data: bytes):
            offsets.append((obj_id, len(buf)))
            buf.extend(f"{obj_id} 0 obj\n".encode())
            buf.extend(data)
            buf.extend(b"\nendobj\n")

        buf.extend(b"%PDF-1.4\n")

        # obj 1 = catalog, obj 2 = pages (filled later), obj 3 = font
        # page objects start at 4
        page_obj_ids = list(range(4, 4 + len(pages)))
        stream_obj_ids = list(range(4 + len(pages), 4 + 2 * len(pages)))

        # font
        add(3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

        # page streams
        for i, pg in enumerate(pages):
            s = _page_stream(pg)
            add(stream_obj_ids[i],
                f"<< /Length {len(s)} >>\nstream\n".encode() + s + b"\nendstream")

        # page objects
        for i, oid in enumerate(page_obj_ids):
            add(oid,
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PW} {PH}] "
                f"/Contents {stream_obj_ids[i]} 0 R "
                f"/Resources << /Font << /F1 3 0 R >> >> >>".encode())

        # pages dict
        kids = " ".join(f"{oid} 0 R" for oid in page_obj_ids)
        add(2, f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())

        # catalog
        add(1, b"<< /Type /Catalog /Pages 2 0 R >>")

        # xref
        xref_pos = len(buf)
        all_objs = sorted(offsets, key=lambda x: x[0])
        buf.extend(f"xref\n0 {len(all_objs)+1}\n".encode())
        buf.extend(b"0000000000 65535 f \n")
        for _, off in all_objs:
            buf.extend(f"{off:010d} 00000 n \n".encode())
        buf.extend(
            f"trailer\n<< /Size {len(all_objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode()
        )

        try:
            with open(output_path, "wb") as f:
                f.write(buf)
            return f"✅ Created PDF: {output_path}"
        except Exception as e:
            return f"❌ PDF write error: {e}"
    
    @staticmethod
    def open_file(path: str) -> str:
        if not path:
            return "❌ No file path specified"
        
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"❌ File does not exist: {path}"
        
        success, _ = run_cmd(f"xdg-open {shlex.quote(path)}")
        return f"✅ Opened {path}" if success else f"❌ Failed to open {path}"
    
    @staticmethod
    def take_screenshot() -> str:
        import time
        tool = find_tool(Config.TOOLS["screenshot"])
        if not tool:
            return "❌ No screenshot tool found"

        # Hide any BenX GTK windows so they don't appear in the screenshot
        try:
            import gi
            gi.require_version('Gtk', '4.0')
            from gi.repository import GLib
            # Signal all BenX windows to hide, wait for compositor to redraw
            success_hide, _ = run_cmd("hyprctl dispatch focuswindow class:^((?!BenX).)*$", shell=False)
        except Exception:
            pass
        time.sleep(0.4)  # Give compositor time to redraw without BenX

        path = Config.SCREENSHOT_PATH
        success, _ = run_cmd(f"{tool} {path}")
        return f"✅ Screenshot saved to {path}" if success else "❌ Failed to take screenshot"
    
    # Process Management
    @staticmethod
    def kill_process(process_name: str) -> str:
        if not process_name:
            return "❌ No process specified"
        
        try:
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        proc.kill()
                        killed.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed:
                return f"✅ Killed: {', '.join(killed)}"
            return f"❌ Process '{process_name}' not found"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def list_processes() -> str:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc.info['cpu_percent'] = proc.cpu_percent(interval=0.1)
                    processes.append(proc.info)
                except:
                    continue
            
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            result = "🖥️ Top Processes:\n"
            for proc in processes[:15]:
                result += f"  • {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']:.1f}%, Mem: {proc['memory_percent']:.1f}%)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def find_process(query: str) -> str:
        if not query:
            return "❌ No query specified"
        
        try:
            matches = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if query.lower() in proc.info['name'].lower():
                        matches.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except:
                    continue
            
            if matches:
                result = f"🔍 Found {len(matches)} processes:\n"
                for match in matches[:10]:
                    result += f"  • {match}\n"
                return result
            return f"❌ No processes found matching '{query}'"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # System Control
    @staticmethod
    def lock_screen() -> str:
        success, _ = run_cmd("loginctl lock-session")
        return "✅ Screen locked" if success else "❌ Failed to lock screen"
    
    @staticmethod
    def shutdown() -> str:
        success, _ = run_cmd("shutdown now")
        return "✅ Shutting down..." if success else "❌ Failed to shutdown"
    
    @staticmethod
    def restart() -> str:
        success, _ = run_cmd("reboot")
        return "✅ Restarting..." if success else "❌ Failed to restart"
    
    @staticmethod
    def suspend() -> str:
        success, _ = run_cmd("systemctl suspend")
        return "✅ Suspending..." if success else "❌ Failed to suspend"
    
    @staticmethod
    def battery() -> str:
        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = "🔌 Charging" if battery.power_plugged else "🔋 Battery"
                time_left = f" ({battery.secsleft // 3600}h {(battery.secsleft % 3600) // 60}m)" if battery.secsleft > 0 else ""
                return f"{plugged}: {percent}%{time_left}"
            return "❌ Battery info not available"
        except:
            return "❌ Battery info not available"
    
    @staticmethod
    def system_info() -> str:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            result = "💻 System Information:\n"
            result += f"  CPU: {psutil.cpu_count()} cores, {cpu_percent:.1f}% usage\n"
            result += f"  Memory: {memory.percent:.1f}% used ({memory.used/1024**3:.1f}GB/{memory.total/1024**3:.1f}GB)\n"
            result += f"  Disk: {disk.percent:.1f}% used ({disk.used/1024**3:.1f}GB/{disk.total/1024**3:.1f}GB)\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @staticmethod
    def disk_usage(path: str = "/") -> str:
        try:
            disk = psutil.disk_usage(path)
            result = f"💾 Disk Usage for {path}:\n"
            result += f"  Total: {disk.total/1024**3:.2f} GB\n"
            result += f"  Used: {disk.used/1024**3:.2f} GB ({disk.percent:.1f}%)\n"
            result += f"  Free: {disk.free/1024**3:.2f} GB\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Network
    @staticmethod
    def connect_wifi(ssid: str) -> str:
        if not ssid:
            return "❌ No SSID specified"
        success, _ = run_cmd(f"nmcli device wifi connect {shlex.quote(ssid)}")
        return f"✅ Connected to {ssid}" if success else f"❌ Failed to connect to {ssid}"
    
    @staticmethod
    def list_wifi() -> str:
        success, output = run_cmd("nmcli device wifi list")
        return f"📶 WiFi Networks:\n{output}" if success else "❌ Failed to list networks"
    
    @staticmethod
    def network_status() -> str:
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_io_counters()
            
            result = "🌐 Network Status:\n"
            result += f"  Bytes sent: {stats.bytes_sent / 1024**2:.2f} MB\n"
            result += f"  Bytes received: {stats.bytes_recv / 1024**2:.2f} MB\n"
            result += f"  Interfaces: {', '.join(interfaces.keys())}\n"
            return result
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Media Control
    @staticmethod
    def play_music() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} play")
        return "✅ Playing music" if success else "❌ Failed to play"
    
    @staticmethod
    def pause_music() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} pause")
        return "✅ Music paused" if success else "❌ Failed to pause"
    
    @staticmethod
    def next_track() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} next")
        return "✅ Next track" if success else "❌ Failed"
    
    @staticmethod
    def previous_track() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, _ = run_cmd(f"{tool} previous")
        return "✅ Previous track" if success else "❌ Failed"
    
    @staticmethod
    def get_media_info() -> str:
        tool = find_tool(Config.TOOLS["media"])
        if not tool:
            return "❌ No media player found"
        success, output = run_cmd(f"{tool} metadata")
        return f"🎵 {output}" if success else "❌ Failed to get media info"
    
    # Utilities
    @staticmethod
    def get_clipboard() -> str:
        success, output = run_cmd("xclip -selection clipboard -o")
        return f"📋 Clipboard: {output[:200]}" if success else "❌ Failed to read clipboard"
    
    @staticmethod
    def set_clipboard(text: str) -> str:
        if not text:
            return "❌ No text specified"
        success, _ = run_cmd(f"echo {shlex.quote(text)} | xclip -selection clipboard", shell=True)
        return "✅ Clipboard updated" if success else "❌ Failed to update clipboard"
    
    @staticmethod
    def get_weather(city: str = "") -> str:
        if not city:
            success, city = run_cmd("curl -s ipinfo.io/city")
            city = city.strip() if success else "your location"
        
        success, output = run_cmd(f"curl -s 'wttr.in/{shlex.quote(city)}?format=3'")
        return f"🌤️ Weather: {output}" if success else "❌ Failed to get weather"
    
    @staticmethod
    def open_url(url: str) -> str:
        if not url:
            return "❌ No URL specified"
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
        return f"✅ Opened {url}" if success else f"❌ Failed to open {url}"
    
    @staticmethod
    def search_github(query: str) -> str:
        """Search GitHub repositories or answer GitHub user questions."""
        if not query:
            return "❌ No search query specified"

        username = CommandEngine._extract_github_username(query)
        if username and CommandEngine._looks_like_github_user_question(query):
            return CommandEngine.github_user_summary(username)

        if username and len(query.split()) <= 3 and all(
            token.lower() in CommandEngine.GITHUB_QUERY_STOPWORDS or token == username
            for token in query.split()
        ):
            url = f"https://github.com/{username}?tab=repositories"
            success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
            return f"✅ Opened GitHub repositories for: {username}" if success else "❌ Failed to open GitHub"

        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"https://github.com/search?q={encoded_query}&type=repositories"
        success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
        return f"✅ Searching GitHub for: {query}" if success else "❌ Failed to open GitHub"
    
    @staticmethod
    def open_whatsapp_contact(contact: str) -> str:
        """Open WhatsApp chat for a phone number or WhatsApp Web for manual contact search."""
        if not contact:
            return "❌ No contact specified"

        normalized_phone = CommandEngine._normalize_phone_number(contact)
        if normalized_phone:
            url = f"https://web.whatsapp.com/send?phone={urllib.parse.quote(normalized_phone)}"
        else:
            url = "https://web.whatsapp.com"

        success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
        if not success:
            return "❌ Failed to open WhatsApp"

        if normalized_phone:
            return f"✅ Opening WhatsApp chat for {contact}"
        return f"✅ Opened WhatsApp Web. Search for '{contact}' manually."

    @staticmethod
    def send_whatsapp_message(contact: str, message: str) -> str:
        """Send a WhatsApp message immediately when a phone number is available."""
        if not contact:
            return "❌ No WhatsApp contact or phone number specified"
        if not message:
            return "❌ No WhatsApp message specified"

        normalized_phone = CommandEngine._normalize_phone_number(contact)
        encoded_message = urllib.parse.quote(message)

        if not normalized_phone:
            url = "https://web.whatsapp.com"
            success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
            if not success:
                return "❌ Failed to open WhatsApp"
            return (
                f"⚠️ Opened WhatsApp Web, but immediate send needs a phone number. "
                f"Search for '{contact}', paste the message, and press Enter."
            )

        url = (
            "https://web.whatsapp.com/send"
            f"?phone={urllib.parse.quote(normalized_phone)}&text={encoded_message}"
        )
        success, _ = run_cmd(f"xdg-open {shlex.quote(url)}")
        if not success:
            return "❌ Failed to open WhatsApp"

        if AUTOMATION_AVAILABLE:
            CommandEngine._press_enter_after_delay()
            return f"✅ Sending WhatsApp message to {contact} now"

        return (
            f"✅ Opened WhatsApp chat for {contact} with the message filled in. "
            "Press Enter once the page loads to send it."
        )
    
    @staticmethod
    def read_screen_text() -> str:
        """Extract and format text from screen using OCR"""
        if not OCR_AVAILABLE:
            raise ImportError("OCR not available. Install: pip install pytesseract Pillow")

        result = CommandEngine.take_screenshot()
        if "❌" in result:
            return result

        try:
            img = Image.open(Config.SCREENSHOT_PATH)
            raw = pytesseract.image_to_string(img).strip()

            if not raw:
                return "📄 No text found on screen"

            # Filter out noise: keep only lines with real content
            lines = [
                line.strip() for line in raw.splitlines()
                if len(line.strip()) > 2 and not all(c in r'|_-=\/' for c in line.strip())
            ]

            if not lines:
                return "📄 No readable text found on screen"

            return "📄 Screen Text:\n" + "\n".join(lines[:60])
        except Exception as e:
            return f"❌ OCR error: {str(e)}"
    
    @staticmethod
    def install_package(package: str) -> str:
        if not package:
            return "❌ No package specified"
        
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -S {shlex.quote(package)} --noconfirm", timeout=300)
                elif manager == "pacman":
                    success, output = run_cmd(f"sudo pacman -S {shlex.quote(package)} --noconfirm", timeout=300)
                elif manager == "apt":
                    success, output = run_cmd(f"sudo apt install -y {shlex.quote(package)}", timeout=300)
                else:
                    success, output = run_cmd(f"sudo {manager} install -y {shlex.quote(package)}", timeout=300)
                
                return f"✅ Installed {package}" if success else f"❌ Failed to install {package}"
        
        return "❌ No package manager found"
    
    @staticmethod
    def update_system() -> str:
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -Syu --noconfirm", timeout=600)
                elif manager == "pacman":
                    success, output = run_cmd(f"sudo pacman -Syu --noconfirm", timeout=600)
                elif manager == "apt":
                    success, output = run_cmd(f"sudo apt update && sudo apt upgrade -y", timeout=600)
                else:
                    success, output = run_cmd(f"sudo {manager} update -y", timeout=600)
                
                return f"✅ System updated" if success else f"❌ Failed to update system"
        
        return "❌ No package manager found"
    
    @staticmethod
    def check_updates() -> str:
        managers = ["yay", "pacman", "apt", "dnf", "zypper"]
        for manager in managers:
            success, _ = run_cmd(f"which {manager}")
            if success:
                if manager == "yay":
                    success, output = run_cmd(f"yay -Qu")
                elif manager == "pacman":
                    success, output = run_cmd(f"pacman -Qu")
                elif manager == "apt":
                    success, output = run_cmd(f"apt list --upgradable")
                else:
                    success, output = run_cmd(f"{manager} check-update")
                
                return f"📦 Updates available:\n{output[:500]}" if success else "✅ System is up to date"
        
        return "❌ No package manager found"
    
    @staticmethod
    def install_python_package(packages: str) -> str:
        """Install Python packages using pip"""
        if not packages:
            return "❌ No packages specified"
        
        package_list = [p.strip() for p in re.split(r'[, ]+', packages) if p.strip()]
        if not package_list:
            return "❌ No valid packages found"
        
        pip_cmd = None
        for cmd in ["pip3", "pip"]:
            success, _ = run_cmd(f"which {cmd}")
            if success:
                pip_cmd = cmd
                break
        
        if not pip_cmd:
            return "❌ pip not found. Install pip first."
        
        packages_str = " ".join([shlex.quote(p) for p in package_list])
        success, output = run_cmd(f"{pip_cmd} install {packages_str}", timeout=300)
        
        if success:
            return f"✅ Installed Python packages: {', '.join(package_list)}"
        else:
            return f"❌ Failed to install packages. Error: {output[:200]}"

    # ── Bluetooth ────────────────────────────────────────────────────────────

    @staticmethod
    def bluetooth_list_paired() -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.list_paired()

    @staticmethod
    def bluetooth_list_available() -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.list_available()

    @staticmethod
    def bluetooth_connect(device: str) -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.connect(device)

    @staticmethod
    def bluetooth_disconnect(device: str) -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.disconnect(device)

    @staticmethod
    def bluetooth_pair(mac: str) -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.pair(mac)

    @staticmethod
    def bluetooth_status() -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.status()

    @staticmethod
    def bluetooth_power(on: bool) -> str:
        from jarvis_ai.bluetooth_manager import BluetoothManager
        return BluetoothManager.power(on)

    # ── Notifications ───────────────────────────────────────────────────

    @staticmethod
    def send_notification(title: str, body: str = "", urgency: str = "normal") -> str:
        from jarvis_ai.notification_sender import NotificationSender
        return NotificationSender.send(title, body, urgency)

    # ── Email ──────────────────────────────────────────────────────────────

    @staticmethod
    def email_read_inbox(count: int = 5) -> str:
        from jarvis_ai.email_manager import EmailManager
        return EmailManager.read_inbox(count)

    @staticmethod
    def email_read_body(index: int = 1) -> str:
        from jarvis_ai.email_manager import EmailManager
        return EmailManager.read_email_body(index)

    @staticmethod
    def email_send(to: str, subject: str, body: str) -> str:
        from jarvis_ai.email_manager import EmailManager
        return EmailManager.send(to, subject, body)

    @staticmethod
    def email_search(query: str) -> str:
        from jarvis_ai.email_manager import EmailManager
        return EmailManager.search_emails(query)

    # ── Browser Automation ──────────────────────────────────────────────

    @staticmethod
    def browser_open(url: str) -> str:
        from jarvis_ai.browser_automation import BrowserAutomation
        return BrowserAutomation.open_url(url)

    @staticmethod
    def browser_scrape(url: str, selector: str = "body") -> str:
        from jarvis_ai.browser_automation import BrowserAutomation
        return BrowserAutomation.scrape(url, selector)

    @staticmethod
    def browser_screenshot(url: str) -> str:
        from jarvis_ai.browser_automation import BrowserAutomation
        return BrowserAutomation.screenshot(url)

    @staticmethod
    def browser_search(query: str) -> str:
        from jarvis_ai.browser_automation import BrowserAutomation
        return BrowserAutomation.search_and_scrape(query)

    @staticmethod
    def list_workspaces() -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.list_workspaces_summary()

    @staticmethod
    def switch_workspace(ws_id: int) -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.switch_workspace(ws_id)

    @staticmethod
    def move_to_workspace(ws_id: int) -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.move_window_to_workspace(ws_id)

    @staticmethod
    def focus_window(title: str) -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.focus_window_by_title(title)

    @staticmethod
    def find_app_workspace(app: str) -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.find_app_workspace(app)

    @staticmethod
    def close_active_window() -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.close_active_window()

    @staticmethod
    def toggle_fullscreen() -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.toggle_fullscreen()

    @staticmethod
    def toggle_float() -> str:
        from jarvis_ai.workspace_monitor import WorkspaceMonitor
        return WorkspaceMonitor.toggle_float()




