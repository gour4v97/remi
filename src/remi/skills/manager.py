"""Skill manager: discovers, parses, and executes custom user and built-in skills."""
from __future__ import annotations

import logging
import os
import tomllib
import urllib.parse
from pathlib import Path
from typing import Any

from remi.core import config
from remi.core.registry import SkillRegistry
from remi.skills._base import Skill, SkillAction

logger = logging.getLogger(__name__)


def user_skills_dir() -> Path:
    """Return user custom skills directory."""
    return config.APPDATA / "skills"


def builtin_skills_dir() -> Path:
    """Return built-in skills directory."""
    return Path(__file__).resolve().parent / "builtin"


class SkillManager:
    """Discovers and executes declarative TOML and Python skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        """Scan built-in and user directories to register all skills."""
        self._skills.clear()
        
        # 1. Load built-ins
        b_dir = builtin_skills_dir()
        if b_dir.exists():
            for p in b_dir.glob("*.toml"):
                self._load_toml_file(p)

        # 2. Load user skills
        u_dir = user_skills_dir()
        if u_dir.exists():
            for p in u_dir.glob("*.toml"):
                self._load_toml_file(p)

        # 3. Synchronize with SkillRegistry
        for name, skill in self._skills.items():
            SkillRegistry.register_value(name, skill)

    def _load_toml_file(self, path: Path) -> None:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            name = data.get("name", path.stem)
            desc = data.get("description", "")
            triggers = data.get("triggers", [])
            act_data = data.get("action", {})

            action = SkillAction(
                action_type=act_data.get("type", "open_url"),
                target=act_data.get("target", act_data.get("url", "")),
                spoken=act_data.get("spoken", f"executing {name}"),
                params=act_data,
            )

            skill = Skill(
                name=name,
                description=desc,
                triggers=triggers,
                action=action,
                enabled=data.get("enabled", True),
            )
            self._skills[name] = skill
        except Exception as ex:
            logger.warning(f"Failed to load skill at {path}: {ex}")

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def match_and_execute(self, text: str, cfg: dict) -> tuple[bool, str, str]:
        """Check all registered skills against text. Return (handled, spoken, detail)."""
        for skill in self._skills.values():
            if not skill.enabled:
                continue
            matched, payload = skill.matches(text)
            if matched and skill.action:
                return self._run_action(skill, payload, cfg)
        return False, "", ""

    def _run_action(self, skill: Skill, payload: str, cfg: dict) -> tuple[bool, str, str]:
        act = skill.action
        if not act:
            return False, "", ""

        # Action: open_url or search
        if act.action_type in ("open_url", "search"):
            from remi.tools import browser, router
            if not router.ensure_cdp(cfg):
                return False, "browser not reachable", "CDP down"
            
            target = act.target
            if payload:
                # Replace placeholder {query} or append query
                if "{query}" in target:
                    target = target.replace("{query}", urllib.parse.quote(payload))
                elif act.params.get("search_url"):
                    target = act.params["search_url"].replace("{query}", urllib.parse.quote(payload))
                else:
                    target = f"{target.rstrip('/')}/search?q={urllib.parse.quote(payload)}"
            
            browser.new_tab(cfg.get("cdp_port", 9222), target)
            spoken = act.spoken.replace("{payload}", payload) if "{payload}" in act.spoken else act.spoken
            return True, spoken, f"skill:{skill.name}"

        # Action: speak
        if act.action_type == "speak":
            spoken = act.spoken.replace("{payload}", payload)
            return True, spoken, f"skill:{skill.name}"

        return False, "", ""
