"""
Module chứa các hàm tiện ích (Utility functions) dùng chung cho toàn bộ dự án.
Đảm bảo nguyên tắc DRY (Don't Repeat Yourself).
"""
import os
import re
import json
import unicodedata

# ==========================================================
# 1. XỬ LÝ CHUỖI VÀ ĐỊNH DANH (ID NORMALIZATION)
# ==========================================================

def remove_accents(s: str) -> str:
    """
    Loại bỏ dấu tiếng Việt an toàn (Bao gồm cả xử lý chữ Đ/đ).
    Gom từ các hàm: remove_accents, remove_accents_safe, remove_accents_lower.
    """
    if not s or not isinstance(s, str): 
        return ""
    s = s.replace("Đ", "D").replace("đ", "d")
    nkfd = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nkfd if not unicodedata.combining(c)])

def normalize_id(id_str: str) -> str:
    """
    Chuẩn hóa ID: Bỏ dấu, thay ký tự đặc biệt bằng gạch dưới, viết hoa toàn bộ.
    Tự động dọn dẹp các dấu gạch dưới thừa.
    """
    if not id_str: 
        return "UNKNOWN"
    
    clean_str = remove_accents(str(id_str))
    # Thay ký tự đặc biệt bằng gạch dưới
    clean_str = re.sub(r"[^a-zA-Z0-9_]", "_", clean_str)
    # Viết hoa và xóa gạch dưới 2 đầu
    res = clean_str.upper().strip("_")
    # Xử lý trùng lặp gạch dưới (VD: VI__THUOC -> VI_THUOC)
    return re.sub(r"_+", "_", res)

# ==========================================================
# 2. XỬ LÝ JSON (JSON REPAIR & PARSING)
# ==========================================================

def robust_json_load(file_path_or_content: str, is_path: bool = True):
    """
    Giải mã JSON bất chấp lỗi escape, dấu phẩy thừa, hoặc bọc trong Markdown ```json.
    Gom từ các hàm: robust_json_parse, robust_json_load, _clean_json_response.
    """
    if is_path:
        if not os.path.exists(file_path_or_content): 
            return None
        with open(file_path_or_content, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = str(file_path_or_content)
    
    if not content.strip(): 
        return None

    # 1. Quét Markdown tag nếu có
    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        content = match.group(1)
    else:
        # Bắt object hoặc array thuần
        match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
        if match:
            content = match.group(1)

    # 2. Dọn rác gạch chéo ngược và dấu phẩy thừa do LLM sinh ra
    content = re.sub(r'\\(?![nrtfb"\\/]|u[0-9a-fA-F]{4})', r'', content)
    content = re.sub(r',\s*([\]}])', r'\1', content)
    
    try:
        data = json.loads(content)
        # Trả về object đầu tiên nếu bị bọc trong list 1 phần tử
        return data[0] if isinstance(data, list) and len(data) == 1 else data
    except json.JSONDecodeError:
        try:
            # Nỗ lực cứu hộ cuối cùng
            content = content.replace('\\', '')
            return json.loads(content)
        except:
            return None

# ==========================================================
# 3. ĐỊNH DẠNG VĂN BẢN VÀ LATEX
# ==========================================================

def apply_latex_format(text: str) -> str:
    """
    Chuẩn hóa đơn vị đo lường và bọc LaTeX cho các con số.
    Gom từ các hàm: format_text_latex, wrap_latex.
    """
    if not isinstance(text, str):
        return text
        
    # Chuẩn hóa đơn vị
    text = re.sub(r'\b(gam|gram|gr)\b', 'g', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(kilogam|kilogram|kg)\b', 'kg', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(mililit|ml)\b', 'ml', text, flags=re.IGNORECASE)
    
    # Bọc LaTeX cho số + đơn vị đo lường (VD: 10g -> $10g$)
    pattern = r'(?<![\$\d])(\d+(?:[.,-]\d+)?)\s*(g|ml|mg|kg|%|°C|bát|phần|ống|muỗng)\b(?!\$)'
    text = re.sub(pattern, r'$\1\2$', text)
    
    # Chuẩn hóa escape dấu % (chỉ thêm \ nếu chưa có)
    text = text.replace('\\%', '%').replace('%', '\\%')
    return text

def clean_text(text: str) -> str:
    """Loại bỏ khoảng trắng thừa và ký tự xuống dòng rác."""
    if not isinstance(text, str): 
        return text
    text = text.replace("\\n", " ").replace("\n", " ")
    return re.sub(r'\s{2,}', ' ', text).strip()

# ==========================================================
# 4. HỖ TRỢ HỆ THỐNG FILE (FILE SYSTEM UTILS)
# ==========================================================

def get_page_number(file_path: str) -> int:
    """
    Trích xuất số trang từ tên file để sắp xếp chuẩn (Natural Sort).
    Dùng cho các vòng lặp xử lý file.
    """
    fname = os.path.basename(file_path)
    match = re.search(r'(\d+)', fname)
    return int(match.group(1)) if match else 999999