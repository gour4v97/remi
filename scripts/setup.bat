@echo off
:: ===================================================================
:: Remi Suite Setup
:: Publisher: GAURAV
:: Copyright (c) 2026 GAURAV. All rights reserved.
:: ===================================================================
title Remi Setup Wizard - Publisher: GAURAV
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if %errorlevel% neq 0 (
    echo.
    echo PowerShell setup failed. Falling back to python setup...
    python -m remi setup
)
pause
