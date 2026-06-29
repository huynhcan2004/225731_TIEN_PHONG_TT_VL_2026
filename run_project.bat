@echo off
title YHCT Diamond Project Starter with Ngrok
color 0A

echo ======================================================
echo     DANG KHOI CHAY HE THONG YHCT DIAMOND + NGROK (2026)
echo ======================================================

:: 1. Khoi chay Backend trong cua so moi
echo [*] Dang bat Backend (FastAPI)...
start "Backend - Port 63064" cmd /k "venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 63064"

:: 2. Cho 2 giay de Backend on dinh
timeout /t 2 /nobreak > nul

:: 3. Khoi chay Frontend (Vite) va ep mo cong mang LAN (--host)
echo [*] Dang bat Frontend (Vite --host)...
start "Frontend - Port 51582" cmd /k "cd frontend && npm run dev -- --host"

:: 4. Cho 2 giay de Frontend len mo cong hop le
timeout /t 2 /nobreak > nul

:: 5. Khoi chay Ngrok trong cua so moi de quat link ra Internet (Đã tắt theo yêu cầu chạy local hoàn toàn)
echo [*] Ngrok Tunnel đã được tắt.

echo ------------------------------------------------------
echo [THANH CONG] Toàn bộ hệ thống Backend và Frontend cục bộ đang chạy!
echo - Backend FastAPI: http://localhost:63064
echo - Frontend Vite   : http://localhost:51582
echo ------------------------------------------------------
echo Nhấn phím bất kỳ để đóng cửa sổ thông báo này.
pause > nul