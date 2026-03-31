"""
Module: app/main.py
Chức năng: Điểm khởi tạo trung tâm của ứng dụng FastAPI.
Nhiệm vụ:
- Cấu hình ứng dụng (FastAPI instance).
- Thiết lập Middleware (CORS, Security).
- Đăng ký các Router thành phần (Auth, Chatbot, Base).
- Quản lý sự kiện khởi động và đóng ứng dụng.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import chatbot, base # base là router chứa health check

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

    # 3. ĐĂNG KÝ CÁC ROUTER (API ROUTES)
    # Tách biệt các nhóm chức năng để dễ quản lý và mở rộng
    
    # Nhóm API cơ bản (Health check, welcome)
    app.include_router(base.router)
    
    # Nhóm API Chatbot (Nơi xử lý chính của dự án)
    app.include_router(chatbot.router)

    # Các router sẽ làm sau (Auth, Payment, File Upload)
    # app.include_router(auth.router)
    # app.include_router(file_upload.router)

    # 4. QUẢN LÝ VÒNG ĐỜI (LIFESPAN EVENTS)
    @app.on_event("startup")
    async def startup_event():
        """Thực hiện các tác vụ khi server bắt đầu chạy."""
        print(f"🚀 [System] {settings.PROJECT_NAME} đang khởi động...")
        print(f"📡 [Endpoint] Tài liệu API: http://localhost:8000/docs")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Thực hiện các tác vụ dọn dẹp khi server tắt."""
        print(f"🛑 [System] {settings.PROJECT_NAME} đang đóng kết nối...")

    return app

# Thực thể ứng dụng chính được Uvicorn gọi
app = create_app()