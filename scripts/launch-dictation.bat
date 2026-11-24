@echo off
:: ===================================================================
:: Voice Trans Push-to-Talk Dictation
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Voice Trans Dictation - Publisher: GAURAV
cd /d "%~dp0\.."
echo Starting Voice Trans Push-to-Talk Dictation (Ctrl+Alt+Space)...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m remi dictation
) else (
    python -m remi dictation
)
if %errorlevel% neq 0 (
    echo.
    echo Voice Trans encountered an error. Running diagnostics...
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe -m remi doctor
    ) else (
        python -m remi doctor
    )
    pause
)
