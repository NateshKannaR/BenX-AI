"""
Voice Handler - Mic input + System audio capture + TTS
"""
import logging
import os
import subprocess
import tempfile
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


def _get_monitor_source() -> Optional[str]:
    """Find the PipeWire/PulseAudio monitor source (captures system audio output)."""
    try:
        out = subprocess.check_output(
            ["pactl", "list", "sources", "short"], text=True, timeout=5
        )
        for line in out.splitlines():
            if ".monitor" in line:
                return line.split()[1]  # source name
    except Exception as e:
        logger.warning(f"Could not find monitor source: {e}")
    return None


class VoiceHandler:
    """Voice input/output handler"""

    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        self._sys_listen_thread: Optional[threading.Thread] = None
        self._sys_listen_stop = threading.Event()

        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300   # lower for system audio
                self.recognizer.dynamic_energy_threshold = True
            except Exception as e:
                logger.warning(f"Voice recognition setup failed: {e}")

        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                logger.warning(f"TTS setup failed: {e}")

    # ── Microphone input ──────────────────────────────────────────────────────

    def listen(self) -> Optional[str]:
        """Listen from microphone."""
        if not self.recognizer:
            return None
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.error(f"Mic listen error: {e}")
            return None

    # ── System audio capture ──────────────────────────────────────────────────

    def listen_system_audio(self, duration: int = 10) -> Optional[str]:
        """
        Capture system audio output (speakers) for `duration` seconds
        and transcribe it. Uses the PipeWire monitor source.
        """
        if not VOICE_AVAILABLE:
            return None

        monitor = _get_monitor_source()
        if not monitor:
            logger.warning("No monitor source found — cannot capture system audio")
            return None

        wav_file = tempfile.mktemp(suffix=".wav")
        try:
            # Record system audio via parec → pipe → ffmpeg → WAV
            parec_cmd = [
                "parec",
                "--device", monitor,
                "--format=s16le",
                "--rate=16000",
                "--channels=1",
            ]
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "s16le", "-ar", "16000", "-ac", "1",
                "-i", "pipe:0",
                "-t", str(duration),
                wav_file
            ]

            logger.info(f"Capturing system audio for {duration}s from {monitor}")
            parec_proc = subprocess.Popen(parec_cmd, stdout=subprocess.PIPE)
            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=parec_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            ffmpeg_proc.wait(timeout=duration + 5)
            parec_proc.terminate()

            # Transcribe the WAV
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_file) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            logger.info(f"System audio transcribed: {text[:80]}")
            return text

        except sr.UnknownValueError:
            logger.info("System audio: no speech detected")
            return None
        except Exception as e:
            logger.error(f"System audio capture failed: {e}")
            return None
        finally:
            try:
                os.remove(wav_file)
            except Exception:
                pass

    def start_system_audio_monitor(
        self,
        on_speech_cb,
        chunk_duration: int = 8
    ):
        """
        Continuously monitor system audio in background.
        Calls on_speech_cb(text) whenever speech is detected.
        """
        if self._sys_listen_thread and self._sys_listen_thread.is_alive():
            logger.warning("System audio monitor already running")
            return

        self._sys_listen_stop.clear()

        def _loop():
            logger.info("System audio monitor started")
            while not self._sys_listen_stop.is_set():
                text = self.listen_system_audio(duration=chunk_duration)
                if text and text.strip():
                    try:
                        on_speech_cb(text.strip())
                    except Exception as e:
                        logger.error(f"System audio callback error: {e}")
            logger.info("System audio monitor stopped")

        self._sys_listen_thread = threading.Thread(target=_loop, daemon=True)
        self._sys_listen_thread.start()

    def stop_system_audio_monitor(self):
        """Stop the continuous system audio monitor."""
        self._sys_listen_stop.set()

    # ── TTS ───────────────────────────────────────────────────────────────────

    def speak(self, text: str):
        """Speak text using TTS."""
        if not self.tts_engine:
            return
        try:
            threading.Thread(
                target=lambda: (self.tts_engine.say(text), self.tts_engine.runAndWait()),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"TTS error: {e}")











