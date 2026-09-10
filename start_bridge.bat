@echo off
setlocal
chcp 65001 >nul
title Obsidian Bridge

REM ============================================================
REM  Obsidian Bridge Launcher
REM  Starts the local bridge service (obsidian_bridge.py) so that
REM  http links inside Feishu Base can open local Obsidian notes.
REM  Keep this window open while using the feature.
REM
REM  NOTE: This file is intentionally ASCII-only. Chinese text in a
REM  .bat file breaks cmd.exe parsing (UTF-8 vs GBK codepage) and
REM  causes an instant crash. Do not add non-ASCII characters here.
REM ============================================================

cd /d "%~dp0"

set "PY=C:\Users\MDSNALW\.workbuddy\binaries\python\versions\3.13.12\python.exe"

if not exist "%PY%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No usable Python found.
        echo         Install Python or make sure it is on PATH.
        echo.
        pause
        exit /b 1
    )
    set "PY=python"
)

echo ============================================================
echo   Starting Obsidian Bridge ...
echo   Close this window to stop the service.
echo ============================================================
echo.

"%PY%" obsidian_bridge.py

echo.
echo Service stopped.
pause
