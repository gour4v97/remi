@echo off
:: ===================================================================
:: Remi Browser Voice Controller
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Remi Voice Assistant - Publisher: GAURAV
cd /d "%~dp0\.."
echo Starting Remi Browser Voice Controller (Ctrl+Alt+B)...
python -m remi start
if %errorlevel% neq 0 (
    echo.
    echo Remi encountered an error. Running diagnostics...
    python -m remi doctor
    pause
)
