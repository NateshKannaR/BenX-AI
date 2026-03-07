"""
Voice Handler - Speech recognition and text-to-speech
"""
import logging
from typing import Optional
import threading

logger = logging.getLogger(__name__)

# Optional dependencies
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


class VoiceHandler:
    """Voice input/output handler"""
    
    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        
        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 4000
            except Exception as e:
                logger.warning(f"Voice recognition setup failed: {e}")
        
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                logger.warning(f"TTS setup failed: {e}")
    
    def listen(self) -> Optional[str]:
        """Listen for voice input"""
        if not self.recognizer:
            return None
        
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            try:
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error(f"Voice recognition error: {e}")
                return None
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return None
    
    def speak(self, text: str):
        """Speak text using TTS"""
        if not self.tts_engine:
            return
        
        try:
            def _speak():
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            thread = threading.Thread(target=_speak, daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"TTS error: {e}")









