import os
import json
import re
import glob
import time
import traceback
from collections import defaultdict
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import robust_json_load, normalize_id, remove_accents, get_page_number

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us-central1"

# Sử dụng cấu trúc Medallion từ file cấu hình
BRONZE_DIR = settings.DIR_BRONZE_RAW
GOLD_STEP2_DIR = settings.DIR_SILVER_MAPPED
LOG_STEP3_DIR = settings.DIR_LOGS_AUDIT
DIAMOND_OUT_DIR = settings.DIR_SILVER_AUDITED

os.makedirs(DIAMOND_OUT_DIR, exist_ok=True)

# File ghi nhận số liệu học thuật cho bài báo
TELEMETRY_FILE = os.path.join(DIAMOND_OUT_DIR, "step4_telemetry_report.json")

# ==========================================================
# 2. ENGINE DUNG HỢP VÀ CHỈNH SỬA LOGIC (CORE)
# ==========================================================

def finalize_json(data):
    """Làm sạch LaTeX và chuẩn hóa hiển thị cuối cùng"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json_str = json_str.replace('\\\\%', '%').replace('\\%', '%')
    
    # Bọc LaTeX số + đơn vị phổ biến (Đã bổ sung đơn vị YHCT cổ)
    pattern = r'(?<![\$\d])(\d+(?:[.,-]\d+)?)\s*(g|ml|mg|%|°C|bát|phần|ống|muỗng|kilôgam|lạng|chỉ|đồng cân|phân|tễ|thang)\b(?!\$)'
    json_str = re.sub(pattern, r'$\1\2$', json_str, flags=re.IGNORECASE)
    
    # Escape duy nhất cho % trong LaTeX
    json_str = json_str.replace('%', '\\\\%')
    return json.loads(json_str)

def fix_misassigned_remedy_ids(rels, nodes, hub_id):
    """
    CƠ CHẾ "SỬA LỖI GÁN LỘN": 
    Duyệt qua các quan hệ chủ trị để tái định nghĩa ID bài thuốc bị AI gán nhầm.
    """
    id_mapping = {} # Cũ -> Mới
    
    # Bước 1: Phát hiện sự lệch pha giữa ID bài thuốc và Bệnh thực tế điều trị
    for r in rels:
        f_id = str(r.get("from", ""))
        t_id = str(r.get("to", ""))
        rt = r.get("relation_type", "")
        
        if f_id.startswith("BT_") and rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
            # Lấy tên bệnh từ ID của đích (To)
            actual_disease = t_id.replace("B_", "").replace("NHOMBENH_", "").replace("S_", "")
            
            # Kiểm tra xem trong ID gốc (From) có chứa tên bệnh thực tế này không
            if actual_disease not in f_id:
                # Nếu không khớp, tạo ID mới dựa trên quy chuẩn: BT_TENBENH_TENHU_VAN_TAY
                # Lấy phần hậu tố (Vân tay) từ ID cũ (ví dụ: _ICH_MA_I)
                parts = f_id.split("_")
                fingerprint = "_".join(parts[-2:]) if len(parts) > 2 else "GENERIC"
                new_id = f"BT_{actual_disease}_{fingerprint}"
                
                # Lưu vào map để sửa đồng bộ
                # Chú ý: Cần thêm context (mo_ta_chi_tiet) để tránh đổi nhầm bài thuốc khác
                # Ở đây đệ dùng logic đơn giản: mỗi quan hệ chủ trị bị sai sẽ tạo ra một mỏ neo mới
                id_mapping[(f_id, t_id)] = new_id

    # Bước 2: Cập nhật lại toàn bộ Relationships
    new_rels = []
    for r in rels:
        f_id = r.get("from")
        t_id = r.get("to")
        
        # Nếu cặp (from, to) này nằm trong danh sách cần sửa
        if (f_id, t_id) in id_mapping:
            r["from"] = id_mapping[(f_id, t_id)]
        
        # Đặc biệt: Nếu là quan hệ BAO_GOM_VI_THUOC, phải tìm xem bài thuốc này 
        # đã bị đổi ID ở bước trên chưa dựa vào logic "phoi_ngu_logic"
        if r.get("relation_type") == "BAO_GOM_VI_THUOC":
            logic_text = r.get("properties", {}).get("phoi_ngu_logic", "").upper()
            for (old_bt, target_dis), new_bt in id_mapping.items():
                if f_id == old_bt and remove_accents(target_dis) in remove_accents(logic_text):
                    r["from"] = new_bt
                    break

        new_rels.append(r)
        
    return new_rels, nodes

def extract_dosage_fix(data):
    """
    Bóc tách liều lượng tổng quát bằng NLP Regex chuyên sâu.
    """
    rels = data.get("relationships", [])
    
    # Regex bắt liều lượng hiện đại và cổ truyền YHCT
    dosage_pattern = r'\$(\d+[\d\.,-]*\s*[a-zA-Z%°C/\\^]*|đồng cân|chỉ|lạng|phân|tễ|thang)\$'

    for r in rels:
        if r.get("relation_type") == "BAO_GOM_VI_THUOC":
            props = r.get("properties", {})
            
            # --- CƠ CHẾ LỌC TỪ THỪA (CHỈ LẤY CON SỐ BỌC LATEX) ---
            lieu_luong_hien_tai = props.get("lieu_luong", "")
            if isinstance(lieu_luong_hien_tai, str) and lieu_luong_hien_tai:
                ll_lower = lieu_luong_hien_tai.lower().strip()
                if ll_lower not in ["không rõ", "theo chỉ định", "tùy chỉnh", "lượng bằng nhau"]:
                    first_idx = lieu_luong_hien_tai.find('$')
                    last_idx = lieu_luong_hien_tai.rfind('$')
                    # Nếu tìm thấy cụm latex hợp lệ, cắt bỏ toàn bộ chữ thừa bên ngoài
                    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
                        props["lieu_luong"] = lieu_luong_hien_tai[first_idx:last_idx+1]
            # -----------------------------------------------------

            if not props.get("lieu_luong") and props.get("mo_ta_chi_tiet"):
                desc = str(props["mo_ta_chi_tiet"])
                to_id = str(r.get("to", ""))
                
                # Bóc tách tên lõi để đối chiếu phạm vi hẹp
                core_name = to_id.replace("VI_THUOC_", "").replace("VT_", "").replace("_", " ").lower()
                desc_lower = remove_accents(desc).lower()
                core_lower = remove_accents(core_name).lower()
                
                idx = desc_lower.find(core_lower)
                
                if idx != -1:
                    # Quét phạm vi hẹp 60 ký tự xung quanh vị thuốc
                    substring = desc[idx : idx + 60] 
                    match = re.search(dosage_pattern, substring)
                    if match:
                        props["lieu_luong"] = match.group(0)
                
                if not props.get("lieu_luong"):
                    all_matches = re.findall(dosage_pattern, desc)
                    if len(all_matches) == 1:
                        props["lieu_luong"] = all_matches[0]

            r["properties"] = props
            
    data["relationships"] = rels
    return data

def merge_and_deduplicate_edges(existing_rels, new_rels, is_from_secondary_file=False):
    """
    Thuật toán hợp nhất đồ thị (Graph Fusion): Khử trùng lặp cạnh tuyệt đối.
    MỚI: Bổ sung cờ is_from_secondary_file và MÀNG LỌC ẢO GIÁC TOÀN DIỆN.
    """
    edge_map = {}
    
    # Danh sách các quan hệ DNA cấm xuất hiện ở file phụ (Bài thuốc, Dược lý)
    FORBIDDEN_DNA_RELS = ["CO_TINH", "CO_VI", "QUY_KINH"]
    
    def add_to_map(rel, is_secondary):
        f = normalize_id(rel.get("from", ""))
        t = normalize_id(rel.get("to", ""))
        rt = str(rel.get("relation_type", "")).upper()
        
        # Trích xuất property để kiểm tra bằng chứng
        props = rel.get("properties", {})
        desc = str(props.get("mo_ta_chi_tiet", "")).lower()
        lieu_dung = str(props.get("lieu_dung", "")).lower()
        
        # 🔴 TẦNG 1: MÀNG LỌC ĐỊNH TUYẾN (Chặn DNA đi lạc sang file phụ)
        if is_secondary and rt in FORBIDDEN_DNA_RELS:
            return
            
        # 🔴 TẦNG 2: MÀNG LỌC BẰNG CHỨNG ẢO GIÁC (Dọn rác AI suy luận)
        if rt in FORBIDDEN_DNA_RELS:
            # DNA tuyệt đối cấm suy luận
            FATAL_STR = ["suy luận", "không được đề cập", "không thấy nói", "chưa rõ quy kinh", "có thể liên quan", "không đề cập trực tiếp", "dựa trên công năng"]
            if any(s in desc for s in FATAL_STR):
                return # Trảm ngay lập tức
        elif rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG", "BAO_GOM_VI_THUOC"]:
            # Điều trị/Bài thuốc cũng cấm AI tự diễn giải y lý
            if "suy luận" in desc or "có lẽ" in desc:
                return # Trảm
            
            # Gạn đục khơi trong: Nếu thiếu liều dùng thì cập nhật lại chữ cho chuyên nghiệp
            UNCLEAR_DOSAGE_STR = ["chưa rõ", "không đề cập liều", "không ghi liều", "không có thông tin"]
            if any(s in lieu_dung for s in UNCLEAR_DOSAGE_STR):
                if "lieu_dung" in props:
                    props["lieu_dung"] = "Chưa rõ (Theo nguyên tác)"
            
        key = (f, t, rt)
        
        if not f or not t or not rt: return
        
        rel["from"], rel["to"], rel["relation_type"] = f, t, rt
        rel["properties"] = props # Cập nhật lại properties đã được làm sạch
        
        if key not in edge_map:
            edge_map[key] = rel
        else:
            # Nếu đã tồn tại cạnh, tiến hành gộp properties để bảo tồn dữ liệu
            existing_props = edge_map[key].setdefault("properties", {})
            new_props = rel.get("properties", {})
            
            for k, v in new_props.items():
                if v and not existing_props.get(k):
                    existing_props[k] = v
                elif v and existing_props.get(k) and isinstance(v, str) and isinstance(existing_props[k], str):
                    # Tránh gộp chuỗi giống nhau
                    if v.lower() not in existing_props[k].lower():
                        existing_props[k] = existing_props[k] + " | " + v

    for r in existing_rels: 
        add_to_map(r, is_secondary=False) # File core định danh luôn được pass (chỉ lọc nội dung)
    for r in new_rels: 
        add_to_map(r, is_secondary=is_from_secondary_file)
    
    return list(edge_map.values())

def inject_missing_nodes(nodes, rels):
    """
    Tự động hoàn thiện Lược đồ (Ontology Auto-completion):
    Phát hiện các ID trong Relationships mà chưa được định nghĩa trong Nodes để tự động tạo mới.
    """
    existing_node_ids = {normalize_id(n.get("id", "")) for n in nodes if n.get("id")}
    
    # Ánh xạ tiền tố thành Label chuẩn theo Ontology YHCT
    prefix_to_label = {
        "B_": "Benh", "S_": "TrieuChung", "HC_": "HoatChat", 
        "DL_": "DuocLy", "CN_": "CongNang", "BT_": "BaiThuoc", 
        "VT_": "ViThuoc", "T_": "Tinh", "V_": "Vi", "K_": "Kinh",
        "NHOMBENH_": "NhomBenh", "G_": "DoiTuong"
    }

    for r in rels:
        for node_id in [r.get("from"), r.get("to")]:
            if not node_id: continue
            
            if node_id not in existing_node_ids:
                # Suy luận Label dựa trên tiền tố
                injected_label = "ThucThe"
                for prefix, label in prefix_to_label.items():
                    if str(node_id).startswith(prefix):
                        injected_label = label
                        break
                
                # Tạo Canonical Name cơ bản từ ID
                core_name = node_id.split("_", 1)[-1].replace("_", " ").title() if "_" in node_id else node_id
                
                nodes.append({
                    "id": node_id,
                    "label": injected_label,
                    "properties": {
                        "canonical_name": core_name
                    }
                })
                existing_node_ids.add(node_id)
                
    return nodes

def execute_patch(draft_json, logs_to_apply, blacklisted_ids):
    """Thiết quân luật Vá lỗi (Patch Execution)"""
    if "entity" in draft_json and "id" in draft_json["entity"]:
        draft_json["entity"]["id"] = normalize_id(draft_json["entity"]["id"])
    elif "entity_hub" in draft_json:
        draft_json["entity_hub"] = normalize_id(draft_json["entity_hub"])
        
    hub_id = draft_json.get("entity", {}).get("id") or draft_json.get("entity_hub", "")
    
    rels = draft_json.get("relationships", [])
    nodes = draft_json.get("nodes", [])
    
    # 1. ÉP CHUẨN HÓA ID TRƯỚC KHI VÁ
    for n in nodes:
        if "id" in n: n["id"] = normalize_id(n["id"])
    for r in rels:
        if "from" in r: r["from"] = normalize_id(r["from"])
        if "to" in r: r["to"] = normalize_id(r["to"])
        if "relation_type" in r: r["relation_type"] = str(r["relation_type"]).upper()

    # 2. LOẠI BỎ LỆNH ẢO GIÁC
    filtered_logs = [log for log in logs_to_apply if log.get("ma_loi_ref") not in blacklisted_ids]

    # 3. TIẾN HÀNH VÁ LỖI
    for cmd in filtered_logs:
        p = cmd.get("payload", {})
        action = cmd.get('han_dong')
        
        f_raw = str(p.get('from', ''))
        f_id = hub_id if ("_BAI_THUOC" not in f_raw and hub_id) else normalize_id(f_raw)
        t_id = normalize_id(p.get('to'))
        rt = str(p.get("relation_type", "")).strip().upper()
        
        # Bơm tiền tố nếu AI quên
        if rt == "CO_CHUA_HOAT_CHAT" and t_id and not t_id.startswith("HC_"): t_id = f"HC_{t_id}"
        if rt == "CO_TAC_DUNG_DUOC_LY" and t_id and not t_id.startswith("DL_"): t_id = f"DL_{t_id}"

        if action == "SUA_ID":
            old_id = normalize_id(p.get("source_id"))
            new_id = normalize_id(p.get("id_moi") or t_id)
            if not old_id or not new_id: continue
            for n in nodes:
                if n["id"] == old_id: n["id"] = new_id
            for r in rels:
                if r["from"] == old_id: r["from"] = new_id
                if r["to"] == old_id: r["to"] = new_id
            continue

        if action == "XOA_EDGE":
            rels = [r for r in rels if not (r['from'] == f_id and r['to'] == t_id)]
            continue

        if action in ["THEM_EDGE", "SUA_PROPERTIES"]:
            if not f_id or not t_id: continue
            if str(f_id).startswith("VI_THUOC_") and str(t_id).startswith("BT_"): f_id, t_id = t_id, f_id
            
            raw_props = p.get("gia_tri_moi") or {}
            if not rt: rt = "CHU_TRI_BENH" if str(t_id).startswith("B_") else "BAO_GOM_VI_THUOC"

            found = False
            for r in rels:
                if r["from"] == f_id and r["to"] == t_id:
                    r.setdefault("properties", {}).update(raw_props)
                    r["relation_type"] = rt
                    found = True
                    break
            
            if not found and action == "THEM_EDGE":
                rels.append({
                    "from": f_id, "to": t_id, "relation_type": rt,
                    "properties": raw_props, 
                    "source": {"source_id": p.get("source_id") or "STEP4_PATCH"},
                    "confidence_score": 1.0
                })

    # 4. CHỐT CHẶN CUỐI: SỬA LỖI GÁN LỘN, KHỬ TRÙNG LẶP & TỰ ĐỘNG THÊM NODE MỒ CÔI
    rels, nodes = fix_misassigned_remedy_ids(rels, nodes, hub_id)
    
    # Ép False vì ở giai đoạn patch này tất cả đã được coi là core
    rels = merge_and_deduplicate_edges(rels, [], is_from_secondary_file=False) 
    nodes = inject_missing_nodes(nodes, rels)
    
    draft_json["relationships"] = rels
    draft_json["nodes"] = nodes
    return draft_json

# ==========================================================
# 3. RUNNER: GỘP MẢNH, ĐỐI SOÁT VÀ TINH LUYỆN
# ==========================================================

def run_diamond_refiner():
    core_gold_files = sorted(glob.glob(os.path.join(GOLD_STEP2_DIR, "*_dinh_danh.json")), key=get_page_number)
    
    total = len(core_gold_files)
    telemetry_data = {
        "timestamp": str(os.popen('date').read().strip() if os.name != 'nt' else time.ctime()),
        "total_files_processed": total,
        "total_patches_proposed": 0,
        "total_patches_rejected_by_verifier": 0,
        "total_patches_applied": 0,
        "details": []
    }
    
    print(f"💎 STEP 4: SEMANTIC RE-ANCHORING ENGINE & REFINER ({total} vị thuốc)")
    print("="*80)

    for idx, core_path in enumerate(core_gold_files):
        try:
            base_name = os.path.basename(core_path).replace("_dinh_danh.json", "")
            
            output_path = os.path.join(DIAMOND_OUT_DIR, f"{base_name}.json")
            if os.path.exists(output_path):
                print(f"⏩ [{idx+1:03d}/{total:03d}] Bỏ qua: {base_name} (Đã hoàn thiện)")
                continue

            remedy_path = core_path.replace("_dinh_danh.json", "_bai_thuoc.json")
            pharma_path = core_path.replace("_dinh_danh.json", "_duoc_ly.json") 
            
            core_gold = robust_json_load(core_path)
            remedy_gold = robust_json_load(remedy_path)
            pharma_gold = robust_json_load(pharma_path) 
            
            # 🟢 THỰC THI MÀNG LỌC ĐỊNH TUYẾN KHI GỘP (True = File Phụ, Cấm DNA)
            combined_rels = core_gold.get("relationships", [])
            if remedy_gold: 
                combined_rels = merge_and_deduplicate_edges(combined_rels, remedy_gold.get("relationships", []), is_from_secondary_file=True)
            if pharma_gold: 
                combined_rels = merge_and_deduplicate_edges(combined_rels, pharma_gold.get("relationships", []), is_from_secondary_file=True)
            
            core_gold["relationships"] = combined_rels
            
            hub_id = normalize_id(core_gold["entity"]["id"])
            core_gold["entity"]["id"] = hub_id
            
            core_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_dinh_danh_LOG.json")
            remedy_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_bai_thuoc_LOG.json")
            pharma_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_duoc_ly_LOG.json")
            
            core_log = robust_json_load(core_log_path) or {"lenh_sua": []}
            remedy_log = robust_json_load(remedy_log_path) or {"lenh_sua": []}
            pharma_log = robust_json_load(pharma_log_path) or {"lenh_sua": []}
            
            all_step3_patches = core_log.get("lenh_sua", []) + remedy_log.get("lenh_sua", []) + pharma_log.get("lenh_sua", [])

            # Lấy data Bronze gốc (hiện tại không còn gọi AI nên data này có thể không bắt buộc, 
            # nhưng vẫn giữ nguyên theo yêu cầu không cắt xén cấu trúc cũ)
            bronze_matches = glob.glob(os.path.join(BRONZE_DIR, f"{base_name}.json"))
            if not bronze_matches: 
                print(f"⚠️ Thiếu file Bronze gốc cho {base_name}")
                continue
            bronze_data = robust_json_load(bronze_matches[0])
            if isinstance(bronze_data, list): bronze_data = bronze_data[0]

            print(f" 🧪 [{idx+1:03d}/{total:03d}] {hub_id:<25} | Patches: {len(all_step3_patches)} |", end=" ", flush=True)

            # KHÔNG GỌI AI NỮA -> Mặc định chấp nhận toàn bộ patch
            blacklisted_ids = []

            # Ghi nhận Telemetry học thuật
            proposed = len(all_step3_patches)
            rejected = len(blacklisted_ids) # Sẽ luôn là 0 vì không còn filter AI
            applied = proposed - rejected
            telemetry_data["total_patches_proposed"] += proposed
            telemetry_data["total_patches_rejected_by_verifier"] += rejected
            telemetry_data["total_patches_applied"] += applied
            telemetry_data["details"].append({
                "entity": hub_id, "proposed": proposed, "rejected": rejected, "applied": applied
            })

            # THỰC THI DUNG HỢP VÀ TÁI ĐỊNH DANH
            final_diamond = execute_patch(core_gold, all_step3_patches, blacklisted_ids)
            final_diamond = extract_dosage_fix(final_diamond)
            final_diamond = finalize_json(final_diamond)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(final_diamond, f, ensure_ascii=False, indent=2)
            
            print(f"Gộp thành công (Áp dụng {applied}/{proposed} lệnh).")

        except Exception as e:
            print(f"\n ❌ LỖI NGHIÊM TRỌNG TẠI {core_path}:\n{traceback.format_exc()}")

    # Lưu báo cáo Telemetry
    with open(TELEMETRY_FILE, "w", encoding="utf-8") as f:
        json.dump(telemetry_data, f, ensure_ascii=False, indent=2)

    print("="*80)
    print(f"✅ HOÀN TẤT GIAI ĐOẠN 4: SEMANTIC RE-ANCHORING ENGINE")
    print(f"📊 Thống kê kiểm toán:")
    print(f"   - Tổng lệnh đề xuất (Proposed) : {telemetry_data['total_patches_proposed']}")
    print(f"   - Tổng lệnh bị hủy (Hallucinated): {telemetry_data['total_patches_rejected_by_verifier']} (Đã tắt AI Audit)")
    print(f"   - Lệnh được áp dụng (Applied)  : {telemetry_data['total_patches_applied']}")
    print(f"📂 Dữ liệu Diamond sẵn sàng tại: {DIAMOND_OUT_DIR}")

if __name__ == "__main__":
    run_diamond_refiner()