import os
import json
import glob
import re
import sys
from collections import defaultdict

# Đảm bảo import được settings từ thư mục gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN từ settings
# ==========================================
INPUT_DIR = settings.DIR_GOLD_LINKED
OUTPUT_DIR = settings.DIR_GOLD_LINKED

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. TỪ ĐIỂN TRI THỨC (Bao phủ cả Thuần Việt & Hán Việt để không bị mất dữ liệu)
KNOWN_TASTES = {
    "CAY", "TAN", "CHUA", "TOAN", "DANG", "KHO", "DANG_KHO", 
    "NGOT", "CAM", "MAN", "HAM", "NHAT", "DAM", "CHAT"
}

KNOWN_NATURES = {
    "HAN", "NHIET", "ON", "LUONG", "BINH", "AM", "LANH", 
    "DAI_NHIET", "DAI_ON", "HOI_HAN", "HOI_ON", "VI_ON", "VI_HAN", "TRUNG_TINH"
}

KNOWN_MERIDIANS = {
    "TAM", "CAN", "TY", "PHE", "THAN", "DOM", "DAN", "VI", 
    "DAI_TRANG", "TIEU_TRANG", "BANG_QUANG", "TAM_BAO", "TAM_TIEU"
}

def clean_tinh_vi_kinh_id(raw_id):
    """Hàm phẫu thuật ID: Xử lý từng trường hợp lỗi cụ thể (Case-by-case)"""
    if not raw_id: return "UNKNOWN"
    
    # Làm sạch thô ban đầu
    clean = str(raw_id).upper().strip().replace(" ", "_")

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 1: DIỆT TIỀN TỐ KÉP (T_T_, V_V_, K_K_)
    # ---------------------------------------------------------
    clean = re.sub(r'^T_T_', 'T_', clean)
    clean = re.sub(r'^V_V_', 'V_', clean)
    clean = re.sub(r'^K_K_', 'K_', clean)

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 2: XÓA CÁC THỰC THỂ RÁC XÁC ĐỊNH (TRASH REMOVAL)
    # ---------------------------------------------------------
    # Bổ sung T_AN_THAN, T_HOAT, T_CO_TINH, V_CO_VI vào danh sách trảm
    trash_ids = {
        "T_KHONG_DOC", "V_KHONG_DOC", "T_AN_THAN", "V_AN_THAN", 
        "T_KY_TU", "V_KY_TU", "T_THAO_QUA", "V_THAO_QUA", 
        "T_HOAT", "V_HOAT", "T_TINH", "V_VI", "T_DUONG", "V_DUONG",
        "T_CO_TINH", "V_CO_VI" # Rác rỗng từ log kiểm toán
    }
    if clean in trash_ids:
        return "UNKNOWN"

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 3: GỌT VỎ RÁC NỘI HÀM (VERBOSE PEELING)
    # ---------------------------------------------------------
    temp_core = clean
    verbose_patterns = [
        r'VI_CO_TINH_', r'VI_TINH_', r'CO_TINH_', r'TINH_',
        r'VI_CO_VI_', r'CO_VI_', r'VI_VI_'
    ]
    
    for pat in verbose_patterns:
        temp_core = re.sub(r'^(T_|V_|K_)' + pat, r'\1', temp_core)
        temp_core = re.sub(r'^' + pat, "", temp_core)

    # Bảo vệ K_VI: Chỉ lột vỏ 'VI_' đơn lẻ nếu KHÔNG phải Kinh mạch
    if not temp_core.startswith("K_"):
        temp_core = re.sub(r'^(T_|V_)?VI_', r'\1', temp_core)

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 4: SỬA LỖI LẶP TỪ (STUTTERING FIX)
    # ---------------------------------------------------------
    # Sửa lỗi V_CAY_CAY -> V_CAY
    temp_core = re.sub(r'^(.*)_\1$', r'\1', temp_core)

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 5: XỬ LÝ ID HỖN HỢP & NẮN DÒNG (SURGICAL FIX)
    # ---------------------------------------------------------
    # Xử lý V_CAY_DANG -> Giữ lại vị đầu tiên để đưa về Node chuẩn
    if "CAY_DANG" in temp_core: temp_core = temp_core.replace("CAY_DANG", "CAY")
    if "TAN_KHO" in temp_core: temp_core = temp_core.replace("TAN_KHO", "TAN")
    
    # Xử lý T_CAY_ON -> T_ON (Vì CAY là vị, ON là tính)
    if "CAY_ON" in temp_core: temp_core = temp_core.replace("CAY_ON", "ON")
    if "TAN_ON" in temp_core: temp_core = temp_core.replace("TAN_ON", "ON")

    # Sau khi xử lý hỗn hợp, lấy phần nhân thực sự
    core_only = re.sub(r'^[TVK]_', "", temp_core)
    if not core_only or core_only == "UNKNOWN": return "UNKNOWN"

    # Sửa lỗi chéo nhãn (Ví dụ T_CAY -> V_CAY)
    if core_only in KNOWN_TASTES:
        return f"V_{core_only}"
    if core_only in KNOWN_NATURES:
        return f"T_{core_only}"
    
    # Bảo vệ Kinh mạch
    if temp_core.startswith("K_"):
        for m in KNOWN_MERIDIANS:
            if m in temp_core: return f"K_{m}"
        return temp_core

    return temp_core

def process_file(filepath):
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --- CHẶNG 1: PHẪU THUẬT RELATIONSHIPS ---
        new_rels = {}
        for rel in data.get("relationships", []):
            rt = str(rel.get("relation_type", "")).upper()
            to_id = str(rel.get("to", ""))
            from_id = str(rel.get("from", ""))
            
            # Chỉ can thiệp vào nhóm Tính, Vị, Kinh
            if rt in ["CO_TINH", "CO_VI", "QUY_KINH"] or to_id.startswith(("T_", "V_", "K_")):
                clean_to_id = clean_tinh_vi_kinh_id(to_id)
                
                # Tiêu diệt nếu là UNKNOWN
                if clean_to_id == "UNKNOWN":
                    continue  
                
                # Nắn lại Type quan hệ cho khớp với ID đích mới
                if clean_to_id.startswith("T_"): rt = "CO_TINH"
                elif clean_to_id.startswith("V_"): rt = "CO_VI"
                elif clean_to_id.startswith("K_"): rt = "QUY_KINH"
                
                rel["to"] = clean_to_id
                rel["relation_type"] = rt
                
            # Hợp nhất quan hệ trùng lặp (Deduplication)
            edge_key = (from_id, rt, rel["to"])
            if edge_key in new_rels:
                existing = new_rels[edge_key]
                d1 = existing.get("properties", {}).get("mo_ta_chi_tiet", "")
                d2 = rel.get("properties", {}).get("mo_ta_chi_tiet", "")
                if d2 and d2 not in d1:
                    existing["properties"]["mo_ta_chi_tiet"] = f"{d1} | {d2}".strip(" | ")
            else:
                new_rels[edge_key] = rel

        data["relationships"] = list(new_rels.values())

        # --- CHẶNG 2: PHẪU THUẬT NODES ---
        active_ids = {r["from"] for r in data["relationships"]} | {r["to"] for r in data["relationships"]}
        new_nodes = {}
        
        for node in data.get("nodes", []):
            nid = str(node.get("id", ""))
            if nid.startswith(("T_", "V_", "K_")):
                clean_nid = clean_tinh_vi_kinh_id(nid)
                if clean_nid == "UNKNOWN": continue
                
                node["id"] = clean_nid
                # Tạo tên hiển thị (Canonical Name)
                name = clean_nid.split("_", 1)[-1].replace("_", " ").title()
                node["properties"]["canonical_name"] = name
                
                # Gán nhãn Neo4j chuẩn
                if clean_nid.startswith(("T_", "V_")): node["label"] = "TinhVi"
                elif clean_nid.startswith("K_"): node["label"] = "KinhMach"
                nid = clean_nid

            if nid in active_ids:
                new_nodes[nid] = node

        # Bổ sung Node nếu mảng nodes bị thiếu nhưng relationships có dùng
        for aid in active_ids:
            if aid not in new_nodes and aid.startswith(("T_", "V_", "K_")):
                lbl = "TinhVi" if aid.startswith(("T_", "V_")) else "KinhMach"
                nm = aid.split("_", 1)[-1].replace("_", " ").title()
                new_nodes[aid] = {"id": aid, "label": lbl, "properties": {"canonical_name": nm}}

        data["nodes"] = list(new_nodes.values())

        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"💥 Lỗi tại file {filename}: {e}")

def run():
    files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    print(f"🚀 [DIAMOND_SURGICAL_FIXER_V4] Đang xử lý {len(files)} files...")
    for f in files:
        process_file(f)
    print(f"✅ HOÀN TẤT! Đồ thị của huynh hiện đã đạt độ tinh khiết Diamond.")

if __name__ == "__main__":
    run()