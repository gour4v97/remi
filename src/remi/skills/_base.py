"""Base Skill specifications and models for extensible voice workflows.

Modeled after OpenJarvis skills standard.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillAction:
    """Action executed when a skill trigger matches."""
    action_type: str  # "open_url", "search", "hotkey", "exec", "speak", "custom"
    target: str = ""
    spoken: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """Declarative skill definition loaded from TOML or Python."""
    name: str
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    action: SkillAction | None = None
    handler: Callable[[str, dict], Any] | None = None
    enabled: bool = True

    def matches(self, text: str) -> tuple[bool, str]:
        """Check if voice text matches any trigger, returning (matches, payload)."""
        t = text.lower().strip()
        for trig in self.triggers:
            trig_clean = trig.lower().strip()
            if t == trig_clean:
                return True, ""
            if t.startswith(trig_clean + " "):
                return True, t[len(trig_clean) + 1:].strip()
            # Regex match support if trigger starts with ^
            if trig_clean.startswith("^") and re.search(trig_clean, t):
                return True, t
        return False, ""


class BaseSkill(ABC):
    """Abstract class for programmatic Python skills."""

    name: str
    description: str
    triggers: list[str]

    @abstractmethod
    def execute(self, text: str, payload: str, context: dict) -> Any:
        """Execute custom skill logic."""
        pass
