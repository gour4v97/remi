"""Unit tests for PipelineTimer latency tracking."""
from __future__ import annotations

import time
from remi.core.perf import PipelineTimer


def test_pipeline_timer_lifecycle():
    timer = PipelineTimer(session_id="test_session")
    timer.mark("key_up")
    time.sleep(0.01)
    timer.mark("audio_ready")
    time.sleep(0.01)
    timer.mark("transcribed")
    timer.mark("action_done")

    summary = timer.summary()
    assert "key_up" in summary
    assert "audio_ready" in summary
    assert "transcribed" in summary
    assert "action_done" in summary

    assert summary["audio_ready"]["since_start_ms"] >= summary["key_up"]["since_start_ms"]
    assert timer.total_ms() > 0.0
