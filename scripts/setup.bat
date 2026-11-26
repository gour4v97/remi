@echo off
:: ===================================================================
:: Remi Suite Setup
:: Publisher: Gaurav Manjhi
:: Copyright (c) 2026 Gaurav Manjhi. All rights reserved.
:: ===================================================================
title Remi Setup Wizard - Publisher: Gaurav Manjhi
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if %errorlevel% neq 0 (
    echo.
    echo PowerShell setup failed. Falling back to python setup...
    python -m remi setup
)
pause
