"""Local ASR via the whisper.cpp CLI (whisper-cli.exe), reusing the suite's ggml models.

The binary is bootstrapped on first use from the official whisper.cpp release
(b5454, whisper-bin-x64.zip) into %LOCALAPPDATA%\\remi-suite-py\\bin.
"""
import json
import re
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from . import config

WHISPER_ZIP_URL = "https://github.com/ggerganov/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip"
WHISPER_CLI = config.BIN_DIR / "whisper-cli.exe"


def ensure_whisper_cli() -> Path:
    if WHISPER_CLI.exists():
        return WHISPER_CLI
    config.ensure_dirs()
    print(f"downloading whisper.cpp CLI (~2 MB) from {WHISPER_ZIP_URL} …")
    zip_path = config.BIN_DIR / "whisper-bin.zip"
    urllib.request.urlretrieve(WHISPER_ZIP_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name  # flatten — the CLI only needs its siblings
            if name.lower().endswith((".exe", ".dll")):
                (config.BIN_DIR / name).write_bytes(z.read(info))
    zip_path.unlink(missing_ok=True)
    if not WHISPER_CLI.exists():
        raise RuntimeError("whisper-cli.exe not found in the downloaded archive")
    return WHISPER_CLI


def transcribe_pcm(pcm: bytes, model: str, language: str = "hinglish") -> str:
    """pcm = 16 kHz mono s16le. Returns the raw transcript text."""
    import wave
    exe = ensure_whisper_cli()
    model_path = config.model_path(model)
    if not model_path.exists():
        raise FileNotFoundError(
            f"model '{model}' not found — run the .NET suite's download or: "
            f"voice-trans model download {model}")
    wav_path = config.LOCALAPPDATA / "utterance.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)
    lang = "en" if language == "en" else "hi" if language == "hi" else "auto"
    proc = subprocess.run(
        [str(exe), "--model", str(model_path), "--file", str(wav_path),
         "--language", lang, "--no-gpu", "-t", "8"],
        capture_output=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"whisper-cli failed: {proc.stderr.decode(errors='replace')[-300:]}")
    # stdout lines look like: [00:00:00.000 --> 00:00:01.200]   Open GitHub.
    out = []
    for line in proc.stdout.decode(errors="replace").splitlines():
        m = re.match(r"^\[[^\]]+\]\s*(.*)$", line.strip())
        if m and m.group(1):
            out.append(m.group(1))
    return "".join(out)


def peak_amplitude(pcm: bytes) -> int:
    peak = 0
    for i in range(0, len(pcm) - 1, 2):
        s = pcm[i] | (pcm[i + 1] << 8)
        a = s if s < 0x8000 else 0x10000 - s
        peak = max(peak, a)
    return peak
