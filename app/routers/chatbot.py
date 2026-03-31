"""
Module: app/routers/chatbot.py
Chức năng: Định nghĩa các API Endpoints cho hệ thống Chatbot AI.
Nhiệm vụ: 
- Tiếp nhận yêu cầu truy vấn tri thức từ Frontend hoặc các dịch vụ tích hợp (Laravel).
- Thực thi kiểm tra bảo mật (API Key & JWT).
- Giao tiếp với lớp Service để xử lý logic GraphRAG.
- Trả về kết quả theo chuẩn định dạng đã quy định trong Schemas.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from app.models.schemas import ChatRequest, ChatResponse
from chatbot.services.chat_service import YHCTChatService
from app.config import settings

# Khởi tạo Router với tiền tố /chatbot và nhóm tags để tự động sinh tài liệu API (Swagger)
router = APIRouter(prefix="/chatbot", tags=["Hệ thống Trí tuệ Nhân tạo"])

# ==========================================================
# 🛡️ CƠ CHẾ BẢO MẬT (SECURITY DEPENDENCIES)
# ==========================================================

async def verify_internal_access(x_api_key: str = Header(None)):
    """
    Dependency dùng để xác thực API Key từ phía Laravel.
    Kiểm tra Header 'X-API-KEY' có khớp với cấu hình trong .env hay không.
    """
    if x_api_key != settings.LARAVEL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã xác thực API Key không hợp lệ hoặc đã hết hạn."
        )
    return x_api_key

# Ghi chú: Dependency cho JWT sẽ được tích hợp sau khi hoàn thiện router/auth.py
# Hiện tại endpoint này cho phép gọi công khai hoặc qua API Key để bạn dễ chạy thử (Testing)

# ==========================================================
# 🚀 CÁC ĐƯỜNG DẪN API (ENDPOINTS)
# ==========================================================

@router.post("/query", response_model=ChatResponse)
async def ask_ai_specialist(
    request: ChatRequest,
    # dependency_api_key: str = Depends(verify_internal_access) # Mở comment này để bắt buộc dùng API Key
):
    """
    Endpoint chính để thực hiện hội thoại với Chuyên gia YHCT Diamond.
    
    Yêu cầu (Request Body):
    - message (str): Câu hỏi ngôn ngữ tự nhiên.
    - model (str, optional): Tên model AI (Gemini/Qwen).
    
    Phản hồi (Response):
    - answer (str): Câu trả lời từ AI.
    - intent (str): Ý định người dùng.
    - entities (list): Các thực thể AI tìm thấy.
    - exec_time (float): Tốc độ xử lý.
    """
    
    # 1. Khởi tạo lớp dịch vụ điều phối Chatbot
    chat_service = YHCTChatService(model_name=request.model)
    
    # 2. Thực thi quy trình GraphRAG (Phân tích -> Truy xuất -> Tổng hợp)
    result = await chat_service.get_ai_response(user_query=request.message)
    
    # 3. Xử lý lỗi dựa trên trạng thái trả về từ Service
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("answer")
        )
    
    if result.get("status") == "warning":
        # Trả về 200 kèm cảnh báo trong nội dung nếu AI không hiểu ý định
        return result

    # 4. Trả về kết quả cuối cùng khớp với Schema ChatResponse
    return result

@router.get("/health", tags=["Giám sát"])
async def check_chatbot_health():
    """
    Kiểm tra xem module Chatbot và NLU có đang hoạt động ổn định không.
    """
    try:
        from chatbot.llm_provider import ollama
        # Thử gọi danh sách model của Ollama để check kết nối
        ollama.list()
        return {"status": "healthy", "service": "Chatbot Logic Engine", "ai_connection": "OK"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.post("/clear-cache", tags=["Quản trị"])
async def clear_system_cache(x_api_key: str = Header(None)):
    """
    Xóa bộ nhớ đệm (Cache) của hệ thống NLU. 
    Yêu cầu quyền Admin (Laravel API Key).
    """
    if x_api_key != settings.LARAVEL_API_KEY:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện hành động này.")
        
    chat_service = YHCTChatService()
    chat_service.reset_cache()
    return {"message": "Đã làm sạch bộ nhớ đệm thành công."}    