@echo off
title MATTERSIM AI GUI - ENVIRONMENT SETUP
color 0B

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    color 0E
    echo [INFO] Administrator privileges are required to install Python and C++ Build Tools.
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~dpnx0\"' -Verb RunAs"
    exit /b
)

echo ====================================================================
echo                 MATTERSIM APPLICATION ENVIRONMENT SETUP
echo ====================================================================
echo.
echo This script will automatically install Python, C++ Build Tools, and libraries.
echo Please do not close this window. It may take some time.
echo.

:: 1. Check Python
set "PYTHON_EXE=python"
python -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo [WARNING] Python is not installed or not in PATH.
    echo Downloading Python 3.10.11...
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    if exist python_installer.exe (
        echo Installing Python 3.10.11 silently...
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del python_installer.exe
        echo [OK] Python installed successfully.
        
        :: Refresh PATH in current session (simple workaround)
        set "PATH=%ProgramFiles%\Python310\Scripts\;%ProgramFiles%\Python310\;%PATH%"
    ) else (
        color 0C
        echo [ERROR] Failed to download Python.
        pause
        exit /b
    )
)

:: Re-verify Python
python -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python installation failed or PATH not updated. Please install manually.
    pause
    exit /b
)

for /f "tokens=* trims=" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"') do set "PY_VER=%%i"
color 0B
echo [OK] Python detected! (Version: %PY_VER%)
echo.

:: 2. Check C++ Build Tools
echo Checking for Microsoft C++ Build Tools (required for ASE and MatterSim)...
set "MSVC_FOUND=0"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC" set "MSVC_FOUND=1"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2019\BuildTools\VC\Tools\MSVC" set "MSVC_FOUND=1"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC" set "MSVC_FOUND=1"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC" set "MSVC_FOUND=1"

if "%MSVC_FOUND%"=="0" (
    color 0E
    echo C++ Build Tools not found. Downloading installer...
    curl -L -o vs_buildtools.exe https://aka.ms/vs/17/release/vs_buildtools.exe
    if exist vs_buildtools.exe (
        echo Installing C++ Build Tools (This will take 5-10 minutes)...
        echo Please wait, downloading and installing in background...
        start /wait vs_buildtools.exe --quiet --wait --norestart --nocache --installPath "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools" --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
        del vs_buildtools.exe
        color 0B
        echo [OK] C++ Build Tools installed.
    ) else (
        color 0C
        echo [ERROR] Failed to download C++ Build Tools.
        pause
        exit /b
    )
) else (
    echo [OK] Microsoft C++ Build Tools already installed.
)

:: 3. Install Python Dependencies
echo.
echo [1/2] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [2/2] Installing machine learning and GUI dependencies...
echo (This may take 2-5 minutes depending on your network speed as PyTorch and MatterSim are large packages)
echo.
python -m pip install -r requirements.txt

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
