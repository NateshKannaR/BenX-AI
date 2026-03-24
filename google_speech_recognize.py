import argparse
import os
import sys
import tempfile
import wave
from pathlib import Path

import speech_recognition as sr

def transcribe_with_google(audio_path: Path, language: str = "en-US") -> str:
    recognizer = sr.Recognizer()

    with sr.AudioFile(str(audio_path)) as source:
        audio_data = recognizer.record(source)   

    try:
        result = recognizer.recognize_google(audio_data, language=language)
        return result
    except sr.UnknownValueError:
        return "Google Speech Recognition could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

def main() -> None:
    audio_file = Path("/tmp/audio.wav")
    try:
        transcript = transcribe_with_google(audio_file)
        print(transcript)
    except Exception as err:
        print(f"❌  Transcription error: {err}")

if __name__ == "__main__":
    main()""")

Action: python_run("python google_speech_recognize.py