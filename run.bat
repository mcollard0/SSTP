@echo off
rem Stuart Saves the Pomodoro Launcher for Windows
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%PYTHONPATH%
python -m sstp.app %*
