@echo off
title Comic Bubble Maker
cd /d "C:\Users\steav\.gemini\antigravity\scratch\comic-bubble-maker"
"C:\Users\steav\AppData\Local\Programs\Python\Python312\python.exe" comic_bubble_app.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
