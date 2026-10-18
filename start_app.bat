@echo off
chcp 65001 > nul
title Comic Bubble Maker

cd /d "%~dp0"

echo [Comic Bubble Maker] アプリを起動しています...
python comic_bubble_app.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo アプリの起動中にエラーが発生しました。
    pause
)
