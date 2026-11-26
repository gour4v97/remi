# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller packaging specification for standalone Remi Suite executable on Windows.

Build command:
    pyinstaller build_windows.spec
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
src_dir = Path("src").resolve()

datas = [
    ("configs/default.toml", "configs"),
    ("src/remi/skills/builtin/*.toml", "remi/skills/builtin"),
    ("src/remi/assets/*", "remi/assets"),
    ("assets/remi.ico", "assets"),
    ("assets/logo.png", "assets"),
    ("testdata/open-github.wav", "testdata"),
]

hiddenimports = [
    "remi",
    "remi.agents.browser_agent",
    "remi.agents.dictation_agent",
    "remi.core.config",
    "remi.core.events",
    "remi.core.memory",
    "remi.core.perf",
    "remi.core.registry",
    "remi.engine.whisper_cpp",
    "remi.engine.llm",
    "remi.speech.capture",
    "remi.speech.tts",
    "remi.speech.translit",
    "remi.speech.vad",
    "remi.speech.wakeword",
    "remi.tools.browser",
    "remi.tools.delivery",
    "remi.tools.router",
    "remi.ui.tray",
    "remi.ui.overlay",
    "remi.ui.autostart",
    "sounddevice",
    "pystray",
    "pyperclip",
    "pyttsx3",
    "websocket",
    "click",
    "PIL",
    "tkinter",
]

a = Analysis(
    ['src/remi/__main__.py'],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'scipy', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='remi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/remi.ico' if Path('assets/remi.ico').exists() else None,
    version='version_info.txt' if Path('version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='remi',
)
