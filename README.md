# Remi Suite

Two Windows voice apps by **gour4v97**, in pure **Python**, sharing one local voice engine:

| App | What it does | Trigger |
|---|---|---|
| **Voice Trans** 🎙️ | Push-to-talk dictation — speak, and the transcript is typed into whatever app has focus | `Ctrl+Alt+Space` |
| **Remi Browser** 🌐 | Voice-controlled browser — 40+ commands in English/Hindi/Hinglish, with spoken confirmations | `Ctrl+Alt+B` |

```
[hotkey] → speak → [hotkey] → 🧠 local Whisper (GPU: ~0.3 s) → 🖥️ typed / browser action → 🔊 spoken confirmation
```

Everything runs locally — your voice never leaves the machine.

## Performance

- A **persistent whisper.cpp server** loads the model once and stays warm (both apps share it)
- On NVIDIA GPUs it automatically uses the **CUDA build**: transcription drops from ~30 s (CPU) to **~0.3 s**
- No NVIDIA GPU? It transparently falls back to the CPU build — still fully offline
- Cached SAPI TTS engine, so confirmations don't lag either

## Setup (once)

```powershell
py -m pip install -r python/requirements.txt
```

The whisper.cpp binaries + CUDA build download themselves into `%LOCALAPPDATA%\remi-suite-py\` on first use, and models are borrowed from an existing `%LOCALAPPDATA%\voice-trans\models` folder (or: `py voice_trans.py model download large-v3-turbo-q5_0`).

## Run

```powershell
cd python
py voice_trans.py        # dictation tray app    (Ctrl+Alt+Space)
py remi.py               # browser tray app      (Ctrl+Alt+B)

py voice_trans.py autostart on     # start with Windows
py remi.py autostart on
```

Full command lists: [`python/README.md`](python/README.md).

## Repository layout

```
python/          the suite (voicecore engine + two apps) — see its README
testdata/        sample WAVs for say-audio / pipeline testing
```

## License

MIT — see [LICENSE](LICENSE).
