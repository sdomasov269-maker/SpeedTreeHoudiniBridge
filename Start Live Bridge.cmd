@echo off
cd /d "%~dp0"
python "%~dp0live_bridge.py"
if errorlevel 1 pause
