# app/security/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
from app.models.base_db import db
from datetime import datetime, timedelta, timezone

# Đường dẫn để lấy token (dùng cho Swagger UI và Frontend)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- TIỆN ÍCH MẬT KHẨU ---
def hash_password(password: str) -> str:
    passwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(passwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        passwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(passwd_bytes, hashed_bytes)
    except Exception as e:
        print(f"[SECURITY ERROR] verify_password failed: {e}")
        return False

# --- QUẢN LÝ JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Tạo mã JWT có thời hạn. 
    Mặc định sử dụng ACCESS_TOKEN_EXPIRE_MINUTES từ .env
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Thêm claim 'exp' vào payload
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, # Sử dụng đúng tên biến trong .env
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

# --- DEPENDENCY: LẤY USER HIỆN TẠI ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Hàm gác cổng: Giải mã Token và trả về thông tin User từ SQLite.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Giải mã và kiểm tra chữ ký
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = int(payload.get("sub")) # Đảm bảo là số nguyên để khớp với SQLite
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Truy vấn thông tin từ Database Manager (SQLite)
    user = db.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user
# app/security/security.py

async def admin_required(current_user: dict = Depends(get_current_user)):
    # Kiểm tra xem user có quyền admin không
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Huynh không có quyền truy cập vào khu vực này!"
        )
    return current_user