from jose import jwt
from app.config import settings

def create_access_token(data: dict):
    """
    Tạo mã JWT dựa trên dữ liệu người dùng, 
    sử dụng SECRET_KEY và ALGORITHM từ file .env
    """
    to_encode = data.copy()
    # Ký tên vào Token bằng chìa khóa bí mật
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt