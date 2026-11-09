"""Base Agent abstractions for Remi voice assistants."""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract interface for all runnable voice agents."""

    @abstractmethod
    def start(self) -> None:
        """Launch the agent's main loop / system tray."""
        pass

    @abstractmethod
    def toggle(self) -> None:
        """Triggered when hotkey is pressed."""
        pass

    @abstractmethod
    def process_audio(self, pcm: bytes) -> Any:
        """Process captured audio buffer."""
        pass
