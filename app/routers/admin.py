"""
Module: app/routers/admin.py
Chức năng: Quản trị hệ thống (Admin Panel).
Nhiệm vụ:
- Thống kê tổng quan (Dashboard Stats).
- Quản lý tài khoản người dùng (Account Management).
- Đối soát giao dịch nạp tiền SePay (Finance Reconciliation).
- Cấu hình tham số AI & GraphRAG (AI Configuration).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, UploadFile, File
from app.models.base_db import db
from app.security.security import get_current_user
from typing import List, Dict, Any
import os
import uuid
import shutil
from dotenv import set_key
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["Quản trị Hệ thống"])

# --- LỚP BẢO VỆ ADMIN (DEPENDENCY) ---

async def admin_required(current_user: dict = Depends(get_current_user)):
    """
    Rào chắn bảo mật: Chỉ cho phép tài khoản có role 'admin' đi qua.
    Dựa trên cột role đã thêm vào SQLite.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Huynh không có quyền truy cập vào khu vực quản trị!"
        )
    return current_user

async def root_admin_required(current_user: dict = Depends(get_current_user)):
    """
    Rào chắn bảo mật: Chỉ cho phép tài khoản có quyền admin và là Admin gốc (Root Admin).
    """
    if current_user.get("role") != "admin" or not db.is_root_admin(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Admin gốc mới có quyền thực hiện hành động này!"
        )
    return current_user

# --- 1. THỐNG KÊ TỔNG QUAN (DASHBOARD) ---

@router.get("/dashboard-stats")
async def get_dashboard_stats(days: int = 7, admin: dict = Depends(admin_required)):
    """Lấy số liệu tổng hợp cho trang chủ Admin Dashboard."""
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    
    try:
        # 1.1 Tổng doanh thu từ các đơn SePay thành công
        cursor.execute("SELECT SUM(amount_vnd) as total_rev FROM payments WHERE status = 'completed'")
        rev_row = cursor.fetchone()
        total_revenue = rev_row['total_rev'] if rev_row and rev_row['total_rev'] else 0
        
        # 1.2 Tổng số người dùng
        cursor.execute("SELECT COUNT(id) as total_users FROM users")
        total_users = cursor.fetchone()['total_users']
        
        # 1.3 Tổng lượt truy vấn AI (Chat history)
        cursor.execute("SELECT COUNT(id) as total_queries FROM chat_history WHERE role = 'user'")
        total_queries = cursor.fetchone()['total_queries']
        
        # 1.4 Lấy 5 giao dịch SePay mới nhất để hiển thị nhanh
        cursor.execute("""
            SELECT id, user_id, amount_vnd, token_amount, status, transaction_type, created_at 
            FROM payments 
            ORDER BY created_at DESC LIMIT 5
        """)
        recent_transactions = [dict(row) for row in cursor.fetchall()]
        
        # 1.5 Thống kê truy vấn AI theo từng ngày trong khoảng `days` ngày qua
        import datetime
        today_utc = datetime.datetime.utcnow().date()
        days_list = [today_utc - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]
        days_str = [d.strftime("%Y-%m-%d") for d in days_list]
        
        queries_by_day = {d: 0 for d in days_str}
        
        # Truy vấn CSDL để lấy số lượng chat_history của 'user' theo ngày
        if db.is_postgres:
            cursor.execute("""
                SELECT timestamp::date as date_val, COUNT(id) as cnt 
                FROM chat_history 
                WHERE role = 'user' AND timestamp >= CURRENT_DATE + CAST(%s AS INTERVAL)
                GROUP BY timestamp::date
            """, (f"-{days} days",))
        else:
            cursor.execute("""
                SELECT DATE(timestamp) as date_val, COUNT(id) as cnt 
                FROM chat_history 
                WHERE role = 'user' AND timestamp >= DATE('now', ?)
                GROUP BY DATE(timestamp)
            """, (f"-{days} days",))

        
        for row in cursor.fetchall():
            d_val = row['date_val']
            if d_val in queries_by_day:
                queries_by_day[d_val] = row['cnt']
                
        daily_queries = [{"date": d, "count": queries_by_day[d]} for d in days_str]
        
    finally:
        conn.close()
        
    # 1.6 Truy vấn Neo4j: Đếm tổng số thực thể tri thức (Nodes)
    neo_result = db.query_graph("MATCH (n) RETURN count(n) AS total_nodes")
    total_nodes = neo_result[0]['total_nodes'] if neo_result else 0

    return {
        "total_revenue": total_revenue,
        "total_users": total_users,
        "total_queries": total_queries,
        "total_nodes": total_nodes,
        "recent_transactions": recent_transactions,
        "daily_queries": daily_queries
    }

# --- 2. QUẢN LÝ TÀI KHOẢN (USER MANAGEMENT) ---

@router.get("/users", response_model=List[Dict[str, Any]])
async def get_all_users(admin: dict = Depends(admin_required)):
    """Danh sách toàn bộ nhân sĩ trong hệ thống."""
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, username, email, role, token_balance, is_premium, created_at 
            FROM users 
            ORDER BY created_at DESC
        """)
        users_list = [dict(row) for row in cursor.fetchall()]
        
        # Tối ưu hóa: Lấy email admin gốc một lần duy nhất từ cấu hình/cache
        from app.config import settings
        admin_email = getattr(settings, "ADMIN_EMAIL", None) or db.get_setting("root_admin_email", "")
        if not admin_email:
            cursor.execute("SELECT email FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            admin_email = row['email'] if row else ""
            
        for u in users_list:
            u["is_root_admin"] = (u["role"] == "admin" and u["email"] == admin_email)
            
        return users_list
    finally:
        conn.close()


@router.post("/users/{user_id}/change-role")
async def change_user_role(user_id: int, new_role: str = Body(..., embed=True), admin: dict = Depends(admin_required)):
    """Cấp quyền hoặc hạ quyền người dùng (admin/user)."""
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return {"message": f"Đã cập nhật vai trò của User {user_id} thành {new_role}"}
    finally:
        conn.close()

@router.post("/users/role-by-email")
async def change_role_by_email(
    payload: dict = Body(...),
    admin: dict = Depends(root_admin_required)
):
    """Cấp/Hạ quyền admin của tài khoản khác thông qua Email (Chỉ dành cho Admin gốc)."""
    email = payload.get("email", "").strip()
    role = payload.get("role", "user").strip()
    
    if not email:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp email.")
    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ. Chỉ chấp nhận 'admin' hoặc 'user'.")
        
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy tài khoản với email '{email}'")
        
        user_id = user_row["id"]
        # Không được tự hạ quyền của chính mình (admin gốc)
        if user_id == admin["id"] and role != "admin":
            raise HTTPException(status_code=400, detail="Không thể tự hạ quyền của chính mình!")
            
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        return {"status": "success", "message": f"Đã cập nhật vai trò của {email} thành {role}."}
    finally:
        conn.close()

@router.post("/users/add-tokens")
async def add_tokens_by_email(
    payload: dict = Body(...),
    admin: dict = Depends(root_admin_required)
):
    """Nạp hoặc trừ token của tài khoản khác thông qua Email (Chỉ dành cho Admin gốc)."""
    email = payload.get("email", "").strip()
    try:
        tokens = float(payload.get("tokens", 0.0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Số lượng token không hợp lệ.")
        
    if not email:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp email.")
        
    # 1. Truy vấn email để lấy user_id và đóng kết nối ngay
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy tài khoản với email '{email}'")
        user_id = user_row["id"]
    finally:
        conn.close()
        
    # 2. Thực hiện đổi số dư trên một kết nối SQLite độc lập của change_token_balance
    success = db.change_token_balance(
        user_id=user_id,
        amount=abs(tokens),
        description="Admin gốc điều chỉnh token",
        tx_type='in' if tokens >= 0 else 'out',
        force=True
    )
    if not success:
        raise HTTPException(status_code=500, detail="Lỗi thay đổi số dư tài khoản.")
        
    # 3. Ghi log lịch sử giao dịch vào payments trên một kết nối SQLite độc lập mới
    conn_write = db._get_sqlite_conn()
    cursor_write = conn_write.cursor()
    try:
        cursor_write.execute("""
            INSERT INTO payments (user_id, amount_vnd, token_amount, status, transaction_type)
            VALUES (?, 0.0, ?, 'completed', 'admin')
        """, (user_id, tokens))
        conn_write.commit()
    except Exception as e:
        try:
            print(f"[ERROR] Khong the ghi log payment admin: {e}")
        except Exception:
            pass
    finally:
        conn_write.close()
            
    return {"status": "success", "message": f"Đã cộng/trừ {tokens} Token cho tài khoản {email}."}

# --- 3. ĐỐI SOÁT GIAO DỊCH (FINANCE) ---

@router.get("/payments")
async def get_all_payments(admin: dict = Depends(admin_required)):
    """Lịch sử nạp tiền chi tiết để đối soát với ngân hàng qua SePay."""
    conn = db._get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # Join bảng payments với users để hiện Email người nạp
        cursor.execute("""
            SELECT p.*, u.email as user_email 
            FROM payments p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# --- 4. CẤU HÌNH AI & GRAPHRAG (AI CONFIG) ---

@router.get("/settings")
async def get_ai_settings(admin: dict = Depends(admin_required)):
    """Lấy cấu hình hiện tại của hệ thống AI từ SQLite CSDL."""
    fallback_keys_str = db.get_setting("gemini_fallback_keys", "")
    
    # Sửa lỗi bóc tách API Key phụ (loại bỏ dấu nháy đơn/kép)
    fallback_keys = []
    if fallback_keys_str:
        for k in fallback_keys_str.split(","):
            k_clean = k.strip()
            if (k_clean.startswith("'") and k_clean.endswith("'")) or (k_clean.startswith('"') and k_clean.endswith('"')):
                k_clean = k_clean[1:-1].strip()
            if k_clean:
                fallback_keys.append(k_clean)

    openai_fallback_keys_str = db.get_setting("openai_fallback_keys", "")
    openai_fallback_keys = []
    if openai_fallback_keys_str:
        for k in openai_fallback_keys_str.split(","):
            k_clean = k.strip()
            if (k_clean.startswith("'") and k_clean.endswith("'")) or (k_clean.startswith('"') and k_clean.endswith('"')):
                k_clean = k_clean[1:-1].strip()
            if k_clean:
                openai_fallback_keys.append(k_clean)

    # Lấy nhiệt độ (temperature) dạng float
    try:
        temp = float(db.get_setting("temperature", "0.7"))
    except ValueError:
        temp = 0.7

    try:
        cost_per_query = float(db.get_setting("cost_per_query", "1000.0"))
    except ValueError:
        cost_per_query = 1000.0

    try:
        tokens_rate = int(db.get_setting("tokens_per_1000_vnd", "10000"))
    except ValueError:
        tokens_rate = 10000

    root_admin_email = db.get_setting("root_admin_email", "")

    return {
        "active_model": db.get_setting("active_model", "gemini-2.5-flash"),
        "temperature": temp,
        "graph_depth": 2,
        "max_tokens": 2048,
        "system_prompt": db.get_setting("system_prompt", "Bạn là chuyên gia Y học Cổ truyền giàu kinh nghiệm..."),
        "neo4j_status": "Connected",
        "gemini_api_key": db.get_setting("gemini_api_key", ""),
        "gemini_fallback_keys": fallback_keys,
        "openai_api_key": db.get_setting("openai_api_key", ""),
        "openai_fallback_keys": openai_fallback_keys,
        "tokens_per_1000_vnd": tokens_rate,
        "cost_per_query": cost_per_query,
        "root_admin_email": root_admin_email,
        "qwen_api_url": db.get_setting("qwen_api_url", "http://localhost:11434"),
        "site_title": db.get_setting("site_title", "Chatbot YHCT Diamond"),
        "site_description": db.get_setting("site_description", "Hệ thống tra cứu vị thuốc và bài thuốc Y học cổ truyền dựa trên Đồ thị tri thức"),
        "site_keywords": db.get_setting("site_keywords", "YHCT, chatbot, AI, đồ thị tri thức, đông y"),
        "site_logo": db.get_setting("site_logo", "")
    }

@router.post("/settings/update")
async def update_ai_settings(new_settings: dict, admin: dict = Depends(admin_required)):
    """Cập nhật các tham số vận hành AI trực tiếp vào SQLite CSDL."""
    
    if "active_model" in new_settings:
        db.set_setting("active_model", new_settings["active_model"])
        
    if "temperature" in new_settings:
        db.set_setting("temperature", str(new_settings["temperature"]))
        
    if "system_prompt" in new_settings:
        db.set_setting("system_prompt", new_settings["system_prompt"])

    if "gemini_api_key" in new_settings:
        db.set_setting("gemini_api_key", new_settings["gemini_api_key"])
            
    if "gemini_fallback_keys" in new_settings:
        # Làm sạch và lưu các key phụ dưới dạng danh sách ngăn cách bởi dấu phẩy
        cleaned_keys = []
        for k in new_settings["gemini_fallback_keys"]:
            k_clean = k.strip()
            if (k_clean.startswith("'") and k_clean.endswith("'")) or (k_clean.startswith('"') and k_clean.endswith('"')):
                k_clean = k_clean[1:-1].strip()
            if k_clean:
                cleaned_keys.append(k_clean)
        fallback_keys_str = ",".join(cleaned_keys)
        db.set_setting("gemini_fallback_keys", fallback_keys_str)
            
    if "openai_api_key" in new_settings:
        db.set_setting("openai_api_key", new_settings["openai_api_key"])

    if "openai_fallback_keys" in new_settings:
        cleaned_keys = []
        for k in new_settings["openai_fallback_keys"]:
            k_clean = k.strip()
            if (k_clean.startswith("'") and k_clean.endswith("'")) or (k_clean.startswith('"') and k_clean.endswith('"')):
                k_clean = k_clean[1:-1].strip()
            if k_clean:
                cleaned_keys.append(k_clean)
        fallback_keys_str = ",".join(cleaned_keys)
        db.set_setting("openai_fallback_keys", fallback_keys_str)

    if "tokens_per_1000_vnd" in new_settings:
        db.set_setting("tokens_per_1000_vnd", str(new_settings["tokens_per_1000_vnd"]))

    if "cost_per_query" in new_settings:
        db.set_setting("cost_per_query", str(new_settings["cost_per_query"]))

    if "root_admin_email" in new_settings:
        db.set_setting("root_admin_email", str(new_settings["root_admin_email"]))
            
    if "qwen_api_url" in new_settings:
        db.set_setting("qwen_api_url", new_settings["qwen_api_url"])
        
    if "seo" in new_settings:
        seo_data = new_settings["seo"]
        if "site_title" in seo_data:
            db.set_setting("site_title", seo_data["site_title"])
        if "description" in seo_data:
            db.set_setting("site_description", seo_data["description"])
        if "keywords" in seo_data:
            db.set_setting("site_keywords", seo_data["keywords"])
        if "site_logo" in seo_data:
            db.set_setting("site_logo", seo_data["site_logo"])
            
    try:
        print(f"[Admin] Da cap nhat cau hinh vao SQLite CSDL.")
    except Exception:
        pass
    return {"status": "success", "message": "Đã lưu API Key và áp dụng cấu hình AI mới vào CSDL."}

@router.post("/docs/{page_id}", summary="Cập nhật nội dung trang tài liệu công khai")
async def update_doc(page_id: str, payload: dict = Body(...), admin: dict = Depends(admin_required)):
    import json
    if "content" not in payload:
        raise HTTPException(status_code=400, detail="Thiếu trường content")
    
    content = payload["content"]
    # Nếu là support, contact hoặc sidebar, ta convert về chuỗi JSON để lưu trữ đồng bộ
    if page_id in ["support", "contact", "sidebar"]:
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
            
    db.set_setting("doc_" + page_id, content)
    return {"status": "success", "message": f"Đã cập nhật nội dung trang {page_id} thành công."}

@router.post("/upload-logo", summary="Tải ảnh logo lên hệ thống")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(admin_required)
):
    """Tải ảnh logo từ máy tính của admin lên backend và lưu trữ tĩnh."""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPG, JPEG, PNG, GIF, WEBP, SVG."
        )
    
    unique_filename = f"logo_{uuid.uuid4().hex}{file_ext}"
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi ghi file lên máy chủ: {str(e)}"
        )
    
    base_url = str(request.base_url).rstrip("/")
    logo_url = f"{base_url}/uploads/{unique_filename}"
    
    return {
        "status": "success",
        "logo_url": logo_url
    }