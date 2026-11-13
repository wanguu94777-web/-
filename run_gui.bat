@echo off
chcp 65001 >nul
title RPG Maker MV / MZ JSON 翻譯神器
echo 正在啟動 RPG Maker 翻譯工具 GUI...
python rpg_translator_gui.py
if %errorlevel% neq 0 (
    echo.
    echo 啟動失敗，請確認已安裝 Python 3.8+ 並加入環境變數 PATH。
    pause
)
