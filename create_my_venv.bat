@echo off
chcp 65001 > nul
echo ==========================================================
echo SCRIPT TAO MOI TRUONG AO VA CAI DAT THU VIEN CHO MATTERSIM
echo ==========================================================

:: Chuyen vao dung thu muc ma file .bat nay dang dung
cd /d "%~dp0"
echo Thu muc dang lam viec: %CD%
echo.

echo [BUOC 1] DANG TAO MOI TRUONG AO (.venv)...
uv --version > nul 2>&1
if %errorlevel% equ 0 (
    echo =^> May co san 'uv', dang dung 'uv' de tao sieu toc...
    uv venv
) else (
    echo =^> Dang dung Python mac dinh de tao...
    python -m venv .venv
)

echo.
echo [BUOC 2] KIEM TRA PYTHON TRONG MOI TRUONG AO VUA TAO...
if exist ".\.venv\Scripts\python.exe" (
    echo =^> [OK] Da tim thay python.exe nam gon trong moi truong ao (.venv)!
    .\.venv\Scripts\python.exe --version
) else (
    echo =^> [LOI] Khong tim thay python trong moi truong ao. Tao that bai!
    pause
    exit /b
)

echo.
echo [BUOC 3] DANG TAI VA CAI DAT THU VIEN TU requirements.txt...
echo (Cac thu vien nay se nam rieng trong thu muc cua ban, khong anh huong toi thay)
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
    echo =^> [LOI] Khong tim thay file requirements.txt de cai dat!
)

echo.
echo ==========================================================
echo HOAN THANH! MOI TRUONG CUA RIENG BAN DA SAN SANG.
echo ==========================================================
echo De bat dau xai, ban mo PowerShell o thu muc nay roi go:
echo 1. .\.venv\Scripts\Activate.ps1
echo 2. python <ten_file_ban_muon_chay>.py
echo.
pause
