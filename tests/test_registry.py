"""Unit tests for Remi registry pattern."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.core.registry import (
    AgentRegistry,
    EngineRegistry,
    RegistryBase,
    ToolRegistry,
)


class TestRegistry(unittest.TestCase):
    def test_registry_registration_and_get(self):
        class TestItemRegistry(RegistryBase):
            pass

        @TestItemRegistry.register("mock_item")
        class MockItem:
            pass

        self.assertTrue(TestItemRegistry.contains("mock_item"))
        self.assertTrue(TestItemRegistry.contains("MOCK_ITEM"))  # Case-insensitive
        self.assertIs(TestItemRegistry.get("mock_item"), MockItem)

    def test_registry_missing_key_raises(self):
        class BlankRegistry(RegistryBase):
            pass

        with self.assertRaises(KeyError):
            BlankRegistry.get("non_existent")

    def test_core_registries_populated(self):
        import remi.engine.whisper_cpp
        import remi.agents.browser_agent
        import remi.agents.dictation_agent
        import remi.tools.router

        self.assertTrue(EngineRegistry.contains("whisper_cpp"))
        self.assertTrue(AgentRegistry.contains("browser"))
        self.assertTrue(AgentRegistry.contains("dictation"))
        self.assertTrue(ToolRegistry.contains("router"))


if __name__ == "__main__":
    unittest.main()
