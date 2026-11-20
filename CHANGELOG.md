# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Check the OpenJarvis config enabled flag in the `/health` endpoint to prevent timeouts during unit tests.
- Sanitize Windows console encoding in `eval_router` and set `PYTHONIOENCODING` in CI.
- Auto-detect the local virtualenv Python in batch launchers.
- Close the SQLite connection in the `temp_memory` test fixture to release the Windows file lock.

---

## [0.3.0] - 2026-11-16

### Added
- **Latency pass**: Per-stage `PipelineTimer` latency instrumentation; `WarmMicCapture` to eliminate per-command mic cold-start latency; non-blocking TTS with instant speech interruption; instant `Ctrl+V` paste-text delivery mode; `PersistentCDPSession` reusing one WebSocket across commands. Total turnaround fell from ~1,645 ms to ~315 ms on the RTX 4050 laptop (the README's own benchmark figures).
- **LLM intent resolver improvements**: Hinglish support, instance caching, and model prioritization.
- **Voice-activity detection**: Silero/Energy VAD (off by default).
- **SQLite memory store**: Remembers the last ten turns, so follow-ups like "open that again" resolve.
- **New skills**: `morning_digest` (Hinglish morning digest) and `system_controls` (voice control for Calculator, Notepad, and more, with a native Windows app launcher).
- **Desktop HUD overlay**: Floating status pill (Listening / Thinking / Done / Error) in the browser agent, with real-time streaming partial transcription.
- **Wake word detection**: Wake word engine with a comprehensive eval test harness.
- **Kokoro local TTS**: Hindi/Hinglish neural text-to-speech, fully on-device.
- **One-click install**: `install.ps1` bootstrapper, plus `remi bench` and `remi eval` CLI commands.
- **OpenJarvis local brain connector**: Local brain integration with REST memory endpoints.
- **BackgroundScheduler daemon**: Scheduled background tasks, plus an agentskills.io manifest importer.
- **Unit test suites**: Comprehensive tests for `MemoryStore`, VAD, and `PipelineTimer`.

### Changed
- Version bumped to v0.3.0; optional dependencies updated and `eval_router` wired into CI.
- Added a PyInstaller packaging spec.
- Polished the README showcase and added a graphical HUD banner visual asset.

---

## [0.2.0] - 2026-11-09

### Added
- **OpenJarvis Architecture**: Modularized into 5 composable pillars (`engine`, `speech`, `tools`, `agents`, `core`).
- **Registry System**: Generic `@RegistryBase` decorator registration across engines, agents, tools, speech, and TTS.
- **Modern Packaging**: Full `src/` layout with `pyproject.toml` and console script entrypoints (`remi`, `voice-trans`).
- **Rich Click CLI**: Subcommands for `start`, `dictation`, `say`, `say-audio`, `doctor`, `model`, `history`, and `autostart`.
- **Event Bus**: Decoupled thread-safe pub/sub event system (`EventBus`).
- **Hardware Auto-Discovery**: Automatic detection of NVIDIA GPUs, CUDA build availability, and model weights.
- **Full Unit Test Suite**: Comprehensive tests for registry, config, router, and transliteration passing in CI and standalone `unittest`.
- **Developer Experience**: Added `Makefile`, GitHub Actions CI workflow, and issue templates.
- **Documentation**: New architecture diagram, complete voice grammar table, and getting-started guides in `docs/`.

### Changed
- Refactored `voicecore` engine into clean, typed submodules with backward-compatible import shims.
- Improved punctuation formatting and Hinglish transliteration accuracy.
- Added cross-platform safe fallbacks for Win32 API calls (`winreg`, `ctypes.windll`, `user32`).

---

## [0.1.0] - 2026-03-01

### Added
- Initial pure-Python port of Remi Browser and Voice Trans.
- Integration with whisper.cpp HTTP server and Chrome DevTools Protocol.
- Hinglish transliteration and SAPI TTS spoken feedback.
