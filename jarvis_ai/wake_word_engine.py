"""
Wake Word Engine for BenX.

How it works (zero extra dependencies):
  1. Record 2-second audio chunks from mic via parec + ffmpeg
  2. Send to Groq Whisper API for transcription (reuses existing GROQ_API_KEY)
  3. If transcript contains "benx" -> wake word detected
  4. Record a longer follow-up chunk (command)
  5. Transcribe command -> pass to BenX AI

No pvporcupine, no openwakeword, no pyaudio needed.
"""
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
import requests
from typing import Callable, Optional
from pathlib import Path

from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

WAKE_WORDS = {"benx", "ben x", "hey benx", "hey ben", "ok benx"}
WAKE_CHUNK_SEC  = 2    # seconds per detection chunk
CMD_CHUNK_SEC   = 6    # seconds to record command after wake word
SAMPLE_RATE     = 16000
CHANNELS        = 1


def _get_mic_source() -> Optional[str]:
    """Get the default mic input source name."""
    parec_bin = shutil.which("pactl")
    if not parec_bin:
        return None
    try:
        out = subprocess.check_output(
            [parec_bin, "get-default-source"], text=True, timeout=3
        ).strip()
        return out if out else None
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("pactl get-default-source failed: %s", e)
    try:
        out = subprocess.check_output(
            [parec_bin, "list", "sources", "short"], text=True, timeout=3
        )
        for line in out.splitlines():
            if "input" in line.lower() and "monitor" not in line.lower():
                return line.split()[1]
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("pactl list sources failed: %s", e)
    return None


def _record_wav(source: str, duration: int) -> Optional[str]:
    """Record `duration` seconds from `source` into a temp WAV file."""
    parec_bin = shutil.which("parec")
    ffmpeg_bin = shutil.which("ffmpeg")
    if not parec_bin or not ffmpeg_bin:
        logger.debug("parec or ffmpeg not found in PATH")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav = tmp.name
    tmp.close()

    parec = None
    try:
        parec = subprocess.Popen(
            [parec_bin, "--device", source,
             "--format=s16le", f"--rate={SAMPLE_RATE}",
             f"--channels={CHANNELS}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        ffmpeg = subprocess.Popen(
            [ffmpeg_bin, "-y",
             "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
             "-i", "pipe:0",
             "-t", str(duration),
             wav],
            stdin=parec.stdout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Terminate parec first so ffmpeg stdin closes, then communicate() drains safely
        time.sleep(duration)
        parec.terminate()
        ffmpeg.communicate(timeout=5)
        return wav if Path(wav).exists() and Path(wav).stat().st_size > 1000 else None
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Record failed: %s", e)
        if parec is not None:
            try:
                parec.terminate()
            except OSError as te:
                logger.debug("parec terminate failed: %s", te)
        return None


def _transcribe_groq(wav_path: str) -> str:
    """Transcribe WAV using Groq Whisper API."""
    safe = Path(wav_path).resolve()
    tmp_dir = Path(tempfile.gettempdir()).resolve()
    if not str(safe).startswith(str(tmp_dir)):
        logger.warning("Rejected wav path outside temp dir: %s", wav_path)
        return ""
    if not Config.GROQ_KEY:
        return ""
    try:
        with open(safe, "rb") as f:
            resp = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {Config.GROQ_KEY}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"model": "whisper-large-v3-turbo", "language": "en"},
                timeout=15
            )
        if resp.status_code == 200:
            return resp.json().get("text", "").strip().lower()
        logger.debug("Whisper API %s: %s", resp.status_code, resp.text[:100])
    except (requests.RequestException, OSError) as e:
        logger.debug("Transcribe failed: %s", e)
    return ""


def _contains_wake_word(text: str) -> bool:
    t = text.lower().strip()
    return any(w in t for w in WAKE_WORDS)


class WakeWordEngine:
    """
    Always-on wake word listener.
    Runs in background thread, calls on_wake_word(command_text) when triggered.
    """

    def __init__(self, on_wake_word: Callable[[str], None]):
        self.on_wake_word = on_wake_word
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active = False
        self._source: Optional[str] = None

    def start(self) -> str:
        if self._active:
            return "⚠️ Wake word engine already running"
        source = _get_mic_source()
        if not source:
            return "❌ No microphone found. Check audio settings."
        self._source = source
        self._stop.clear()
        self._active = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Wake word engine started on source: %s", source)
        return f"✅ Listening for 'BenX' on {source}"

    def stop(self):
        self._stop.set()
        self._active = False
        logger.info("Wake word engine stopped")

    def is_active(self) -> bool:
        return self._active

    def _loop(self):
        logger.info("Wake word loop running")
        while not self._stop.is_set():
            try:
                wav = _record_wav(self._source, WAKE_CHUNK_SEC)
                if not wav:
                    time.sleep(0.5)
                    continue

                text = _transcribe_groq(wav)
                try:
                    os.remove(wav)
                except OSError as e:
                    logger.debug("Failed to remove wav: %s", e)

                if not text:
                    continue

                logger.debug("Wake chunk: '%s'", text)

                if not _contains_wake_word(text):
                    continue

                logger.info("Wake word detected in: '%s'", text)

                inline = self._extract_inline_command(text)
                if inline:
                    self.on_wake_word(inline)
                    continue

                cmd_wav = _record_wav(self._source, CMD_CHUNK_SEC)
                if not cmd_wav:
                    self.on_wake_word("")
                    continue

                cmd_text = _transcribe_groq(cmd_wav)
                try:
                    os.remove(cmd_wav)
                except OSError as e:
                    logger.debug("Failed to remove cmd wav: %s", e)

                self.on_wake_word(cmd_text.strip() if cmd_text else "")

            except (subprocess.SubprocessError, OSError, requests.RequestException) as e:
                logger.warning("Wake word engine transient error: %s", e)
                time.sleep(1)
            except Exception as e:
                # Unexpected errors should also be logged for diagnosis but not swallowed silently.
                logger.exception("Wake word loop unexpected exception:")
                time.sleep(1)

        self._active = False
        logger.info("Wake word loop exited")

    def _extract_inline_command(self, text: str) -> str:
        """Extract command that came in the same utterance as the wake word."""
        t = text.lower().strip()
        for wake in sorted(WAKE_WORDS, key=len, reverse=True):
            if wake in t:
                after = t[t.index(wake) + len(wake):].strip(" ,.")
                if len(after) > 3:
                    return after
        return ""
