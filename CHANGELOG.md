# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
