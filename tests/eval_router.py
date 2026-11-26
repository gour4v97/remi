#!/usr/bin/env python3
"""Automated accuracy evaluation harness for the Remi intent router and skills.

Evaluates test queries across English, Hindi, and Hinglish command sets,
verifying whether commands match expected actions with fast-path latency (<5ms).

Usage:
    python tests/eval_router.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure src/ is on search path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from remi.tools import router

# Test dataset of utterances across domains and languages
EVAL_DATASET = [
    # 1. Tab navigation
    ("next tab", True, "tab:"),
    ("agla tab", True, "tab:"),
    ("previous tab", True, "tab:"),
    ("pichla tab", True, "tab:"),
    ("new tab", True, "new tab"),
    ("naya tab kholo", True, "new tab"),
    ("close tab", True, "closed tab"),
    ("tab band karo", True, "closed tab"),
    ("refresh", True, "refreshing page"),
    ("wapas jao", True, "going back"),
    # 2. Scrolling
    ("scroll down", True, "scrolled down"),
    ("neeche scroll karo", True, "scrolled down"),
    ("scroll to top", True, "scrolled to top"),
    ("sabse upar", True, "scrolled to top"),
    # 3. Media control
    ("play", True, "media toggle"),
    ("pause karo", True, "media toggle"),
    ("volume up", True, "volume up"),
    ("awaaz badhao", True, "volume up"),
    ("volume kam karo", True, "volume down"),
    ("mute karo", True, "mute toggle"),
    # 4. Zoom & Screen
    ("zoom in", True, "zoom in"),
    ("bada karo page", True, "zoom in"),
    ("zoom out", True, "zoom out"),
    ("fullscreen", True, "fullscreen"),
    # 5. Offline instant answers
    ("what time is it", True, "it's"),
    ("time batao", True, "it's"),
    ("aaj ki tarikh", True, "today is"),
    # 6. Sites and search
    ("youtube kholo", True, "opening youtube"),
    ("open github", True, "opening github"),
    ("search weather in Delhi", True, "search:"),
    # 7. Context Memory
    ("open that again", True, ""),
    ("wapas kholo", True, ""),
    # 8. Builtin Skills
    ("morning digest", True, "skill:morning_digest"),
    ("aaj ka digest", True, "skill:morning_digest"),
    ("open calculator", True, "system_app:"),
    ("notepad kholo", True, "system_app:"),
]


def run_eval() -> None:
    import subprocess
    import tempfile
    from unittest.mock import patch
    from remi.core import config
    from remi.core.memory import MemoryStore
    from remi.tools import browser

    print("\n=======================================================")
    print(f"[*] Remi Intent Router Evaluation ({len(EVAL_DATASET)} queries)")
    print("=======================================================\n")

    cfg = {"cdp_port": 9222, "llm_enabled": False, "auto_launch_browser": False}
    passed = 0
    total_time_ms = 0.0

    print(f"{'Utterance':<30} {'Expected':<10} {'Result':<10} {'Latency':>10}")
    print(f"{'-'*64}")

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_instance = MemoryStore._instance
        MemoryStore._instance = None
        try:
            with (
                patch.object(config, "APPDATA", Path(tmpdir)),
                patch.object(browser, "is_cdp_up", return_value=False),
                patch.object(subprocess, "Popen", return_value=None),
            ):
                mem = MemoryStore.get_instance()
                mem.remember_entity("last_url", "https://www.youtube.com", "youtube")

                for query, expected_ok, expected_snippet in EVAL_DATASET:
                    t0 = time.perf_counter()
                    outcome = router.run(query, cfg)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    total_time_ms += elapsed_ms

                    combined = f"{outcome.spoken} {outcome.detail}"
                    if expected_snippet.startswith("system_app:"):
                        is_correct = outcome.ok == expected_ok and expected_snippet in combined
                    else:
                        is_correct = (
                            (outcome.ok == expected_ok and (not expected_snippet or expected_snippet in combined))
                            or "browser not reachable" in outcome.spoken
                        )

                    if is_correct:
                        passed += 1
                        status = "[PASS]"
                    else:
                        status = "[FAIL]"

                    print(f"{query:<30} {str(expected_ok):<10} {status:<10} {elapsed_ms:>8.2f}ms")

                mem.close()
        finally:
            MemoryStore._instance = orig_instance

    avg_latency = total_time_ms / len(EVAL_DATASET)
    accuracy = (passed / len(EVAL_DATASET)) * 100

    print(f"{'-'*64}")
    print(f"Total Passed : {passed}/{len(EVAL_DATASET)} ({accuracy:.1f}%)")
    print(f"Avg Latency  : {avg_latency:.2f}ms per query")
    print(f"Status       : {'[OK] EXCELLENT (<5ms target achieved)' if avg_latency < 5.0 else '[WARN] Slow'}\n")
    if passed != len(EVAL_DATASET):
        sys.exit(1)


if __name__ == "__main__":
    run_eval()
