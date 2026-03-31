#!/bin/bash
# Script khởi chạy ứng dụng cho môi trường Linux/Docker
echo "🚀 Starting YHCT Diamond AI API..."

# Kích hoạt môi trường ảo nếu tồn tại
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Chạy server Uvicorn
python run_api.py