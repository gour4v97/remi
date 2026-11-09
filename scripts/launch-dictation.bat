@echo off
title Voice Trans Dictation
echo Starting Voice Trans Push-to-Talk Dictation (Ctrl+Alt+Space)...
python -m remi dictation
if %errorlevel% neq 0 (
    pause
)
