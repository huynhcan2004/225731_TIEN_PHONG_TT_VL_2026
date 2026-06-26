"""
Module: app/main.py
Chức năng: Điểm khởi tạo trung tâm của ứng dụng FastAPI.
Nhiệm vụ:
- Cấu hình ứng dụng (FastAPI instance).
- Thiết lập Middleware (CORS, Security).
- Đăng ký các Router thành phần (Auth, Chatbot, Payment, Base).
- Quản lý sự kiện khởi động và đóng ứng dụng.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, chatbot, payment, base, webhook
from app.routers import admin
def create_app() -> FastAPI:
    """
    Hàm khởi tạo ứng dụng (Factory Pattern).
    Giúp dễ dàng cấu hình cho môi trường Testing hoặc Production.
    """
    
    # 1. Khởi tạo thực thể FastAPI với thông tin từ settings
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Hệ thống API điều phối Đồ thị tri thức Y Học Cổ Truyền Diamond.",
        docs_url="/docs",  # Đường dẫn tài liệu Swagger UI
        redoc_url="/redoc"
    )

    # 2. CẤU HÌNH CORS (Cross-Origin Resource Sharing)
    # Cho phép Frontend (React) và Backend khác (Laravel) có thể gọi API này an toàn.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Trong thực tế, hãy liệt kê cụ thể Domain của React/Laravel
        allow_credentials=True,
        allow_methods=["*"],  # Cho phép tất cả các phương thức GET, POST, PUT, DELETE...
        allow_headers=["*"],  # Cho phép các Header tùy chỉnh (như X-API-KEY, Authorization)
    )

    # Phục vụ ảnh upload tĩnh (như Logo)
    from fastapi.staticfiles import StaticFiles
    import os
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    # 3. ĐĂNG KÝ CÁC ROUTER (API ROUTES)
    # Đã loại bỏ hoàn toàn prefix="/api/v1" theo thống nhất của huynh.
    
    # Nhóm API cơ bản (Health check)
    app.include_router(base.router)
    
    # Nhóm API chức năng chính (Auth, Chat, Thanh toán)
    # Đường dẫn sẽ trực tiếp là: /auth/..., /chatbot/..., /payment/...
    app.include_router(auth.router)
    app.include_router(chatbot.router)
    app.include_router(payment.router)
    app.include_router(webhook.router)
    
    app.include_router(admin.router)
    # 4. QUẢN LÝ VÒNG ĐỜI (LIFESPAN EVENTS)
    @app.on_event("startup")
    async def startup_event():
        """Thực hiện các tác vụ khi server bắt đầu chạy."""
        try:
            print(f"[System] {settings.PROJECT_NAME} đang khởi động...")
            print(f"[Endpoint] Tài liệu API: http://localhost:8000/docs")
            print(f"[Payment] API Nạp tiền đã sẵn sàng tại: /payment/create")
        except Exception:
            pass

    @app.on_event("shutdown")
    async def shutdown_event():
        """Thực hiện các tác vụ dọn dẹp khi server tắt."""
        try:
            print(f"[System] {settings.PROJECT_NAME} đang đóng kết nối...")
        except Exception:
            pass

    return app

# Thực thể ứng dụng chính được Uvicorn gọi
app = create_app()