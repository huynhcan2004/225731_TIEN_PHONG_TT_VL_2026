import sqlite3
import os

# Đường dẫn database - Huynh kiểm tra xem file .db nằm ở đâu nhé
DB_PATH = 'yhct_database.db' 

def upgrade_and_fix_admin():
    if not os.path.exists(DB_PATH):
        print(f"❌ Không tìm thấy file {DB_PATH}. Huynh hãy chạy Backend để nó tạo DB trước đã!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Thêm cột 'role' vào bảng users (Nếu chưa có)
        print("🛠 Đang kiểm tra cấu trúc bảng...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            print("✅ Đã thêm cột 'role' thành công.")
        except sqlite3.OperationalError:
            print("ℹ️ Cột 'role' đã tồn tại, bỏ qua bước thêm cột.")

        # 2. Liệt kê danh sách email để huynh chọn (Phòng trường hợp gõ sai email)
        cursor.execute("SELECT id, email, username FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("⚠️ Database hiện chưa có người dùng nào. Huynh hãy mở web và đăng nhập Google 1 lần nhé!")
            return

        print("\n--- Danh sách người dùng trong hệ thống ---")
        for u in users:
            print(f"ID: {u[0]} | Email: {u[1]} | Tên: {u[2]}")
        
        # 3. Yêu cầu nhập email muốn lên Admin
        email_to_admin = input("\n👉 Nhập chính xác Email huynh muốn cấp quyền ADMIN: ").strip()

        # 4. Thực hiện nâng cấp
        cursor.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email_to_admin,))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"\n🎉 THÀNH CÔNG! Tài khoản {email_to_admin} hiện đã là ADMIN.")
            print("🚀 Bây giờ huynh có thể vào link http://localhost:5173/admin rồi đó!")
        else:
            print(f"\n❌ Lỗi: Không tìm thấy email '{email_to_admin}' trong danh sách trên.")

    except Exception as e:
        print(f"❌ Lỗi phát sinh: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_and_fix_admin()