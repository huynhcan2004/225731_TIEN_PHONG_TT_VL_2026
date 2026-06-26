"""
Module: utils/project_tree.py
Chức năng: Hiển thị cấu trúc thư mục dự án YHCT Diamond dưới dạng sơ đồ cây (Tree) trên Terminal.
Nhiệm vụ:
- Liệt kê phân cấp các file và folder từ thư mục gốc.
- Loại trừ các thư mục môi trường và cache để báo cáo chuyên nghiệp.
"""

import os
import sys
from pathlib import Path

# Đảm bảo in được tiếng Việt có dấu trên console Windows không bị UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Danh sách các thư mục/file tên chính xác cần loại bỏ để sơ đồ đẹp và gọn
IGNORE_LIST = {
    'venv', '.git', '__pycache__', '.pytest_cache', 
    '.vscode', 'node_modules', '.ipynb_checkpoints',
    'debug_images'
}

def print_tree(directory, prefix=""):
    """
    Hàm đệ quy để vẽ sơ đồ cây thư mục.
    """
    try:
        items = sorted(
            [
                item for item in os.listdir(directory) 
                if item not in IGNORE_LIST and not item.endswith('.json') and not item.endswith('.txt') and not item.endswith('.log')
            ],
            key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower())
        )
    except Exception:
        return
    
    for i, item in enumerate(items):
        path = os.path.join(directory, item)
        is_last = (i == len(items) - 1)
        
        connector = "+-- " if is_last else "|-- "
        
        # In an toàn với ký tự Unicode
        try:
            print(f"{prefix}{connector}{item}")
        except UnicodeEncodeError:
            # Fallback nếu console vẫn không hỗ trợ UTF-8
            safe_item = item.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
            print(f"{prefix}{connector}{safe_item}")
        
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if is_last else "|   ")
            print_tree(path, new_prefix)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    project_name = os.path.basename(project_root)
    
    print(f"\n[PROJECT STRUCTURE]: {project_name}")
    print("=" * 50)
    print(".")
    print_tree(project_root)
    print("=" * 50)
    
    try:
        user_name = os.getlogin()
    except Exception:
        user_name = "User"
        
    print(f"\n[Success] So do duoc tao vao luc: {user_name} - 2026")
