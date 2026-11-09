"""Registry pattern for Remi Suite - modeled after OpenJarvis composable primitives.

Allows modules to register implementations via decorators and look them up dynamically at runtime.
"""
from typing import Callable, ClassVar, Generic, TypeVar

T = TypeVar("T")


class RegistryBase(Generic[T]):
    """Base generic registry enabling decorator and programmatic registration."""

    _registry: ClassVar[dict[str, type[T] | T | Callable[..., T]]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry = {}

    @classmethod
    def register(cls, key: str) -> Callable[[type[T] | Callable[..., T]], type[T] | Callable[..., T]]:
        """Decorator to register a class or factory function under a unique key."""
        def decorator(item: type[T] | Callable[..., T]) -> type[T] | Callable[..., T]:
            cls._registry[key.lower()] = item
            return item
        return decorator

    @classmethod
    def register_value(cls, key: str, value: T) -> T:
        """Imperatively register an instance or object."""
        cls._registry[key.lower()] = value
        return value

    @classmethod
    def get(cls, key: str) -> type[T] | T | Callable[..., T]:
        """Retrieve registered item by key."""
        k = key.lower()
        if k not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "none"
            raise KeyError(f"'{key}' not found in {cls.__name__}. Available: {available}")
        return cls._registry[k]

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if key exists in the registry."""
        return key.lower() in cls._registry

    @classmethod
    def list_keys(cls) -> list[str]:
        """Return list of all registered keys."""
        return sorted(cls._registry.keys())

    @classmethod
    def create(cls, key: str, *args, **kwargs) -> T:
        """Instantiate or call the registered factory."""
        item = cls.get(key)
        if callable(item):
            return item(*args, **kwargs)
        return item


class EngineRegistry(RegistryBase):
    """Registry for ASR and Inference engines (e.g. whisper_cpp, mock, cloud)."""


class AgentRegistry(RegistryBase):
    """Registry for runnable agents (e.g. browser, dictation, assistant)."""


class ToolRegistry(RegistryBase):
    """Registry for automation tools and routers (e.g. browser, router, delivery)."""


class SpeechRegistry(RegistryBase):
    """Registry for speech capture, audio processing, and transliteration."""


class TTSRegistry(RegistryBase):
    """Registry for Text-to-Speech synthesis engines (e.g. sapi, mock)."""
