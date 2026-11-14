"""Per-stage pipeline latency timer for --bench mode.

Usage:
    timer = PipelineTimer()
    timer.mark("key_up")
    # ... do work ...
    timer.mark("transcribed")
    timer.mark("action_done")
    timer.print_table()     # pretty stdout table
    timer.log_to_file()     # append JSON line to ~/remi-bench.jsonl
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical stage order for display
STAGES = [
    "key_up",        # hotkey released / recording handed off
    "audio_ready",   # PCM bytes validated (not silent, not too short)
    "http_sent",     # POST body sent to whisper.cpp server
    "transcribed",   # transcript text received from ASR
    "parsed",        # command router matched (or fell through to LLM)
    "action_done",   # browser/delivery/LLM action complete
    "tts_start",     # TTS speak() invoked
]


class PipelineTimer:
    """Stamps named pipeline stages and reports per-stage latency deltas.

    Lightweight: uses time.perf_counter() with no external dependencies.
    Thread-safe reads; not designed for concurrent writes from multiple threads.
    """

    def __init__(self, session_id: str = ""):
        self._marks: dict[str, float] = {}
        self._session = session_id or str(int(time.time() * 1000))
        self._t0 = time.perf_counter()

    def mark(self, stage: str) -> float:
        """Record a named stage timestamp.

        Returns:
            Milliseconds elapsed since timer creation.
        """
        t = time.perf_counter()
        self._marks[stage] = t
        elapsed = (t - self._t0) * 1000
        logger.debug(f"[PERF] {stage}: +{elapsed:.1f}ms total")
        return elapsed

    def summary(self) -> dict[str, dict]:
        """Return ordered dict of stage -> timing data.

        Each entry has:
            since_start_ms: ms from timer creation to this stage
            delta_ms: ms from previous recorded stage to this stage
            prev_stage: name of the previous stage (for display)
        """
        result: dict[str, dict] = {}
        prev_t = self._t0
        prev_name = "start"
        # Iterate in canonical order, skip unrecorded stages
        all_stages = STAGES + [s for s in self._marks if s not in STAGES]
        for stage in all_stages:
            if stage not in self._marks:
                continue
            t = self._marks[stage]
            since_start = (t - self._t0) * 1000
            delta = (t - prev_t) * 1000
            result[stage] = {
                "since_start_ms": round(since_start, 1),
                "delta_ms": round(delta, 1),
                "prev_stage": prev_name,
            }
            prev_t = t
            prev_name = stage
        return result

    def total_ms(self) -> float:
        """Return total elapsed ms across all recorded stages."""
        if not self._marks:
            return 0.0
        return (max(self._marks.values()) - self._t0) * 1000

    def log_to_file(self, path: Optional[Path] = None) -> None:
        """Append a JSON summary line to bench.jsonl (default: ~/remi-bench.jsonl)."""
        p = path or Path.home() / "remi-bench.jsonl"
        entry = {
            "session": self._session,
            "total_ms": round(self.total_ms(), 1),
            "stages": self.summary(),
        }
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as ex:
            logger.warning(f"Could not write bench log to {p}: {ex}")

    def print_table(self) -> None:
        """Pretty-print latency table to stdout."""
        summary = self.summary()
        if not summary:
            print("[BENCH] No pipeline stages recorded.")
            return
        sep = "─" * 21 + "┼" + "─" * 14 + "┼" + "─" * 14
        print(f"\n┌{'─'*21}┬{'─'*14}┬{'─'*14}┐")
        print(f"│ {'Stage':<19} │ {'Since start':>12} │ {'Delta':>12} │")
        print(f"├{sep}┤")
        for stage, data in summary.items():
            since = f"{data['since_start_ms']}ms"
            delta = f"{data['delta_ms']}ms"
            # Highlight slow stages (>300ms delta)
            flag = " ⚠" if data["delta_ms"] > 300 else "  "
            print(f"│ {stage:<19} │ {since:>12} │ {delta:>12}{flag}│")
        print(f"└{'─'*21}┴{'─'*14}┴{'─'*14}┘")
        print(f"  Total: {self.total_ms():.1f}ms\n")
