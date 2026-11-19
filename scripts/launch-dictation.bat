@echo off
:: ===================================================================
:: Voice Trans Push-to-Talk Dictation
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Voice Trans Dictation - Publisher: GAURAV
cd /d "%~dp0\.."
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)
echo Starting Voice Trans Push-to-Talk Dictation (Ctrl+Alt+Space)...
"%PY_EXE%" -m remi dictation
if %errorlevel% neq 0 (
    echo.
    echo Voice Trans encountered an error. Running diagnostics...
    "%PY_EXE%" -m remi doctor
    pause
)
