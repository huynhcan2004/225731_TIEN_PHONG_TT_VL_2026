import os
import json
import re
import glob
import traceback
from google import genai
from google.genai import types

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import robust_json_load, normalize_id, remove_accents

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

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# ==========================================================
# 2. PROMPT FORENSIC VERIFIER (CHỈ THẨM ĐỊNH - KHÔNG SÁNG TẠO)
# ==========================================================
P4_REVIEW_PROMPT = """
VAI TRÒ: Senior Forensic Verifier (Chuyên gia Thẩm định Pháp chứng).
NHIỆM VỤ: Kiểm tra xem các lệnh vá lỗi từ Step 3 có phải là 'ảo giác' không bằng cách đối soát với BRONZE_TEXT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. QUY TẮC THẨM ĐỊNH (STRICT VERIFICATION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 🛑 CHỈ KIỂM TRA - KHÔNG BỔ SUNG:
   - Bạn chỉ được phép xem xét các lệnh có sẵn trong 'STEP3_PROPOSED_PATCHES'.
   - TUYỆT ĐỐI CẤM trích xuất thêm bất kỳ thông tin nào khác từ BRONZE_TEXT.
   - Bạn là người thẩm định, KHÔNG PHẢI người đi tìm thông tin thiếu.

2. 🛑 DIỆT ẢO GIÁC:
   - Nếu một lệnh sửa của Step 3 yêu cầu thêm thông tin mà thông tin đó KHÔNG CÓ THẬT trong văn bản Bronze -> Ra lệnh 'DISCARD' (Bỏ qua) bằng cách đưa 'ma_loi_ref' vào danh sách 'lenh_bi_loai_bo'.
   - Nếu bằng chứng trích dẫn trong 'bang_chung_bronze' bị AI Step 3 tự bịa ra hoặc lấy râu ông nọ cắm cằm bà kia -> Ra lệnh 'DISCARD'.

3. 🛑 BẢO VỆ ID:
   - Giữ nguyên toàn bộ ID từ Step 3. Không được tự ý 'làm đẹp' ID (Ví dụ: Step 3 đưa ra K_CAN, cấm tự đổi thành KINH_CAN).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. YÊU CẦU ĐẦU RA (JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Chỉ trả về danh sách các ID (ma_loi_ref) của lệnh sửa bị loại bỏ (vì ảo giác).
- Nếu tất cả các lệnh của Step 3 đều hợp lệ và đúng pháp chứng, trả về mảng rỗng.
- Định dạng JSON: 
{ 
  "lenh_bi_loai_bo": [ "ma_loi_ref_1", "ma_loi_ref_2" ] 
}
"""

# ==========================================================
# 3. ENGINE VÁ LỖI VÀ CHUẨN HÓA (CORE LOGIC)
# ==========================================================

def finalize_json(data):
    """Làm sạch LaTeX và chuẩn hóa hiển thị cuối cùng"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json_str = json_str.replace('\\\\%', '%').replace('\\%', '%')
    
    # Bọc LaTeX số + đơn vị phổ biến
    pattern = r'(?<![\$\d])(\d+(?:[.,-]\d+)?)\s*(g|ml|mg|%|°C|bát|phần|ống|muỗng|kilôgam)\b(?!\$)'
    json_str = re.sub(pattern, r'$\1\2$', json_str)
    
    # Escape duy nhất cho % trong LaTeX
    json_str = json_str.replace('%', '\\\\%')
    return json.loads(json_str)

def extract_dosage_fix(data):
    """
    Hàm bóc tách liều lượng tổng quát: 
    Tìm đích danh từng vị thuốc trong đoạn mô tả và lấy số lượng tương ứng của nó.
    """
    rels = data.get("relationships", [])
    
    # Regex chuẩn cho liều lượng LaTeX (số, dải số, đơn vị)
    dosage_pattern = r'\$(\d+[\d\.,-]*\s*[a-zA-Z%°C/\\^]*)\$'

    for r in rels:
        # Chỉ xử lý các cạnh thành phần bài thuốc
        if r.get("relation_type") == "BAO_GOM_VI_THUOC":
            props = r.get("properties", {})
            
            # Chỉ vá nếu lieu_luong rỗng và mo_ta_chi_tiet có dữ liệu
            if not props.get("lieu_luong") and props.get("mo_ta_chi_tiet"):
                desc = str(props["mo_ta_chi_tiet"])
                to_id = str(r.get("to", ""))
                
                # 1. TRÍCH XUẤT TÊN LÕI TỪ ID (Dành cho mọi vị thuốc)
                # Ví dụ: VT_NGAI_DIEP -> NGAI DIEP, VI_THUOC_ICH_MAU -> ICH MAU
                core_name = to_id.replace("VI_THUOC_", "").replace("VT_", "").replace("_", " ").lower()
                
                # Đã thay thế remove_accents_lower bằng hàm remove_accents từ utils.helpers
                desc_lower = remove_accents(desc).lower()
                core_lower = remove_accents(core_name).lower()
                
                # 2. TÌM VỊ TRÍ CỦA VỊ THUỐC ĐÓ TRONG VĂN BẢN
                idx = desc_lower.find(core_lower)
                
                if idx != -1:
                    # 3. QUÉT PHẠM VI HẸP (50 ký tự sau tên vị thuốc)
                    # Cách này giúp Ngải diệp lấy đúng số của Ngải diệp, không lấy nhầm của Ích mẫu
                    substring = desc[idx : idx + 60] 
                    match = re.search(dosage_pattern, substring)
                    if match:
                        props["lieu_luong"] = match.group(0)
                
                # 4. CƠ CHẾ DỰ PHÒNG (Nếu tên bị AI viết khác đi một chút)
                if not props.get("lieu_luong"):
                    # Nếu trong đoạn mô tả chỉ có duy nhất 1 liều lượng, lấy luôn
                    all_matches = re.findall(dosage_pattern, desc)
                    if len(all_matches) == 1:
                        props["lieu_luong"] = all_matches[0]

            r["properties"] = props
            
    data["relationships"] = rels
    return data

# ==========================================================
# CẬP NHẬT TRONG STEP 4: MÀNG LỌC ẢO GIÁC & ÉP ID CHUẨN ĐA TẦNG
# ==========================================================

def execute_patch(draft_json, logs_to_apply, blacklisted_ids):
    # 1. Chuẩn hoá ID của thực thể gốc (Entity Hub) ngay lập tức
    if "entity" in draft_json and "id" in draft_json["entity"]:
        draft_json["entity"]["id"] = normalize_id(draft_json["entity"]["id"])
    elif "entity_hub" in draft_json:
        draft_json["entity_hub"] = normalize_id(draft_json["entity_hub"])
        
    hub_id = draft_json.get("entity", {}).get("id") or draft_json.get("entity_hub", "")
    
    rels = draft_json.get("relationships", [])
    nodes = draft_json.get("nodes", [])
    
    # 2. LOẠI BỎ LỆNH ẢO GIÁC (Bị AI Step 4 bắt được)
    filtered_logs = [log for log in logs_to_apply if log.get("ma_loi_ref") not in blacklisted_ids]

    # 3. ÉP CHUẨN HÓA ID CHO DỮ LIỆU GỐC TRƯỚC KHI VÁ
    # Điều này đảm bảo file xuất ra sạch bóng chữ thường và dấu tiếng Việt
    for n in nodes:
        if "id" in n: n["id"] = normalize_id(n["id"])
        
    for r in rels:
        if "from" in r: r["from"] = normalize_id(r["from"])
        if "to" in r: r["to"] = normalize_id(r["to"])
        if "relation_type" in r: r["relation_type"] = str(r["relation_type"]).upper()
    
    patch_map = {}
    for cmd in filtered_logs:
        p = cmd.get("payload", {})
        action = cmd.get('han_dong')
        
        # CHUẨN HÓA NGAY KHI ĐỌC PAYLOAD TỪ LOG
        source_id = normalize_id(p.get('source_id'))
        
        # BỘ LỌC THÔNG MINH: Nếu 'from' thiếu tiền tố mỏ neo, ép về hub_id
        f_raw = str(p.get('from', ''))
        if "_BAI_THUOC" not in f_raw and hub_id:
            f_id = hub_id
        else:
            f_id = normalize_id(f_raw)
            
        t_id = normalize_id(p.get('to'))
        rt = str(p.get("relation_type", "")).strip().upper()
        
        # Tự động chèn tiền tố cho Hoạt chất/Dược lý nếu AI Step 3 quên
        if rt == "CO_CHUA_HOAT_CHAT" and t_id and not t_id.startswith("HC_"):
            t_id = f"HC_{t_id}"
        if rt == "CO_TAC_DUNG_DUOC_LY" and t_id and not t_id.startswith("DL_"):
            t_id = f"DL_{t_id}"
        
        # Ghi đè payload để dùng ở logic vá bên dưới
        p["from"] = f_id
        p["to"] = t_id
        p["relation_type"] = rt
        
        if action in ["SUA_ID", "XOA_RAC"]:
            key = (source_id, action)
        else:
            key = (f_id, t_id, action)
        patch_map[key] = cmd

    for key, cmd in patch_map.items():
        action = cmd.get("han_dong")
        p = cmd.get("payload", {})

        if action == "SUA_ID":
            # Chuẩn hóa ID để map chính xác
            old_id = normalize_id(p.get("source_id"))
            new_id = normalize_id(p.get("id_moi") or p.get("to"))
            if not old_id or not new_id: continue
            for n in nodes:
                if n["id"] == old_id: n["id"] = new_id
            for r in rels:
                if r["from"] == old_id: r["from"] = new_id
                if r["to"] == old_id: r["to"] = new_id
            continue

        if action == "XOA_EDGE":
            f_id = p.get('from')
            t_id = p.get('to')
            # Vì rels đã được normalize ở đầu hàm, ta có thể so sánh trực tiếp
            rels = [r for r in rels if not (r['from'] == f_id and r['to'] == t_id)]
            continue

        if action in ["THEM_EDGE", "SUA_PROPERTIES"]:
            # Lấy ID đã qua màng lọc chuẩn hóa ở trên
            f_id = p.get('from')
            t_id = p.get('to')
            if not f_id or not t_id: continue
            
            if str(f_id).startswith("VI_THUOC_") and str(t_id).startswith("BT_"):
                f_id, t_id = t_id, f_id

            raw_props = p.get("gia_tri_moi") or {}
            rt = p.get("relation_type") or ("CHU_TRI_BENH" if str(t_id).startswith("B_") else "BAO_GOM_VI_THUOC")

            found = False
            for r in rels:
                if r["from"] == f_id and r["to"] == t_id:
                    # CHỈ UPDATE PROPERTIES, GIỮ NGUYÊN CONFIDENCE_SCORE CŨ
                    r.setdefault("properties", {}).update(raw_props)
                    r["relation_type"] = rt
                    found = True
                    break
            
            if not found and action == "THEM_EDGE":
                rels.append({
                    "from": f_id, "to": t_id, "relation_type": rt,
                    "properties": raw_props, 
                    "source": {"source_id": p.get("source_id") or "STEP4_PATCH"},
                    "confidence_score": 1.0  # Gán mặc định 1.0 cho các cạnh do Audit thêm vào
                })

    draft_json["relationships"] = rels
    draft_json["nodes"] = nodes
    return draft_json

# ==========================================================
# 4. RUNNER: GỘP 3 FILE VÀ TINH LUYỆN
# ==========================================================

def run_diamond_refiner():
    # 1. Lấy danh sách các file Core (Loại trừ Bài thuốc và Dược lý)
    all_gold_files = sorted(glob.glob(os.path.join(GOLD_STEP2_DIR, "*.json")))
    core_gold_files = [f for f in all_gold_files if "_BAI_THUOC.json" not in f and "_DUOC_LY.json" not in f]
    
    total = len(core_gold_files)
    print(f"💎 STEP 4: DIAMOND CONSOLIDATION & REFINER ({total} vị thuốc)")
    print("="*60)

    for idx, core_path in enumerate(core_gold_files):
        try:
            base_name = os.path.basename(core_path).replace(".json", "")
            
            # 🟢 CHECKPOINT: Bỏ qua nếu file Diamond cuối cùng đã tồn tại
            output_path = os.path.join(DIAMOND_OUT_DIR, f"{base_name}.json")
            if os.path.exists(output_path):
                print(f"⏩ [{idx+1:03d}/{total:03d}] Bỏ qua: {base_name} (Đã hoàn thành Step 4)")
                continue

            remedy_path = core_path.replace(".json", "_BAI_THUOC.json")
            pharma_path = core_path.replace(".json", "_DUOC_LY.json") # Đã thêm file Dược lý
            
            # Tải dữ liệu Gold (Core + Bài thuốc + Dược lý)
            core_gold = robust_json_load(core_path)
            remedy_gold = robust_json_load(remedy_path)
            pharma_gold = robust_json_load(pharma_path) # Đã thêm
            
            # GỘP DỮ LIỆU TẠM THỜI ĐỂ AI REVIEW
            if remedy_gold:
                core_gold["relationships"].extend(remedy_gold.get("relationships", []))
            if pharma_gold: # Đã thêm logic gộp Dược lý
                core_gold["relationships"].extend(pharma_gold.get("relationships", []))
            
            # Chuẩn hóa ID hub ngay lập tức để đồng bộ toàn luồng
            hub_id = normalize_id(core_gold["entity"]["id"])
            core_gold["entity"]["id"] = hub_id
            
            # Tải Log Step 3 tương ứng (Core, Bài thuốc, Dược lý)
            core_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_LOG.json")
            remedy_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_BAI_THUOC_LOG.json")
            pharma_log_path = os.path.join(LOG_STEP3_DIR, f"{base_name}_DUOC_LY_LOG.json") # Đã thêm
            
            core_log = robust_json_load(core_log_path) or {"lenh_sua": []}
            remedy_log = robust_json_load(remedy_log_path) or {"lenh_sua": []}
            pharma_log = robust_json_load(pharma_log_path) or {"lenh_sua": []} # Đã thêm
            
            # Gom tất cả lệnh vá từ 3 nguồn Audit
            all_step3_patches = core_log.get("lenh_sua", []) + remedy_log.get("lenh_sua", []) + pharma_log.get("lenh_sua", [])

            # Tìm file Bronze gốc
            bronze_matches = glob.glob(os.path.join(BRONZE_DIR, f"*{hub_id}*.json"))
            if not bronze_matches: continue
            bronze_data = robust_json_load(bronze_matches[0])

            # Hiển thị trạng thái gộp 3 mảnh ghép
            status_bt = 'Có' if remedy_gold else 'Ko'
            status_dl = 'Có' if pharma_gold else 'Ko'
            print(f" 🧪 [{idx+1:03d}/{total:03d}] {hub_id:<25} | Gộp: BT={status_bt}, DL={status_dl} |", end=" ", flush=True)

            # GỌI AI FORENSIC VERIFIER CHỈ ĐỂ TÌM ẢO GIÁC
            review_context = {
                "ENTITY_ID": hub_id,
                "BRONZE_TEXT": bronze_data.get("van_ban_tho", {}),
                "STEP3_PROPOSED_PATCHES": all_step3_patches
            }
            
            res = client.models.generate_content(
                model=settings.MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=P4_REVIEW_PROMPT,
                    response_mime_type="application/json",
                    temperature=0
                ),
                contents=[json.dumps(review_context, ensure_ascii=False)]
            )
            
            # Lấy danh sách ID ảo giác cần loại bỏ
            step4_response = robust_json_load(res.text, is_path=False) or {"lenh_bi_loai_bo": []}
            blacklisted_ids = step4_response.get("lenh_bi_loai_bo", [])
            
            # THỰC THI PHẪU THUẬT VÀ GỘP FILE VẬT LÝ (Có màng lọc chuẩn hóa ID & Ảo giác)
            final_diamond = execute_patch(core_gold, all_step3_patches, blacklisted_ids)
            
            # TỰ ĐỘNG BÓC TÁCH LIỀU LƯỢNG BẰNG REGEX (Giải cứu dữ liệu cũ)
            final_diamond = extract_dosage_fix(final_diamond)
            
            # LÀM SẠCH VÀ LƯU KẾT QUẢ CUỐI CÙNG
            final_diamond = finalize_json(final_diamond)
            output_path = os.path.join(DIAMOND_OUT_DIR, f"{base_name}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(final_diamond, f, ensure_ascii=False, indent=2)
            
            print("DONE!")

        except Exception as e:
            print(f"\n ❌ LỖI TẠI {core_path}: {str(e)[:100]}")

    print("="*60)
    print(f"✅ HOÀN TẤT! Toàn bộ 3 mảnh ghép (Core + Bài thuốc + Dược lý) đã được chuẩn hóa ID, vá lỗi liều lượng và gộp vào file Diamond tại: {DIAMOND_OUT_DIR}")

if __name__ == "__main__":
    run_diamond_refiner()