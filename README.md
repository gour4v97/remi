# Remi 🎙️➡️🌐

**Voice-controlled browser for Windows.** Press a hotkey, speak a command — in English, Hindi, or Hinglish — and Remi drives your browser: opens sites, searches, scrolls, switches tabs, clicks buttons, plays and pauses videos.

By **gour4v97**. Everything runs locally: your voice is transcribed on your own machine with Whisper — no audio, transcripts, or commands ever leave your PC (unless you opt into a cloud provider yourself).

```
[Ctrl+Alt+B] → "open youtube" → [Ctrl+Alt+B] → 🧠 local whisper → 🖱️ browser opens youtube → 🔊 "opening youtube"
```

## What you can say

| English | Hinglish |
|---|---|
| open youtube / open gmail / open chatgpt | youtube kholo, gmail khol do |
| search nvidia rtx 4050 price | dhundo nvidia rtx 4050 price |
| youtube lofi beats | youtube lofi beats |
| scroll down / scroll up / scroll top / scroll bottom | niche, upar, sabse niche |
| new tab / close tab / next tab / previous tab | naya tab, tab band karo, agla tab |
| refresh / go back / forward | refresh karo, wapas jao |
| play / pause (any video/audio on the page) | chalao, roko |
| click subscribe / click sign in | click karo subscribe |
| type hello world (into the focused input) | likho hello world |
| read title (speaks the page title) | title batao |

Site shortcuts: youtube, google, gmail, whatsapp, chatgpt, github, instagram, facebook, reddit, wikipedia, amazon, flipkart, twitter/x, linkedin, netflix, hotstar, maps, drive, spotify. Anything that looks like a domain (`example.com`) opens directly; anything else becomes a Google search.

## Commands (CLI)

```
remi                     run the daemon (tray icon + trigger hotkey)
remi toggle              start/stop listening in the running daemon
remi status              daemon status (JSON)
remi stop                quit the daemon
remi say "<command>"     run a text command directly (testing/scripting)
remi say-audio <file.wav>  run the full voice pipeline on a WAV file
remi history             recent commands
remi doctor              readiness checks (mic, model, browser, debug port)
remi model list | download <name> | <name>
```

## Setup

```powershell
winget install Microsoft.DotNet.SDK.8
dotnet build src\Remi\Remi.csproj -c Release

# model (Remi borrows voice-trans models automatically if present; otherwise download)
src\Remi\bin\Release\net8.0-windows\remi.exe model download large-v3-turbo-q5_0

src\Remi\bin\Release\net8.0-windows\remi.exe        # tray daemon starts
```

Press `Ctrl+Alt+B`, speak, press again. Done.

**Browser control** uses the Chrome DevTools Protocol (works with Microsoft Edge and Chrome). The first browser command launches the browser with a debug port. By default Remi uses a **dedicated browser profile** (`%LOCALAPPDATA%\remi\browser-profile`) because Windows browsers ignore the debug-port flag when an instance is already running — a separate profile guarantees voice control works. Set `browser_profile = "default"` in the config to use your main profile instead (then close the browser fully before starting Remi).

## Configuration

`%APPDATA%\remi\config.toml`:

```toml
trigger_hotkey = "ctrl+alt+b"     # restart the daemon to apply
local_model = "large-v3-turbo-q5_0"
cdp_port = 9222
voice_feedback = true             # spoken confirmations
auto_launch_browser = true
browser_path = ""                 # empty = auto-detect Edge/Chrome
browser_profile = "remi"          # "remi" (dedicated, reliable) or "default" (main profile)
max_recording_seconds = 60
```

## How it works

1. **Capture** — WASAPI microphone → 16 kHz mono PCM
2. **Transcribe** — local Whisper (whisper.cpp via Whisper.net); Hindi speech is romanized to Hinglish before parsing
3. **Route** — a command grammar matches the transcript (English + Hinglish verbs)
4. **Act** — Chrome DevTools Protocol over HTTP + WebSocket: tab management, `Runtime.evaluate` for scrolling, clicking, media control, and typing
5. **Confirm** — Windows SAPI text-to-speech speaks the result; every command is logged to a local JSONL history

## Notes & limits

- Windows browsers won't let background apps inject into **elevated (admin)** windows — the same boundary every automation tool has
- `click` matches visible text on links/buttons — it can't click arbitrary canvas or coordinate targets
- The dedicated browser profile is separate from your daily profile, so it starts without your logins (use `browser_profile = "default"` if you want your own session)
- Language detection on very short clips can waver; clear commands work best

## License

MIT — see [LICENSE](LICENSE).
