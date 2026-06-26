# Tạo file: tools/add_tokens.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.base_db import db

def give_free_tokens(user_id: int, amount: float):
    print(f"🔄 Đang bơm {amount} tokens cho User ID: {user_id}...")
    try:
        db.change_token_balance(
            user_id=user_id,
            amount=amount, # Số dương là nạp thêm
            description="Quà tặng từ Admin (Testing)",
            tx_type='in' # Giao dịch nạp vào
        )
        new_balance = db.get_user_balance(user_id)
        print(f"✅ Thành công! Số dư mới: {new_balance}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    # Huynh chỉ cần thay user_id và số lượng ở đây
    give_free_tokens(user_id=1, amount=1000000000000000.0)