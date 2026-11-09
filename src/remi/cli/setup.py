"""Interactive setup wizard and installer for Remi Voice Assistant.

Guides users through system inspection, model downloading, browser configuration,
and creating one-click desktop launchers. Modeled after OpenJarvis 'jarvis init'.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

import click

from remi.core import config
from remi.core.constants import (
    APP_BROWSER_ID,
    APP_DICTATION_ID,
    APP_DISPLAY_NAME,
    APP_VERSION,
    MODEL_CATALOG,
)
from remi.engine import whisper_cpp
from remi.engine.llm import auto_detect_llm
from remi.tools import browser


def run_setup(non_interactive: bool = False) -> None:
    """Run interactive or automated setup wizard."""
    click.echo("\n" + "=" * 60)
    click.echo(f"   🚀 Welcome to {APP_DISPLAY_NAME} (v{APP_VERSION}) Setup Wizard")
    click.echo("=" * 60 + "\n")
    click.echo("This wizard will inspect your environment, verify hardware acceleration,")
    click.echo("download speech recognition models, and configure launch shortcuts.\n")

    # Step 1: Directory Setup
    click.echo("[1/6] 📁 Initializing configuration directories...")
    config.ensure_dirs()
    click.echo(f"  • Config location  : {config.APPDATA}")
    click.echo(f"  • Data & models    : {config.LOCALAPPDATA}")
    click.echo("  ✓ Directories ready.\n")

    # Step 2: Hardware Inspection
    click.echo("[2/6] 🖥️ Inspecting hardware acceleration...")
    has_gpu = whisper_cpp.has_nvidia()
    if has_gpu:
        click.echo("  ✓ NVIDIA GPU detected! Sub-second (~0.3s) CUDA inference available.")
        cuda_ready = whisper_cpp.WHISPER_SERVER_CUDA.exists()
        if not cuda_ready:
            download_cuda = False if non_interactive else click.confirm("  → Would you like to download the whisper.cpp CUDA build (~250 MB)?", default=True)
            if download_cuda:
                click.echo("  Downloading CUDA acceleration build...")
                try:
                    whisper_cpp.ensure_cuda()
                    click.echo("  ✓ CUDA build installed successfully.")
                except Exception as ex:
                    click.echo(f"  ⚠️ CUDA download failed: {ex}")
            else:
                click.echo("  → Staying on CPU mode.")
        else:
            click.echo("  ✓ CUDA whisper.cpp server already installed.")
    else:
        click.echo("  • No NVIDIA GPU detected. Remi will use optimized CPU multithreading.\n")

    # Step 3: Whisper Model Setup
    click.echo("\n[3/6] 🧠 Speech Recognition Model...")
    cfg = config.load(APP_BROWSER_ID)
    current_model = cfg.get("local_model", "large-v3-turbo-q5_0")
    model_path = config.model_path(current_model)

    if model_path.exists():
        click.echo(f"  ✓ Active model '{current_model}' is already downloaded.")
    else:
        click.echo(f"  Recommended model: large-v3-turbo-q5_0 (~574 MB - fast, high accuracy)")
        dl_model = False if non_interactive else click.confirm(f"  → Download '{current_model}' now?", default=True)
        if dl_model:
            target_path = config.LOCALAPPDATA / "models" / f"ggml-{current_model}.bin"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{current_model}.bin"
            click.echo(f"  Downloading {current_model} from HuggingFace...")

            def _prog(blocks, bs, total):
                done = blocks * bs
                if total > 0:
                    pct = min(100, done * 100 // total)
                    mb = done / 1048576
                    tot_mb = total / 1048576
                    print(f"\r    [{pct:3}%] {mb:.1f} MB / {tot_mb:.1f} MB", end="")

            try:
                urllib.request.urlretrieve(url, target_path, reporthook=_prog)
                click.echo(f"\n  ✓ Model downloaded to {target_path}")
            except Exception as ex:
                click.echo(f"\n  ⚠️ Model download postponed ({ex}). You can download later via 'remi model download'.")
        else:
            click.echo("  → Postponed. Download later with 'remi model download'.")

    # Step 4: Browser Integration
    click.echo("\n[4/6] 🌐 Checking Browser DevTools integration...")
    b_exe = browser.find_browser_exe()
    if b_exe:
        click.echo(f"  ✓ Detected browser executable: {b_exe}")
    else:
        click.echo("  ⚠️ Microsoft Edge or Google Chrome was not found at standard paths.")
        click.echo("     Remi will still dictate text and launch search URLs.")

    # Step 5: Local SLM / LLM Detection
    click.echo("\n[5/6] 🤖 Probing Local Language Models...")
    llm = auto_detect_llm()
    if llm:
        click.echo(f"  ✓ Found active local SLM: {llm.__class__.__name__} ({llm.model})")
        click.echo("     Natural conversational voice intent routing will be enabled!")
    else:
        click.echo("  • No active Ollama / LM Studio server found on localhost.")
        click.echo("     (Optional) Install Ollama or LM Studio anytime for conversational Q&A.")

    # Step 6: Create Launchers & Autostart
    click.echo("\n[6/6] 🛠️ Generating One-Click Desktop Launchers...")
    created_launchers = create_launcher_scripts()
    for l in created_launchers:
        click.echo(f"  ✓ Created launcher: {l}")

    click.echo("\n" + "=" * 60)
    click.echo("   🎉 Remi Suite Setup Complete!")
    click.echo("=" * 60)
    click.echo("\nQuick Commands:")
    click.echo("  • Start Browser Voice Assistant : remi start      (Hotkey: Ctrl+Alt+B)")
    click.echo("  • Start Dictation App           : remi dictation  (Hotkey: Ctrl+Alt+Space)")
    click.echo("  • Start REST API Server         : remi serve      (Port: 8765)")
    click.echo("  • System Health Diagnostics     : remi doctor\n")


def create_launcher_scripts() -> list[str]:
    """Generate double-clickable Windows .bat launchers and shell scripts."""
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    scripts_dir = root_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    results: list[str] = []

    # 1. Remi Browser Launcher (Windows batch)
    remi_bat = scripts_dir / "launch-remi.bat"
    remi_bat_content = """@echo off
title Remi Voice Assistant
echo Starting Remi Browser Voice Controller (Ctrl+Alt+B)...
python -m remi start
if %errorlevel% neq 0 (
    pause
)
"""
    remi_bat.write_text(remi_bat_content, encoding="utf-8")
    results.append(str(remi_bat))

    # 2. Voice Trans Dictation Launcher (Windows batch)
    dict_bat = scripts_dir / "launch-dictation.bat"
    dict_bat_content = """@echo off
title Voice Trans Dictation
echo Starting Voice Trans Push-to-Talk Dictation (Ctrl+Alt+Space)...
python -m remi dictation
if %errorlevel% neq 0 (
    pause
)
"""
    dict_bat.write_text(dict_bat_content, encoding="utf-8")
    results.append(str(dict_bat))

    # 3. Setup / Doctor (Windows batch)
    setup_bat = scripts_dir / "setup.bat"
    setup_bat_content = """@echo off
title Remi Setup Wizard
python -m remi setup
pause
"""
    setup_bat.write_text(setup_bat_content, encoding="utf-8")
    results.append(str(setup_bat))

    return results
