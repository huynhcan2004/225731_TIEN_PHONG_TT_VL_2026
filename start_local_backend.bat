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

:: 2. Mo cua so CMD moi de chay ngrok Tunnel (Đã tắt theo yêu cầu chạy local hoàn toàn)
echo [2/2] Ngrok Tunnel đã được tắt. Chỉ chạy Backend cục bộ...
:: start "ngrok Tunnel" cmd /k "ngrok http --domain=YOUR_DOMAIN.ngrok-free.app 8000"
:: start "ngrok Tunnel" cmd /k "ngrok http 8000"

echo.
echo ========================================================
echo ĐÃ KHỞI CHẠY XONG TIẾN TRÌNH BACKEND CỤC BỘ!
echo ========================================================
pause
