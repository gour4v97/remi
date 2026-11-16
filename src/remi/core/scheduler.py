"""Background task and cron scheduler for automated daily skills (e.g. morning digest).

Built using standard library threading and time routines. Zero extra dependencies.
Supports:
- Daily scheduled routines (e.g. 08:00 AM daily briefing)
- Recurring interval routines (e.g. hourly checks)
- In-process non-blocking daemon thread runner
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Any, Callable

from remi.core import config
from remi.skills import SkillManager
from remi.speech import tts
from remi.tools import router

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        target_time: str,  # "HH:MM" in 24hr format, e.g. "08:00"
        action_fn: Callable[[], Any],
        enabled: bool = True,
    ):
        self.name = name
        self.target_time = target_time
        self.action_fn = action_fn
        self.enabled = enabled
        self.last_run_date: str | None = None

    def should_run(self, now: datetime.datetime) -> bool:
        if not self.enabled:
            return False

        today_str = now.strftime("%Y-%m-%d")
        if self.last_run_date == today_str:
            return False  # Already executed today

        current_hm = now.strftime("%H:%M")
        return current_hm >= self.target_time

    def execute(self, now: datetime.datetime) -> None:
        self.last_run_date = now.strftime("%Y-%m-%d")
        try:
            logger.info(f"Executing scheduled task: {self.name}")
            self.action_fn()
        except Exception as ex:
            logger.error(f"Scheduled task {self.name} failed: {ex}")


class BackgroundScheduler:
    """Lightweight in-process cron daemon for Remi."""

    _instance: "BackgroundScheduler | None" = None
    _lock = threading.Lock()

    def __init__(self, check_interval_s: float = 30.0):
        self.check_interval_s = check_interval_s
        self.tasks: list[ScheduledTask] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._tasks_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "BackgroundScheduler":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def add_daily_task(self, name: str, time_hh_mm: str, action_fn: Callable[[], Any]) -> None:
        """Register a daily recurring task at HH:MM (24-hour time)."""
        with self._tasks_lock:
            # Replace existing task if same name
            self.tasks = [t for t in self.tasks if t.name != name]
            self.tasks.append(ScheduledTask(name, time_hh_mm, action_fn))
        logger.info(f"Registered daily task '{name}' at {time_hh_mm}")

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("BackgroundScheduler started.")

    def stop(self) -> None:
        self._running = False

    def _run_loop(self) -> None:
        while self._running:
            now = datetime.datetime.now()
            with self._tasks_lock:
                pending = [t for t in self.tasks if t.should_run(now)]

            for task in pending:
                task.execute(now)

            time.sleep(self.check_interval_s)


def run_morning_digest_routine() -> None:
    """Trigger the morning digest skill automatically."""
    cfg = config.load("remi-py")
    mgr = SkillManager()
    handled, spoken, detail = mgr.match_and_execute("morning digest", cfg)
    if handled:
        tts.say(spoken, enabled=cfg.get("voice_feedback", True))


def init_default_schedules() -> BackgroundScheduler:
    """Initialize default background routines (e.g. 08:00 AM Morning Digest)."""
    scheduler = BackgroundScheduler.get_instance()
    cfg = config.load("remi-py")
    schedule_cfg = cfg.get("schedule", {})

    if schedule_cfg.get("morning_digest_enabled", True):
        target_time = schedule_cfg.get("morning_digest_time", "08:00")
        scheduler.add_daily_task("morning_digest", target_time, run_morning_digest_routine)

    scheduler.start()
    return scheduler
