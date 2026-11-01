"""Local-only JSONL history."""
import json
import threading
import uuid
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()


def append(app: str, entry: dict):
    entry.setdefault("id", uuid.uuid4().hex)
    entry.setdefault("at", datetime.now(timezone.utc).isoformat())
    with _lock:
        with open(config.history_path(app), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load(app: str, last: int = 20):
    p = config.history_path(app)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out[-last:]
