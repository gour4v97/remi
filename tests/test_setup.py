"""Unit tests for Remi setup wizard and launcher generators."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.cli.setup import create_launcher_scripts, run_setup


class TestSetup(unittest.TestCase):
    def test_create_launcher_scripts(self):
        scripts = create_launcher_scripts()
        self.assertGreaterEqual(len(scripts), 2)
        for s in scripts:
            p = Path(s)
            self.assertTrue(p.exists(), f"Launcher script {p} does not exist")
            content = p.read_text(encoding="utf-8")
            self.assertIn("python -m remi", content)

    def test_non_interactive_setup_execution(self):
        # Verify run_setup executes without unhandled exceptions in non-interactive mode
        try:
            run_setup(non_interactive=True)
        except Exception as ex:
            self.fail(f"run_setup(non_interactive=True) raised unexpected exception: {ex}")


if __name__ == "__main__":
    unittest.main()
