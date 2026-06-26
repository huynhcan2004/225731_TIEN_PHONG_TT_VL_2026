"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 7 — DIAMOND PIPELINE (HYBRID LINKER & SANITY CHECKER)      ║
║  Chức năng 1 (Linker): Đồng bộ hóa toàn cục. Nếu từ điển không   ║
║  có, tự động khởi tạo thực thể "Chay" bằng Python để đảm bảo bao ║
║  phủ 100% dữ liệu Gold (Không bỏ sót bất kỳ file nào).           ║
║  Chức năng 2 (Validator): Quét toàn vẹn JSON ngay trên RAM, phát ║
║  hiện đứt gãy, xung đột hướng, cô lập Node.                      ║
║  BẢN NÂNG CẤP: KÉO 'HINT' TỪ ĐIỂN + NẠP CHAY KHI MISSING         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
import re
import sys
import time
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import remove_accents, apply_latex_format

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
INPUT_DIR = settings.DIR_GOLD_VALIDATED 
DICTIONARY_PATH = settings.FILE_DICT_FINAL
OUTPUT_DIR = settings.DIR_GOLD_LINKED
REPORT_FILE = settings.FILE_GRAPH_REPORT

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

# DANH SÁCH TIỀN TỐ CHUẨN
KNOWN_PREFIXES = [
    "VI_THUOC_", "BAI_THUOC_", "BT_", "VT_", 
    "CN_", "HC_", "DL_", "B_", "S_", "V_", "T_", "K_", "G_"
]

# ĐỊNH NGHĨA CHIỀU MŨI TÊN CHUẨN MỰC (ĐÃ MỞ RỘNG FIX LỖI 3)
SCHEMA_RULES = {
    "BAO_GOM_VI_THUOC":     (("BT_", "BAI_THUOC_"), ("VT_", "VI_THUOC_")), 
    "CHU_TRI_BENH":         (("BT_", "BAI_THUOC_", "VT_", "VI_THUOC_"), ("B_",)), 
    "CHU_TRI_TRIEU_CHUNG":  (("BT_", "BAI_THUOC_", "VT_", "VI_THUOC_"), ("S_",)), 
    "CO_TINH":              (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("T_",)), 
    "CO_VI":                (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("V_",)), 
    "QUY_KINH":             (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_", "HC_"), ("K_",)), 
    "CO_CONG_NANG":         (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("CN_",)), 
    "CO_TAC_DUNG_DUOC_LY":  (("VT_", "VI_THUOC_", "HC_"), ("DL_",)), 
    "CO_CHUA_HOAT_CHAT":    (("VT_", "VI_THUOC_"), ("HC_",)), 
    "KIENG_KY":             (("VT_", "VI_THUOC_", "BT_", "BAI_THUOC_"), ("G_", "B_", "S_", "VT_", "VI_THUOC_")), 
}

# ==========================================================
# 2. HÀM CHUẨN HÓA CƯỠNG CHẾ (FALLBACK ALGORITHMS)
# ==========================================================

def force_normalize_id(raw_val, ten_raw=None):
    """
    Biến bất kỳ chuỗi nào thành ID chuẩn Diamond.
    Ví dụ: 'VI_THUOC_RAN' -> 'VT_RAN', 'Cỏ làu' -> 'VT_CO_LAU'
    Nếu từ điển thiếu, hàm này sẽ đảm bảo file vẫn lên được đồ thị.
    """
    if not raw_val and not ten_raw: return "UNKNOWN"
    
    val = str(raw_val if raw_val else ten_raw)
    
    clean = remove_accents(val).upper().strip()
    clean = re.sub(r'[^A-Z0-9_]', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')

    # Rút gọn tiền tố AI sinh ra (VI_THUOC_ -> VT_, BAI_THUOC_ -> BT_)
    clean = re.sub(r'^VI_THUOC_', 'VT_', clean)
    clean = re.sub(r'^BAI_THUOC_', 'BT_', clean)
    clean = re.sub(r'^DUOC_LIEU_', 'VT_', clean)
    clean = re.sub(r'^CAY_', 'VT_', clean)

    # Bổ sung tiền tố nếu thiếu
    valid_prefixes = ("VT_", "BT_", "CN_", "DL_", "HC_", "B_", "S_", "K_", "T_", "V_", "G_")
    if not clean.startswith(valid_prefixes):
        clean = "VT_" + clean
        
    return clean

def finalize_formatting(data):
    if isinstance(data, dict): return {k: finalize_formatting(v) for k, v in data.items()}
    elif isinstance(data, list): return [finalize_formatting(item) for item in data]
    elif isinstance(data, str): return apply_latex_format(data)
    return data

# ==========================================================
# 3. HÀM KIỂM DUYỆT (VALIDATOR ALGORITHMS)
# ==========================================================

def extract_prefix(entity_id):
    if not entity_id: return ""
    entity_id_upper = str(entity_id).upper()
    for prefix in KNOWN_PREFIXES:
        if entity_id_upper.startswith(prefix): return prefix
    if "_" in entity_id_upper: return entity_id_upper.split("_")[0] + "_"
    return "UNKNOWN_"

def check_cycles(relationships):
    graph = defaultdict(list)
    for rel in relationships:
        u, v = rel.get('from'), rel.get('to')
        if u and v: graph[u].append(v)

    visited = {}
    path = []
    cycles_found = []

    def dfs(node):
        visited[node] = 1
        path.append(node)
        for neighbor in graph.get(node, []):
            if visited.get(neighbor) == 1:
                idx = path.index(neighbor)
                cycle_path = path[idx:] + [neighbor]
                cycles_found.append(" 🔄 ".join(cycle_path))
            elif visited.get(neighbor) != 2:
                dfs(neighbor)
        visited[node] = 2
        path.pop()

    for node in list(graph.keys()):
        if visited.get(node) != 2: dfs(node)
    return cycles_found

def check_bidirectional_conflicts(relationships):
    edges = set()
    conflicts = []
    for rel in relationships:
        u, v = rel.get("from"), rel.get("to")
        if not u or not v: continue
        if (v, u) in edges: conflicts.append(f"Xung đột hướng: {u} ↔ {v}")
        edges.add((u, v))
    return conflicts

def check_duplicates(relationships):
    seen = set()
    dupes = []
    for rel in relationships:
        u, v, rtype = rel.get("from"), rel.get("to"), rel.get("relation_type")
        if not u or not v or not rtype: continue
        edge_signature = (u, v, rtype.upper())
        if edge_signature in seen: dupes.append(f"Trùng lặp quan hệ: {u} -[{rtype}]-> {v}")
        seen.add(edge_signature)
    return dupes

# ==========================================================
# 4. ENGINE DUNG HỢP (HYBRID PROCESSOR)
# ==========================================================

def process_file_pipeline(path, lookup, entity_info):
    """
    Thực hiện Linker nắn dữ liệu:
    - Nếu có trong từ điển: Lấy tên chuẩn, aliases, hint.
    - Nếu KHÔNG có: Dùng Python tạo ID nạp CHAY để bảo vệ file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --- A. Hub Entity ---
        old_hub_id = data.get("entity", {}).get("id", "")
        ten_raw_hub = data.get("entity", {}).get("ten_raw", "")
        
        # Tạo ID chuẩn hóa để tìm kiếm hoặc làm ID dự phòng
        norm_id_for_search = force_normalize_id(old_hub_id, ten_raw_hub)
        new_hub_id = lookup.get(norm_id_for_search.lower(), lookup.get(ten_raw_hub.lower(), norm_id_for_search))

        data["entity"]["id"] = new_hub_id
        
        if new_hub_id in entity_info:
            data["entity"]["canonical_name"] = entity_info[new_hub_id]["name"]
        else:
            # NẠP CHAY: Nếu từ điển không có, tự sinh tên từ Raw
            data["entity"]["canonical_name"] = ten_raw_hub.title() if ten_raw_hub else new_hub_id.split("_", 1)[-1].replace("_", " ").title()
        
        data["entity"]["display_name"] = data["entity"]["canonical_name"]

        # --- B. Cập nhật Đặc tính YHCT (Áp dụng cho Tính, Vị, Kinh) ---
        for claim in data.get("claims", []):
            dt = claim.get("dac_tinh_yhct", {})
            if dt:
                for field in ["vi", "tinh", "quy_kinh"]:
                    if field in dt and dt[field]:
                        vals = dt[field] if isinstance(dt[field], list) else [dt[field]]
                        prefix = "V_" if field == "vi" else ("T_" if field == "tinh" else "K_")
                        
                        mapped = []
                        for v in vals:
                            norm_v = force_normalize_id(v)
                            # Đảm bảo tiền tố đúng chuẩn Tính/Vị/Kinh
                            if not norm_v.startswith(prefix):
                                norm_v = norm_v.replace("VT_", prefix)
                            mapped.append(lookup.get(f"{prefix}{str(v).lower().strip()}", lookup.get(str(v).lower().strip(), norm_v)))
                            
                        dt[field] = list(set(mapped)) if isinstance(dt[field], list) else mapped[0]

        # --- C. Cập nhật Mối quan hệ ---
        seen_edges = {} 
        
        for rel in data.get("relationships", []):
            rel.setdefault("properties", {})
            rt = str(rel.get("relation_type", "")).upper()
            
            # Xử lý TO (Đích)
            to_raw = str(rel.get("to", ""))
            t_norm = force_normalize_id(to_raw)
            new_to_id = lookup.get(t_norm.lower(), t_norm)
            
            # Xử lý FROM (Nguồn)
            from_raw = str(rel.get("from", ""))
            if from_raw == old_hub_id or from_raw.lower() == ten_raw_hub.lower(): 
                new_from_id = new_hub_id
            else:
                f_norm = force_normalize_id(from_raw)
                new_from_id = lookup.get(f_norm.lower(), f_norm)
            
            # Đảo chiều logic: Bài thuốc bao gồm Vị thuốc
            if rt in ["CO_TRONG_BAI_THUOC", "THAN_PHAN_CUA"] or (rt == "BAO_GOM_VI_THUOC" and new_from_id.startswith("VT_")):
                new_from_id, new_to_id = new_to_id, new_from_id
                rt = "BAO_GOM_VI_THUOC"
            
            # Đảo chiều logic: Vị thuốc chủ trị Bệnh/Triệu chứng
            if rt.startswith("CHU_TRI"):
                if new_from_id.startswith(("B_", "S_")) and new_to_id.startswith(("VT_", "BT_", "HC_", "DL_")):
                    new_from_id, new_to_id = new_to_id, new_from_id
            
            if new_from_id == new_to_id: continue # Diệt vòng lặp tự trỏ

            # Ép chuẩn Type quan hệ
            if new_to_id.startswith("CN_"): rt = "CO_CONG_NANG"
            elif new_to_id.startswith("DL_"): rt = "CO_TAC_DUNG_DUOC_LY"
            elif new_to_id.startswith("HC_"): rt = "CO_CHUA_HOAT_CHAT"
            elif new_to_id.startswith("T_"): rt = "CO_TINH"
            elif new_to_id.startswith("V_"): rt = "CO_VI"
            elif new_to_id.startswith("K_"): rt = "QUY_KINH"
            elif new_to_id.startswith("B_") and "KIENG" not in rt: rt = "CHU_TRI_BENH"
            elif new_to_id.startswith("S_") and "KIENG" not in rt: rt = "CHU_TRI_TRIEU_CHUNG"
            elif new_to_id.startswith("G_"): rt = "KIENG_KY"
            elif new_from_id.startswith("BT_") and new_to_id.startswith("VT_"): rt = "BAO_GOM_VI_THUOC"
            elif new_from_id.startswith(("VT_", "BT_")) and new_to_id.startswith(("VT_", "BT_")):
                if "KIENG" in rt or "KY" in rt: rt = "KIENG_KY"

            edge_key = (new_from_id, rt, new_to_id)
            if edge_key not in seen_edges:
                rel["from"], rel["to"], rel["relation_type"] = new_from_id, new_to_id, rt
                seen_edges[edge_key] = rel
            else:
                o_desc = str(seen_edges[edge_key]["properties"].get("mo_ta_chi_tiet", ""))
                n_desc = str(rel["properties"].get("mo_ta_chi_tiet", ""))
                if n_desc and n_desc not in o_desc:
                    seen_edges[edge_key]["properties"]["mo_ta_chi_tiet"] = (o_desc + " | " + n_desc).strip(" | ")

        data["relationships"] = list(seen_edges.values())

        # --- D. Xây dựng lại Nodes (VÉT CẠN KÈM HINT TỪ ĐIỂN HOẶC NẠP CHAY) ---
        all_ids = {new_hub_id}
        for r in data["relationships"]: all_ids.update([r["from"], r["to"]])
        
        rebuilt_nodes = []
        prefix_to_label = {
            "BT_": "BaiThuoc", "VT_": "ViThuoc", "B_": "Benh", "S_": "TrieuChung", 
            "G_": "DoiTuong", "HC_": "HoatChat", "DL_": "DuocLy", "CN_": "CongNang", 
            "K_": "KinhMach", "V_": "TinhVi", "T_": "TinhVi"
        }
        
        for eid in sorted(list(all_ids)):
            if not eid or eid == "UNKNOWN": continue
            
            label = "ThucThe"
            for pfx, lbl in prefix_to_label.items():
                if eid.startswith(pfx): label = lbl; break
            
            node_item = {"id": eid, "label": label, "properties": {}}
            
            # Ánh xạ Tên, Bí danh và SEARCH_VECTOR_HINT từ Từ điển
            if eid in entity_info:
                node_item["properties"]["canonical_name"] = entity_info[eid]["name"]
                if entity_info[eid].get("aliases"):
                    node_item["properties"]["aliases"] = entity_info[eid]["aliases"]
                # FIX LỖI 2: Đảm bảo Hint được đẩy vào đúng chuẩn
                if entity_info[eid].get("hint"):
                    node_item["properties"]["search_vector_hint"] = entity_info[eid]["hint"]
            else:
                # NẠP CHAY
                node_item["properties"]["canonical_name"] = eid.split("_", 1)[-1].replace("_", " ").title()

            # Vét cạn thuộc tính riêng của Hub Node (Bảo tồn properties của Entity gốc)
            if eid == new_hub_id:
                ent_p = data.get("entity", {}).get("properties", {})
                for k, v in ent_p.items(): 
                    # Tránh ghi đè search_vector_hint nếu Dictionary đã nạp
                    if k == "search_vector_hint" and "search_vector_hint" in node_item["properties"]:
                        continue
                    if v and str(v).lower() != "không có thông tin": 
                        node_item["properties"][k] = str(v)
                
                node_item["properties"]["ten_khoa_hoc"] = str(data.get("entity", {}).get("ten_khoa_hoc", ""))
                node_item["properties"]["ho_thuc_vat"] = str(data.get("entity", {}).get("ho_thuc_vat", ""))
                
                if data.get("claims"):
                    mo_ta = data["claims"][0].get("mo_ta_theo_nguon", {})
                    for k, v in mo_ta.items():
                        if v: node_item["properties"][k] = str(v)

            rebuilt_nodes.append(node_item)
        
        data["nodes"] = rebuilt_nodes
        data = finalize_formatting(data)
        
        # Lưu file Diamond
        with open(os.path.join(OUTPUT_DIR, os.path.basename(path)), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return data, None
        
    except Exception as e:
        return None, f"Lỗi hệ thống khi Link: {str(e)}"

def validate_memory_data(filename, data, error_report, stats):
    """Chạy Sanity Check trực tiếp trên biến data vừa được Linker tạo ra."""
    hub_id = data.get("entity", {}).get("id", "")
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])
    
    node_ids_in_list = {str(n.get("id")) for n in nodes if n.get("id")}
    node_ids_in_rels = set()
    file_errors = []

    for rel in relationships:
        from_id = str(rel.get("from", ""))
        to_id = str(rel.get("to", ""))
        rel_type = (rel.get("relation_type") or rel.get("type", "")).upper()
        
        if not from_id or not to_id:
            file_errors.append(f"[Đứt gãy] Quan hệ '{rel_type}' thiếu ID.")
            stats["total_dangling"] += 1
            continue

        node_ids_in_rels.update([from_id, to_id])
        
        if from_id == to_id:
            file_errors.append(f"[Tự trỏ] Node '{from_id}' tự nối nó qua {rel_type}.")
            stats["total_cycles"] += 1
            
        if rel_type in SCHEMA_RULES:
            allowed_from, allowed_to = SCHEMA_RULES[rel_type]
            from_prefix = extract_prefix(from_id)
            to_prefix = extract_prefix(to_id)
            
            if not any(from_prefix == p for p in allowed_from):
                file_errors.append(f"[Sai Logic Nguồn] '{from_id}' ({from_prefix}) không được làm Nguồn cho {rel_type}.")
                stats["total_schema_violations"] += 1
            if not any(to_prefix == p for p in allowed_to):
                file_errors.append(f"[Sai Logic Đích] '{to_id}' ({to_prefix}) không được làm Đích cho {rel_type}.")
                stats["total_schema_violations"] += 1
        else:
            file_errors.append(f"[Cảnh báo Schema] Quan hệ '{rel_type}' không nằm trong SCHEMA_RULES đang kích hoạt.")
            stats["total_schema_violations"] += 1

    conflicts = check_bidirectional_conflicts(relationships)
    for c in conflicts:
        file_errors.append(f"[Xung đột 2 chiều] {c}")
        stats["total_conflicts"] += 1

    dupes = check_duplicates(relationships)
    for d in dupes:
        file_errors.append(f"[Trùng lặp cạnh] {d}")
        stats["total_duplicates"] += 1

    cycles = check_cycles(relationships)
    for cy in cycles:
        file_errors.append(f"[Vòng lặp logic] {cy}")
        stats["total_cycles"] += 1

    orphans = node_ids_in_list - node_ids_in_rels
    if hub_id in orphans:
        file_errors.append(f"[CÔ LẬP HUB] Node chính '{hub_id}' không có kết nối!")
        stats["total_orphans"] += 1
        orphans.remove(hub_id)
    for o in orphans:
        file_errors.append(f"[Node mồ côi] '{o}' không có cạnh nối.")
        stats["total_orphans"] += 1

    ghosts = node_ids_in_rels - node_ids_in_list
    for g in ghosts:
        file_errors.append(f"[Node Ma] '{g}' có cạnh nhưng thiếu định nghĩa trong nodes.")
        stats["total_schema_violations"] += 1

    if file_errors:
        error_report[filename] = file_errors
        stats["files_with_errors"] += 1
    else:
        stats["files_passed"] += 1

# ==========================================================
# 5. CHƯƠNG TRÌNH ĐIỀU KHIỂN CHÍNH (MAIN EXECUTOR)
# ==========================================================

def run_diamond_pipeline():
    print(f"🚀 KHỞI ĐỘNG DIAMOND PIPELINE (HYBRID: TỪ ĐIỂN + NẠP CHAY)")
    print(f"📂 Nguồn: {INPUT_DIR}")
    
    lookup = {}
    entity_info = {}

    if not os.path.exists(DICTIONARY_PATH):
        print(f"⚠️ CẢNH BÁO: Không thấy từ điển tại {DICTIONARY_PATH}. Tiến hành nạp CHAY 100%.")
    else:
        with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
            dict_data = json.load(f)
        
        # Vì Step 6 lưu dữ liệu dạng List, ta lặp trực tiếp qua dict_data
        for ent in dict_data: 
            cid = force_normalize_id(ent["canonical_id"])
            
            entity_info[cid] = {
                "name": ent["canonical_name"], 
                "aliases": ent.get("aliases", []),
                "hint": ent.get("search_vector_hint", "") 
            }
            
            # Ánh xạ cả ID và Alias để tra cứu siêu tốc
            lookup[cid.lower()] = cid
            prefix = cid.split('_')[0] + "_" if "_" in cid else ""
            lookup[f"{prefix}{cid.lower()}"] = cid
            
            keys_low_priority = {ent["canonical_name"].lower()}
            # Step 6 đã gộp raw_found vào aliases hoặc xử lý riêng, 
            # hãy đảm bảo các trường này tồn tại trong object ent
            if "raw_found" in ent:
                keys_low_priority.update([str(r).lower().strip() for r in ent.get("raw_found", [])])
            if "aliases" in ent:
                keys_low_priority.update([str(a).lower().strip() for a in ent.get("aliases", [])])
            
            for k in keys_low_priority:
                if k:
                    lk = f"{prefix}{k}"
                    if lk not in lookup: lookup[lk] = cid
                    if k not in lookup: lookup[k] = cid

    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    total_files = len(files)
    
    print(f"🔗 Đang xử lý đồng bộ và kiểm duyệt cho {total_files} file...\n")
    
    error_report = defaultdict(list)
    stats = {
        "files_passed": 0, "files_with_errors": 0, "total_orphans": 0,
        "total_schema_violations": 0, "total_cycles": 0, "total_duplicates": 0,
        "total_conflicts": 0, "total_dangling": 0
    }

    for path in files:
        filename = os.path.basename(path)
        
        # CHẶNG 1: LINKER (CÓ FALLBACK NẠP CHAY)
        linked_data, link_err = process_file_pipeline(path, lookup, entity_info)
        
        if link_err:
            error_report[filename].append(link_err)
            stats["files_with_errors"] += 1
            continue
            
        # CHẶNG 2: VALIDATOR (Chạy thẳng trên Memory Data)
        validate_memory_data(filename, linked_data, error_report, stats)

    # XUẤT BÁO CÁO SANITY CHECKER
    report_content = []
    report_content.append("="*70)
    report_content.append(" BÁO CÁO KIỂM ĐỊNH TOÀN VẸN ĐỒ THỊ KIM CƯƠNG (FINAL PIPELINE) ".center(70))
    report_content.append("="*70)
    report_content.append(f"📍 Tổng số file quét: {total_files}")
    report_content.append(f"✅ Số file đạt chuẩn 100%: {stats['files_passed']}")
    report_content.append(f"⚠️ Số file còn cảnh báo:  {stats['files_with_errors']}")
    report_content.append("-" * 70)
    report_content.append(f"🔍 PHÂN TÍCH ANOMALY (SAU KHI ĐÃ TỰ ĐỘNG SỬA):")
    report_content.append(f"   - Vi phạm Schema/Prefix: {stats['total_schema_violations']}")
    report_content.append(f"   - Đứt gãy ID (Dangling): {stats['total_dangling']}")
    report_content.append(f"   - Node mồ côi (Orphans): {stats['total_orphans']}")
    report_content.append(f"   - Cạnh trùng lặp:        {stats['total_duplicates']}")
    report_content.append(f"   - Xung đột 2 chiều:      {stats['total_conflicts']}")
    report_content.append(f"   - Vòng lặp logic:        {stats['total_cycles']}")
    report_content.append("="*70 + "\n")

    if error_report:
        report_content.append("📌 DANH SÁCH CHI TIẾT FILE CÓ CẢNH BÁO SCHEMA:\n")
        for filename, errors in sorted(error_report.items()):
            report_content.append(f"📁 [FILE] {filename}")
            for err in set(errors): 
                report_content.append(f"   ❌ {err}")
            report_content.append("")
    else:
        report_content.append("🎉 TUYỆT VỜI! ĐỒ THỊ ĐẠT ĐỘ TINH KHIẾT TUYỆT ĐỐI. SẴN SÀNG NẠP NEO4J.")

    report_text = "\n".join(report_content)
    print(report_text)
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(f"\n💾 Dữ liệu Diamond đã lưu tại: {OUTPUT_DIR}")
    print(f"📊 Báo cáo Sanity Check đã lưu tại: {REPORT_FILE}")

if __name__ == "__main__":
    run_diamond_pipeline()