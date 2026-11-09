"""Unit tests for Devanagari transliteration and smart punctuation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.speech.translit import (
    has_devanagari,
    smart_writing,
    to_roman,
)


class TestTranslit(unittest.TestCase):
    def test_has_devanagari(self):
        self.assertTrue(has_devanagari("नमस्ते"))
        self.assertFalse(has_devanagari("Hello world"))
        self.assertTrue(has_devanagari("YouTube खोलो"))

    def test_to_roman_basic(self):
        self.assertEqual(to_roman("नमस्ते"), "namaste")
        self.assertEqual(to_roman("भारत"), "bharat")
        self.assertEqual(to_roman("खोलो"), "kholo")

    def test_to_roman_english_passthrough(self):
        self.assertEqual(to_roman("Open YouTube"), "Open YouTube")

    def test_smart_writing_punctuation(self):
        input_text = "hello comma world full stop this is a test"
        res = smart_writing(input_text, mode="smart")
        self.assertIn("Hello, world. This is a test", res)

    def test_smart_writing_hindi_punctuation(self):
        input_text = "नमस्ते पूर्ण विराम"
        res = smart_writing(input_text, mode="smart")
        self.assertIn("।", res)


if __name__ == "__main__":
    unittest.main()
