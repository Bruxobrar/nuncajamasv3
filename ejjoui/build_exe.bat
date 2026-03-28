@echo off
cd /d "%~dp0"
pyinstaller --noconfirm --onefile --windowed --name ejjoui app.py
