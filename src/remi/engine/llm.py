"""Local LLM and SLM (Small Language Model) inference and intent resolution engine.

Supports Ollama, llama.cpp, LM Studio, vLLM, and any local OpenAI-compatible endpoint.
Follows OpenJarvis local-first engine design with Hinglish context.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from remi.core.registry import EngineRegistry

logger = logging.getLogger(__name__)

SYSTEM_INTENT_PROMPT = """You are Remi, a fast, concise personal voice assistant for Windows.
You understand English AND Hinglish (Hindi-English mix).
Analyze the user's spoken command and respond ONLY with a single JSON object. No explanation, no markdown backticks.
JSON schema:
{
  "action": "speak" | "open_url" | "search" | "browser_action",
  "detail": "short detail",
  "spoken": "concise spoken response under 20 words",
  "url": "optional url to navigate to",
  "search_query": "optional search query if action is search"
}

Examples:
User: "What is 45 plus 88?"
Response: {"action": "speak", "detail": "calculation", "spoken": "45 plus 88 is 133."}

User: "Find recipes for chocolate cake"
Response: {"action": "search", "detail": "cake recipes", "spoken": "searching for chocolate cake recipes", "search_query": "chocolate cake recipes"}

User: "Go to BBC news"
Response: {"action": "open_url", "detail": "bbc news", "spoken": "opening bbc news", "url": "https://www.bbc.com"}

User: "Mausam kaisa hai aaj?"
Response: {"action": "search", "detail": "weather", "spoken": "searching for today's weather", "search_query": "weather today"}

User: "Mujhe naya tab chahiye"
Response: {"action": "browser_action", "detail": "new tab", "spoken": "opening new tab"}

User: "Volume thoda kam karo"
Response: {"action": "browser_action", "detail": "volume down", "spoken": "turning volume down"}
"""

PREFERRED_MODELS = [
    "llama3.2:3b",
    "llama3.2:1b",
    "qwen2.5:3b",
    "qwen2.5:1.5b",
    "qwen2.5:0.5b",
    "phi3:mini",
    "phi3.5:mini",
    "gemma2:2b",
    "mistral:7b",
]


def _pick_model(available: list[str]) -> str | None:
    avail_lower = {m.lower(): m for m in available}
    for pref in PREFERRED_MODELS:
        if pref in avail_lower:
            return avail_lower[pref]
    return available[0] if available else None


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    duration_ms: int = 0


class BaseLLMEngine(ABC):
    """Abstract interface for local language model inference engines."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        pass


@EngineRegistry.register("llm_ollama")
class OllamaEngine(BaseLLMEngine):
    """Local inference engine connecting to Ollama (http://127.0.0.1:11434)."""

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", model: str = "llama3.2:3b", timeout: int = 15):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read().decode("utf-8"))
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
            return LLMResponse(
                content=res.get("response", "").strip(),
                model=res.get("model", self.model),
                duration_ms=int(res.get("total_duration", 0) / 1_000_000),
            )


@EngineRegistry.register("llm_openai")
@EngineRegistry.register("llm_compat")
class OpenAICompatEngine(BaseLLMEngine):
    """Connects to any local OpenAI-compatible server (LM Studio, llama.cpp, vLLM)."""

    def __init__(self, endpoint: str = "http://127.0.0.1:1234/v1", model: str = "local-model", timeout: int = 15):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.endpoint}/models", method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            req = urllib.request.Request(f"{self.endpoint}/models", method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read().decode("utf-8"))
                return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            return []

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        url = f"{self.endpoint}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
            choice = res.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "").strip()
            return LLMResponse(content=content, model=res.get("model", self.model))


@EngineRegistry.register("llm_mock")
class MockLLMEngine(BaseLLMEngine):
    """Deterministic mock LLM engine for testing."""

    def __init__(self, default_response: str = '{"action": "speak", "spoken": "I understood your request."}'):
        self.default_response = default_response

    def is_available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["mock-slm"]

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> LLMResponse:
        return LLMResponse(content=self.default_response, model="mock-slm")


def auto_detect_llm() -> BaseLLMEngine | None:
    """Probe standard localhost endpoints and pick optimal model."""
    ollama = OllamaEngine()
    if ollama.is_available():
        models = ollama.list_models()
        if models:
            ollama.model = _pick_model(models) or models[0]
        return ollama

    lmstudio = OpenAICompatEngine(endpoint="http://127.0.0.1:1234/v1")
    if lmstudio.is_available():
        models = lmstudio.list_models()
        if models:
            lmstudio.model = _pick_model(models) or models[0]
        return lmstudio

    llamacpp = OpenAICompatEngine(endpoint="http://127.0.0.1:8080/v1")
    if llamacpp.is_available():
        return llamacpp

    return None


class IntentResolver:
    """Interprets unparsed voice commands using a local SLM/LLM."""

    def __init__(self, engine: BaseLLMEngine | None = None, cfg: dict | None = None):
        self.cfg = cfg or {}
        if engine:
            self.engine = engine
        else:
            backend = self.cfg.get("llm_backend", "auto")
            endpoint = self.cfg.get("llm_endpoint", "http://127.0.0.1:11434")
            model = self.cfg.get("llm_model", "llama3.2:3b")
            timeout = int(self.cfg.get("llm_timeout", 12))

            if backend == "ollama":
                self.engine = OllamaEngine(endpoint=endpoint, model=model, timeout=timeout)
            elif backend in ("openai", "openai_compat", "lmstudio"):
                self.engine = OpenAICompatEngine(endpoint=endpoint, model=model, timeout=timeout)
            elif backend == "mock":
                self.engine = MockLLMEngine()
            else:
                detected = auto_detect_llm()
                self.engine = detected if detected else OllamaEngine(endpoint=endpoint, model=model, timeout=timeout)

    def is_ready(self) -> bool:
        return self.engine is not None and self.engine.is_available()

    def resolve(self, text: str) -> dict[str, Any] | None:
        """Query local SLM to resolve intent into structured JSON action."""
        if not self.is_ready():
            return None

        prompt = f"User voice command: '{text}'"
        try:
            res = self.engine.generate(prompt, system=SYSTEM_INTENT_PROMPT, temperature=0.1)
            raw = res.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "action" in parsed:
                return parsed
        except Exception as ex:
            logger.debug(f"LLM intent resolution skipped: {ex}")
        return None


_cached_resolver: IntentResolver | None = None
_resolver_lock = threading.Lock()


def get_resolver(cfg: dict | None = None) -> IntentResolver:
    """Return a process-wide cached IntentResolver instance."""
    global _cached_resolver
    with _resolver_lock:
        if _cached_resolver is None:
            _cached_resolver = IntentResolver(cfg=cfg)
        return _cached_resolver
