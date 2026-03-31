"""
╔══════════════════════════════════════════════════════════════════╗
║  SMART GRAPH SANITY CHECKER (TRÌNH KIỂM DUYỆT ĐỒ THỊ THÔNG MINH) ║
║  Chức năng: Quét toàn vẹn JSON, ép chuẩn Ontology, phát hiện     ║
║  xung đột hai chiều, đứt gãy, trùng lặp và vòng lặp logic.       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
from collections import defaultdict

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings

# ==========================================================
# 1. CẤU HÌNH & TỪ ĐIỂN ONTOLOGY (SMART RULES)
# ==========================================================
# Cập nhật đường dẫn theo kiến trúc Medallion
INPUT_DIR = settings.DIR_GOLD_LINKED
REPORT_FILE = settings.FILE_GRAPH_REPORT

os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

# DANH SÁCH TIỀN TỐ CHUẨN (Sắp xếp từ dài xuống ngắn để bóc tách chính xác)
KNOWN_PREFIXES = [
    "VI_THUOC_", "BAI_THUOC_", "BT_", "VT_", 
    "CN_", "HC_", "DL_", "B_", "S_", "V_", "T_", "K_", "G_"
]

# ĐỊNH NGHĨA CHIỀU MŨI TÊN CHUẨN MỰC (Tuyệt đối không được đi ngược)
# Cấu trúc: "TÊN_QUAN_HỆ": ( [Tiền_tố_được_phép_của_FROM], [Tiền_tố_được_phép_của_TO] )
SCHEMA_RULES = {
    "BAO_GOM_VI_THUOC":     (("BT_", "BAI_THUOC_"), ("VT_", "VI_THUOC_")), 
    "CHU_TRI_BENH":         (("BT_", "BAI_THUOC_", "VT_", "VI_THUOC_"), ("B_",)), 
    "CHU_TRI_TRIEU_CHUNG":  (("BT_", "BAI_THUOC_", "VT_", "VI_THUOC_"), ("S_",)), 
    "CO_TINH":              (("VT_", "VI_THUOC_"), ("T_",)), 
    "CO_VI":                (("VT_", "VI_THUOC_"), ("V_",)), 
    "QUY_KINH":             (("VT_", "VI_THUOC_"), ("K_",)), 
    "CO_CONG_NANG":         (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("CN_",)), 
    "CO_TAC_DUNG_DUOC_LY":  (("VT_", "VI_THUOC_"), ("DL_",)), 
    "CO_CHUA_HOAT_CHAT":    (("VT_", "VI_THUOC_"), ("HC_",)), 
    "KIENG_KY":             (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("G_", "B_", "VT_", "VI_THUOC_")), 
}

# ==========================================================
# 2. CÁC HÀM THUẬT TOÁN LÕI (CORE ALGORITHMS)
# ==========================================================

def extract_prefix(entity_id):
    """Trích xuất tiền tố chuẩn xác dựa trên danh sách KNOWN_PREFIXES."""
    if not entity_id:
        return ""
    entity_id_upper = str(entity_id).upper()
    for prefix in KNOWN_PREFIXES:
        if entity_id_upper.startswith(prefix):
            return prefix
    # Nếu không thuộc danh sách chuẩn, thử tách bằng dấu '_' đầu tiên
    if "_" in entity_id_upper:
        return entity_id_upper.split("_")[0] + "_"
    return "UNKNOWN_"

def check_cycles(relationships):
    """DFS phát hiện vòng lặp logic (A -> B -> C -> A)."""
    graph = defaultdict(list)
    for rel in relationships:
        if rel.get('from') and rel.get('to'):
            graph[rel['from']].append(rel['to'])

    visited = {}
    path = []
    cycles_found = []

    def dfs(node):
        visited[node] = 1 # Đang thăm
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if visited.get(neighbor) == 1:
                # Phát hiện vòng lặp
                cycle_path = path[path.index(neighbor):] + [neighbor]
                cycles_found.append(" 🔄 ".join(cycle_path))
            elif visited.get(neighbor) != 2:
                dfs(neighbor)
                
        visited[node] = 2 # Đã thăm xong
        path.pop()

    for node in list(graph.keys()):
        if visited.get(node) != 2:
            dfs(node)
            
    return cycles_found

def check_bidirectional_conflicts(relationships):
    """Phát hiện mâu thuẫn 2 chiều (A -> B và B -> A đồng thời)."""
    edges = set()
    conflicts = []
    for rel in relationships:
        u, v = rel.get("from"), rel.get("to")
        if not u or not v: continue
        
        if (v, u) in edges:
            conflicts.append(f"Xung đột hướng: {u} ↔ {v}")
        edges.add((u, v))
    return conflicts

def check_duplicates(relationships):
    """Phát hiện các quan hệ bị lặp lại hoàn toàn."""
    seen = set()
    dupes = []
    for rel in relationships:
        u, v, rtype = rel.get("from"), rel.get("to"), rel.get("relation_type") or rel.get("type")
        if not u or not v or not rtype: continue
        
        edge_signature = (u, v, rtype)
        if edge_signature in seen:
            dupes.append(f"Trùng lặp quan hệ: {u} -[{rtype}]-> {v}")
        seen.add(edge_signature)
    return dupes

# ==========================================================
# 3. TRÌNH KIỂM DUYỆT CHÍNH (MAIN VALIDATOR)
# ==========================================================

def run_validator():
    print("🕵️ Đang khởi động Trình Thanh tra Đồ thị Thông minh (Smart Graph Validator)...")
    files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    
    if not files:
        print(f"❌ Không tìm thấy file nào trong thư mục {INPUT_DIR}")
        return

    total_files = len(files)
    error_report = defaultdict(list)
    
    stats = {
        "files_passed": 0,
        "files_with_errors": 0,
        "total_orphans": 0,
        "total_schema_violations": 0,
        "total_cycles": 0,
        "total_duplicates": 0,
        "total_conflicts": 0,
        "total_dangling": 0
    }

    for path in files:
        filename = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                error_report[filename].append("[Lỗi Cấu trúc] File JSON bị hỏng, không thể đọc.")
                stats["files_with_errors"] += 1
                continue
            
        hub_id = data.get("entity", {}).get("id", "")
        nodes = data.get("nodes", [])
        relationships = data.get("relationships", [])
        
        node_ids_in_list = {n.get("id") for n in nodes if n.get("id")}
        node_ids_in_rels = set()
        file_errors = []

        # ======================================================
        # BƯỚC 1: KIỂM TRA MỐI QUAN HỆ & SCHEMA
        # ======================================================
        for rel in relationships:
            from_id = rel.get("from", "")
            to_id = rel.get("to", "")
            rel_type = rel.get("relation_type") or rel.get("type", "")
            
            # Lỗi 1.0: Đứt gãy (Dangling Edge)
            if not from_id or not to_id:
                file_errors.append(f"[Đứt gãy/Dangling] Quan hệ '{rel_type}' bị thiếu ID nguồn (from) hoặc đích (to).")
                stats["total_dangling"] += 1
                continue

            node_ids_in_rels.update([from_id, to_id])
            
            # Lỗi 1.1: Self-loop (Tự trỏ vào chính mình)
            if from_id == to_id:
                file_errors.append(f"[Tự trỏ/Self-Loop] Node '{from_id}' tự trỏ vào chính nó qua quan hệ {rel_type}.")
                stats["total_cycles"] += 1
                
            # Lỗi 1.2: Sai quy tắc chiều (Schema Direction Violation)
            if rel_type in SCHEMA_RULES:
                allowed_from, allowed_to = SCHEMA_RULES[rel_type]
                from_prefix = extract_prefix(from_id)
                to_prefix = extract_prefix(to_id)
                
                if not any(from_prefix == p for p in allowed_from):
                    file_errors.append(f"[Sai Logic Tác Nhân] '{from_id}' (Tiền tố {from_prefix}) không được làm Nguồn cho quan hệ {rel_type}. Chỉ cho phép: {allowed_from}")
                    stats["total_schema_violations"] += 1
                    
                if not any(to_prefix == p for p in allowed_to):
                    file_errors.append(f"[Sai Logic Đích Đến] '{to_id}' (Tiền tố {to_prefix}) không được làm Đích cho quan hệ {rel_type}. Chỉ cho phép: {allowed_to}")
                    stats["total_schema_violations"] += 1
            else:
                file_errors.append(f"[Cảnh báo Schema] Quan hệ '{rel_type}' không nằm trong từ điển SCHEMA_RULES hợp lệ.")
                stats["total_schema_violations"] += 1

        # ======================================================
        # BƯỚC 2: KIỂM TRA TÍNH TOÀN VẸN ĐỒ THỊ CAO CẤP
        # ======================================================
        
        # 2.1 Mâu thuẫn 2 chiều
        conflicts = check_bidirectional_conflicts(relationships)
        for conflict in conflicts:
            file_errors.append(f"[Xung đột/Bidirectional] {conflict}")
            stats["total_conflicts"] += 1

        # 2.2 Trùng lặp quan hệ
        dupes = check_duplicates(relationships)
        for dupe in dupes:
            file_errors.append(f"[Trùng lặp/Duplicate] {dupe}")
            stats["total_duplicates"] += 1

        # 2.3 Vòng lặp đa tầng
        cycles = check_cycles(relationships)
        for cycle in cycles:
            file_errors.append(f"[Vòng lặp logic/Cycle] {cycle}")
            stats["total_cycles"] += 1

        # ======================================================
        # BƯỚC 3: KIỂM TRA TÌNH TRẠNG CÔ LẬP
        # ======================================================
        
        # 3.1 Node Mồ côi (Có khai báo nhưng không dùng)
        orphans = node_ids_in_list - node_ids_in_rels
        if hub_id in orphans:
            # Hub node mồ côi là lỗi cực kỳ nghiêm trọng
            file_errors.append(f"[CÔ LẬP TOÀN DIỆN] Node chính '{hub_id}' không có bất kỳ kết nối nào trong đồ thị!")
            stats["total_orphans"] += 1
            orphans.remove(hub_id)
            
        for orphan in orphans:
            file_errors.append(f"[Node Thừa/Orphan] '{orphan}' được định nghĩa trong mảng 'nodes' nhưng không có cạnh nối.")
            stats["total_orphans"] += 1

        # 3.2 Node Ma (Dùng nhưng không khai báo) - Tùy chọn, vì Graph DB thường tự tạo Node mới
        ghosts = node_ids_in_rels - node_ids_in_list
        if hub_id and hub_id not in node_ids_in_list:
             file_errors.append(f"[Mất tích Hub] Node chính '{hub_id}' không được định nghĩa trong mảng 'nodes'!")
             stats["total_schema_violations"] += 1

        # ======================================================
        # TỔNG KẾT FILE
        # ======================================================
        if file_errors:
            error_report[filename] = file_errors
            stats["files_with_errors"] += 1
        else:
            stats["files_passed"] += 1

    # ==========================================================
    # 4. KẾT XUẤT BÁO CÁO (SMART REPORTING)
    # ==========================================================
    
    report_content = []
    report_content.append("="*70)
    report_content.append(" BÁO CÁO KIỂM ĐỊNH TÍNH TOÀN VẸN ĐỒ THỊ (SMART SANITY CHECK) ".center(70))
    report_content.append("="*70)
    report_content.append(f"📍 Tổng số file quét: {total_files}")
    report_content.append(f"✅ Số file SẠCH 100%: {stats['files_passed']}")
    report_content.append(f"⚠️ Số file chứa LỖI:  {stats['files_with_errors']}")
    report_content.append("-" * 70)
    report_content.append(f"🔍 BÓC TÁCH CÁC LOẠI LỖI (ANOMALY BREAKDOWN):")
    report_content.append(f"   - Vi phạm Logic Tiền tố / Schema: {stats['total_schema_violations']}")
    report_content.append(f"   - Đứt gãy / Mất ID (Dangling):    {stats['total_dangling']}")
    report_content.append(f"   - Node mồ côi / Không kết nối:    {stats['total_orphans']}")
    report_content.append(f"   - Cạnh trùng lặp (Duplicates):    {stats['total_duplicates']}")
    report_content.append(f"   - Xung đột 2 chiều (Conflicts):   {stats['total_conflicts']}")
    report_content.append(f"   - Vòng lặp phi logic (Cycles):    {stats['total_cycles']}")
    report_content.append("="*70 + "\n")

    if error_report:
        report_content.append("📌 DANH SÁCH FILE VÀ MÔ TẢ LỖI CHI TIẾT:\n")
        for filename, errors in sorted(error_report.items()):
            report_content.append(f"📁 [FILE] {filename}")
            for err in set(errors): # Dùng set() để tránh in lặp lại cùng một lỗi trong 1 file
                report_content.append(f"   ❌ {err}")
            report_content.append("")
    else:
        report_content.append("🎉 TUYỆT VỜI! HỆ THỐNG ĐỒ THỊ CỦA BẠN ĐACT ĐỘ TINH KHIẾT TUYỆT ĐỐI KHÔNG CÒN RÁC.")

    report_text = "\n".join(report_content)
    
    # In ra Terminal
    print(report_text)
    
    # Ghi ra File
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(f"\n💾 Đã lưu báo cáo chi tiết tại: {REPORT_FILE}")

if __name__ == "__main__":
    run_validator()