"""Remi Agents subpackage (BrowserVoiceAgent, DictationAgent)."""
from remi.agents._base import BaseAgent
from remi.agents.browser_agent import BrowserVoiceAgent, say_audio, say_text
from remi.agents.dictation_agent import DictationAgent, apply_dictionary, load_dictionary

__all__ = [
    "BaseAgent",
    "BrowserVoiceAgent",
    "DictationAgent",
    "say_text",
    "say_audio",
    "load_dictionary",
    "apply_dictionary",
]
