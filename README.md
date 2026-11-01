# Remi Suite

Two Windows voice apps by **gour4v97**, sharing one local voice engine (Whisper — fully offline, Hindi / English / Hinglish):

| App | What it does | Trigger |
|---|---|---|
| **[Voice Trans](src/VoiceTrans/)** 🎙️ | Push-to-talk dictation — speak, and the transcript is typed into whatever app has focus | `Ctrl+Alt+Space` |
| **[Remi Browser](src/Remi/)** 🌐 | Voice-controlled browser — open sites, search, scroll, switch tabs, click, play/pause, with spoken confirmations | `Ctrl+Alt+B` |

```
[hotkey] → speak → [hotkey] → 🧠 local Whisper transcription → 🖥️ typed into your app / browser action → 🔊 spoken confirmation
```

Both apps run side by side (different hotkeys, separate tray icons). Your voice never leaves the machine unless you enable a cloud provider yourself.

## Build (one solution, both apps)

```powershell
winget install Microsoft.DotNet.SDK.8
dotnet build Remi.sln -c Release
```

Executables land in `src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe` and `src\Remi\bin\Release\net8.0-windows\remi.exe`.

## One-time setup

```powershell
# get a local model once — both apps share it (574 MB, best Hindi/Hinglish quality)
src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe model download large-v3-turbo-q5_0

# run both daemons (tray icons appear)
src\VoiceTrans\bin\Release\net8.0-windows\voice-trans.exe
src\Remi\bin\Release\net8.0-windows\remi.exe
```

Press `Ctrl+Alt+Space` to dictate anywhere, `Ctrl+Alt+B` to command your browser. Full command lists and config in each app's folder ([Voice Trans](src/VoiceTrans/) · [Remi Browser](src/Remi/)).

## Four implementations, one engine

| Language | Location | Status |
|---|---|---|
| C# / .NET 8 | `src/` (this solution) | original, full-featured |
| Python | [`python/`](python/) | full port — tray, hotkeys, CDP, TTS |
| Java | [`java/`](java/) | full port — tray, hotkeys, CDP, TTS |

All implementations share the same ggml models and the whisper.cpp CLI engine, plus the same config philosophy, so you can run whichever stack you prefer (one suite at a time — hotkeys would collide).

## Repository layout

```
src/            C#/.NET apps (VoiceTrans + Remi)
python/         Python port (voicecore + two apps)
java/           Java port (single jar, two apps)
testdata/       sample WAVs for replay/pipeline testing
```

## License

MIT — see [LICENSE](LICENSE).
