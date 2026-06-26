import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.base_db import db
from app.config import settings
from app.security.security import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/payment", tags=["Thanh toán"])

def is_transaction_recent(tx_date_str: str, payment_created_str: str) -> bool:
    """
    Kiểm tra xem giao dịch ngân hàng có xảy ra gần thời điểm tạo hóa đơn hay không.
    - tx_date_str: Định dạng 'YYYY-MM-DD HH:MM:SS' (Múi giờ GMT+7 - Việt Nam)
    - payment_created_str: Định dạng 'YYYY-MM-DD HH:MM:SS' (Múi giờ UTC - SQLite)
    Chấp nhận giao dịch diễn ra từ 10 phút trước đến 24 giờ sau khi tạo hóa đơn.
    """
    if not tx_date_str or not payment_created_str:
        return False
    try:
        # 1. Parse SePay transaction date (GMT+7)
        tx_dt = datetime.strptime(tx_date_str, "%Y-%m-%d %H:%M:%S")
        tx_dt = tx_dt.replace(tzinfo=timezone(timedelta(hours=7)))
        tx_epoch = tx_dt.timestamp()

        # 2. Parse SQLite payment created_at (UTC)
        pay_dt = datetime.strptime(payment_created_str, "%Y-%m-%d %H:%M:%S")
        pay_dt = pay_dt.replace(tzinfo=timezone.utc)
        pay_epoch = pay_dt.timestamp()

        # Cho phép sai số clock drift 10 phút trước, và thời gian hoàn tất đơn tối đa 24 giờ
        time_diff = tx_epoch - pay_epoch
        return -600 <= time_diff <= 86400
    except Exception as e:
        print(f"⚠️ [Time Check Error] Lỗi đối soát thời gian: {e}")
        return False

@router.get("/rate")
async def get_payment_rate():
    """Lấy tỷ lệ quy đổi token hiện tại (Số token ứng với 1.000 VNĐ)."""
    try:
        tokens_per_1000_vnd = int(db.get_setting("tokens_per_1000_vnd", "10000"))
    except ValueError:
        tokens_per_1000_vnd = 10000
    return {"tokens_per_1000_vnd": tokens_per_1000_vnd}

@router.post("/create")
async def create_payment(
    amount_k: int = Query(..., description="Số tiền nạp tính bằng nghìn VNĐ (2, 20, 50, 100)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Bước 1: Tạo bản ghi thanh toán và trả về thông tin QR cho khách.
    Tỷ lệ quy đổi: Lấy động từ CSDL (Mặc định 1.000đ = 10.000 Token).
    """
    try:
        tokens_per_1000_vnd = float(db.get_setting("tokens_per_1000_vnd", "10000"))
    except ValueError:
        tokens_per_1000_vnd = 10000.0

    amount_vnd = float(amount_k * 1000)
    token_amount = float(amount_k * tokens_per_1000_vnd) 

    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # 1. Lưu bản ghi nạp tiền vào bảng payments với trạng thái 'pending'
        cursor.execute(
            "INSERT INTO payments (user_id, amount_vnd, token_amount, status) VALUES (?, ?, ?, ?)",
            (current_user['id'], amount_vnd, token_amount, 'pending')
        )
        payment_id = cursor.lastrowid
        conn.commit()

        # 2. Mã hóa ID thành chuỗi HEX để làm nội dung chuyển khoản bảo mật
        hex_id = db.encode_payment_id(payment_id)
        
        # Nội dung chuyển khoản chuẩn: VD: YHCT_CHATBOTNAPTOKEN5EAEF
        payment_content = f"{settings.NAME_WEB}NAPTOKEN{hex_id}"
        
        # 3. Tạo URL mã QR động qua VietQR (MB Bank)
        qr_url = f"https://img.vietqr.io/image/mbbank-0773470204-compact2.png?amount={int(amount_vnd)}&addInfo={payment_content}"

        return {
            "hex_id": hex_id,
            "content": payment_content,
            "amount": amount_vnd,
            "qr_url": qr_url
        }
    finally:
        conn.close()

@router.get("/status/{hex_id}")
async def check_status(hex_id: str, current_user: dict = Depends(get_current_user)):
    """
    Bước 2 (Polling): Kiểm tra trạng thái giao dịch từ SePay V2.
    Nếu khớp nội dung, thời gian và số tiền, tiến hành cộng Token và chốt đơn.
    """
    # 1. Giải mã hex_id để lấy payment_id gốc trong database
    payment_id = db.decode_payment_id(hex_id)
    payment = db.get_payment_by_id(payment_id)

    # Kiểm tra tính hợp lệ của hóa đơn
    if not payment or payment['user_id'] != current_user['id']:
        raise HTTPException(status_code=404, detail="Hóa đơn không hợp lệ")

    # Nếu hóa đơn đã hoàn thành từ trước đó, trả về ngay để Frontend dừng polling
    if payment['status'] == 'completed':
        return {"status": "completed"}

    try:
        async with httpx.AsyncClient() as client:
            # 2. Gọi API SePay V2 lấy danh sách giao dịch mới nhất
            sepay_key = db.get_setting("sepay_api_key") or settings.SEPAY_API_KEY
            if sepay_key and ((sepay_key.startswith("'") and sepay_key.endswith("'")) or (sepay_key.startswith('"') and sepay_key.endswith('"'))):
                sepay_key = sepay_key[1:-1].strip()
            headers = {
                "Authorization": f"Bearer {sepay_key}",
                "Content-Type": "application/json"
            }
            url = "https://userapi.sepay.vn/v2/transactions"
            
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"⚠️ SePay V2 Error: {response.status_code}")
                return {"status": "pending"}
            
            result = response.json()
            # Theo tài liệu SePay V2, danh sách giao dịch nằm trong trường 'data'
            transactions = result.get('data', [])

        print(f"🔍 Đang đối soát đơn {hex_id} với {len(transactions)} giao dịch gần nhất từ SePay...")

        # Định dạng tìm kiếm nội dung: 'NAPTOKEN' + HEX_ID (Không khớp nếu đằng sau là ký tự Hex khác)
        pattern = rf"NAPTOKEN{hex_id}(?![0-9A-F])"

        for tx in transactions:
            # Lấy nội dung, số tiền thực tế khách đã chuyển (amount_in), và ngày giao dịch
            content = tx.get('transaction_content', '')
            amount_in = float(tx.get('amount_in', 0))
            tx_date = tx.get('transaction_date', '')

            # 3. Đối soát: Khớp nội dung (Regex) VÀ Khớp số tiền (>= số tiền yêu cầu) VÀ Khớp thời gian gần đây
            if re.search(pattern, content, re.IGNORECASE) and amount_in >= payment['amount_vnd']:
                if is_transaction_recent(tx_date, payment['created_at']):
                    print(f"✅ KHỚP GIAO DỊCH! Nội dung: {content} - Số tiền: {amount_in} - Ngày GD: {tx_date}")
                    
                    # 4. THỰC THI GIAO DỊCH (ATOMIC): Cộng Token + Chốt hóa đơn trong cùng 1 Transaction
                    success = db.complete_payment_and_add_tokens(
                        payment_id=payment_id,
                        user_id=payment['user_id'],
                        token_amount=payment['token_amount'],
                        hex_id=hex_id
                    )
                    
                    if success:
                        print(f"🚀 [Success] Đã cộng {payment['token_amount']} Token cho User ID {current_user['id']}")
                        return {"status": "completed"}
                    else:
                        print(f"❌ [Error] Lỗi khi thực thi cập nhật số dư vào Database.")
                else:
                    print(f"⚠️ Phát hiện giao dịch khớp nội dung {content} nhưng quá hạn thời gian: GD {tx_date} so với đơn tạo lúc {payment['created_at']}")

    except Exception as e:
        print(f"❌ Lỗi hệ thống khi xử lý SePay V2: {e}")
    
    # Nếu chưa tìm thấy giao dịch khớp, tiếp tục chờ
    return {"status": "pending"}