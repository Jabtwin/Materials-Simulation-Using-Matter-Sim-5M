@echo off
title MATTERSIM AI GUI - ENVIRONMENT SETUP
color 0B
echo ====================================================================
echo                 MATTERSIM APPLICATION ENVIRONMENT SETUP
echo ====================================================================
echo.
echo This script will help you automatically install Python and required libraries.
echo.

:: 1. Smart Python detection to avoid Windows Store alias
set "PYTHON_EXE=python"
if exist "C:\Users\Admin\AppData\Local\Python\bin\python.exe" (
    set "PYTHON_EXE=C:\Users\Admin\AppData\Local\Python\bin\python.exe"
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=py"
    )
)

:: Verify if the detected Python is actually functional (not the fake Windows Store alias)
%PYTHON_EXE% -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [WARNING] Python is NOT installed or correctly configured on this computer!
    echo.
    echo The script will now automatically open the Python download page in your browser.
    echo Installation Steps:
    echo   1. Download the Python 3.10 or 3.11 installer for Windows.
    echo   2. CRITICAL: Make sure to check the box "Add Python.exe to PATH" at the bottom of the installer!
    echo   3. Once Python is installed, close this window and run this script again.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b
)

:: Show version
for /f "tokens=* trims=" %%i in ('%PYTHON_EXE% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"') do set "PY_VER=%%i"
echo [OK] Python detected! (Version: %PY_VER% using executable: %PYTHON_EXE%)
echo.
echo [1/2] Upgrading pip...
%PYTHON_EXE% -m pip install --upgrade pip

echo.
echo [2/2] Installing machine learning and GUI dependencies...
echo (This may take 2-5 minutes depending on your network speed as PyTorch and MatterSim are large packages)
echo.
%PYTHON_EXE% -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    color 0A
    echo.
    echo ====================================================================
    echo        CONGRATULATIONS! ENVIRONMENT SETUP COMPLETED SUCCESSFULLY!
    echo ====================================================================
    echo.
    echo You can now close this window and double-click the file:
    echo "run_app.bat" to start the application!
    echo.
) else (
    color 0C
    echo.
    echo ====================================================================
    echo       [ERROR] An error occurred during the library installation.
    echo ====================================================================
    echo Please check your internet connection and run this script again.
    echo.
)

pause

