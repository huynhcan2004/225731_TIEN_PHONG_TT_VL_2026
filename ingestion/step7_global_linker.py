"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 7 — DIAMOND GLOBAL LINKER (BẢN CHUẨN KÉP - BULLETPROOF)    ║
║  Chức năng: Đồng bộ hóa toàn cục, bảo vệ Bài thuốc (BT_), dùng   ║
║  100% nhãn tiếng Việt và VÉT CẠN toàn bộ mô tả vào Hub Node.     ║
║  HOTFIX 1: Bảo tồn đường link đa tầng (HC -> DL, CN -> B).       ║
║  HOTFIX 2: Soft-Fix đổi VT_ thành B_ cho các cạnh CHU_TRI bị sai.║
║  HOTFIX 3: Cưỡng chế Hub Node phải mang tiền tố VT_ (Chống lấn át)║
║  HOTFIX 4: Cứu các "Nút mồ côi" không có quan hệ (Orphan Nodes). ║
║  HOTFIX 5: Cưỡng chế đảo chiều quan hệ nếu AI xác định ngược.    ║
║  HOTFIX 6: Chuẩn hóa đơn vị đo lường trước khi bọc LaTeX.        ║
║  HOTFIX 7: Giải quyết xung đột đồng âm (Prefix-aware mapping).   ║
║  HOTFIX 8: BỘ LỌC THÔNG MINH - Sửa lỗi sai tiền tố (như CN_CAY). ║
║  HOTFIX 9: DIỆT TIỀN TỐ KÉP TẬN GỐC - Chống bẫy từ khóa sinh B_DL║
║  HOTFIX 10: AUTO-SYNC RELATION - Ép chuẩn Schema y khoa tuyệt đối║
║  HOTFIX 11: DEDUPLICATE EDGES - Khử trùng lặp và gộp ngữ cảnh    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
import re

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import remove_accents, apply_latex_format

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
INPUT_DIR = settings.DIR_GOLD_VALIDATED 
DICTIONARY_PATH = settings.FILE_DICT_FINAL
OUTPUT_DIR = settings.DIR_GOLD_LINKED

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================================
# 🛠️ HÀM CHUẨN HÓA (KẾ THỪA KỶ LUẬT THÉP & SMART FILTER)
# ==========================================================

def normalize_final_id(cid):
    """Cưỡng ép ID tuân thủ Prefix Diamond và diệt rác nội hàm."""
    if not cid: return "UNKNOWN"
    
    # 1. Chuyển chữ hoa, bào sạch dấu bằng hàm chuẩn từ helpers
    cid = remove_accents(str(cid).upper().strip())
    
    # 2. Ép chuẩn tiền tố Vị thuốc ở đầu chuỗi (BẢO VỆ DƯỢC LÝ DL_ KHỎI LỖI MATCHING)
    if not cid.startswith("DL_"):
        # Chỉ replace nếu ID bắt đầu bằng D_, VI_, v.v.. mà không phải là DL_
        cid = re.sub(r'^(VI_THUOC_|DUOC_LIEU_|CAY_|D_|VI_)', 'VT_', cid)
    
    # 3. 🚨 LOGIC CHỐNG LỒNG TIỀN TỐ TỪ RÁC TEXT
    noise_pattern = r'(BT_|VT_|CN_|DL_|B_|S_)(VI_THUOC_|THUOC_|CAY_)'
    cid = re.sub(noise_pattern, r'\1', cid)
    
    # 4. --- BẢO VỆ TIỀN TỐ CHUYÊN MÔN KHỎI "BẪY TỪ KHÓA" ---
    # Kiểm tra xem ID ĐÃ CÓ tiền tố chuyên môn hợp lệ chưa
    has_valid_prefix = re.match(r'^(B|S|CN|DL|HC|VT|BT|K|T|V)_', cid)
    
    if not has_valid_prefix:
        # Nếu chưa có tiền tố nào, mới được phép dựa vào chữ "BENH" hoặc "TRIEU_CHUNG" để gắn B_ hoặc S_
        if "TRIEU_CHUNG" in cid: 
            cid = "S_" + cid.replace("TRIEU_CHUNG_", "")
        elif "BENH" in cid: 
            cid = "B_" + cid.replace("BENH_", "")
    else:
        # Nếu đã có (VD: DL_CHUA_BENH_NGOAI_DA), thì chỉ cắt bỏ từ thừa cho gọn, KHÔNG GẮN THÊM B_
        cid = cid.replace("BENH_", "").replace("TRIEU_CHUNG_", "")
        
    # 5. --- HOTFIX 9: DIỆT TIỀN TỐ KÉP ĐỆ QUY (DOUBLE PREFIX DESTROYER) ---
    # Vòng lặp xóa tiền tố thừa bên ngoài (VD: B_DL_ -> DL_, CN_DL_ -> DL_, B_CN_ -> CN_)
    while True:
        if re.match(r'^(B|S|CN|DL|HC|VT|K|T|V|BT)_(B|S|CN|DL|HC|VT|K|T|V|BT)_', cid):
            # Giữ lại nhóm 2 (tiền tố lõi bên trong), xóa nhóm 1 (tiền tố bị lồng bên ngoài)
            cid = re.sub(r'^(B|S|CN|DL|HC|VT|K|T|V|BT)_((B|S|CN|DL|HC|VT|K|T|V|BT)_)', r'\2', cid)
        else:
            break
            
    # 6. --- HOTFIX 8: SMART SEMANTIC FILTER (NẮN LẠI TIỀN TỐ BỊ SAI BẢN CHẤT) ---
    # Xử lý các ca AI nhầm lẫn giữa Công năng, Vị, Tính và Quy Kinh (VD: CN_CAY -> V_CAY)
    core_part = cid.split('_', 1)[-1].lower() if '_' in cid else cid.lower()
    
    if cid.startswith("CN_"):
        # Trục VỊ
        if core_part in ["cay", "ngot", "dang", "chua", "man", "nhat", "chat"] or core_part.startswith("vi_"):
            cid = cid.replace("CN_", "V_", 1)
        # Trục TÍNH
        elif core_part in ["han", "nhiet", "on", "luong", "binh"] or core_part.startswith("tinh_"):
            cid = cid.replace("CN_", "T_", 1)
        # Trục KINH MẠCH
        elif core_part in ["can", "tam", "ty", "phe", "than", "vi", "dom", "dai_trang", "tieu_trang", "bang_quang", "tam_tieu", "tam_bao"] or core_part.startswith("kinh_"):
            cid = cid.replace("CN_", "K_", 1)
            
    # 7. Dọn dẹp dấu gạch dưới thừa
    cid = re.sub(r'_+', '_', cid)
    return cid.strip('_')

def finalize_formatting(data):
    """Duyệt đệ quy qua toàn bộ Dictionary để format từng value một bằng apply_latex_format"""
    if isinstance(data, dict):
        return {k: finalize_formatting(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [finalize_formatting(item) for item in data]
    elif isinstance(data, str):
        return apply_latex_format(data)
    else:
        return data

# ==========================================================
# 🧠 TRÌNH ĐỒNG BỘ HÓA (CORE LOGIC BULLETPROOF)
# ==========================================================

def run_step_7_diamond_linker():
    print(f"🚀 Giai đoạn 7: Đang khởi động trình Vét cạn & Đồng bộ dữ liệu...")
    
    if not os.path.exists(DICTIONARY_PATH):
        print(f"❌ Lỗi: Không thấy từ điển tại {DICTIONARY_PATH}")
        return

    # 1. TẢI TỪ ĐIỂN VÀ XÂY DỰNG PREFIX-AWARE LOOKUP
    with open(DICTIONARY_PATH, "r", encoding="utf-8") as f:
        dict_data = json.load(f)
    
    lookup = {}
    entity_info = {}

    print(f"📚 Đang nạp {len(dict_data.get('dictionary', []))} thực thể từ Master Dictionary...")

    # --- NÂNG CẤP CHỐNG GỘP NHẦM TRONG LOOKUP (Prefix-aware) ---
    for ent in dict_data.get("dictionary", []):
        cid = normalize_final_id(ent["canonical_id"])
        prefix = cid.split('_')[0] + "_" if "_" in cid else ""
        
        keys_low_priority = {ent["canonical_name"].lower()}
        keys_low_priority.update([str(r).lower().strip() for r in ent.get("raw_found", [])])
        keys_low_priority.update([str(a).lower().strip() for a in ent.get("aliases", [])])
        
        for k in keys_low_priority:
            if k:
                # HOTFIX 7: Tra cứu theo cụm (Tên + Prefix) để chống đồng âm
                lookup_key_with_prefix = f"{prefix}{k}"
                if lookup_key_with_prefix not in lookup:
                    lookup[lookup_key_with_prefix] = cid
                
                # Vẫn giữ lookup bằng tên thuần túy cho các trường hợp không có prefix mồi
                if k not in lookup:
                    lookup[k] = cid

    for ent in dict_data.get("dictionary", []):
        cid = normalize_final_id(ent["canonical_id"])
        entity_info[cid] = {
            "name": ent["canonical_name"], 
            "aliases": ent.get("aliases", [])
        }
        # Ghi đè bằng ID chuẩn để đảm bảo độ chính xác tuyệt đối
        lookup[cid.lower()] = cid
        
        prefix = cid.split('_')[0] + "_" if "_" in cid else ""
        lookup[f"{prefix}{cid.lower()}"] = cid

    # 2. ĐỒNG BỘ HÓA FILE
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    print(f"🔗 Đang xử lý đồng bộ tri thức cho {len(files)} file...")
    
    processed_count = 0

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # --- A. Hub Entity (Cây thuốc chủ đạo của file) ---
            old_hub_id = data.get("entity", {}).get("id", "")
            raw_hub_name = data.get("entity", {}).get("ten_raw", "").lower()
            entity_type = data.get("entity", {}).get("entity_type", "")
            
            # Khử nhiễu tiền tố ID cũ bằng Smart Filter trước khi tra cứu
            clean_old_hub_id = normalize_final_id(old_hub_id)
            
            # Tra cứu Hub ID (Ưu tiên VT_)
            new_hub_id = lookup.get(f"VT_{clean_old_hub_id.lower()}", lookup.get(clean_old_hub_id.lower(), lookup.get(f"VT_{raw_hub_name}", clean_old_hub_id)))
            
            # --- HOTFIX 3: BẢO VỆ HUB NODE KHỎI "IDENTITY THEFT" ---
            if entity_type == "VI_THUOC" and not new_hub_id.startswith("VT_"):
                new_hub_id = "VT_" + remove_accents(data.get("entity", {}).get("ten_raw", ""))
            # --------------------------------------------------------

            data["entity"]["id"] = new_hub_id
            if new_hub_id in entity_info:
                data["entity"]["canonical_name"] = entity_info[new_hub_id]["name"]
                data["entity"]["display_name"] = entity_info[new_hub_id]["name"]
            else:
                fallback_name = data.get("entity", {}).get("ten_raw", "")
                data["entity"]["canonical_name"] = fallback_name.title() if fallback_name else new_hub_id
                data["entity"]["display_name"] = data["entity"]["canonical_name"]

            # --- B. Cập nhật Đặc tính YHCT (Tính/Vị/Quy Kinh) ---
            for claim in data.get("claims", []):
                dt = claim.get("dac_tinh_yhct", {})
                if dt:
                    for field in ["vi", "tinh", "quy_kinh"]:
                        if field in dt and dt[field]:
                            vals = dt[field] if isinstance(dt[field], list) else [dt[field]]
                            
                            prefix = "V_" if field == "vi" else ("T_" if field == "tinh" else "K_")
                            mapped = [lookup.get(f"{prefix}{str(v).lower().strip()}", lookup.get(str(v).lower().strip(), normalize_final_id(v))) for v in vals]
                            
                            dt[field] = list(set(mapped)) if isinstance(dt[field], list) else mapped[0]

            # --- C. Cập nhật Mối quan hệ (BẢO TỒN PROPERTIES & CHỐNG PHẲNG HÓA & KHỬ TRÙNG) ---
            seen_edges = {} # Từ điển để khử trùng lặp cạnh (Hotfix 11)
            
            for rel in data.get("relationships", []):
                
                # BẢO TỒN PROPERTIES HIỆN TẠI (Không ghi đè)
                rel.setdefault("properties", {})
                
                # Xử lý Relation Type để làm cơ sở ép hướng
                rel_type = str(rel.get("relation_type", "")).upper()
                
                # 1. XỬ LÝ 'to' (Node đích) 
                to_raw = str(rel.get("to", ""))
                # Lọc an toàn ID qua Smart Filter trước
                norm_to_id = normalize_final_id(to_raw)
                core_to = norm_to_id.split("_", 1)[-1].replace("_", " ").lower() if "_" in norm_to_id else norm_to_id.lower()
                prefix_to = norm_to_id.split('_')[0] + "_" if "_" in norm_to_id else ""

                new_to_id = lookup.get(norm_to_id.lower(), lookup.get(f"{prefix_to}{core_to}", norm_to_id))
                
                # --- HOTFIX 2: CHỮA CHÁY QUAN HỆ CHU_TRI TRỎ VÀO VỊ THUỐC ---
                if rel_type.startswith("CHU_TRI") and new_to_id.startswith("VT_"):
                    safe_core = remove_accents(core_to).upper()
                    # An toàn hơn: bọc qua normalize_final_id để chặn đứng sinh ra tiền tố kép nếu safe_core là DL_...
                    new_to_id = normalize_final_id(f"B_{safe_core}")
                # ---------------------------------------------------

                # 2. XỬ LÝ 'from' (Node nguồn)
                from_raw = str(rel.get("from", ""))
                norm_from_id = normalize_final_id(from_raw)
                core_from = norm_from_id.split("_", 1)[-1].replace("_", " ").lower() if "_" in norm_from_id else norm_from_id.lower()
                prefix_from = norm_from_id.split('_')[0] + "_" if "_" in norm_from_id else ""
                
                mapped_from = lookup.get(norm_from_id.lower(), lookup.get(f"{prefix_from}{core_from}", norm_from_id))
                
                # --- HOTFIX 1: BẢO TỒN LIÊN KẾT ĐA TẦNG (Chống Phẳng Hóa) ---
                if from_raw == old_hub_id or from_raw.lower() == raw_hub_name:
                    new_from_id = new_hub_id
                elif not mapped_from:
                    new_from_id = new_hub_id
                else:
                    new_from_id = mapped_from
                # ---------------------------------------------------
                
                # --- HOTFIX 5: CƯỠNG CHẾ ĐẢO CHIỀU QUAN HỆ NẾU AI LÀM NGƯỢC ---
                # Ví dụ AI làm: B_DAU_DAU -> CHU_TRI -> VT_ICH_MAU
                if rel_type.startswith("CHU_TRI"):
                    if new_from_id.startswith(("B_", "S_")) and new_to_id.startswith(("VT_", "BT_", "HC_", "DL_")):
                        new_from_id, new_to_id = new_to_id, new_from_id
                
                if rel_type == "BAO_GOM_VI_THUOC":
                    if new_from_id.startswith("VT_") and new_to_id.startswith("BT_"):
                        new_from_id, new_to_id = new_to_id, new_from_id
                # -----------------------------------------------------------

                # --- HOTFIX 10: AUTO-SYNC RELATION TYPE THEO SCHEMA RULES ---
                # Ép chuẩn tên quan hệ 1:1 theo tiền tố đích và nguồn, loại bỏ mọi ảo giác AI
                if new_to_id.startswith("CN_"):
                    rel_type = "CO_CONG_NANG"
                elif new_to_id.startswith("DL_"):
                    rel_type = "CO_TAC_DUNG_DUOC_LY"
                elif new_to_id.startswith("HC_"):
                    rel_type = "CO_CHUA_HOAT_CHAT"
                elif new_to_id.startswith("T_"):
                    rel_type = "CO_TINH"
                elif new_to_id.startswith("V_"):
                    rel_type = "CO_VI"
                elif new_to_id.startswith("K_"):
                    rel_type = "QUY_KINH"
                elif new_to_id.startswith("B_"):
                    # Nếu là kiêng kỵ thì giữ nguyên, còn lại tất cả về CHU_TRI_BENH
                    if "KIENG" in rel_type or "KY" in rel_type:
                        rel_type = "KIENG_KY"
                    else:
                        rel_type = "CHU_TRI_BENH"
                elif new_to_id.startswith("S_"):
                    if "KIENG" in rel_type or "KY" in rel_type:
                        rel_type = "KIENG_KY"
                    else:
                        rel_type = "CHU_TRI_TRIEU_CHUNG"
                elif new_to_id.startswith("G_"):
                    rel_type = "KIENG_KY"
                elif new_from_id.startswith("BT_") and new_to_id.startswith("VT_"):
                    rel_type = "BAO_GOM_VI_THUOC"
                elif new_from_id.startswith(("VT_", "BT_")) and new_to_id.startswith(("VT_", "BT_")):
                    # Vị thuốc kiêng kỵ vị thuốc khác
                    if "KIENG" in rel_type or "KY" in rel_type:
                        rel_type = "KIENG_KY"
                # -----------------------------------------------------------

                rel["relation_type"] = rel_type
                rel["from"] = new_from_id
                rel["to"] = new_to_id
                
                # Làm giàu Properties an toàn
                if new_to_id in entity_info:
                    rel["properties"]["to_display_name"] = entity_info[new_to_id]["name"]
                    if entity_info[new_to_id]["aliases"]:
                        rel["properties"]["to_aliases"] = ", ".join(entity_info[new_to_id]["aliases"])
                else:
                    rel["properties"]["to_display_name"] = new_to_id.split("_", 1)[-1].replace("_", " ").title()
                
                # --- HOTFIX 11: KHỬ TRÙNG LẶP CẠNH (DEDUPLICATE EDGES) ---
                edge_key = (new_from_id, rel_type, new_to_id)
                
                if edge_key not in seen_edges:
                    seen_edges[edge_key] = rel
                else:
                    # Cạnh đã tồn tại -> Gộp mô tả chi tiết để tránh mất ngữ cảnh
                    old_desc = str(seen_edges[edge_key]["properties"].get("mo_ta_chi_tiet", ""))
                    new_desc = str(rel["properties"].get("mo_ta_chi_tiet", ""))
                    
                    if new_desc and new_desc not in old_desc:
                        combined_desc = (old_desc + " | " + new_desc).strip(" | ")
                        seen_edges[edge_key]["properties"]["mo_ta_chi_tiet"] = combined_desc
                # -----------------------------------------------------------
                
            # Đẩy lại danh sách cạnh đã được khử trùng lặp
            data["relationships"] = list(seen_edges.values())

            # --- D. Xây dựng lại Nodes (Nhãn Tiếng Việt 100% & VÉT CẠN DỮ LIỆU) ---
            all_ids = set()
            for r in data["relationships"]:
                all_ids.update([r["from"], r["to"]])
            
            # --- HOTFIX 4: CỨU CÁC NÚT MỒ CÔI (ORPHAN NODES) TỪ MẢNG CŨ ---
            for old_node in data.get("nodes", []):
                old_node_id = str(old_node.get("id", ""))
                norm_old_node = normalize_final_id(old_node_id)
                core_old = norm_old_node.split("_", 1)[-1].replace("_", " ").lower() if "_" in norm_old_node else norm_old_node.lower()
                prefix_old = norm_old_node.split('_')[0] + "_" if "_" in norm_old_node else ""
                
                mapped_old_id = lookup.get(norm_old_node.lower(), lookup.get(f"{prefix_old}{core_old}", norm_old_node))
                if mapped_old_id:
                    all_ids.add(mapped_old_id)
            # -------------------------------------------------------------
            
            rebuilt_nodes = []
            for eid in sorted(list(all_ids)):
                if not eid: continue
                
                # Phân loại Label chính xác theo Prefix Diamond
                label = "ThucThe"
                if eid.startswith("BT_"): label = "BaiThuoc"
                elif eid.startswith("VT_"): label = "ViThuoc"
                elif eid.startswith("B_"): label = "Benh"
                elif eid.startswith("S_"): label = "TrieuChung"
                elif eid.startswith("G_"): label = "DoiTuong" 
                elif eid.startswith("HC_"): label = "HoatChat"
                elif eid.startswith("DL_"): label = "DuocLy"
                elif eid.startswith("CN_"): label = "CongNang"
                elif eid.startswith("K_"): label = "KinhMach"
                elif eid.startswith(("V_", "T_")): label = "TinhVi"

                node_item = {"id": eid, "label": label, "properties": {}}
                
                # Điền thông tin tên và bí danh
                if eid in entity_info:
                    node_item["properties"]["canonical_name"] = entity_info[eid]["name"]
                    node_item["properties"]["aliases"] = entity_info[eid]["aliases"]
                else:
                    node_item["properties"]["canonical_name"] = eid.split("_", 1)[-1].replace("_", " ").title()

                # ========================================================
                # TRỌNG TÂM: VÉT CẠN DỮ LIỆU VÀO HUB NODE (CÂY THUỐC)
                # ========================================================
                if eid == new_hub_id:
                    # 1. Lấy thông tin từ block entity gốc
                    entity_props = data.get("entity", {}).get("properties", {})
                    for k, v in entity_props.items():
                        if v: node_item["properties"][k] = str(v)
                    
                    ten_khoa_hoc = data.get("entity", {}).get("ten_khoa_hoc", "")
                    if ten_khoa_hoc: node_item["properties"]["ten_khoa_hoc"] = str(ten_khoa_hoc)
                    
                    ho_thuc_vat = data.get("entity", {}).get("ho_thuc_vat", "")
                    if ho_thuc_vat: node_item["properties"]["ho_thuc_vat"] = str(ho_thuc_vat)

                    # 2. Lấy thông tin mô tả chi tiết từ claims
                    claims = data.get("claims", [])
                    if claims:
                        mo_ta = claims[0].get("mo_ta_theo_nguon", {})
                        for key, val in mo_ta.items():
                            if val and val != [] and val != "": 
                                node_item["properties"][key] = str(val)
                # ========================================================

                rebuilt_nodes.append(node_item)
            
            data["nodes"] = rebuilt_nodes
            
            # --- E. Lưu kết quả ---
            data = finalize_formatting(data)
            
            with open(os.path.join(OUTPUT_DIR, os.path.basename(path)), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            processed_count += 1
            
        except Exception as e:
            print(f" ⚠️ Lỗi nghiêm trọng tại file {os.path.basename(path)}: {str(e)}")

    print(f"---")
    print(f"✅ HOÀN TẤT: Đã bảo tồn liên kết đa tầng & vét cạn dữ liệu thành công cho {processed_count} file.")
    print(f"📁 Dữ liệu cuối cùng sẵn sàng tại: {OUTPUT_DIR}")

if __name__ == "__main__":
    run_step_7_diamond_linker()