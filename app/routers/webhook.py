from fastapi import APIRouter, Request, HTTPException, Header
from app.models.base_db import db
from app.config import settings
from app.routers.payment import is_transaction_recent
import re

router = APIRouter(prefix="/webhook", tags=["Fintech Webhook"])

@router.post("/sepay")
async def sepay_webhook(request: Request):
    """
    Xử lý thông báo biến động số dư tự động từ SePay.
    Tài liệu: https://docs.sepay.vn/tich-hop-webhook.html
    """
    # 1. Xác thực API Key từ Header Authorization nếu được cấu hình
    sepay_key = db.get_setting("sepay_api_key") or settings.SEPAY_API_KEY
    if sepay_key and ((sepay_key.startswith("'") and sepay_key.endswith("'")) or (sepay_key.startswith('"') and sepay_key.endswith('"'))):
        sepay_key = sepay_key[1:-1].strip()
    if sepay_key:
        auth_header = request.headers.get("Authorization")
        expected_auth = f"Bearer {sepay_key}"
        if auth_header != expected_auth:
            raise HTTPException(status_code=401, detail="Mã xác thực Webhook không hợp lệ")

    # 2. Lấy dữ liệu từ SePay gửi sang
    data = await request.json()
    
    # Lấy các trường quan trọng (SePay webhook sử dụng transferAmount và transactionDate)
    content = data.get("content", "")                                      # Nội dung chuyển khoản
    amount_in = float(data.get("transferAmount") or data.get("amount_in") or 0) # Số tiền khách chuyển
    tx_date = data.get("transactionDate", "")                              # Thời gian giao dịch (GMT+7)
    
    print(f"🔔 [Webhook] Nhận tín hiệu từ SePay: {content} - {amount_in} VND - Ngày GD: {tx_date}")

    # 3. Tìm mã HEX_ID trong nội dung bằng Regex
    # Pattern khớp với: NAPTOKEN<HEX_ID>
    pattern = rf"NAPTOKEN([0-9A-F]+)"
    match = re.search(pattern, content, re.IGNORECASE)
    
    if not match:
        return {"status": "error", "message": "Nội dung không chứa mã nạp hợp lệ"}

    hex_id = match.group(1).upper()
    
    # 4. Giải mã lấy ID hóa đơn gốc
    payment_id = db.decode_payment_id(hex_id)
    payment = db.get_payment_by_id(payment_id)

    if not payment:
        return {"status": "error", "message": f"Không tìm thấy hóa đơn cho mã {hex_id}"}

    # 5. Kiểm tra trạng thái và số tiền
    if payment['status'] == 'completed':
        return {"status": "success", "message": "Hóa đơn này đã được xử lý trước đó"}

    # Kiểm tra số tiền (Cho phép sai số nhỏ hoặc nạp dư thì vẫn cộng theo hóa đơn)
    if amount_in < payment['amount_vnd']:
        return {"status": "error", "message": "Số tiền chuyển khoản không đủ"}

    # Kiểm tra thời gian giao dịch tránh sử dụng giao dịch cũ từ trước
    if not is_transaction_recent(tx_date, payment['created_at']):
        print(f"⚠️ [Webhook Blocked] Giao dịch quá hạn hoặc lệch thời gian: GD {tx_date} so với đơn tạo lúc {payment['created_at']}")
        return {"status": "error", "message": "Giao dịch quá hạn hoặc thời gian không khớp"}

    # 6. THỰC THI CHỐT ĐƠN (Atomic Update)
    success = db.complete_payment_and_add_tokens(
        payment_id=payment_id,
        user_id=payment['user_id'],
        token_amount=payment['token_amount'],
        hex_id=hex_id
    )

    if success:
        return {"status": "success", "message": "Đã cộng token tự động"}
    else:
        raise HTTPException(status_code=500, detail="Lỗi cập nhật database")