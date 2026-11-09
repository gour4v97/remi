"""Unit tests for local LLM and SLM intent resolution."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.core.registry import EngineRegistry
from remi.engine.llm import (
    IntentResolver,
    MockLLMEngine,
    OllamaEngine,
    OpenAICompatEngine,
)
from remi.tools.router import run


class TestLLMEngine(unittest.TestCase):
    def test_registry_contains_llm_engines(self):
        self.assertTrue(EngineRegistry.contains("llm_ollama"))
        self.assertTrue(EngineRegistry.contains("llm_openai"))
        self.assertTrue(EngineRegistry.contains("llm_mock"))

    def test_mock_llm_generation(self):
        engine = MockLLMEngine(default_response='{"action": "speak", "spoken": "Hello from mock SLM"}')
        self.assertTrue(engine.is_available())
        self.assertEqual(engine.list_models(), ["mock-slm"])

        res = engine.generate("Say hello")
        self.assertIn("Hello from mock SLM", res.content)

    def test_intent_resolver_speak_action(self):
        engine = MockLLMEngine(default_response='{"action": "speak", "spoken": "42 is the answer", "detail": "math"}')
        resolver = IntentResolver(engine=engine)
        self.assertTrue(resolver.is_ready())

        intent = resolver.resolve("What is the meaning of life?")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "speak")
        self.assertEqual(intent["spoken"], "42 is the answer")

    def test_intent_resolver_open_url_action(self):
        engine = MockLLMEngine(default_response='{"action": "open_url", "url": "https://news.ycombinator.com", "spoken": "opening hacker news"}')
        resolver = IntentResolver(engine=engine)
        intent = resolver.resolve("open hacker news")
        self.assertEqual(intent["action"], "open_url")
        self.assertEqual(intent["url"], "https://news.ycombinator.com")

    def test_router_integration_with_mock_llm(self):
        # Configure router with mock backend
        cfg = {
            "cdp_port": 9222,
            "auto_launch_browser": False,
            "llm_enabled": True,
            "llm_backend": "mock",
        }
        # Unknown command that would normally fail
        outcome = run("Tell me a bedtime story about robots", cfg)
        self.assertTrue(outcome.ok)


if __name__ == "__main__":
    unittest.main()
