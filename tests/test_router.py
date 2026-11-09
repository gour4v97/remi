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


if __name__ == "__main__":
    unittest.main()
