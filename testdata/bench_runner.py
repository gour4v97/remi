#!/usr/bin/env python3
"""Bench runner: pipe all testdata/*.wav files through the full Remi pipeline
and print an aggregate latency table.

Usage:
    python testdata/bench_runner.py
    python testdata/bench_runner.py --wav testdata/open-github.wav --runs 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure src/ is on path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def run_bench(wav_path: Path, run_idx: int) -> dict | None:
    """Run one WAV through the pipeline, return timing dict or None on error."""
    try:
        from remi.agents.browser_agent import say_audio
        from remi.core.perf import PipelineTimer

        t0 = time.perf_counter()
        say_audio(str(wav_path))
        total = (time.perf_counter() - t0) * 1000

        return {
            "wav": wav_path.name,
            "run": run_idx,
            "total_ms": round(total, 1),
        }
    except Exception as ex:
        print(f"  [ERROR] {wav_path.name} run {run_idx}: {ex}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Remi pipeline latency benchmark")
    parser.add_argument("--wav", help="Specific WAV file to test (default: all in testdata/)")
    parser.add_argument("--runs", type=int, default=3, help="Repetitions per WAV (default: 3)")
    parser.add_argument("--out", help="Output JSONL file path (default: remi-bench.jsonl)")
    args = parser.parse_args()

    testdata = Path(__file__).resolve().parent
    if args.wav:
        wav_files = [Path(args.wav)]
    else:
        wav_files = sorted(testdata.glob("*.wav"))

    if not wav_files:
        print("No WAV files found. Add test recordings to testdata/")
        sys.exit(1)

    print(f"\nRemi Pipeline Benchmark — {len(wav_files)} file(s), {args.runs} run(s) each\n")

    all_results: list[dict] = []
    for wav in wav_files:
        print(f"  {wav.name}:")
        for i in range(1, args.runs + 1):
            result = run_bench(wav, i)
            if result:
                print(f"    run {i}: {result['total_ms']}ms total")
                all_results.append(result)
            time.sleep(0.5)  # Let GPU cool slightly between runs

    if not all_results:
        print("\nNo successful runs.")
        return

    # Aggregate stats per WAV
    print(f"\n{'─'*50}")
    print(f"{'WAV':<30} {'Avg':>8} {'Min':>8} {'Max':>8}")
    print(f"{'─'*50}")
    by_wav: dict[str, list[float]] = {}
    for r in all_results:
        by_wav.setdefault(r["wav"], []).append(r["total_ms"])
    for wav_name, times in sorted(by_wav.items()):
        avg = sum(times) / len(times)
        print(f"{wav_name:<30} {avg:>7.0f}ms {min(times):>7.0f}ms {max(times):>7.0f}ms")
    print(f"{'─'*50}")

    all_times = [r["total_ms"] for r in all_results]
    grand_avg = sum(all_times) / len(all_times)
    print(f"{'OVERALL':<30} {grand_avg:>7.0f}ms {min(all_times):>7.0f}ms {max(all_times):>7.0f}ms\n")

    if grand_avg < 1000:
        print("✅ Target met: average < 1000ms")
    else:
        print(f"⚠️  Average {grand_avg:.0f}ms exceeds 1000ms target — check bench.jsonl for per-stage breakdown")

    # Save full results
    out_path = Path(args.out) if args.out else Path.home() / "remi-bench.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")
    print(f"Results appended to {out_path}")


if __name__ == "__main__":
    main()
