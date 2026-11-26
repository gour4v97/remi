"""Unit tests for Remi setup wizard, launcher generators, icons, and autostart."""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.cli.setup import create_launcher_scripts, run_setup
from remi.core.constants import APP_BROWSER_ID, APP_DICTATION_ID
from remi.ui.autostart import _value_for
from remi.ui.tray import make_icon


class TestSetup(unittest.TestCase):
    def test_create_launcher_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts = create_launcher_scripts(target_dir=Path(tmpdir))
            self.assertGreaterEqual(len(scripts), 3)
            for s in scripts:
                p = Path(s)
                self.assertTrue(p.exists(), f"Launcher script {p} does not exist")
                content = p.read_text(encoding="utf-8")
                self.assertIn("Gaurav Manjhi", content)
                if p.name.startswith("launch-"):
                    self.assertIn("-m remi", content)
                    self.assertIn("venv\\Scripts\\python.exe", content)

    def test_non_interactive_setup_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from unittest.mock import patch
            with patch("remi.cli.setup.create_launcher_scripts", return_value=[]):
                run_setup(non_interactive=True)

    def test_tray_icon_and_svg_assets(self):
        img = make_icon((74, 144, 217), "R")
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (64, 64))

        root = Path(__file__).resolve().parent.parent
        self.assertTrue((root / "assets" / "remi.ico").exists())
        ET.parse(root / "assets" / "logo.svg")
        ET.parse(root / "assets" / "hud-demo.svg")

    def test_autostart_command_generation(self):
        cmd_browser = _value_for("remi.exe", APP_BROWSER_ID)
        cmd_dict = _value_for("voice-trans.exe", APP_DICTATION_ID)
        self.assertIn("-m remi start", cmd_browser)
        self.assertIn("-m remi dictation", cmd_dict)


if __name__ == "__main__":
    unittest.main()
