@echo off
cd /d "%~dp0"
title RPG Maker MV / MZ Translator GUI

echo ========================================================
echo   Starting RPG Maker MV / MZ Translator GUI...
echo ========================================================

where python >nul 2>nul
if %errorlevel% equ 0 (
    python rpg_translator_gui.py
    goto check_exit
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py rpg_translator_gui.py
    goto check_exit
)

echo.
echo [ERROR] Python not found!
echo Please make sure Python 3.8+ is installed and added to PATH.
echo.
pause
exit /b 1

:check_exit
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)