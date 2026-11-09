"""Unit tests for configuration management."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.core import config
from remi.core.constants import DEFAULT_MODEL, DEFAULT_ASR_PORT, DEFAULT_CDP_PORT


class TestConfig(unittest.TestCase):
    def test_config_defaults(self):
        cfg = config.load("test-app")
        self.assertEqual(cfg["local_model"], DEFAULT_MODEL)
        self.assertEqual(cfg["asr_port"], DEFAULT_ASR_PORT)
        self.assertEqual(cfg["cdp_port"], DEFAULT_CDP_PORT)
        self.assertEqual(cfg["app"], "test-app")

    def test_paths_not_empty(self):
        self.assertIsNotNone(config.APPDATA)
        self.assertIsNotNone(config.LOCALAPPDATA)
        self.assertIsNotNone(config.BIN_DIR)


if __name__ == "__main__":
    unittest.main()
