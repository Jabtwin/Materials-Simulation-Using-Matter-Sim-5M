@echo off
chcp 65001 > nul
echo ===================================================
echo SCRIPT TAO MOI TRUONG AO VA CAI DAT THU VIEN RIENG
echo ===================================================
echo Vui long cho trong it phut...
echo.

echo [1] Kiem tra xem may co cong cu 'uv' hay khong...
uv --version > nul 2>&1
if %errorlevel% equ 0 (
    echo =^> Da tim thay cong cu 'uv'! Se su dung 'uv' de cai dat sieu toc.
    echo.
    echo [2] Dang tao moi truong ao (.venv)...
    uv venv
    
    echo.
    echo [3] Dang cai dat cac thu vien tu requirements.txt...
    uv pip install -r requirements.txt
    
) else (
    echo =^> Khong tim thay 'uv'. Se dung cach thong thuong (pip)...
    echo.
    echo [2] Dang tao moi truong ao (.venv)...
    python -m venv .venv
    
    echo.
    echo [3] Dang cai dat cac thu vien (co the mat vai phut)...
    call .\.venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo.
echo ===================================================
echo HOAN THANH! MOI TRUONG AO CUA RIENG BAN DA DUOC TAO.
echo Ban khong con lo anh huong den du an cua thay nua!
echo ===================================================
echo.
echo De chay chuong trinh cua ban, ban chi can mo PowerShell, sau do:
echo 1. Go: .\.venv\Scripts\Activate.ps1
echo 2. Go: python ten_file_cua_ban.py (vi du: python engine.py)
echo.
pause
