"""
Bluetooth Manager - bluetoothctl wrapper for BenX
"""
import subprocess
import re
import logging

logger = logging.getLogger(__name__)


def _bt(cmd: str, timeout: int = 6) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["bluetoothctl"] + cmd.split(),
            capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)


def _bt_input(commands: str, timeout: int = 8) -> str:
    """Send multiple commands to bluetoothctl interactive mode"""
    try:
        r = subprocess.run(
            ["bluetoothctl"],
            input=commands, capture_output=True, text=True, timeout=timeout
        )
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)


class BluetoothManager:

    @staticmethod
    def list_paired() -> str:
        ok, out = _bt("paired-devices")
        if not out.strip():
            return "📡 No paired Bluetooth devices found."
        lines = ["📡 Paired Bluetooth Devices:"]
        for line in out.splitlines():
            m = re.match(r"Device\s+([0-9A-F:]+)\s+(.+)", line, re.IGNORECASE)
            if m:
                lines.append(f"  • {m.group(2)} [{m.group(1)}]")
        return "\n".join(lines) if len(lines) > 1 else "📡 No paired devices."

    @staticmethod
    def list_available() -> str:
        out = _bt_input("scan on\nsleep 4\ndevices\nscan off\n", timeout=12)
        lines = ["📡 Available Bluetooth Devices:"]
        seen = set()
        for line in out.splitlines():
            m = re.match(r".*Device\s+([0-9A-F:]+)\s+(.+)", line, re.IGNORECASE)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                lines.append(f"  • {m.group(2)} [{m.group(1)}]")
        return "\n".join(lines) if len(lines) > 1 else "📡 No devices found nearby."

    @staticmethod
    def connect(device: str) -> str:
        # device can be MAC or name substring
        mac = BluetoothManager._resolve_mac(device)
        if not mac:
            return f"❌ Device '{device}' not found in paired devices."
        ok, out = _bt(f"connect {mac}")
        return f"✅ Connected to {device}" if ok or "successful" in out.lower() else f"❌ Failed to connect: {out[:100]}"

    @staticmethod
    def disconnect(device: str) -> str:
        mac = BluetoothManager._resolve_mac(device)
        if not mac:
            return f"❌ Device '{device}' not found in paired devices."
        ok, out = _bt(f"disconnect {mac}")
        return f"✅ Disconnected {device}" if ok or "successful" in out.lower() else f"❌ Failed: {out[:100]}"

    @staticmethod
    def pair(mac: str) -> str:
        if not mac:
            return "❌ No MAC address provided."
        out = _bt_input(f"pair {mac}\ntrust {mac}\nconnect {mac}\n", timeout=20)
        if "successful" in out.lower() or "paired" in out.lower():
            return f"✅ Paired and connected to {mac}"
        return f"⚠️ Pairing result: {out[:200]}"

    @staticmethod
    def remove(device: str) -> str:
        mac = BluetoothManager._resolve_mac(device)
        if not mac:
            return f"❌ Device '{device}' not found."
        ok, out = _bt(f"remove {mac}")
        return f"✅ Removed {device}" if ok else f"❌ Failed: {out[:100]}"

    @staticmethod
    def status() -> str:
        ok, out = _bt("show")
        powered = "on" if "Powered: yes" in out else "off"
        discoverable = "yes" if "Discoverable: yes" in out else "no"
        return f"📡 Bluetooth: powered={powered}, discoverable={discoverable}"

    @staticmethod
    def power(on: bool) -> str:
        cmd = "power on" if on else "power off"
        ok, out = _bt(cmd)
        state = "on" if on else "off"
        return f"✅ Bluetooth turned {state}" if ok else f"❌ Failed: {out[:100]}"

    @staticmethod
    def _resolve_mac(device: str) -> str:
        """Resolve device name or MAC to MAC address"""
        if re.match(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$", device, re.IGNORECASE):
            return device.upper()
        _, out = _bt("paired-devices")
        for line in out.splitlines():
            m = re.match(r"Device\s+([0-9A-F:]+)\s+(.+)", line, re.IGNORECASE)
            if m and device.lower() in m.group(2).lower():
                return m.group(1).upper()
        return ""
