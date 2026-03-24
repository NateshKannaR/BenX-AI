"""
Notification Sender - desktop notifications via notify-send for BenX
"""
import subprocess
import logging

logger = logging.getLogger(__name__)


class NotificationSender:

    URGENCY = {"low": "low", "normal": "normal", "critical": "critical"}

    @staticmethod
    def send(title: str, body: str = "", urgency: str = "normal",
             timeout_ms: int = 5000, icon: str = "dialog-information") -> str:
        urgency = NotificationSender.URGENCY.get(urgency.lower(), "normal")
        cmd = [
            "notify-send",
            "--urgency", urgency,
            "--expire-time", str(timeout_ms),
            "--icon", icon,
            title,
        ]
        if body:
            cmd.append(body)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return f"✅ Notification sent: {title}"
            return f"❌ notify-send failed: {r.stderr.strip()[:100]}"
        except FileNotFoundError:
            return "❌ notify-send not found. Install: sudo pacman -S libnotify"
        except Exception as e:
            return f"❌ Notification error: {e}"

    @staticmethod
    def alert(message: str) -> str:
        return NotificationSender.send("BenX Alert", message, urgency="critical",
                                       timeout_ms=0, icon="dialog-warning")

    @staticmethod
    def info(message: str) -> str:
        return NotificationSender.send("BenX", message, urgency="normal",
                                       icon="dialog-information")
