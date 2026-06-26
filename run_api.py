"""
Script khởi chạy ứng dụng FastAPI bằng Uvicorn.
"""

import uvicorn
import os

if __name__ == "__main__":
    # Chạy ứng dụng từ module app.main thực thể app
    # Chỉ bật reload khi ở môi trường phát triển (development)
    is_dev = os.getenv("APP_ENV", "development").lower() == "development"
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=is_dev,
        log_level="info"
    )