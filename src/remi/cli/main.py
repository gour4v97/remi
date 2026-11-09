"""Click-based command line interface for Remi Suite - modeled after OpenJarvis CLI."""
from __future__ import annotations

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
from remi.tools import browser, history


@click.group()
@click.version_option(version=APP_VERSION, prog_name=APP_DISPLAY_NAME)
def main():
    """Remi Suite - Local-first offline voice assistant and dictation for Windows."""
    pass


@main.command(name="start")
@click.option("--hotkey", help="Override trigger hotkey (default: ctrl+alt+b)")
def cmd_start(hotkey: str | None):
    """Start Remi browser voice controller tray app."""
    from remi.agents.browser_agent import BrowserVoiceAgent
    cfg = config.load(APP_BROWSER_ID)
    if hotkey:
        cfg["hotkey"] = hotkey
    whisper_cpp.start_server(cfg)
    click.echo(f"Remi (Python) - hotkey: {cfg['hotkey']} - tray icon starting...")
    agent = BrowserVoiceAgent(cfg)
    agent.start()


@main.command(name="dictation")
@click.option("--hotkey", help="Override trigger hotkey (default: ctrl+alt+space)")
def cmd_dictation(hotkey: str | None):
    """Start Voice Trans push-to-talk dictation tray app."""
    from remi.agents.dictation_agent import DictationAgent
    cfg = config.load(APP_DICTATION_ID)
    if hotkey:
        cfg["hotkey"] = hotkey
    whisper_cpp.start_server(cfg)
    click.echo(f"Voice Trans (Python) - hotkey: {cfg['hotkey']} - tray icon starting...")
    agent = DictationAgent(cfg)
    agent.start()


@main.command(name="say")
@click.argument("text")
def cmd_say(text: str):
    """Execute a voice command directly from text string (no microphone)."""
    from remi.agents.browser_agent import say_text
    ret = say_text(text)
    sys.exit(ret)


@main.command(name="say-audio")
@click.argument("wav_path", type=click.Path(exists=True))
def cmd_say_audio(wav_path: str):
    """Execute a voice command from a 16-bit WAV file."""
    from remi.agents.browser_agent import say_audio
    ret = say_audio(wav_path)
    sys.exit(ret)


@main.command(name="history")
@click.option("--app", default=APP_BROWSER_ID, type=click.Choice([APP_BROWSER_ID, APP_DICTATION_ID]))
@click.option("--limit", "-n", default=20, help="Number of recent entries to show")
def cmd_history(app: str, limit: int):
    """View recent execution history."""
    entries = history.load(app, limit)
    if not entries:
        click.echo("No history records found.")
        return
    click.echo(f"History for {app} (last {len(entries)}):")
    for e in reversed(entries):
        at = e.get("at", "")[:19]
        transcript = e.get("transcript", "")[:35]
        detail = e.get("detail", "") if e.get("ok") else f"ERROR: {e.get('error', '')}"
        click.echo(f"{at}  {transcript:35}  {detail[:50]}")


@main.command(name="doctor")
def cmd_doctor():
    """Diagnose local system setup, hardware, whisper server, and browser."""
    cfg = config.load(APP_BROWSER_ID)
    click.echo("=== Remi System Health Check ===")
    click.echo(f"Python version : {sys.version.split()[0]}")
    click.echo(f"Config path    : {config.config_path(APP_BROWSER_ID)}")
    click.echo(f"NVIDIA GPU     : {'Detected' if whisper_cpp.has_nvidia() else 'Not detected'}")
    click.echo(f"CUDA build     : {'Installed' if whisper_cpp.WHISPER_SERVER_CUDA.exists() else 'Not installed'}")
    click.echo(f"whisper-cli    : {'Installed' if whisper_cpp.WHISPER_CLI.exists() else 'Not installed'}")
    click.echo(f"whisper-server : {'Installed' if whisper_cpp.WHISPER_SERVER.exists() else 'Not installed'}")

    model_name = cfg.get("local_model", "large-v3-turbo-q5_0")
    model_file = config.model_path(model_name)
    click.echo(f"Active model   : {model_name} -> {'FOUND' if model_file.exists() else 'MISSING'}")

    browser_exe = browser.find_browser_exe()
    click.echo(f"Browser exe    : {browser_exe or 'NOT FOUND'}")
    cdp_up = browser.is_cdp_up(cfg["cdp_port"])
    click.echo(f"Browser CDP    : {'ACTIVE' if cdp_up else 'DOWN'} on port {cfg['cdp_port']}")

    # Local SLM/LLM status
    from remi.engine.llm import auto_detect_llm
    llm = auto_detect_llm()
    click.echo(f"Local SLM/LLM  : {llm.__class__.__name__} ({llm.model}) - READY" if llm else "Local SLM/LLM  : Offline (Ollama / LM Studio)")
    click.echo("================================")


@main.command(name="model")
@click.argument("action", default="list")
@click.argument("target", required=False)
def cmd_model(action: str, target: str | None):
    """Manage Whisper models (list, download <name>, download-cuda, set <name>)."""
    if action == "list":
        click.echo(f"Models directory: {config.LOCALAPPDATA / 'models'}")
        for name, mb in sorted(MODEL_CATALOG.items()):
            status = "installed" if config.model_path(name).exists() else "         "
            click.echo(f"  {name:22} {status}  ~{mb} MB")
        return

    if action == "download-cuda":
        ok = whisper_cpp.ensure_cuda()
        click.echo("CUDA build ready:" if ok else "CUDA download failed or NVIDIA GPU not found.")
        sys.exit(0 if ok else 1)

    if action == "download":
        if not target:
            click.echo("Usage: remi model download <model-name>")
            sys.exit(1)
        if target not in MODEL_CATALOG:
            click.echo(f"Unknown model '{target}'. Available: {', '.join(sorted(MODEL_CATALOG))}")
            sys.exit(1)
        if config.model_path(target).exists():
            click.echo(f"Model '{target}' is already installed.")
            return

        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{target}.bin"
        target_path = config.LOCALAPPDATA / "models" / f"ggml-{target}.bin"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        click.echo(f"Downloading ggml-{target}.bin (~{MODEL_CATALOG[target]} MB)...")

        def _prog(blocks, bs, total):
            done = blocks * bs
            if total > 0:
                print(f"\r  {min(100, done * 100 // total):3}%  {done / 1048576:.0f} MB", end="")

        urllib.request.urlretrieve(url, target_path, reporthook=_prog)
        click.echo(f"\nInstalled: {target_path}")
        return

    # Check if action is a model name to activate
    if action in MODEL_CATALOG:
        if not config.model_path(action).exists():
            click.echo(f"'{action}' is not downloaded yet. Run: remi model download {action}")
            sys.exit(1)
        cfg = config.load(APP_BROWSER_ID)
        cfg["local_model"] = action
        config.save(APP_BROWSER_ID, cfg)
        click.echo(f"Active model set to '{action}'")
        return

    click.echo("Usage: remi model [list | download <name> | download-cuda | <name>]")


@main.group(name="llm")
def cmd_llm():
    """Manage and query local Small Language Models (Ollama, LM Studio, llama.cpp)."""
    pass


@cmd_llm.command(name="status")
def cmd_llm_status():
    """Check status of local LLM/SLM inference engines on localhost."""
    from remi.engine.llm import OllamaEngine, OpenAICompatEngine, auto_detect_llm

    click.echo("=== Local LLM / SLM Diagnostics ===")
    
    # 1. Ollama
    ollama = OllamaEngine()
    ollama_up = ollama.is_available()
    click.echo(f"Ollama (port 11434)    : {'ONLINE' if ollama_up else 'Offline'}")
    if ollama_up:
        models = ollama.list_models()
        click.echo(f"  Installed models     : {', '.join(models) if models else 'None found'}")

    # 2. LM Studio
    lmstudio = OpenAICompatEngine(endpoint="http://127.0.0.1:1234/v1")
    lm_up = lmstudio.is_available()
    click.echo(f"LM Studio (port 1234)  : {'ONLINE' if lm_up else 'Offline'}")
    if lm_up:
        models = lmstudio.list_models()
        click.echo(f"  Loaded models        : {', '.join(models) if models else 'None'}")

    # 3. llama.cpp
    llamacpp = OpenAICompatEngine(endpoint="http://127.0.0.1:8080/v1")
    llama_up = llamacpp.is_available()
    click.echo(f"llama.cpp (port 8080)  : {'ONLINE' if llama_up else 'Offline'}")

    active = auto_detect_llm()
    click.echo("------------------------------------")
    if active:
        click.echo(f"Default Active Engine  : {active.__class__.__name__} ({active.model})")
    else:
        click.echo("Default Active Engine  : None (Run 'ollama serve' or start LM Studio)")
    click.echo("====================================")


@cmd_llm.command(name="ask")
@click.argument("prompt")
@click.option("--model", default=None, help="Model name override")
def cmd_llm_ask(prompt: str, model: str | None):
    """Ask a question directly to the active local LLM."""
    from remi.engine.llm import auto_detect_llm

    engine = auto_detect_llm()
    if not engine:
        click.echo("Error: No local LLM found. Please start Ollama, LM Studio, or llama.cpp.", err=True)
        sys.exit(1)

    if model:
        engine.model = model

    click.echo(f"Querying [{engine.model}] on {engine.__class__.__name__}...")
    try:
        res = engine.generate(prompt)
        click.echo(f"\n{res.content}")
    except Exception as ex:
        click.echo(f"Generation failed: {ex}", err=True)
        sys.exit(1)


@main.command(name="autostart")
@click.argument("action", default="status", type=click.Choice(["on", "off", "status"]))
@click.option("--app", default=APP_BROWSER_ID, type=click.Choice([APP_BROWSER_ID, APP_DICTATION_ID]))
def cmd_autostart(action: str, app: str):
    """Configure Windows login autostart for Remi."""
    from remi.ui.autostart import handle_cli
    sys.exit(handle_cli(app, sys.argv[0], action))


def voice_trans():
    """Standalone entry point for voice-trans console script."""
    cmd_dictation()


if __name__ == "__main__":
    main()
