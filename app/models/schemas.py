"""
Module: app/models/schemas.py
Chức năng: Định nghĩa các Pydantic Models (Schemas) cho ứng dụng.
Nhiệm vụ: 
- Xác thực dữ liệu đầu vào (Request Validation).
- Định dạng dữ liệu đầu ra (Response Serialization).
- Cung cấp tài liệu API tự động (OpenAPI/Swagger).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict, Union
from datetime import datetime

# ==========================================================
# 1. SCHEMAS CHO CHATBOT (GRAPH RAG)
# ==========================================================

class ChatRequest(BaseModel):
    """
    Dữ liệu yêu cầu gửi từ Frontend để chat với AI.
    """
    message: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    model: Optional[str] = Field("gemini-2.5-flash", description="Tên mô hình AI muốn sử dụng")
    session_id: Optional[int] = Field(None, description="ID của phiên chat để gom nhóm tin nhắn")
    lang: Optional[str] = Field("vi", description="Ngôn ngữ hiện tại của giao diện (vi hoặc en)")
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Vị thuốc Ích mẫu có tác dụng gì?",
                "model": "gemini-2.5-flash",
                "lang": "vi"
            }
        }

class ChatMetadata(BaseModel):
    """
    Thông tin kỹ thuật đi kèm trong câu trả lời.
    """
    records_found: int = Field(0, description="Số lượng bản ghi tìm thấy trong đồ thị")
    cypher_executed: Optional[str] = Field(None, description="Câu lệnh Cypher đã thực thi (chế độ debug)")
    plant_name: Optional[str] = None # ✨ Thêm để khớp với chatbot.py
    exec_time: float = 0.0

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
    tokens_charged: float = Field(0.0, description="Số token đã tiêu thụ cho câu trả lời này")
    user_token_balance: float = Field(0.0, description="Số dư token còn lại của người dùng")

class TranslateRequest(BaseModel):
    """
    Dữ liệu yêu cầu dịch tin nhắn chatbot.
    """
    text: str = Field(..., description="Nội dung văn bản cần dịch")
    target_lang: str = Field(..., description="Ngôn ngữ mục tiêu ('vi' hoặc 'en')")

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
    # ✨ SỬA ĐỔI: Dùng Any để linh hoạt giữa int (SQLite) và string (Frontend)
    id: Union[int, str] 
    username: str
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None 
    token_balance: float = 0.0      
    is_premium: bool = Field(False, description="Trạng thái tài khoản trả phí")
    
    # ✨ CHÍNH LÀ NÓ! Thêm trường này để Pydantic trả về role cho Frontend
    role: str = Field("user", description="Quyền hạn người dùng (admin/user)") 
    is_root_admin: Optional[bool] = Field(False, description="Trạng thái Admin gốc")
    
    created_at: Any 

    class Config:
        from_attributes = True # Cho phép convert từ dict của SQLite

# ==========================================================
# 3. SCHEMAS CHO THANH TOÁN (PAYMENT)
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
# 4. SCHEMAS CƠ BẢN (BASE) & WEBHOOK
# ==========================================================

class HealthCheck(BaseModel):
    """
    Kiểm tra trạng thái hoạt động của Server.
    """
    status: str = "online"
    version: str
    database_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SePayWebhook(BaseModel):
    """
    Dữ liệu nhận về từ SePay Webhook.
    """
    id: int
    gateway: str
    transactionDate: str
    accountNumber: str
    content: str = Field(..., description="Nội dung chuyển khoản (chứa User ID)")
    transferType: str = Field(..., description="Loại giao dịch (in/out)")
    transferAmount: float = Field(..., description="Số tiền chuyển")
    referenceCode: str