@echo off
title Remi Voice Assistant
echo Starting Remi Browser Voice Controller (Ctrl+Alt+B)...
python -m remi start
if %errorlevel% neq 0 (
    pause
)
