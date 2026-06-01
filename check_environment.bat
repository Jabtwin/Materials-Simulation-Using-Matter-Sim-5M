@echo off
chcp 65001 > nul
echo ===================================================
echo CHECKING IF PYTHON IS INSTALLED...
echo ===================================================

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! 
    echo Python is not installed on this machine, or "Add Python to PATH" was not checked during installation.
    echo Please download Python from python.org and install it first (remember to check "Add to PATH").
    echo ===================================================
    pause
    exit /b
)

echo.
echo Python found! Checking libraries...
echo.
python check_env.py
