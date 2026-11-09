"""Remi Speech subpackage (Microphone capture, Transliteration, TTS)."""
from remi.speech.capture import MicCapture, resample_16k
from remi.speech.translit import (
    CONSONANTS,
    MATRAS,
    VOWELS,
    has_devanagari,
    smart_writing,
    to_roman,
)
from remi.speech.tts import BaseTTS, SapiTTS, say

__all__ = [
    "MicCapture",
    "resample_16k",
    "VOWELS",
    "CONSONANTS",
    "MATRAS",
    "has_devanagari",
    "to_roman",
    "smart_writing",
    "BaseTTS",
    "SapiTTS",
    "say",
]
