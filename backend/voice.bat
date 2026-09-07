@echo off
title SMART AI - Jarkvis Voice Assistant
chcp 65001 >nul
cd /d "%~dp0"
venv\Scripts\python.exe voice_chat_cli.py %*

pause
