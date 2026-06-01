@echo off
if "%~1"=="hidden" goto :main

:: Re-run this batch file completely hidden using VBScript
set "VBS=%temp%\hide_mattersim.vbs"
echo Set objShell = WScript.CreateObject("WScript.Shell") > "%VBS%"
echo objShell.Run """" ^& WScript.Arguments(0) ^& """ hidden", 0, False >> "%VBS%"
cscript //nologo "%VBS%" "%~f0"
del "%VBS%"
exit /b

:main
:: Change directory to current script path
cd /d "%~dp0"

:: 1. Smart Python detection (check .venv first!)
set "PYTHON_EXE=python"
if exist ".\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\.venv\Scripts\python.exe"
) else if exist "C:\Users\Admin\AppData\Local\Python\bin\python.exe" (
    set "PYTHON_EXE=C:\Users\Admin\AppData\Local\Python\bin\python.exe"
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=py"
    )
)

:: Get pythonw.exe instead of python.exe
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"
if "%PYTHON_EXE%"=="py" (
    set "PYTHONW_EXE=pyw"
)

:: Create the lock file
echo loading > splash.lock

:: 2. Launch splash screen in the background
start "" "%PYTHONW_EXE%" "splash.pyw"

:: 3. Launch the application silently using pythonw/pyw
start "" "%PYTHONW_EXE%" "Lattice constant_Prediction.py"
exit
