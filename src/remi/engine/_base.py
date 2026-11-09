"""Abstract Base Class for ASR Inference Engines."""
from abc import ABC, abstractmethod
from pathlib import Path


class BaseASREngine(ABC):
    """Abstract interface for speech transcription engines."""

    @abstractmethod
    def transcribe_pcm(
        self,
        pcm: bytes,
        model: str,
        language: str = "hinglish",
        cfg: dict | None = None,
    ) -> str:
        """Transcribe 16 kHz mono 16-bit PCM audio bytes to text."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the engine is ready to transcribe."""
        pass

    def prewarm(self, cfg: dict | None = None) -> None:
        """Optional hook to initialize/warm-up engine in the background."""
        pass

    def shutdown(self) -> None:
        """Optional hook to clean up resources."""
        pass
