# Remi Suite — Python port

Both apps in pure Python: **Voice Trans** (dictation) and **Remi** (voice-controlled browser). Same features and hotkeys as the .NET originals; transcription runs through the shared **whisper.cpp CLI** (`whisper-cli.exe`, auto-downloaded on first use) so the ggml models are shared with the rest of the suite — nothing is downloaded twice.

By **gour4v97**. Everything runs locally.

## Setup

```powershell
py -m pip install -r requirements.txt
```

That's it — the whisper.cpp CLI bootstraps itself into `%LOCALAPPDATA%\remi-suite-py\bin` on first transcription, and models are borrowed from `%LOCALAPPDATA%\voice-trans\models` (or download via the .NET suite's `model download`).

## Run

```powershell
# dictation (tray icon, Ctrl+Alt+Space)
python voice_trans.py

# browser control (tray icon, Ctrl+Alt+B)
python remi.py

# CLI helpers
python remi.py say "open youtube"
python remi.py say-audio somefile.wav
python remi.py history
python remi.py doctor
python voice_trans.py history
```

> **Important:** the Python and .NET versions register the same hotkeys. Run one suite at a time (`voice-trans stop` + `remi stop` for the .NET daemons first), or change the hotkey in `%APPDATA%\remi-suite-py\*.toml`.

## What you can say (browser)

| English | Hinglish |
|---|---|
| open youtube / open gmail / open chatgpt / go to example.com | youtube kholo, gmail khol do |
| open history / downloads / settings / bookmarks / extensions | history kholo |
| search nvidia rtx 4050 price / youtube lofi beats | dhundo nvidia rtx 4050 |
| scroll down / up / top / bottom / left / right | niche, upar, sabse niche |
| new tab / close tab / next tab / previous tab / duplicate tab | naya tab, tab band karo, agla tab |
| refresh / go back / forward / read title | refresh karo, wapas jao, title batao |
| play / pause / volume up / volume down / mute | chalao, roko, awaaz badhao |
| zoom in / zoom out / reset zoom | bada karo, chhota karo |
| find text / print / select all / copy / fullscreen / exit fullscreen | page me dhundo |
| type hello world (focused input) / click subscribe | likho hello world, dabao subscribe |
| what time / what date (spoken locally, no browser) | kitne baje hain, date batao |

## Performance

- One **whisper.cpp server** stays warm per suite (default port 9177) — model loads once, not per command
- On NVIDIA machines the **CUDA build** (`py remi.py model download-cuda`, also automatic) takes transcription from ~30 s to **~0.3 s**
- whisper-cli.exe remains as an automatic fallback
- TTS uses a cached engine so confirmations are instant

## Layout

```
voicecore/        shared engine: config, capture (sounddevice), ASR (whisper-cli),
                  Devanagari→Roman transliteration, smart writing, delivery
                  (SendInput/clipboard via ctypes), CDP client, command router, history
voice_trans.py    dictation app
remi.py           browser controller app
```

## Notes

- Python 3.11+ (uses stdlib `tomllib`); developed and tested on 3.13
- TTS feedback uses `pyttsx3` (SAPI); every dictation/command is logged to local JSONL
- The `.en`-suffix models won't help for Hindi — use a multilingual model
