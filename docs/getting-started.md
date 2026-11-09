# 🚀 Getting Started with Remi

## System Requirements

- **Operating System:** Microsoft Windows 10 or 11 (64-bit)
- **Python:** Python 3.11, 3.12, or 3.13
- **Browser:** Microsoft Edge or Google Chrome
- **Hardware:**
  - Any CPU (transcription takes ~10-20s on CPU)
  - *Recommended:* NVIDIA GPU with CUDA for sub-second (~0.3s) transcription

---

## 1. Installation

### From Source (Editable Mode)

Clone the repository and install with `pip`:

```bash
git clone https://github.com/gour4v97/remi.git
cd remi
pip install -e .
```

For development (including test runners and linters):

```bash
pip install -e ".[dev]"
```

---

## 2. Model Setup

Remi uses quantized GGML models from `whisper.cpp`. The default model is `large-v3-turbo-q5_0` (~574 MB), which offers an optimal balance of transcription accuracy and speed.

To view available models and download:

```bash
# List catalog and installation status
remi model list

# Download recommended model
remi model download large-v3-turbo-q5_0

# (Optional) If you have an NVIDIA GPU, download the CUDA build:
remi model download-cuda
```

---

## 3. Launching the Apps

### Remi Browser Assistant (`Ctrl+Alt+B`)

```bash
remi start
```

Press `Ctrl+Alt+B`, speak your command (e.g., *"open youtube"*, *"scroll down"*, *"naya tab kholo"*), and press `Ctrl+Alt+B` again to execute.

### Voice Trans Dictation (`Ctrl+Alt+Space`)

```bash
remi dictation
# or use the standalone console command:
voice-trans
```

Place your cursor in any text input (Notepad, VS Code, Slack, Word), press `Ctrl+Alt+Space`, speak, and press the hotkey again to type the transcript.

---

## 4. Health Check

Run the built-in diagnostic tool to verify all system components:

```bash
remi doctor
```

Output:
```text
=== Remi System Health Check ===
Python version : 3.12.3
Config path    : C:\Users\User\AppData\Roaming\remi-suite-py\remi-py.toml
NVIDIA GPU     : Detected
CUDA build     : Installed
whisper-cli    : Installed
whisper-server : Installed
Active model   : large-v3-turbo-q5_0 -> FOUND
Browser exe    : C:\Program Files\Google\Chrome\Application\chrome.exe
Browser CDP    : ACTIVE on port 9222
================================
```

---

## 5. Enable Windows Autostart

To automatically start Remi whenever you log into Windows:

```bash
remi autostart on --app remi-py
remi autostart on --app voice-trans-py
```
