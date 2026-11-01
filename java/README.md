# Remi Suite — Java port

Both apps in plain Java (no framework, no build tool required): **Voice Trans** (dictation) and **Remi** (voice-controlled browser). Transcription runs through the shared **whisper.cpp CLI** (`whisper-cli.exe`, auto-downloaded on first use) with the suite's shared ggml models.

By **gour4v97**. Everything runs locally.

## Setup

```bat
build.bat
```

Requirements: JDK 17+ on PATH (tested on Temurin 21). The script downloads two small JNA jars (Win32 access) from Maven Central on first run, compiles, and produces `remi-suite.jar`.

## Run

```bat
java -jar remi-suite.jar voice-trans          REM dictation tray app (Ctrl+Alt+Space)
java -jar remi-suite.jar remi                 REM browser controller tray app (Ctrl+Alt+B)

java -jar remi-suite.jar remi say "open youtube"
java -jar remi-suite.jar remi say-audio somefile.wav
java -jar remi-suite.jar history remi-java
java -jar remi-suite.jar doctor
```

> **Important:** the Java and .NET versions register the same hotkeys — run one suite at a time (`voice-trans stop` + `remi stop` for the .NET daemons first) or change the hotkeys in `%APPDATA%\remi-suite-java\*.properties`.

## Layout

```
src/suite/
  Suite.java           entry point + CLI + minimal WAV parser
  VoiceTransApp.java   dictation app (hotkey → record → whisper → SendInput/clipboard)
  RemiApp.java         browser controller app (hotkey → record → whisper → CDP → TTS)
  Win.java             JNA: RegisterHotKey + message loop, SendInput, foreground window
  Capture.java         javax.sound.sampled mic capture (16 kHz target, native-rate fallback)
  Asr.java             whisper.cpp CLI bootstrap + transcription
  Cdp.java             Chrome DevTools Protocol over java.net.http (HTTP + WebSocket)
  Router.java          command grammar (English + Hinglish)
  Translit.java        Devanagari → Roman + smart writing
  Config/History/Tts/WavUtil/Tray
lib/                   JNA jars (downloaded by build.bat, not committed)
```

## Notes

- Tray is AWT `SystemTray`; hotkeys use JNA `RegisterHotKey` + a `GetMessage` loop (no global hooks)
- TTS feedback shells out to Windows SAPI via PowerShell (zero dependencies)
- Config lives in `%APPDATA%\remi-suite-java\*.properties`; history + models under `%LOCALAPPDATA%\remi-suite-java`
