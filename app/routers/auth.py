# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
from app.models.schemas import UserLogin, Token, UserOut
from app.models.base_db import db
from app.security.security import verify_password, create_access_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Xác thực & Bảo mật"])

@router.post("/login", response_model=Token)
async def login_standard(user_credentials: UserLogin):
    user = db.get_user_by_username(user_credentials.username)
    if not user or not verify_password(user_credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )
    
    access_token = create_access_token(data={"sub": str(user['id']), "email": user['email']})
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

# ==========================================
# ✨ HYBRID LOGIN: API ĐĂNG KÝ VÀ KIỂM TRA PHIÊN
# ==========================================

@router.post("/login-session")
async def create_login_session(session_id: str = Form(...)):
    """Khởi tạo một phiên chờ đăng nhập cho Mobile App (WebView)"""
    db.create_login_session(session_id)
    return {"status": "created"}

@router.get("/login-session/{session_id}")
async def get_login_session_status(session_id: str):
    """API để Frontend (React) Polling kiểm tra trạng thái đăng nhập"""
    res = db.check_and_consume_login_session(session_id)
    return res

# ==========================================
# 🌐 GOOGLE OAUTH 2.0 LOGIC
# ==========================================

@router.get("/google/login")
async def google_login(state: str = None):
    """
    Chuyển hướng người dùng sang Google để xác thực.
    Tham số 'state' chứa session_id được truyền vào nếu gọi từ Mobile Hybrid App.
    """
    state_param = f"&state={state}" if state else ""
    client_id = db.get_setting("google_client_id") or settings.GOOGLE_CLIENT_ID
    redirect_uri = db.get_setting("google_redirect_uri") or settings.GOOGLE_REDIRECT_URI
    
    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"{state_param}"
    )
    return RedirectResponse(url=google_url)

@router.get("/google/login/flutter")
async def google_login_flutter(session_id: str):
    """
    Chuyển hướng người dùng sang Google để xác thực dành riêng cho Mobile App.
    """
    return await google_login(state=session_id)


@router.get("/google/callback")
async def google_callback(code: str, state: str = None):
    """
    Xử lý mã trả về từ Google.
    Phân luồng: Lưu Token vào DB (Hybrid) hoặc chuyển hướng URL (Web thuần).
    """
    # 1. Trao đổi mã (code) lấy Access Token của Google
    client_id = db.get_setting("google_client_id") or settings.GOOGLE_CLIENT_ID
    client_secret = db.get_setting("google_client_secret") or settings.GOOGLE_CLIENT_SECRET
    redirect_uri = db.get_setting("google_redirect_uri") or settings.GOOGLE_REDIRECT_URI

    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        google_tokens = token_res.json()
        
        # 2. Lấy thông tin user từ Google
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_tokens['access_token']}"}
        )
        user_info = user_info_res.json() # Gồm email, sub (google_id), name, picture

    # 3. Đồng bộ vào Database (Nếu chưa có thì tạo mới)
    user = db.sync_google_user(user_info)
    
    # 4. Tạo JWT của hệ thống mình
    jwt_token = create_access_token(data={"sub": str(user['id']), "email": user['email']})
    
    # 5. Phân luồng xử lý (Hybrid vs Web Standard)
    if state:
        # Nếu có state (session_id) -> Đang chạy Hybrid Login (CCT trên App).
        # Cập nhật Token vào DB để Frontend lấy thông qua Polling.
        db.update_login_session_token(state, jwt_token)
        
        # Hiển thị trang báo thành công và tự động đóng trình duyệt (Chrome Custom Tab)
        html_content = """
        <html>
            <head>
                <title>Đăng nhập thành công</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body style="display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; background-color:#f0fdf4; margin: 0;">
                <div style="text-align:center; padding: 20px;">
                    <h2 style="color:#059669; font-size:24px; margin-bottom: 10px;">✅ Đăng nhập thành công!</h2>
                    <p style="color:#475569; font-size: 14px;">Hệ thống đã kết nối. Vui lòng đóng tab này để quay lại ứng dụng.</p>
                    <script>
                        // Cố gắng tự động đóng tab sau 1.5 giây
                        setTimeout(() => { window.close(); }, 1500);
                    </script>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    else:
        # Nếu không có state -> Đang chạy Web trên máy tính bình thường
        # Redirect thẳng về Frontend kèm Token
        # Trong google_callback (Web)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?access_token={jwt_token}") 
# ✨ Nên đổi tham số thành ?access_token={jwt_token} cho đồng bộ        

# ==========================================
# 👤 PROFILE LOGIC
# ==========================================

@router.get("/me", response_model=UserOut)
async def get_user_profile(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Endpoint lấy thông tin người dùng hiện tại.
    Chỉ cho phép truy cập nếu có Header: Authorization: Bearer <token>
    """
    if not current_user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    
    # Ép kiểu ID sang string để khớp với Schema hiện tại
    user_data = dict(current_user) 
    user_data['id'] = str(user_data['id']) 
    user_data['is_root_admin'] = db.is_root_admin(current_user['id'])
    
    # Chuyển đổi avatar_url thành URL tuyệt đối nếu là ảnh nội bộ
    avatar_url = user_data.get('avatar_url')
    if avatar_url and avatar_url.startswith('/uploads/'):
        base_url = str(request.base_url).rstrip("/")
        user_data['avatar_url'] = f"{base_url}{avatar_url}"
    
    return user_data

@router.post("/avatar", response_model=UserOut)
async def update_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Tải ảnh đại diện mới của người dùng lên và cập nhật thông tin trong CSDL.
    """
    import os
    import uuid
    import shutil
    
    if not current_user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPG, JPEG, PNG, GIF, WEBP."
        )
        
    uploads_dir = os.path.join("uploads", "avatars")
    os.makedirs(uploads_dir, exist_ok=True)
    
    unique_filename = f"avatar_{current_user['id']}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(uploads_dir, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi ghi file lên máy chủ: {str(e)}"
        )
        
    avatar_url = f"/uploads/avatars/{unique_filename}"
    
    # Xoá avatar cũ nếu là file nội bộ
    old_avatar = current_user.get("avatar_url")
    if old_avatar and "/uploads/avatars/" in old_avatar:
        old_filename = old_avatar.split("/uploads/avatars/")[-1]
        old_file_path = os.path.join(uploads_dir, old_filename)
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception:
                pass
                
    db.update_user_avatar(current_user["id"], avatar_url)
    
    # Lấy lại user mới
    updated_user = db.get_user_by_id(current_user["id"])
    if not updated_user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
    user_data = dict(updated_user)
    user_data['id'] = str(user_data['id'])
    user_data['is_root_admin'] = db.is_root_admin(updated_user['id'])
    
    # Chuyển đổi avatar_url thành URL tuyệt đối trước khi trả về
    base_url = str(request.base_url).rstrip("/")
    if user_data.get('avatar_url') and user_data['avatar_url'].startswith('/uploads/'):
        user_data['avatar_url'] = f"{base_url}{user_data['avatar_url']}"
        
    return user_data

@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_my_account(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Yêu cầu xóa tài khoản cá nhân. Hệ thống sẽ tạo yêu cầu xác nhận gửi tới email của Admin.
    """
    import secrets
    from datetime import datetime
    
    user_id = current_user.get("id")
    username = current_user.get("username", "Người dùng")
    email = current_user.get("email", "Không rõ email")
    
    # 1. Tạo một token ngẫu nhiên để xác nhận
    token = secrets.token_urlsafe(32)
    
    # 2. Lưu yêu cầu vào CSDL (hết hạn sau 24h)
    success = db.create_deletion_request(user_id, token, expires_in_hours=24)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo yêu cầu xóa tài khoản. Vui lòng thử lại sau."
        )
        
    # 3. Gửi email xác nhận đến ADMIN_EMAIL
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or db.get_setting("root_admin_email", "")
    
    if not admin_email:
        # Fallback lấy email admin đầu tiên từ CSDL
        conn = db._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            if row:
                admin_email = row['email']
        except Exception:
            pass
        finally:
            conn.close()
            
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USERNAME
    smtp_pass = settings.SMTP_PASSWORD
    
    email_sent = False
    
    if admin_email and smtp_user and smtp_pass:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Link xác nhận trỏ trực tiếp về API backend để Admin nhấp xác nhận
        base_url = str(request.base_url).rstrip('/')
        confirm_url = f"{base_url}/auth/confirm-deletion?token={token}"
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = admin_email
            msg['Subject'] = f"[YHCT Diamond] Yêu cầu xác nhận xóa tài khoản: {username}"
            
            body_text = f"""
Xin chào Admin,

Hệ thống YHCT Diamond nhận được yêu cầu xóa tài khoản của người dùng sau đây:

- Tên tài khoản: {username}
- Email đăng ký: {email}
- Thời gian yêu cầu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Thời gian hết hạn của liên kết: Trong vòng 24 giờ.

Nếu Admin đồng ý xóa tài khoản này cùng toàn bộ dữ liệu lịch sử chat, số dư và thông tin giao dịch liên quan, vui lòng nhấp vào liên kết xác nhận phê duyệt dưới đây:
----------------------------------------
{confirm_url}
----------------------------------------

Lưu ý: Hành động này sẽ xóa vĩnh viễn dữ liệu người dùng và không thể hoàn tác.

---
Tin nhắn này được gửi tự động từ máy chủ API YHCT Diamond.
"""
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [admin_email], msg.as_string())
            server.quit()
            email_sent = True
            print(f"[SMTP] Đã gửi mail xác thực xóa tài khoản của user {username} tới Admin {admin_email}")
        except Exception as e:
            print(f"[SMTP ERROR] Không thể gửi mail xác thực xóa tài khoản: {str(e)}")
            
    return {
        "status": "pending", 
        "message": "Yêu cầu xóa tài khoản đã được gửi đến Admin để phê duyệt. Tài khoản sẽ được xóa sau khi Admin xác nhận qua email.",
        "email_sent": email_sent
    }

@router.get("/confirm-deletion", response_class=HTMLResponse)
async def confirm_account_deletion(token: str):
    """
    Endpoint tiếp nhận xác thực từ link email Admin nhấp chọn.
    """
    res = db.verify_and_execute_deletion(token)
    
    is_success = res.get("status") == "success"
    status_title = "Xác nhận thành công" if is_success else "Xác nhận thất bại"
    status_icon = "✔️" if is_success else "❌"
    color_style = "color: #10b981;" if is_success else "color: #ef4444;"
    border_style = "border-color: rgba(16, 185, 129, 0.2);" if is_success else "border-color: rgba(239, 68, 68, 0.2);"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{status_title} - YHCT Diamond</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #030705;
                color: #f1f5f9;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }}
            .card {{
                background-color: #08150f;
                border: 1px solid rgba(16, 185, 129, 0.15);
                border-radius: 28px;
                padding: 40px 30px;
                max-width: 480px;
                width: 100%;
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
                {border_style}
            }}
            .icon {{
                font-size: 72px;
                margin-bottom: 20px;
                display: block;
            }}
            h1 {{
                font-size: 26px;
                font-weight: 800;
                margin-top: 0;
                margin-bottom: 16px;
                tracking-tight;
                {color_style}
            }}
            p {{
                font-size: 15px;
                line-height: 1.6;
                color: #94a3b8;
                margin-bottom: 36px;
                padding: 0 10px;
            }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
                color: white;
                text-decoration: none;
                padding: 14px 36px;
                border-radius: 14px;
                font-weight: bold;
                font-size: 14px;
                transition: all 0.2s ease;
                box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.2);
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px -3px rgba(16, 185, 129, 0.35);
            }}
            .btn:active {{
                transform: translateY(0);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="icon">{status_icon}</span>
            <h1>{status_title}</h1>
            <p>{res.get("message")}</p>
            <a href="http://localhost:5173" class="btn">Quay lại Trang chủ</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)