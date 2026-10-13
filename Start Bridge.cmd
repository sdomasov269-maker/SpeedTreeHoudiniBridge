@echo off
cd /d "%~dp0"
python "%~dp0launch.py"
if errorlevel 1 pause
