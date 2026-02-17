@echo off
title DND DM Assistant
cd /d %~dp0

echo Starting Ollama...
start "Ollama Server" cmd /k ollama serve

timeout /t 3 > nul

echo Starting DND DM...
py main.py

echo.
echo Game closed. Shutting down Ollama...

taskkill /IM ollama.exe /F >nul 2>nul

echo Ollama closed.
pause
