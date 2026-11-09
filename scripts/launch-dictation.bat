@echo off
:: ===================================================================
:: Voice Trans Push-to-Talk Dictation
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Voice Trans Dictation - Publisher: GAURAV
cd /d "%~dp0\.."
echo Starting Voice Trans Push-to-Talk Dictation (Ctrl+Alt+Space)...
python -m remi dictation
if %errorlevel% neq 0 (
    echo.
    echo Voice Trans encountered an error. Running diagnostics...
    python -m remi doctor
    pause
)
