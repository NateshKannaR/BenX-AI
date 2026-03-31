"""
Bluetooth Call Handler for BenX — incoming + outgoing calls via ofono HFP.

Setup (one-time):
    sudo pacman -S ofono espeak
    sudo systemctl enable --now ofono
    # On your phone: Bluetooth → PC → enable "Phone calls" (HFP)

Outgoing call flow:
    User: "call mom" / "call 9876543210"
    BenX looks up contacts → dials via ofono VoiceCallManager.Dial()
    Shows active call popup with Hangup button

Incoming call flow:
    Phone rings → BenX shows popup with caller name + message box
    User picks: Reject / I'm Busy / Answer & Speak (custom message)
    BenX answers, speaks the message via TTS, hangs up
"""
import logging
import subprocess
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OFONO_SERVICE   = "org.ofono"
OFONO_MANAGER   = "org.ofono.Manager"
OFONO_VCMANAGER = "org.ofono.VoiceCallManager"
OFONO_VCALL     = "org.ofono.VoiceCall"
OFONO_PBAP      = "org.ofono.PhonebookAccess"


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_ofono() -> bool:
    # Check package installed first
    if subprocess.run(["pacman", "-Q", "ofono"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        logger.warning("ofono not installed. Run: sudo pacman -S ofono")
        return False
    # Check dbus Python module
    try:
        import dbus
        import dbus.mainloop.glib
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    except ImportError:
        logger.warning("python-dbus not installed. Run: sudo pacman -S python-dbus")
        return False
    # Try connecting to running ofono
    try:
        dbus.SystemBus().get_object(OFONO_SERVICE, "/")
        return True
    except Exception:
        pass
    # Try starting the service
    try:
        subprocess.run(["sudo", "systemctl", "start", "ofono"],
                       timeout=8, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        dbus.SystemBus().get_object(OFONO_SERVICE, "/")
        return True
    except Exception as e:
        logger.warning("Could not start ofono: %s", e)
        return False


def _get_modems():
    try:
        import dbus
        bus = dbus.SystemBus()
        mgr = dbus.Interface(bus.get_object(OFONO_SERVICE, "/"), OFONO_MANAGER)
        return mgr.GetModems()
    except Exception as e:
        logger.debug("GetModems failed: %s", e)
        return []


def _first_modem_path() -> Optional[str]:
    modems = _get_modems()
    return str(modems[0][0]) if modems else None


def _acquire_sco_fd():
    """Acquire SCO socket fd from ofono HandsfreeAudioCard. Returns (fd, codec) or (None, None)."""
    try:
        import dbus
        bus = dbus.SystemBus()
        mgr = dbus.Interface(bus.get_object(OFONO_SERVICE, "/"), "org.ofono.HandsfreeAudioManager")
        cards = mgr.GetCards()
        if not cards:
            return None, None
        card_path = str(cards[0][0])
        card = dbus.Interface(bus.get_object(OFONO_SERVICE, card_path), "org.ofono.HandsfreeAudioCard")
        fd, codec = card.Acquire()
        return fd.take(), int(codec)
    except Exception as e:
        logger.warning("SCO acquire failed: %s", e)
        return None, None


def _speak(text: str):
    """Speak text over the active HFP call via SCO, fallback to local speakers."""
    import os
    fd, codec = _acquire_sco_fd()
    if fd is not None:
        try:
            # codec 1=CVSD=8kHz, codec 2=mSBC=16kHz
            rate = 16000 if codec == 2 else 8000
            # SCO MTU=48 bytes, interval = 48bytes / (rate * 2bytes) seconds
            chunk = 48
            interval = chunk / (rate * 2)  # seconds per chunk

            espeak = subprocess.Popen(
                ["espeak", "-s", "140", "-v", "en", "--stdout", text],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            ffmpeg = subprocess.Popen(
                ["ffmpeg", "-y",
                 "-f", "wav", "-i", "pipe:0",
                 "-ar", str(rate), "-ac", "1",
                 "-f", "s16le", "pipe:1"],
                stdin=espeak.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            espeak.stdout.close()

            import socket
            sock = socket.fromfd(fd, socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET)
            os.close(fd)  # fromfd dups it, close original

            next_send = time.monotonic()
            while True:
                data = ffmpeg.stdout.read(chunk)
                if not data:
                    break
                # pad to full chunk so SCO packet is always correct size
                if len(data) < chunk:
                    data = data + b'\x00' * (chunk - len(data))
                # pace writes to match real-time audio rate
                now = time.monotonic()
                if next_send > now:
                    time.sleep(next_send - now)
                try:
                    sock.send(data)
                except OSError:
                    break
                next_send += interval

            sock.close()
            ffmpeg.wait(timeout=5)
            espeak.wait(timeout=5)
            return
        except Exception as e:
            logger.warning("SCO speak failed: %s", e)
            try:
                os.close(fd)
            except OSError:
                pass
    # fallback — local speakers
    try:
        subprocess.Popen(
            ["espeak", "-s", "140", "-v", "en", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).wait(timeout=max(3, len(text) // 8))
    except Exception as e:
        logger.warning("espeak fallback failed: %s", e)


def lookup_contact(name_or_number: str) -> tuple[str, str]:
    """
    Returns (display_name, phone_number).
    Tries ofono PBAP phonebook first, falls back to treating input as number.
    """
    import re
    # Already a number
    if re.match(r"^[+\d\s\-()]{5,}$", name_or_number.strip()):
        return name_or_number.strip(), name_or_number.strip()

    # Try fetching contacts via ofono PBAP
    try:
        import dbus
        bus = dbus.SystemBus()
        modem = _first_modem_path()
        if modem:
            pb = dbus.Interface(bus.get_object(OFONO_SERVICE, modem), OFONO_PBAP)
            pb.Import("combined")   # pull contacts from phone
            entries = pb.List()
            query = name_or_number.lower()
            for entry in entries:
                entry_name   = str(entry.get("Name", "")).lower()
                entry_number = str(entry.get("Number", ""))
                if query in entry_name:
                    return str(entry.get("Name", name_or_number)), entry_number
    except Exception as e:
        logger.debug("PBAP lookup failed: %s", e)

    # Return as-is — let the user confirm
    return name_or_number, name_or_number


# ── outgoing call ─────────────────────────────────────────────────────────────

def _ensure_modem_online(modem_path: str) -> tuple[bool, str]:
    """Power on and bring modem online if needed."""
    try:
        import dbus
        bus = dbus.SystemBus()
        modem = dbus.Interface(bus.get_object(OFONO_SERVICE, modem_path), "org.ofono.Modem")
        props = modem.GetProperties()
        if not props.get("Powered", False):
            modem.SetProperty("Powered", dbus.Boolean(True))
            time.sleep(3)
            props = modem.GetProperties()
        if not props.get("Online", False):
            modem.SetProperty("Online", dbus.Boolean(True))
            time.sleep(2)
        return True, ""
    except Exception as e:
        return False, str(e)


def dial(number: str) -> tuple[bool, str]:
    """
    Dial a number via ofono HFP.
    Returns (success, call_path_or_error).
    """
    if not _ensure_ofono():
        return False, "ofono not running"
    modem = _first_modem_path()
    if not modem:
        return False, "No phone modem found. Connect your phone via Bluetooth (HFP)."
    ok, err = _ensure_modem_online(modem)
    if not ok:
        return False, f"Modem offline (enable 'Phone calls' on your phone's Bluetooth settings): {err}"
    try:
        import dbus
        bus = dbus.SystemBus()
        vcm = dbus.Interface(bus.get_object(OFONO_SERVICE, modem), OFONO_VCMANAGER)
        call_path = vcm.Dial(number, "default")
        logger.info("Dialing %s → call path: %s", number, call_path)
        return True, str(call_path)
    except Exception as e:
        logger.error("Dial failed: %s", e)
        return False, str(e)


def hangup_call(call_path: str) -> bool:
    try:
        import dbus
        bus = dbus.SystemBus()
        call_iface = dbus.Interface(bus.get_object(OFONO_SERVICE, call_path), OFONO_VCALL)
        call_iface.Hangup()
        return True
    except Exception as e:
        logger.error("Hangup failed: %s", e)
        return False


def hangup_all() -> bool:
    """Hang up all active calls on the modem."""
    modem = _first_modem_path()
    if not modem:
        return False
    try:
        import dbus
        bus = dbus.SystemBus()
        vcm = dbus.Interface(bus.get_object(OFONO_SERVICE, modem), OFONO_VCMANAGER)
        vcm.HangupAll()
        return True
    except Exception as e:
        logger.error("HangupAll failed: %s", e)
        return False


# ── Call Handler (incoming monitor) ──────────────────────────────────────────

class BluetoothCallHandler:
    """
    Monitors ofono for incoming calls.
    on_incoming_call(caller_name, caller_number, answer_cb, reject_cb)
    """

    def __init__(self, on_incoming_call: Callable):
        self.on_incoming_call = on_incoming_call
        self._active = False
        self._loop   = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        if self._active:
            return "⚠️ Call handler already running"
        if not _ensure_ofono():
            return (
                "❌ ofono not available.\n"
                "Run:  sudo pacman -S ofono\n"
                "Then: sudo systemctl enable --now ofono\n"
                "On your phone: Bluetooth → PC → enable 'Phone calls'"
            )
        modems = _get_modems()
        if not modems:
            return (
                "❌ No phone modem found.\n"
                "Make sure your POCO is connected via Bluetooth with HFP enabled.\n"
                "On phone: Settings → Bluetooth → PC → Phone calls ✓"
            )
        self._active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return f"✅ Call handler active on {len(modems)} modem(s)"

    def stop(self):
        self._active = False
        if self._loop:
            try:
                self._loop.quit()
            except Exception:
                pass

    def is_active(self) -> bool:
        return self._active

    def _run_loop(self):
        try:
            import dbus
            import dbus.mainloop.glib
            from gi.repository import GLib

            main_loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus      = dbus.SystemBus(mainloop=main_loop)
            self._loop = GLib.MainLoop()

            for modem_path, _ in _get_modems():
                bus.add_signal_receiver(
                    handler_function=self._on_call_added,
                    signal_name="CallAdded",
                    dbus_interface=OFONO_VCMANAGER,
                    path=str(modem_path),
                    path_keyword="modem_path"
                )
                logger.info("Watching modem %s", modem_path)

            bus.add_signal_receiver(
                handler_function=self._on_modem_added,
                signal_name="ModemAdded",
                dbus_interface=OFONO_MANAGER
            )

            self._loop.run()
        except Exception as e:
            logger.error("Call handler loop error: %s", e)
        finally:
            self._active = False

    def _on_modem_added(self, path, properties):
        try:
            import dbus
            dbus.SystemBus().add_signal_receiver(
                handler_function=self._on_call_added,
                signal_name="CallAdded",
                dbus_interface=OFONO_VCMANAGER,
                path=str(path),
                path_keyword="modem_path"
            )
        except Exception as e:
            logger.warning("Failed to watch new modem: %s", e)

    def _on_call_added(self, call_path, properties, modem_path=None):
        try:
            state = str(properties.get("State", ""))
            if state not in ("incoming", "waiting"):
                return
            number = str(properties.get("LineIdentification", "Unknown"))
            name   = str(properties.get("Name", "")) or number
            logger.info("Incoming call from %s (%s)", name, number)

            call_str = str(call_path)

            def answer_cb(message: str):
                try:
                    import dbus
                    bus = dbus.SystemBus()
                    iface = dbus.Interface(bus.get_object(OFONO_SERVICE, call_str), OFONO_VCALL)
                    iface.Answer()
                    time.sleep(0.8)
                    _speak(message)
                    time.sleep(0.5)
                    iface.Hangup()
                except Exception as e:
                    logger.error("Answer/speak failed: %s", e)

            def reject_cb():
                try:
                    import dbus
                    bus = dbus.SystemBus()
                    iface = dbus.Interface(bus.get_object(OFONO_SERVICE, call_str), OFONO_VCALL)
                    iface.Hangup()
                except Exception as e:
                    logger.error("Reject failed: %s", e)

            self.on_incoming_call(name, number, answer_cb, reject_cb)
        except Exception as e:
            logger.error("Error handling incoming call: %s", e)
