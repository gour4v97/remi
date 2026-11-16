"""agentskills.io and Hermes manifest importer & converter.

Converts skills following the agentskills.io YAML specification into Remi's native TOML skill format.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from remi.skills import user_skills_dir

logger = logging.getLogger(__name__)


def parse_agentskills_yaml(yaml_content: str) -> dict[str, Any]:
    """Parse a basic agentskills.io manifest."""
    try:
        import yaml
        return yaml.safe_load(yaml_content) or {}
    except ImportError:
        pass

    # Basic fallback parser for simple key-value YAML when pyyaml is absent
    data: dict[str, Any] = {}
    current_key = None
    for line in yaml_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip().strip('"').strip("'")
            if v:
                data[k] = v
            else:
                data[k] = []
                current_key = k
        elif line.startswith("-") and current_key:
            item = line.lstrip("-").strip().strip('"').strip("'")
            if isinstance(data.get(current_key), list):
                data[current_key].append(item)
    return data


def convert_agentskills_to_remi(manifest_yaml: str) -> str:
    """Convert an agentskills.io manifest into Remi TOML representation."""
    spec = parse_agentskills_yaml(manifest_yaml)
    name = spec.get("name", "imported_skill")
    desc = spec.get("description", "Imported from agentskills.io")
    triggers = spec.get("triggers", [name.replace("_", " ")])
    url = spec.get("url", spec.get("endpoint", "https://google.com"))
    spoken = spec.get("spoken", f"executing {name}")

    toml_lines = [
        f'name = "{name}"',
        f'description = "{desc}"',
        f'triggers = [',
    ]
    for t in triggers:
        toml_lines.append(f'    "{t}",')
    toml_lines.append(']')
    toml_lines.append('')
    toml_lines.append('[action]')
    toml_lines.append('type = "open_url"')
    toml_lines.append(f'url = "{url}"')
    toml_lines.append(f'spoken = "{spoken}"')
    toml_lines.append('')

    return "\n".join(toml_lines)


def import_agentskills_file(filepath: Path) -> Path | None:
    """Read an agentskills YAML manifest and save as a Remi skill TOML in user skills directory."""
    if not filepath.exists():
        return None

    content = filepath.read_text(encoding="utf-8")
    toml_str = convert_agentskills_to_remi(content)
    spec = parse_agentskills_yaml(content)
    skill_name = spec.get("name", filepath.stem)

    target_dir = user_skills_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{skill_name}.toml"
    out_file.write_text(toml_str, encoding="utf-8")
    logger.info(f"Imported agentskills.io manifest to {out_file}")
    return out_file
