"""
Bluetooth Call Handler for BenX.

Flow:
  1. Monitor ofono dbus for incoming calls on paired phone (HFP)
  2. Show GTK popup: caller name/number + ask user what BenX should say
  3. User says "answer" / types a message (e.g. "I'm busy, call later")
  4. BenX answers the call via ofono, speaks the message via TTS
  5. Hangs up after speaking

Requirements:
  - ofono running:  sudo systemctl start ofono
  - Phone paired + connected with HFP profile
  - pyttsx3 or espeak for TTS
"""
import logging
import subprocess
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ── ofono dbus constants ──────────────────────────────────────────────────────
OFONO_SERVICE   = "org.ofono"
OFONO_MANAGER   = "org.ofono.Manager"
OFONO_MODEM     = "org.ofono.Modem"
OFONO_VCMANAGER = "org.ofono.VoiceCallManager"
OFONO_VCALL     = "org.ofono.VoiceCall"

# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_ofono() -> bool:
    """Start ofono if not running. Returns True if available."""
    try:
        import dbus
        bus = dbus.SystemBus()
        bus.get_object(OFONO_SERVICE, "/")
        return True
    except Exception:
        pass
    # Try to start it
    try:
        subprocess.run(["sudo", "systemctl", "start", "ofono"],
                       timeout=8, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        import dbus
        bus = dbus.SystemBus()
        bus.get_object(OFONO_SERVICE, "/")
        logger.info("ofono started successfully")
        return True
    except Exception as e:
        logger.warning("Could not start ofono: %s", e)
        return False


def _get_modems():
    """Return list of (path, properties) for all ofono modems."""
    try:
        import dbus
        bus = dbus.SystemBus()
        mgr = dbus.Interface(bus.get_object(OFONO_SERVICE, "/"), OFONO_MANAGER)
        return mgr.GetModems()
    except Exception as e:
        logger.debug("GetModems failed: %s", e)
        return []


def _speak(text: str):
    """Speak text via espeak (fast, no deps) or pyttsx3 fallback."""
    try:
        subprocess.Popen(
            ["espeak", "-s", "140", "-v", "en", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Wait roughly for speech to finish (150 wpm ≈ 2.5 chars/s)
        time.sleep(max(2.0, len(text) / 10))
    except FileNotFoundError:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 140)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.warning("TTS failed: %s", e)


# ── Call Handler ──────────────────────────────────────────────────────────────

class BluetoothCallHandler:
    """
    Monitors ofono for incoming calls on the paired phone.
    Calls on_incoming_call(caller, answer_cb, reject_cb) when a call arrives.
    answer_cb(message) → answers call and speaks message
    reject_cb()        → rejects call silently
    """

    def __init__(self, on_incoming_call: Callable):
        self.on_incoming_call = on_incoming_call
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active = False
        self._loop = None

    def start(self) -> str:
        if self._active:
            return "⚠️ Call handler already running"
        if not _ensure_ofono():
            return (
                "❌ ofono not available.\n"
                "Install it:  sudo pacman -S ofono\n"
                "Then start:  sudo systemctl enable --now ofono\n"
                "And pair your phone with HFP profile."
            )
        modems = _get_modems()
        if not modems:
            return (
                "❌ No phone modem found via ofono.\n"
                "Make sure your phone is:\n"
                "  1. Paired via Bluetooth\n"
                "  2. Connected with HFP (Hands-Free) profile\n"
                "  3. ofono is running: sudo systemctl start ofono"
            )
        self._active = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        modem_names = [str(p) for p, _ in modems]
        return f"✅ Call handler active. Monitoring: {', '.join(modem_names)}"

    def stop(self):
        self._stop.set()
        self._active = False
        if self._loop:
            try:
                self._loop.quit()
            except Exception:
                pass

    def is_active(self) -> bool:
        return self._active

    def _run_loop(self):
        """Run dbus signal listener in its own GLib main loop."""
        try:
            import dbus
            import dbus.mainloop.glib
            from gi.repository import GLib

            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()
            self._loop = GLib.MainLoop()

            # Connect to CallAdded on every modem's VoiceCallManager
            modems = _get_modems()
            for modem_path, _ in modems:
                try:
                    vcm = bus.get_object(OFONO_SERVICE, modem_path)
                    vcm_iface = dbus.Interface(vcm, OFONO_VCMANAGER)
                    bus.add_signal_receiver(
                        handler_function=self._on_call_added,
                        signal_name="CallAdded",
                        dbus_interface=OFONO_VCMANAGER,
                        path=modem_path,
                        path_keyword="modem_path"
                    )
                    logger.info("Watching modem %s for calls", modem_path)
                except Exception as e:
                    logger.warning("Could not watch modem %s: %s", modem_path, e)

            # Also watch for new modems appearing
            bus.add_signal_receiver(
                handler_function=self._on_modem_added,
                signal_name="ModemAdded",
                dbus_interface=OFONO_MANAGER
            )

            logger.info("Call handler loop running")
            self._loop.run()
        except Exception as e:
            logger.error("Call handler loop error: %s", e)
        finally:
            self._active = False
            logger.info("Call handler loop exited")

    def _on_modem_added(self, path, properties):
        """Re-subscribe when a new modem (phone connects) appears."""
        try:
            import dbus
            bus = dbus.SystemBus()
            bus.add_signal_receiver(
                handler_function=self._on_call_added,
                signal_name="CallAdded",
                dbus_interface=OFONO_VCMANAGER,
                path=str(path),
                path_keyword="modem_path"
            )
            logger.info("New modem detected, watching: %s", path)
        except Exception as e:
            logger.warning("Failed to watch new modem: %s", e)

    def _on_call_added(self, call_path, properties, modem_path=None):
        """Fired when an incoming call arrives."""
        try:
            state = str(properties.get("State", ""))
            if state not in ("incoming", "waiting"):
                return

            caller_number = str(properties.get("LineIdentification", "Unknown"))
            caller_name   = str(properties.get("Name", "")) or caller_number

            logger.info("Incoming call from %s (%s)", caller_name, caller_number)

            call_path_str = str(call_path)
            modem_str     = str(modem_path) if modem_path else None

            def answer_cb(message: str):
                self._answer_and_speak(call_path_str, modem_str, message)

            def reject_cb():
                self._reject_call(call_path_str)

            self.on_incoming_call(caller_name, caller_number, answer_cb, reject_cb)

        except Exception as e:
            logger.error("Error handling incoming call: %s", e)

    def _answer_and_speak(self, call_path: str, modem_path: Optional[str], message: str):
        """Answer the call via ofono then speak the message."""
        try:
            import dbus
            bus = dbus.SystemBus()
            call_obj   = bus.get_object(OFONO_SERVICE, call_path)
            call_iface = dbus.Interface(call_obj, OFONO_VCALL)
            call_iface.Answer()
            logger.info("Call answered: %s", call_path)
            time.sleep(0.8)   # brief pause before speaking
            _speak(message)
            time.sleep(0.5)
            # Hang up after delivering the message
            call_iface.Hangup()
            logger.info("Call hung up after message")
        except Exception as e:
            logger.error("Answer/speak failed: %s", e)

    def _reject_call(self, call_path: str):
        """Reject / decline the call."""
        try:
            import dbus
            bus = dbus.SystemBus()
            call_obj   = bus.get_object(OFONO_SERVICE, call_path)
            call_iface = dbus.Interface(call_obj, OFONO_VCALL)
            call_iface.Hangup()
            logger.info("Call rejected: %s", call_path)
        except Exception as e:
            logger.error("Reject call failed: %s", e)
