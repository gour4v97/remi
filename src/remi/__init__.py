"""Remi Suite - Local-first offline voice assistant and dictation for Windows.

Modeled after OpenJarvis composable primitives:
- engine: ASR inference abstractions & persistent whisper.cpp server
- speech: Audio capture, resampling, transliteration, SAPI TTS
- tools: Browser CDP automation, Command grammar router, Windows text delivery
- agents: BrowserVoiceAgent and DictationAgent
- core: Registry, Config, EventBus, Constants
"""
from remi.core.constants import APP_DISPLAY_NAME, APP_VERSION
from remi.core.registry import (
    AgentRegistry,
    EngineRegistry,
    RegistryBase,
    SpeechRegistry,
    ToolRegistry,
    TTSRegistry,
)

__version__ = APP_VERSION
__app_name__ = APP_DISPLAY_NAME

__all__ = [
    "__version__",
    "__app_name__",
    "RegistryBase",
    "EngineRegistry",
    "AgentRegistry",
    "ToolRegistry",
    "SpeechRegistry",
    "TTSRegistry",
]
