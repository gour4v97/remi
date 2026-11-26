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

    def test_sectioned_toml_load_and_save_roundtrip(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "APPDATA", Path(tmpdir)):
                p = config.config_path("section-test")
                p.write_text(
                    '[engine]\nlocal_model = "small"\nasr_port = 9999\n\n'
                    '[llm]\nenabled = false\n\n[openjarvis]\nenabled = true\n',
                    encoding="utf-8",
                )
                loaded = config.load("section-test")
                self.assertEqual(loaded["local_model"], "small")
                self.assertEqual(loaded["asr_port"], 9999)
                self.assertFalse(loaded["llm_enabled"])

                loaded["custom_path"] = r"C:\Users\Test\file.bin"
                config.save("section-test", loaded)
                reloaded = config.load("section-test")
                self.assertEqual(reloaded["custom_path"], r"C:\Users\Test\file.bin")
                self.assertTrue(reloaded["openjarvis"]["enabled"])


if __name__ == "__main__":
    unittest.main()
