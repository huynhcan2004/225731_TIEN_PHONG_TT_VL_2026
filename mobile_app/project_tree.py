"""
Module: project_tree.py
Chức năng: Hiển thị cấu trúc thư mục dự án YHCT Diamond dưới dạng sơ đồ cây (Tree) trên Terminal.
Nhiệm vụ:
- Liệt kê phân cấp các file và folder.
- Loại trừ các thư mục môi trường và cache để báo cáo chuyên nghiệp.
"""

import os
from pathlib import Path

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
    # Lấy danh sách file/folder, BỎ QUA IGNORE_LIST và BỎ QUA CÁC FILE ĐUÔI .json
    # Sắp xếp: Folder trước, File sau
    items = sorted(
        [
            item for item in os.listdir(directory) 
            if item not in IGNORE_LIST and not item.endswith('.json') and not item.endswith('.txt')and not item.endswith('.log')
        ],
        key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower())
    )
    
    for i, item in enumerate(items):
        path = os.path.join(directory, item)
        is_last = (i == len(items) - 1)
        
        # Tạo ký tự vẽ nhánh
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{item}")
        
        # Nếu là thư mục, tiếp tục đệ quy vào trong
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(path, new_prefix)

if __name__ == "__main__":
    # Lấy đường dẫn thư mục hiện tại
    root_dir = os.getcwd()
    project_name = os.path.basename(root_dir)
    
    print(f"\n📂 CẤU TRÚC DỰ ÁN: {project_name}")
    print("=" * 50)
    print(".")
    print_tree(root_dir)
    print("=" * 50)
    
    # Xử lý ngoại lệ an toàn cho os.getlogin() trên một số môi trường IDE/Terminal
    try:
        user_name = os.getlogin()
    except Exception:
        user_name = "User"
        
    print(f"\n✅ Sơ đồ được tạo vào lúc: {user_name} - 2026")