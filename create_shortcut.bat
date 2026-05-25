@echo off
title MatterSim AI Lab - Create Shortcut
color 0B

echo ===================================================
echo           CREATE SHORTCUT FOR MATTERSIM AI LAB
echo ===================================================
echo.
echo Creating Desktop Shortcut for MatterSim AI Lab...
echo.

:: Change directory to current script path
cd /d "%~dp0"

:: Execute PowerShell to create the shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command "$wsh = New-Object -ComObject WScript.Shell; $desktopPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'MatterSim AI Lab.lnk'); $shortcut = $wsh.CreateShortcut($desktopPath); $currentDir = (Get-Location).Path; $shortcut.TargetPath = Join-Path $currentDir 'run_app.bat'; $shortcut.WorkingDirectory = $currentDir; $shortcut.IconLocation = Join-Path $currentDir 'app.ico'; $shortcut.Save(); if (Test-Path $desktopPath) { Write-Host 'SUCCESS' } else { Write-Host 'FAILED' }" > "%TEMP%\shortcut_result.txt" 2>nul

:: Read the operation result
set RESULT=FAILED
if exist "%TEMP%\shortcut_result.txt" (
    set /p RESULT=<"%TEMP%\shortcut_result.txt"
    del "%TEMP%\shortcut_result.txt" >nul 2>&1
)

if "%RESULT%"=="SUCCESS" (
    echo.
    echo ---------------------------------------------------
    echo [SUCCESS] Created 'MatterSim AI Lab' shortcut on your Desktop!
    echo Application icon has been automatically assigned from app.ico.
    echo ---------------------------------------------------
    echo.
) else (
    echo.
    echo ---------------------------------------------------
    echo [ERROR] Failed to create shortcut.
    echo Please check write permissions on your Desktop or run as Administrator.
    echo ---------------------------------------------------
    echo.
)

echo Press any key to exit...
pause > nul
