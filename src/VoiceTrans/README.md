# Voice Trans

Push-to-talk voice dictation for Windows, with **Hindi**, **English**, and **Hinglish** (mixed Hindi-English) support. A native C#/.NET app by **gour4v97**.

Press the trigger hotkey once → speak naturally → press it again → the transcript is typed into whatever app has focus. Everything runs locally by default: audio never leaves your machine unless you explicitly enable a cloud provider.

```
[trigger key] → 🎙 recording → [trigger key] → ✨ transcribe (local whisper) → 📝 typed into the focused app
```

## Features

- **Toggle trigger key** — default `Ctrl+Alt+Space`, configurable (any modifier combo, F-keys, or single keys like `capslock`)
- **Local-first transcription** — Whisper.net (whisper.cpp engine, ggml models), fully offline; optional Groq cloud (`whisper-large-v3`)
- **Languages** — `hinglish` (default: auto-detect Hindi/English/code-mixed speech, output in Roman script), `hi` (Devanagari output), `en`, `auto`
- **Devanagari → Roman transliteration** — "कैसे हो" → "kaise ho"; English parts of Hinglish speech pass through untouched
- **Delivery modes** — `type` (SendInput Unicode — works with Devanagari), `clipboard`, `guarded` (falls back to clipboard with a notification if the focused window changed while you were speaking)
- **Writing modes** — `smart` (deterministic cleanup: spoken punctuation "period"/"अल्प विराम", spacing, capitalization, Hindi danda) / `literal` (verbatim; invalid config fails closed to literal)
- **Pronunciation dictionary** — one term per line, `#` comments (only at line start or after a space); only user terms may rewrite a transcript; terms also seed the ASR prompt
- **Local-only history** — JSONL ring with timings and errors; `export <id>` for redacted single records
- **Doctor** — readiness checks (mic, model, hotkey, clipboard round-trip, daemon)
- **Replay** — re-run any WAV file through the full pipeline
- **Tray app** — state-colored icon (idle blue / recording red / processing amber), mode switches in the menu, balloon notifications
- **Autostart** — optional HKCU Run-key entry

## Quick start

```powershell
# one-time: .NET 8 SDK
winget install Microsoft.DotNet.SDK.8

# build
dotnet build src\VoiceTrans\VoiceTrans.csproj -c Release

# get a local model (recommended: quantized large-v3-turbo — best Hindi/Hinglish, fast on CPU)
src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe model download large-v3-turbo-q5_0
src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe model large-v3-turbo-q5_0   # switch to it

# run (tray icon appears; console hides)
src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe
```

Then focus any window (Notepad, browser, chat), press `Ctrl+Alt+Space`, speak, press again.

## Commands

```
voice-trans                     run the daemon (tray icon + trigger hotkey)
voice-trans toggle              start/stop recording in the running daemon
voice-trans status              daemon status (JSON)
voice-trans stop                quit the daemon
voice-trans doctor              readiness checks (exit code 2 if any FAIL)
voice-trans history [N] [--json]
voice-trans export <id>
voice-trans delivery <type|clipboard|guarded>
voice-trans writing <smart|literal>
voice-trans language <auto|en|hi|hinglish>
voice-trans asr <local|cloud>
voice-trans model list | download <name> | remove <name>
voice-trans auth set groq       store API key (DPAPI-encrypted, current user only)
voice-trans autostart <on|off|status>
voice-trans replay <file.wav>   run a WAV through the full pipeline (debug/testing)
voice-trans translit <text>     Devanagari → Roman (debug helper)
voice-trans convert <in> <out>  convert any WAV to canonical 16 kHz mono s16 (debug helper)
```

## Models

| model | size | notes |
|---|---|---|
| `tiny` / `base` / `small` / `medium` | 75 / 142 / 487 / 1527 MB | multilingual — Hindi, English, Hinglish |
| `large-v3-turbo-q5_0` | 574 MB | best Hindi/Hinglish quality, quantized for fast CPU inference — **recommended default** |
| `large-v3-turbo` | 1620 MB | full-precision turbo; best paired with the CUDA runtime |
| `*.en` variants | — | English-only; cannot handle Hindi |

Models download on explicit command only, from `huggingface.co/ggerganov/whisper.cpp`, with a sha256 sidecar recorded for integrity checks. Default: `small`.

For GPU acceleration add the `Whisper.net.Runtime.Cuda.Windows` NuGet package.

## Configuration

`%APPDATA%\voice-trans\config.toml` — edited live (picked up at the next dictation):

```toml
delivery_mode = "type"        # type | clipboard | guarded
writing_mode = "smart"        # smart | literal
asr_mode = "local"            # local | cloud (cloud needs: auth set groq)
language = "hinglish"         # auto | en | hi | hinglish
local_model = "small"
trigger_hotkey = "ctrl+alt+space"   # restart the daemon after changing this
groq_enabled = false
max_recording_seconds = 120
history_limit = 1000
```

Dictionary: `%APPDATA%\voice-trans\dictionary.txt` — one term per line; `#` comments (only at line start or after a space, so `C#` survives).

Data locations: history at `%LOCALAPPDATA%\voice-trans\history.jsonl`, models at `%LOCALAPPDATA%\voice-trans\models`.

## Privacy

- Recording, transcription (local mode), history, and diagnostics never leave the machine
- Cloud mode only activates when you set `asr_mode = cloud` (or `groq_enabled`) **and** store a key
- History contains transcripts and timings only — never audio, never credentials
- The clipboard always contains the latest transcript (recoverability guarantee before any typing)

## Known limitations

- Elevated (admin) windows can't receive typed text or be read for guarded-mode focus checks — same privilege boundary every SendInput app has
- `capslock`-style single-key hotkeys work via `RegisterHotKey` but can't be suppressed from also toggling Caps Lock state — prefer a modifier combo or an F-key
- Whisper's language detection on very short clips (< 2 s) can be shaky in `auto`/`hinglish` mode — pin `en` or `hi` if that bites
- No GPU/CUDA in the default build (CPU small ≈ 2× realtime on an i5-13420H for short clips)
