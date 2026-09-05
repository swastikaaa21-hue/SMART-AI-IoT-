@echo off
title SMART AI - Asisten IoT
chcp 65001 >nul
cd /d "%~dp0backend"
venv\Scripts\python.exe test_chat_cli.py

pause
