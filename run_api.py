"""
Script khởi chạy ứng dụng FastAPI bằng Uvicorn.
"""

import uvicorn
import os

if __name__ == "__main__":
    # Chạy ứng dụng từ module app.main thực thể app
    # reload=True giúp server tự động cập nhật khi bạn sửa code (chỉ dùng khi Dev)
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )