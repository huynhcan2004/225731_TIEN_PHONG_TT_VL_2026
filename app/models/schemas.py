"""
Module: app/models/schemas.py
Chức năng: Định nghĩa các Pydantic Models (Schemas) cho ứng dụng.
Nhiệm vụ: 
- Xác thực dữ liệu đầu vào (Request Validation).
- Định dạng dữ liệu đầu ra (Response Serialization).
- Cung cấp tài liệu API tự động (OpenAPI/Swagger).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict
from datetime import datetime

# ==========================================================
# 1. SCHEMAS CHO CHATBOT (GRAPH RAG)
# ==========================================================

class ChatRequest(BaseModel):
    """
    Dữ liệu yêu cầu gửi từ Frontend để chat với AI.
    """
    message: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    model: Optional[str] = Field("gemini-2.0-flash", description="Tên mô hình AI muốn sử dụng")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Vị thuốc Ích mẫu có tác dụng gì?",
                "model": "gemini-2.0-flash"
            }
        }

class ChatMetadata(BaseModel):
    """
    Thông tin kỹ thuật đi kèm trong câu trả lời.
    """
    records_found: int = Field(0, description="Số lượng bản ghi tìm thấy trong đồ thị")
    cypher_executed: Optional[str] = Field(None, description="Câu lệnh Cypher đã thực thi (chế độ debug)")

class ChatResponse(BaseModel):
    """
    Cấu trúc phản hồi chuẩn từ Chatbot API.
    """
    answer: str = Field(..., description="Câu trả lời cuối cùng từ AI")
    intent: str = Field(..., description="Ý định người dùng đã phân tích")
    entities: List[str] = Field(default=[], description="Danh sách các thực thể tìm thấy")
    exec_time: float = Field(..., description="Thời gian xử lý tính bằng giây")
    model_used: str = Field(..., description="Mô hình AI đã thực hiện trả lời")
    status: str = Field("success", description="Trạng thái phản hồi (success/error/warning)")
    metadata: Optional[ChatMetadata] = None

# ==========================================================
# 2. SCHEMAS CHO XÁC THỰC (AUTHENTICATION)
# ==========================================================

class UserLogin(BaseModel):
    """
    Dữ liệu đăng nhập.
    """
    username: str = Field(..., description="Tên đăng nhập hoặc Email")
    password: str = Field(..., description="Mật khẩu người dùng")

class Token(BaseModel):
    """
    Cấu trúc Token JWT trả về sau khi đăng nhập thành công.
    """
    access_token: str = Field(..., description="Mã JWT dùng để truy cập các API bảo mật")
    token_type: str = Field("bearer", description="Loại token")
    expires_in: int = Field(..., description="Thời gian hết hạn tính bằng giây")

class UserOut(BaseModel):
    """
    Thông tin người dùng trả về (Không bao gồm mật khẩu).
    """
    id: str
    username: str
    email: Optional[EmailStr] = None
    is_premium: bool = Field(False, description="Trạng thái tài khoản trả phí")
    created_at: datetime

# ==========================================================
# 3. SCHEMAS CHO THANH TOÁN (PAYMENT - PLACEHOLDER)
# ==========================================================

class SubscriptionPlan(BaseModel):
    """
    Thông tin các gói dịch vụ.
    """
    plan_id: str
    name: str
    price: float
    currency: str = "VND"
    features: List[str]

class PaymentInit(BaseModel):
    """
    Yêu cầu khởi tạo thanh toán (ZaloPay/Momo/Stripe).
    """
    plan_id: str
    amount: float
    callback_url: str

class PaymentStatus(BaseModel):
    """
    Kết quả kiểm tra trạng thái thanh toán.
    """
    order_id: str
    is_paid: bool
    transaction_id: Optional[str] = None
    payment_time: Optional[datetime] = None

# ==========================================================
# 4. SCHEMAS CƠ BẢN (BASE)
# ==========================================================

class HealthCheck(BaseModel):
    """
    Kiểm tra trạng thái hoạt động của Server.
    """
    status: str = "online"
    version: str
    database_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)