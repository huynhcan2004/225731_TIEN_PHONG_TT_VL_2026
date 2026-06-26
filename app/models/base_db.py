"""
Module: app/models/base_db.py
Chức năng: Quản lý đa cơ sở dữ liệu (Hybrid Database Management).
Nhiệm vụ: 
- Điều phối kết nối Đồ thị tri thức (Neo4j) qua LangChain.
- Quản lý Cơ sở dữ liệu người dùng, xác thực, Fintech, Lịch sử Chat và Logs (SQLite).
- Triển khai các phương thức hỗ trợ Google OAuth và Billing Process (Polling & XOR).
"""

import sqlite3
import hashlib
import os
from typing import Any
from langchain_neo4j import Neo4jGraph
from app.config import settings
import time

class DatabaseManager:
    """
    Lớp điều phối tập trung (Database Orchestrator).
    Kết hợp Neo4j (Tri thức) và SQLite (Người dùng, Token, Lịch sử & Logs).
    """

    def __init__(self):
        """
        Khởi tạo và thiết lập các kết nối cơ sở dữ liệu.
        Tự động khởi tạo cấu trúc bảng SQLite nếu chưa tồn tại.
        """
        # 1. Kết nối Neo4j (Knowledge Graph)
        self.graph = self._connect_neo4j()
        # self._refresh_neo4j_schema()

        # 2. Kết nối SQLite (Auth, Billing, Chat & Logs)
        self.sqlite_path = settings.SQLITE_DB_PATH # Định nghĩa trong config.py
        self._init_sqlite_tables()

    # ==========================================================
    # 🌐 PHẦN 1: NEO4J (KNOWLEDGE GRAPH LOGIC)
    # ==========================================================

    def _connect_neo4j(self) -> Neo4jGraph:
        """Thực hiện kết nối tới cụm Neo4j."""
        try:
            db_name = settings.NEO4J_DB_NAME
            if not db_name or db_name == "neo4j":
                instance = Neo4jGraph(
                    url=settings.NEO4J_URI,
                    username=settings.NEO4J_USER,
                    password=settings.NEO4J_PWD,
                    refresh_schema=False
                )
            else:
                instance = Neo4jGraph(
                    url=settings.NEO4J_URI,
                    username=settings.NEO4J_USER,
                    password=settings.NEO4J_PWD,
                    database=db_name,
                    refresh_schema=False
                )
            print(f"[OK] [Neo4j] Ket noi thanh cong: {db_name or 'Default DB'}")
            return instance
        except Exception as e:
            print(f"[ERROR] [Neo4j Error] Loi ket noi: {str(e)}")
            return None

    def _refresh_neo4j_schema(self):
        """Làm mới cấu trúc đồ thị để LangChain nhận diện node/relation."""
        if self.graph:
            try:
                self.graph.refresh_schema()
                print("[REFRESH] [Neo4j] Da cap nhat Schema tri thuc.")
            except Exception as e:
                print(f"[WARNING] [Neo4j Warning] Khong the cap nhat schema: {e}")

    def query_graph(self, cypher: str, params: dict = None, retries=2):
        """Thực thi truy vấn Cypher với cơ chế Auto-Retry chống rớt mạng ngầm."""
        if not self.graph:
            return []
            
        for attempt in range(retries):
            try:
                # Ép Langchain gọi xuống Neo4j Driver mới nhất
                result = self.graph.query(cypher, params=params)
                return result
            except Exception as e:
                print(f"[WARNING] [Neo4j Query Warning] Lan thu {attempt + 1} that bai do mat ket noi. Dang thu lai... Loi: {e}")
                time.sleep(0.5) # Nghỉ nửa giây rồi giật lại kết nối
                
                # Nếu là lần thử cuối cùng mà vẫn lỗi thì mới báo lỗi thực sự
                if attempt == retries - 1:
                    print(f"[ERROR] [Neo4j Query Error] Da thu {retries} lan nhung van that bai: {e}")
        return []

    # ==========================================================
    # 🏦 PHẦN 2: SQLITE (AUTH, FINTECH, CHAT & LOGS LOGIC)
    # ==========================================================

    def _get_sqlite_conn(self):
        """Tạo kết nối SQLite mới (để tránh lỗi threading)."""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row # Cho phép truy cập dữ liệu theo tên cột
        return conn

    def _init_sqlite_tables(self):
        """Khởi tạo cấu trúc bảng SQLite cho người dùng, thanh toán, lịch sử và logs."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        # Bảng Users: Quản lý định danh và số dư
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                avatar_url TEXT,
                token_balance REAL DEFAULT 0.0,
                google_id TEXT,
                is_premium INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user', -- ✨ ĐÃ THÊM CỘT PHÂN QUYỀN ROLE
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bảng Token History: Nhật ký biến động số dư (Đối soát Fintech)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT, -- 'in' (nạp), 'out' (trừ)
                amount REAL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Bảng Chat History: Lưu vết hội thoại AI
        # ✨ ĐÃ CẬP NHẬT: Thêm cột session_id để gom nhóm tin nhắn
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                user_id INTEGER,
                role TEXT, -- 'user' hoặc 'assistant'
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Bảng User Logs: Lưu vết hành động (Audit Log)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT, -- 'ASK_AI', 'LOGIN', 'TOPUP'
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Bảng Payments: Quản lý hóa đơn nạp tiền
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount_vnd REAL,
                token_amount REAL,
                status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed'
                transaction_type TEXT DEFAULT 'sepay', -- 'sepay' (nạp qua SePay) hoặc 'admin' (admin điều chỉnh)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Thêm cột transaction_type cho database đã tồn tại trước đó
        try:
            cursor.execute("ALTER TABLE payments ADD COLUMN transaction_type TEXT DEFAULT 'sepay'")
        except sqlite3.OperationalError:
            pass
        
        
        # ✨ BẢNG MỚI: QUẢN LÝ PHIÊN ĐĂNG NHẬP HYBRID (CLOUD-SYNC POLLING)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_sessions (
                session_id TEXT PRIMARY KEY,
                token TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Bảng System Settings: Lưu cấu hình hệ thống động và API keys
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Bảng Support Messages: Lưu trữ yêu cầu hỗ trợ và liên hệ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                subject TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bảng Deletion Requests: Yêu cầu xóa tài khoản chờ Admin phê duyệt qua email
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deletion_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'expired'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Khởi tạo tài khoản Admin mặc định chatbotyhct / 123456789
        cursor.execute("SELECT * FROM users WHERE username = ?", ("chatbotyhct",))
        admin_user = cursor.fetchone()
        if not admin_user:
            import bcrypt
            password_hash = bcrypt.hashpw(b"123456789", bcrypt.gensalt()).decode("utf-8")
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, avatar_url, token_balance, google_id, role) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("chatbotyhct", "chatbotyhct@yhct-diamond.vn", password_hash, "", 999999.0, "", "admin")
            )
            print("[SQLITE] Khoi tao thanh cong tai khoan Admin Mac Dinh: chatbotyhct / 123456789")
        
        conn.commit()
        conn.close()
        print("[SQLITE] Da kiem tra va dong bo cau truc bang (Bao gom System Settings & Support Messages).")
        
        # Đồng bộ cấu hình từ DB ra RAM khi start app
        self._sync_system_settings()

    # --- CLOUD-SYNC POLLING LOGIC (HYBRID APP) ---

    def create_login_session(self, session_id: str):
        """Khởi tạo phiên chờ đăng nhập và dọn dẹp các phiên cũ (TTL 10 phút)"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # TTL & Tự động dọn dẹp: Xóa session quá 10 phút để tránh rác DB
            cursor.execute("DELETE FROM login_sessions WHERE created_at < datetime('now', '-10 minutes')")
            # Tạo session mới ở trạng thái chờ
            cursor.execute("INSERT INTO login_sessions (session_id, status) VALUES (?, 'pending')", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def update_login_session_token(self, session_id: str, token: str):
        """Lưu JWT Token vào phiên khi Google Auth thành công và đổi trạng thái"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE login_sessions SET token = ?, status = 'completed' WHERE session_id = ?", (token, session_id))
            conn.commit()
        finally:
            conn.close()

    def check_and_consume_login_session(self, session_id: str):
        """Lấy token và XÓA NGAY LẬP TỨC để đảm bảo One-time Use (Bảo mật cao nhất)"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT token, status FROM login_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row and row['status'] == 'completed':
                # One-time Use: Hủy session ngay sau khi lấy Token thành công
                cursor.execute("DELETE FROM login_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return {"status": "completed", "access_token": row['token']}
            return {"status": "pending"}
        finally:
            conn.close()

    # --- CHỨC NĂNG XÁC THỰC (AUTH & ROLES) ---

    def sync_google_user(self, google_info: dict) -> dict:
        """Đồng bộ hóa user từ Google OAuth 2.0."""
        email = google_info.get("email")
        google_id = google_info.get("sub")
        name = google_info.get("name")
        picture = google_info.get("picture")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        # Kiểm tra xem tài khoản này có trùng khớp với Email Admin cấu hình ở env/settings không để tự động thăng chức
        from app.config import settings
        admin_email = getattr(settings, "ADMIN_EMAIL", None) or self.get_setting("root_admin_email", "")
        is_admin_user = False
        if admin_email and email and email.lower().strip() == admin_email.lower().strip():
            is_admin_user = True

        role = 'admin' if is_admin_user else 'user'

        if user:
            # Cập nhật avatar, tên, google_id và tự thăng chức lên admin nếu khớp email admin
            if is_admin_user:
                cursor.execute(
                    "UPDATE users SET avatar_url = ?, username = ?, google_id = ?, role = 'admin' WHERE email = ?",
                    (picture, name, google_id, email)
                )
            else:
                cursor.execute(
                    "UPDATE users SET avatar_url = ?, username = ?, google_id = ? WHERE email = ?",
                    (picture, name, google_id, email)
                )
        else:
            # ✨ NẾU LÀ USER MỚI, MẶC ĐỊNH CHO ROLE LÀ 'user' (HOẶC 'admin' NẾU LÀ ROOT)
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, avatar_url, token_balance, google_id, role) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, email, "", picture, 1000.0, google_id, role)
            )
            cursor.execute(
                "INSERT INTO token_history (user_id, type, amount, description) VALUES (last_insert_rowid(), 'in', 1000.0, 'Quà chào mừng Google Login')",
            )

        conn.commit()
        # Query lại để lấy đầy đủ thông tin (bao gồm role) trả về Frontend
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        final_user = dict(cursor.fetchone())
        conn.close()
        return final_user

    def get_user_by_id(self, user_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
        
    def update_user_avatar(self, user_id: int, avatar_url: str) -> bool:
        """Cập nhật avatar_url cho user."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        conn.commit()
        conn.close()
        return True
        
    def is_admin(self, user_id: int) -> bool:
        """Kiểm tra nhanh xem user có phải admin không"""
        user = self.get_user_by_id(user_id)
        return user is not None and user.get('role') == 'admin'

    def is_root_admin(self, user_id: int) -> bool:
        """Kiểm tra xem user có phải admin gốc không"""
        user = self.get_user_by_id(user_id)
        if not user or user.get('role') != 'admin':
            return False
        
        # Lấy email của admin gốc từ cấu hình
        from app.config import settings
        admin_email = getattr(settings, "ADMIN_EMAIL", None) or self.get_setting("root_admin_email", "")
        if admin_email:
            return user.get('email') == admin_email
            
        # Nếu chưa cấu hình, mặc định admin đầu tiên được tạo trong hệ thống là admin gốc
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return user.get('email') == row['email']
        except Exception as e:
            print(f"[WARNING] [DB Warning] Loi is_root_admin: {e}")
        finally:
            conn.close()
            
        return False

    # --- CHỨC NĂNG TÍNH PHÍ (BILLING) ---

    def change_token_balance(self, user_id: int, amount: float, description: str, tx_type: str = 'out', force: bool = False):
        """
        Cập nhật số dư Token và ghi nhật ký giao dịch.
        tx_type: 'in' (nạp vào), 'out' (tiêu xài)
        """
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        try:
            val = float(amount)
            current_bal = 0.0
            
            # KIỂM TRA SỐ DƯ NẾU LÀ TRỪ TIỀN
            if tx_type == 'out':
                cursor.execute("SELECT token_balance FROM users WHERE id = ?", (user_id,))
                user_record = cursor.fetchone()
                current_bal = user_record['token_balance'] if user_record else 0.0
                if not force and current_bal < val:
                    try:
                        print(f"[ERROR] [Billing] User {user_id} khong du so du de thuc hien giao dich.")
                    except Exception:
                        pass
                    return False

            delta = val if tx_type == 'in' else -val
            
            # Nếu là trừ tiền bởi Admin (force=True), ta kẹp số dư tối thiểu về 0 (không để âm)
            if tx_type == 'out' and force:
                if current_bal - val < 0:
                    delta = -current_bal
                    val = current_bal # Ghi nhận số lượng thực tế đã trừ để khớp lịch sử
            
            # 1. Cập nhật số dư trong bảng users
            cursor.execute(
                "UPDATE users SET token_balance = token_balance + ? WHERE id = ?", 
                (delta, user_id)
            )
            
            # 2. Ghi vào lịch sử biến động số dư
            cursor.execute(
                "INSERT INTO token_history (user_id, type, amount, description) VALUES (?, ?, ?, ?)", 
                (user_id, tx_type, val, description)
            )
            
            conn.commit()
            try:
                print(f"[OK] [DB Success]: Da {'cong' if tx_type=='in' else 'tru'} {val} Token cho User {user_id}.")
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                print(f"[ERROR] [DB Error] Khong the thay doi so du: {e}")
            except Exception:
                pass
            return False
        finally:
            conn.close()

    def get_user_balance(self, user_id: int) -> float:
        user = self.get_user_by_id(user_id)
        return float(user['token_balance']) if user else 0.0

    # --- CHỨC NĂNG CHAT HISTORY CẬP NHẬT ---

    def save_chat_message(self, user_id: int, role: str, content: str, session_id: int = None):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # 1. Nếu chưa có session_id (tức là người dùng vừa bấm "+ Hội thoại mới")
            # Chúng ta sẽ tạo một ID phiên mới dựa trên thời gian thực (timestamp)
            if session_id is None:
                session_id = int(time.time())

            # 2. Lưu tin nhắn vào DB kèm theo session_id
            cursor.execute(
                "INSERT INTO chat_history (session_id, user_id, role, content) VALUES (?, ?, ?, ?)", 
                (session_id, user_id, role, content)
            )
            conn.commit()
            
            # 3. QUAN TRỌNG NHẤT: Trả về session_id để chatbot.py và Frontend biết đang chat ở luồng nào
            return session_id
            
        except Exception as e:
            print(f"[ERROR] Loi luu lich su chat vao DB: {e}")
            return None
        finally:
            conn.close()

    def get_recent_sessions(self, user_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Gom nhóm theo session_id, lấy câu hỏi đầu tiên của user làm tiêu đề (content)
            # Sắp xếp theo MAX(h.id) DESC để đẩy phiên hội thoại mới nhất lên đầu danh sách (tự đôn lên)
            cursor.execute("""
                SELECT h.session_id as id, 
                       (SELECT content FROM chat_history WHERE session_id = h.session_id AND role = 'user' ORDER BY id ASC LIMIT 1) as content
                FROM chat_history h
                WHERE h.user_id = ? AND h.session_id IS NOT NULL
                GROUP BY h.session_id
                ORDER BY MAX(h.id) DESC
                LIMIT 100
            """, (user_id,))
            rows = cursor.fetchall()
            
            # Trả về mảng dict chuẩn định dạng Frontend yêu cầu
            return [{"id": r[0], "content": r[1] or "Hội thoại không tiêu đề", "timestamp": str(r[0])} for r in rows if r[0] is not None]
        except Exception as e:
            print(f"[ERROR] Loi lay danh sach lich su chat: {e}")
            return []
        finally:
            conn.close()

    def get_conversation_detail(self, session_id: int, user_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Lấy toàn bộ các tin nhắn thuộc luồng session_id này, sắp xếp tăng dần theo id của tin nhắn
            cursor.execute("""
                SELECT role, content 
                FROM chat_history 
                WHERE session_id = ? AND user_id = ?
                ORDER BY id ASC
            """, (session_id, user_id))
            rows = cursor.fetchall()
            
            return [{"role": r[0], "content": r[1]} for r in rows]
        except Exception as e:
            print(f"[ERROR] Loi lay chi tiet cuoc hoi thoai cho session_id {session_id}: {e}")
            return []
        finally:
            conn.close()

    def delete_chat_session(self, session_id: int, user_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Xóa toàn bộ các bản ghi có chung mã session_id thuộc sở hữu của user_id này
            cursor.execute(
                "DELETE FROM chat_history WHERE session_id = ? AND user_id = ?", 
                (session_id, user_id)
            )
            conn.commit()
            print(f"[DELETE] [DB SUCCESS] Da xoa hoan toan phien chat co session_id: {session_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Loi khi thuc hien xoa phien chat {session_id}: {e}")
            return False
        finally:
            conn.close()

    # --- BẢO MẬT & THANH TOÁN (XOR OBFUSCATION) ---

    def encode_payment_id(self, p_id: int) -> str:
        """Mã hóa ID hóa đơn bằng XOR Key từ settings."""
        return hex(p_id ^ settings.SECRET_XOR_KEY)[2:].upper()

    def decode_payment_id(self, hex_str: str) -> int:
        """Giải mã chuỗi HEX về ID gốc."""
        try:
            return int(hex_str, 16) ^ settings.SECRET_XOR_KEY
        except:
            return 0

    def get_payment_by_id(self, payment_id: int):
        """Lấy thông tin hóa đơn nạp tiền."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_payment_status(self, payment_id: int, status: str):
        """Cập nhật trạng thái hóa đơn (pending -> completed/failed)."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
            conn.commit()
        finally:
            conn.close()

    def complete_payment_and_add_tokens(self, payment_id: int, user_id: int, token_amount: float, hex_id: str):
        """
        Hàm xử lý trọn gói: Cập nhật hóa đơn thành completed + Cộng tiền vào ví.
        Đảm bảo tính nhất quán dữ liệu (All or Nothing).
        """
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # 1. Kiểm tra xem đơn này đã hoàn thành chưa (tránh cộng tiền 2 lần)
            cursor.execute("SELECT status FROM payments WHERE id = ?", (payment_id,))
            order = cursor.fetchone()
            if order and order['status'] == 'completed':
                return True

            # 2. Cập nhật trạng thái hóa đơn
            cursor.execute("UPDATE payments SET status = 'completed' WHERE id = ?", (payment_id,))
            
            # 3. Cộng tiền vào ví user
            cursor.execute(
                "UPDATE users SET token_balance = token_balance + ? WHERE id = ?", 
                (float(token_amount), user_id)
            )
            
            # 4. Ghi log lịch sử token
            cursor.execute(
                "INSERT INTO token_history (user_id, type, amount, description) VALUES (?, ?, ?, ?)", 
                (user_id, 'in', float(token_amount), f"Nạp tiền thành công (Hóa đơn: {hex_id})")
            )
            
            conn.commit()
            print(f"[FINTECH] Da chot don {hex_id} thanh cong cho User {user_id}!")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] [Fintech Error] Loi khi chot don {hex_id}: {e}")
            return False
        finally:
            conn.close()

    def delete_user_and_all_data(self, user_id: int) -> bool:
        """Xóa hoàn toàn tài khoản người dùng và tất cả dữ liệu liên quan."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Xóa lịch sử chat
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            # Xóa lịch sử token
            cursor.execute("DELETE FROM token_history WHERE user_id = ?", (user_id,))
            # Xóa các giao dịch
            cursor.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
            # Xoa logs
            cursor.execute("DELETE FROM user_logs WHERE user_id = ?", (user_id,))
            # Xoa nguoi dung
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            print(f"[DELETE] [DB SUCCESS] Da xoa hoan toan user {user_id} va tat ca du lieu lien quan.")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Loi khi thuc hien xoa user {user_id}: {e}")
            return False
        finally:
            conn.close()

    def _sync_system_settings(self):
        """
        Đồng bộ cấu hình từ SQLite ra os.environ và settings (RAM).
        Nếu CSDL chưa có cấu hình, ta nạp các giá trị mặc định từ file .env.
        """
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Danh sách các settings và các keys nhạy cảm cần quản lý trong CSDL
            default_settings = {
                "active_model": getattr(settings, "MODEL_ID", "gemini-2.5-flash") or "gemini-2.5-flash",
                "temperature": "0.7",
                "system_prompt": "Bạn là chuyên gia Y học Cổ truyền giàu kinh nghiệm...",
                "gemini_api_key": getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", ""),
                "gemini_fallback_keys": os.getenv("GEMINI_FALLBACK_KEYS", ""),
                "openai_api_key": getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", ""),
                "openai_fallback_keys": os.getenv("OPENAI_FALLBACK_KEYS", ""),
                "tokens_per_1000_vnd": "10000",
                "cost_per_query": "1000.0",
                "root_admin_email": getattr(settings, "ADMIN_EMAIL", None) or os.getenv("ROOT_ADMIN_EMAIL", "") or os.getenv("ADMIN_EMAIL", ""),
                "qwen_api_url": os.getenv("QWEN_API_URL", "http://localhost:11434")
            }

            for key, def_val in default_settings.items():
                if def_val is None:
                    def_val = ""
                # Làm sạch dấu nháy đơn/kép thừa ở đầu và cuối do dotenv để lại
                def_val = str(def_val).strip()
                if (def_val.startswith("'") and def_val.endswith("'")) or (def_val.startswith('"') and def_val.endswith('"')):
                    def_val = def_val[1:-1].strip()

                cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row is None:
                    cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)", (key, def_val))
            conn.commit()

            # Load tất cả settings từ DB lên để đồng bộ ra RAM/Env
            cursor.execute("SELECT key, value FROM system_settings")
            rows = cursor.fetchall()
            for r in rows:
                k = r['key']
                v = r['value']
                
                # Đồng bộ ra os.environ (chữ hoa)
                env_key = k.upper()
                os.environ[env_key] = v
                
                # Đồng bộ ra settings của Pydantic (chữ hoa)
                if hasattr(settings, env_key):
                    if env_key == "TEMPERATURE":
                        try:
                            setattr(settings, env_key, float(v))
                        except ValueError:
                            setattr(settings, env_key, 0.7)
                    else:
                        setattr(settings, env_key, v)
                        
            print("[SETTINGS] Da dong bo cau hinh he thong tu SQLite vao RAM/os.environ.")
        except Exception as e:
            print(f"[WARNING] [Settings Warning] Khong the dong bo cau hinh he thong: {e}")
        finally:
            conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị cấu hình từ CSDL SQLite."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row is not None:
                val = row['value']
                # Tự động làm sạch nháy nếu có
                if isinstance(val, str):
                    val = val.strip()
                    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                        val = val[1:-1].strip()
                return val
            return default
        except Exception as e:
            print(f"[WARNING] [DB Warning] Loi get_setting {key}: {e}")
            return default
        finally:
            conn.close()

    def set_setting(self, key: str, value: Any):
        """Ghi giá trị cấu hình vào CSDL SQLite và đồng bộ ra RAM/Env."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            val_str = str(value).strip()
            # Làm sạch dấu nháy nếu truyền nháy vào
            if (val_str.startswith("'") and val_str.endswith("'")) or (val_str.startswith('"') and val_str.endswith('"')):
                val_str = val_str[1:-1].strip()

            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)", (key, val_str))
            else:
                cursor.execute("UPDATE system_settings SET value = ? WHERE key = ?", (val_str, key))
            conn.commit()
            
            # Đồng bộ ra os.environ
            env_key = key.upper()
            os.environ[env_key] = val_str
            
            # Đồng bộ ra settings
            if hasattr(settings, env_key):
                if env_key == "TEMPERATURE":
                    try:
                        setattr(settings, env_key, float(val_str))
                    except ValueError:
                        setattr(settings, env_key, 0.7)
                else:
                    setattr(settings, env_key, val_str)
        except Exception as e:
            print(f"[ERROR] [DB Error] Loi set_setting {key}: {e}")
        finally:
            conn.close()

    def get_user_by_username(self, username: str):
        """Lấy thông tin người dùng qua Username"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            return dict(user) if user else None
        except Exception as e:
            print(f"[ERROR] [DB Error] Loi get_user_by_username {username}: {e}")
            return None
        finally:
            conn.close()

    def save_support_message(self, name: str, email: str, subject: str, message: str) -> int:
        """Lưu tin nhắn hỗ trợ/liên hệ từ người dùng"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO support_messages (name, email, subject, message)
                VALUES (?, ?, ?, ?)
            """, (name, email, subject, message))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] [DB Error] Loi save_support_message: {e}")
            raise e
        finally:
            conn.close()

    def create_deletion_request(self, user_id: int, token: str, expires_in_hours: int = 24) -> bool:
        """Tạo yêu cầu xóa tài khoản chờ Admin duyệt (có hiệu lực trong 24h)"""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Hủy tất cả các yêu cầu pending cũ của user này
            cursor.execute("UPDATE deletion_requests SET status = 'expired' WHERE user_id = ? AND status = 'pending'", (user_id,))
            # Tính thời gian hết hạn
            cursor.execute(
                """INSERT INTO deletion_requests (user_id, token, expires_at) 
                   VALUES (?, ?, datetime('now', ?))""",
                (user_id, token, f"+{expires_in_hours} hours")
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] [DB Error] Loi create_deletion_request: {e}")
            return False
        finally:
            conn.close()

    def verify_and_execute_deletion(self, token: str) -> dict:
        """Kiểm tra token xóa tài khoản. Nếu hợp lệ, tiến hành xóa tài khoản và dữ liệu."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            # Tìm kiếm bản ghi yêu cầu xóa chưa duyệt và chưa hết hạn
            cursor.execute(
                """SELECT * FROM deletion_requests 
                   WHERE token = ? AND status = 'pending' AND expires_at > datetime('now')""",
                (token,)
            )
            req = cursor.fetchone()
            if not req:
                return {
                    "status": "failed", 
                    "message": "Yêu cầu xóa tài khoản không tồn tại, đã được phê duyệt trước đó hoặc liên kết xác nhận đã hết hạn (chỉ có hiệu lực trong 24 giờ)."
                }
            
            user_id = req['user_id']
            # Đóng kết nối hiện tại để tránh deadlock do SQLite locking khi gọi delete_user_and_all_data
            conn.close()
            
            # Thực thi xóa tài khoản
            success = self.delete_user_and_all_data(user_id)
            if not success:
                return {"status": "failed", "message": "Có lỗi hệ thống xảy ra trong quá trình thực hiện xóa tài khoản."}
            
            # Cập nhật trạng thái
            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE deletion_requests SET status = 'approved' WHERE token = ?", (token,))
            conn.commit()
            return {"status": "success", "message": "Tài khoản người dùng và toàn bộ dữ liệu liên quan đã được xóa vĩnh viễn thành công."}
        except Exception as e:
            print(f"[ERROR] [DB Error] Loi verify_and_execute_deletion: {e}")
            return {"status": "failed", "message": f"Lỗi hệ thống: {e}"}
        finally:
            try:
                conn.close()
            except:
                pass

# Khởi tạo đối tượng DB duy nhất cho toàn hệ thống
db = DatabaseManager()