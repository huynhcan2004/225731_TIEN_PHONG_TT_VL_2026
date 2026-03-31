"""
Module: app/routers/base.py
Chức năng: Chứa các endpoint cơ bản về hệ thống.
"""

from fastapi import APIRouter
from datetime import datetime
from app.config import settings
from app.models.base_db import db

router = APIRouter(tags=["Hệ thống"])

@router.get("/", summary="Lời chào hệ thống")
async def root():
    return {
        "message": f"Chào mừng đến với {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "status": "online"
    }

@router.get("/health", summary="Kiểm tra sức khỏe hệ thống")
async def health_check():
    """
    Kiểm tra trạng thái kết nối của API và Cơ sở dữ liệu.
    """
    db_status = True if db and db.graph else False
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": db_status,
        "environment": "development"
    }