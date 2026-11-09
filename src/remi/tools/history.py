"""Local JSONL execution history logging."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from remi.core import config
from remi.core.registry import ToolRegistry

_lock = threading.Lock()


def append(app: str, entry: dict[str, Any]) -> None:
    """Thread-safe append of an audit log entry to the app JSONL file."""
    entry.setdefault("id", uuid.uuid4().hex)
    entry.setdefault("at", datetime.now(timezone.utc).isoformat())
    with _lock:
        path = config.history_path(app)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load(app: str, last: int = 20) -> list[dict[str, Any]]:
    """Retrieve the last N entries from the history log."""
    path = config.history_path(app)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line_str = line.strip()
            if line_str:
                try:
                    out.append(json.loads(line_str))
                except json.JSONDecodeError:
                    pass
    except Exception:
        return []
    return out[-last:]


@ToolRegistry.register("history")
class HistoryStore:
    """Registered tool interface for logging and retrieving interaction history."""

    def __init__(self, app_name: str = "remi-py"):
        self.app_name = app_name

    def record(self, entry: dict[str, Any]) -> None:
        append(self.app_name, entry)

    def recent(self, count: int = 20) -> list[dict[str, Any]]:
        return load(self.app_name, count)
