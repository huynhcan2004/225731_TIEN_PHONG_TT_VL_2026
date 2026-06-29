"""
Script khởi chạy ứng dụng FastAPI bằng Uvicorn.
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load các biến môi trường từ file .env cục bộ
load_dotenv()

if __name__ == "__main__":
    # Chạy ứng dụng từ module app.main thực thể app
    # Chỉ bật reload khi ở môi trường phát triển (development)
    is_dev = os.getenv("APP_ENV", "development").lower() == "development"
    # Lấy cổng PORT từ biến môi trường tự động gán bởi server (Render/Railway), mặc định 63064 ở local
    port = int(os.getenv("PORT", 63064))
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=is_dev,
        log_level="info"
    )