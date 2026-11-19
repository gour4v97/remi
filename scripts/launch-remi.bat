@echo off
:: ===================================================================
:: Remi Browser Voice Controller
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Remi Voice Assistant - Publisher: GAURAV
cd /d "%~dp0\.."
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)
echo Starting Remi Browser Voice Controller (Ctrl+Alt+B)...
"%PY_EXE%" -m remi start
if %errorlevel% neq 0 (
    echo.
    echo Remi encountered an error. Running diagnostics...
    "%PY_EXE%" -m remi doctor
    pause
)
