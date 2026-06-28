@echo off
title Khoi Chay Hybrid Backend YHCT

echo ========================================================
echo Dang khoi chay Backend va ngrok Tunnel...
echo ========================================================
echo.

:: 1. Mo cua so CMD moi de chay FastAPI Backend
echo [1/2] Dang bat Backend tai cong 8000...
start "FastAPI Backend" cmd /k "set "PYTHONUTF8=1" && set "PYTHONIOENCODING=utf-8" && call venv\Scripts\activate.bat && python run_api.py"

:: Doi 2 giay de backend bat len truoc
timeout /t 2 /nobreak > nul

:: 2. Mo cua so CMD moi de chay ngrok Tunnel
echo [2/2] Dang ket noi ngrok Tunnel...
:: Neu ban da co domain co dinh free cua ngrok, hay bo dau :: o dong duoi va sua lai domain cua ban:
:: start "ngrok Tunnel" cmd /k "ngrok http --domain=YOUR_DOMAIN.ngrok-free.app 8000"
:: Con day la lenh mac dinh chay ngrok cap link ngau nhien:
start "ngrok Tunnel" cmd /k "ngrok http 8000"

echo.
echo ========================================================
echo DA KHOI CHAY XONG CA HAI TIEN TRINH!
echo.
echo * Hay kiem tra CUA SO "ngrok Tunnel" de lay link public moi.
echo * Dung link do de cap nhat len Vercel va Google Cloud Console.
echo ========================================================
pause
