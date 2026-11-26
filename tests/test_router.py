"""Unit tests for voice command router."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.tools.router import run


class TestRouter(unittest.TestCase):
    def test_time_and_date_offline_answers(self):
        cfg = {"cdp_port": 9222, "auto_launch_browser": False}
        outcome = run("what time is it", cfg)
        self.assertTrue(outcome.ok)
        self.assertIn("it's", outcome.spoken)

        outcome_date = run("what date is today", cfg)
        self.assertTrue(outcome_date.ok)
        self.assertIn("today is", outcome_date.spoken)

    def test_hinglish_time(self):
        cfg = {"cdp_port": 9222, "auto_launch_browser": False}
        outcome = run("time batao", cfg)
        self.assertTrue(outcome.ok)
        self.assertIn("it's", outcome.spoken)

    def test_empty_transcript(self):
        cfg = {"cdp_port": 9222, "auto_launch_browser": False}
        outcome = run("", cfg)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.spoken, "nothing heard")

    def test_open_skill_beats_web_search(self):
        import subprocess
        from unittest.mock import patch

        cfg = {"cdp_port": 9222, "auto_launch_browser": False, "llm_enabled": False}
        with patch.object(subprocess, "Popen") as mock_popen:
            out_calc = run("open calculator", cfg)
            self.assertTrue(out_calc.ok)
            self.assertEqual(out_calc.detail, "system_app:calc.exe")
            mock_popen.assert_called_with(["calc.exe"])

            out_note = run("notepad kholo", cfg)
            self.assertTrue(out_note.ok)
            self.assertEqual(out_note.detail, "system_app:notepad.exe")
            mock_popen.assert_called_with(["notepad.exe"])


if __name__ == "__main__":
    unittest.main()
