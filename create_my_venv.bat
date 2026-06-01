@echo off
chcp 65001 > nul
echo ==========================================================
echo SCRIPT TO CREATE VIRTUAL ENVIRONMENT AND INSTALL LIBRARIES
echo ==========================================================

:: Switch to the directory where this .bat file is located
cd /d "%~dp0"
echo Current working directory: %CD%
echo.

echo [STEP 1] CREATING VIRTUAL ENVIRONMENT (.venv)...
uv --version > nul 2>&1
if %errorlevel% equ 0 (
    echo =^> Found 'uv' tool, using 'uv' for ultra-fast creation...
    uv venv
) else (
    echo =^> 'uv' not found, using default Python...
    python -m venv .venv
)

echo.
echo [STEP 2] CHECKING PYTHON IN THE NEW VIRTUAL ENVIRONMENT...
if exist ".\.venv\Scripts\python.exe" (
    echo =^> [OK] Successfully found python.exe inside the .venv!
    .\.venv\Scripts\python.exe --version
) else (
    echo =^> [ERROR] Python not found in the virtual environment. Creation failed!
    pause
    exit /b
)

echo.
echo [STEP 3] DOWNLOADING AND INSTALLING LIBRARIES FROM requirements.txt...
echo (These libraries will be installed in your local environment, not affecting the system)
if exist "requirements.txt" (
    uv --version > nul 2>&1
    if %errorlevel% equ 0 (
        uv pip install -r requirements.txt
    ) else (
        call .\.venv\Scripts\activate.bat
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    )
) else (
    echo =^> [ERROR] requirements.txt file not found! Please ensure it is in the same folder.
)

echo.
echo ==========================================================
echo SUCCESS! YOUR PRIVATE ENVIRONMENT IS READY.
echo ==========================================================
echo To start using it, open PowerShell in this folder and type:
echo 1. .\.venv\Scripts\Activate.ps1
echo 2. python ^<your_script_name^>.py
echo.
pause
