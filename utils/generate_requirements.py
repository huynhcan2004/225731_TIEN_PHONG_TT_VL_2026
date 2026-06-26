#!/usr/bin/env python3
"""
Script: utils/generate_requirements.py
Chức năng: Tự động quét mã nguồn Python (.py), phát hiện các thư viện bên thứ ba,
          tra cứu phiên bản thực tế cài đặt trong venv và xuất ra requirements.txt phân nhóm sạch sẽ.
Tác giả: Antigravity - DevOps / Data Engineer Assistant
Năm: 2026
"""

import os
import ast
import sys
from pathlib import Path
from importlib.metadata import version, packages_distributions

# ----------------------------------------------------------------------
# 1. DANH SÁCH THƯ VIỆN TIÊU CHUẨN CỦA PYTHON (STANDARD LIBRARY RUNTIME)
# ----------------------------------------------------------------------
# Dự phòng cho Python < 3.10 không có sys.stdlib_module_names
STD_LIB_FALLBACK = {
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "copy", "csv",
    "datetime", "decimal", "email", "enum", "fnmatch", "functools", "glob", "hashlib",
    "hmac", "html", "http", "importlib", "inspect", "io", "json", "logging", "math",
    "multiprocessing", "os", "pathlib", "pickle", "pprint", "queue", "random", "re",
    "securesystemslib", "select", "shutil", "signal", "socket", "sqlite3", "ssl",
    "string", "subprocess", "sys", "tempfile", "threading", "time", "traceback",
    "types", "typing", "unittest", "urllib", "uuid", "warnings", "weakref", "xml", "zipfile"
}

def get_stdlib_modules():
    """Lấy danh sách các module tích hợp sẵn của Python."""
    if hasattr(sys, "stdlib_module_names"):
        return sys.stdlib_module_names
    return STD_LIB_FALLBACK

# ----------------------------------------------------------------------
# 2. CẤU HÌNH PHÂN NHÓM THƯ VIỆN (GROUP CONFIGURATION)
# ----------------------------------------------------------------------
GROUPS = {
    "1. NHÓM BACKEND & API FRAMEWORK": [
        "fastapi", "uvicorn", "pydantic", "pydantic-settings", "pydantic_settings",
        "starlette", "python-multipart", "fastapi-users"
    ],
    "2. NHÓM ĐỒ THỊ & CƠ SỞ DỮ LIỆU (NEO4J CLOUD)": [
        "neo4j", "neo4j-graphrag"
    ],
    "3. NHÓM AI, LLM & VECTOR EMBEDDING (OLLAMA & LANGCHAIN)": [
        "langchain", "langchain-community", "langchain-neo4j", "langchain-core", 
        "langchain-openai", "langchain-google-genai", "langchain-google-vertexai", 
        "ollama", "openai", "google-generativeai", "vertexai", "ragas"
    ],
    "4. NHÓM XỬ LÝ DỮ LIỆU & ĐƯỜNG ỐNG MEDALLION (JSON/SILVER/DIAMOND)": [
        "pandas", "numpy", "pyarrow"
    ],
    "5. NHÓM TIỆN ÍCH HỆ THỐNG": [
        "python-dotenv", "requests", "httpx", "pyjwt", "passlib", "python-jose",
        "chainlit", "fitz", "PyMuPDF"
    ]
}

# Thư mục loại trừ khi quét mã nguồn
EXCLUDE_DIRS = {"venv", ".venv", "env", ".git", ".idea", "__pycache__", "build", "dist"}

# ----------------------------------------------------------------------
# 3. QUÉT IMPORT BẰNG AST (ABSTRACT SYNTAX TREE)
# ----------------------------------------------------------------------
class ImportExtractor(ast.NodeVisitor):
    def __init__(self):
        self.imported_modules = set()

    def visit_Import(self, node):
        for alias in node.names:
            root_module = alias.name.split('.')[0]
            self.imported_modules.add(root_module)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module:
            root_module = node.module.split('.')[0]
            self.imported_modules.add(root_module)
        self.generic_visit(node)

def scan_imports(project_dir: Path) -> set:
    """Quét toàn bộ thư mục dự án để tìm các import thực tế sử dụng."""
    extractor = ImportExtractor()
    
    for root, dirs, files in os.walk(project_dir):
        # Loại bỏ các thư mục không muốn quét tại chỗ
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file.endswith('.py') and file != "generate_requirements.py":
                file_path = Path(root) / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=str(file_path))
                        extractor.visit(tree)
                except Exception as e:
                    print(f"[Warning] Khong the phan tich file {file_path}: {e}")
                    
    return extractor.imported_modules

# ----------------------------------------------------------------------
# 4. CHUYỂN ĐỔI IMPORT TÊN MODULE -> TÊN PIP PACKAGE & ĐỐI SOÁT PHIÊN BẢN
# ----------------------------------------------------------------------
def resolve_packages(imported_modules: set, project_dir: Path) -> dict:
    """Ánh xạ import module sang tên package cài trên PyPI và lấy phiên bản."""
    stdlib = get_stdlib_modules()
    pkg_dist = packages_distributions()
    
    resolved_packages = {}
    
    # Xác định các folder/file cục bộ tại root để loại bỏ khỏi danh sách thư viện
    local_names = {p.stem for p in project_dir.iterdir()}
    
    for mod in sorted(imported_modules):
        # 1. Bỏ qua các module tiêu chuẩn, local modules và các file tạm
        if mod in stdlib or mod.startswith("_") or mod in local_names:
            continue
            
        # 2. Ánh xạ sang tên package PyPI
        packages = pkg_dist.get(mod)
        if packages:
            for pkg in packages:
                try:
                    pkg_ver = version(pkg)
                    resolved_packages[pkg] = pkg_ver
                except Exception:
                    pass
        else:
            try:
                pkg_ver = version(mod)
                resolved_packages[mod] = pkg_ver
            except Exception:
                resolved_packages[mod] = None
                
    return resolved_packages

# ----------------------------------------------------------------------
# 5. GHI FILE REQUIREMENTS.TXT VÀ PHÂN NHÓM
# ----------------------------------------------------------------------
def write_requirements(resolved: dict, output_file: Path):
    """Phân nhóm và xuất kết quả ra file requirements.txt."""
    grouped_packages = {group: [] for group in GROUPS}
    others = []
    
    for pkg, ver in resolved.items():
        if ver is None:
            display_str = f"# {pkg} (Chuyen qua cài dat trong venv de nhan phien ban)"
        else:
            display_str = f"{pkg}=={ver}"
            
        matched = False
        pkg_lower = pkg.lower()
        for group, keywords in GROUPS.items():
            if any(k in pkg_lower for k in keywords):
                grouped_packages[group].append(display_str)
                matched = True
                break
        
        if not matched:
            others.append(display_str)
            
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# ======================================================================\n")
        f.write("# FILE REQUIREMENTS.TXT DU AN CHATBOT GRAPHRAG Y HOC CO TRUYEN (2026)\n")
        f.write("# Duoc sinh tu dong boi script generate_requirements.py\n")
        f.write("# ======================================================================\n\n")
        
        for group, pkgs in grouped_packages.items():
            if pkgs:
                f.write(f"# {group}\n")
                for p in sorted(pkgs):
                    f.write(f"{p}\n")
                f.write("\n")
                
        if others:
            f.write("# 6. CAC THU VIEN PHU TRO KHAC\n")
            for p in sorted(others):
                f.write(f"{p}\n")
            f.write("\n")

    print(f"[Success] Da ghi danh sach thu vien thanh cong vao: {output_file.resolve()}")

# ----------------------------------------------------------------------
# MAIN ENTRYPOINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    current_dir = Path(__file__).parent
    project_dir = current_dir.parent
    
    print(">>> Bat dau quet ma nguon Python tai:", str(project_dir.resolve()))
    
    modules = scan_imports(project_dir)
    print(f"Found {len(modules)} imported top-level modules.")
    
    resolved = resolve_packages(modules, project_dir)
    print(f"Resolved {len(resolved)} third-party PyPI packages.")
    
    output_path = project_dir / "requirements.txt"
    write_requirements(resolved, output_path)
