"""Unit tests for the modular skills subsystem."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.core.registry import SkillRegistry
from remi.skills._base import Skill, SkillAction
from remi.skills.manager import SkillManager


class TestSkills(unittest.TestCase):
    def test_skill_matching_exact_and_prefix(self):
        act = SkillAction(action_type="open_url", target="https://example.com")
        skill = Skill(
            name="example",
            triggers=["open example", "example search"],
            action=act,
        )

        # Exact match
        matched, payload = skill.matches("open example")
        self.assertTrue(matched)
        self.assertEqual(payload, "")

        # Prefix match with payload
        matched, payload = skill.matches("example search quantum physics")
        self.assertTrue(matched)
        self.assertEqual(payload, "quantum physics")

        # Non-matching
        matched, payload = skill.matches("hello world")
        self.assertFalse(matched)

    def test_builtin_skills_loaded(self):
        mgr = SkillManager()
        skills = mgr.list_skills()
        self.assertGreaterEqual(len(skills), 2)
        names = [s.name for s in skills]
        self.assertIn("developer_tools", names)
        self.assertIn("hacker_news", names)
        self.assertTrue(SkillRegistry.contains("developer_tools"))
        self.assertTrue(SkillRegistry.contains("hacker_news"))


if __name__ == "__main__":
    unittest.main()
