import os
import json
import time
import glob
import traceback
import sys
import re
from google import genai
from google.genai import types

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import normalize_id, robust_json_load, get_page_number
from utils.master_schema_genai import RESPONSE_SCHEMA, STAGE34_SCHEMA

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
# Gán biến môi trường từ cấu hình tập trung
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us-central1"

# Sử dụng cấu trúc Medallion từ file settings
INPUT_DIR = settings.DIR_BRONZE_RAW
OUTPUT_DIR = settings.DIR_SILVER_MAPPED
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Khởi tạo client Vertex AI
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# ==========================================================
# 2. HỆ THỐNG PROMPTS BỐC TÁCH (4 STAGES)
# ==========================================================

STAGE_1_PROMPT = """VAI TRÒ: Chuyên gia Trích xuất Định danh và Phân loại Thực thể YHCT.
NHIỆM VỤ: Phân tích văn bản JSON thô, tạo Entity Node chính của vị thuốc.

QUY TẮC CỐT LÕI:
1. `id`: Phải viết hoa, không dấu, thay khoảng trắng bằng gạch dưới (VD: VI_THUOC_BACH_CHI).
2. `entity_type`: Bắt buộc là "VI_THUOC".
3. `display_name`: Tên tiếng Việt chuẩn.
4. Bóc tách Tên khoa học và Họ thực vật (nếu có).

SCHEMA YÊU CẦU: Khớp chuẩn cấu trúc 'entity' trong SCHEMA.
"""

STAGE_2_PROMPT = """VAI TRÒ: Chuyên gia Phân tích Đặc điểm Sinh học và Bào chế Dược liệu.
NHIỆM VỤ: Phân tích văn bản và trích xuất các thuộc tính cốt lõi (Core Properties).

QUY TẮC BÓC TÁCH:
- `mo_ta_hinh_thai`: Giữ nguyên văn mô tả rễ, thân, lá, hoa, quả.
- `phan_bo`: Nơi mọc, xuất xứ.
- `thu_hai_che_bien`: Cách thu hoạch, phơi sấy, tẩm sao.
- `lieu_dung`: Con số liều lượng (VD: 4 - 8g/ngày).

SCHEMA YÊU CẦU: Khớp chuẩn cấu trúc 'core_properties' trong SCHEMA.
"""

STAGE_3_PROMPT = """VAI TRÒ: Chuyên gia Phân tích Bài Thuốc & Lâm Sàng (Trình độ Bác sĩ YHCT).
NHIỆM VỤ: Phân tích danh sách 'cac_bai_thuoc_raw' để tạo các Node Bài Thuốc và Quan hệ.

QUY TẮC LUẬT DIAMOND:
1. ID Bài Thuốc: Luôn bắt đầu bằng `BAI_THUOC_` + [TÊN BỆNH/TÊN BÀI_VIẾT_HOA_KHÔNG_DẤU].
2. Nếu bài thuốc có tên (VD: "Độc hoạt tang ký sinh thang"): ID = BAI_THUOC_DOC_HOAT_TANG_KY_SINH_THANG.
3. Nếu bài thuốc KHÔNG có tên, chỉ ghi công dụng (VD: "Chữa đau bụng"): ID = BAI_THUOC_CHUA_DAU_BUNG.
4. Quan hệ (Relationships):
   - Từ VI_THUOC hiện tại -> CO_TRONG_BAI_THUOC -> BAI_THUOC.
   - Vai trò: Nếu không rõ Quân/Thần/Tá/Sứ, để "Chưa rõ".
   - Liều lượng: Bóc tách chính xác liều lượng của Vị Thuốc trong bài thuốc đó.

SCHEMA YÊU CẦU:
Trả về mảng (Array) các Object Quan hệ (Relation) theo chuẩn STAGE34_SCHEMA.
"""

STAGE_4_PROMPT = """VAI TRÒ: Chuyên gia Phân tích Dược Lý, Công Năng và Thành phần Hóa học.
NHIỆM VỤ: Bóc tách Tính Vị, Quy Kinh, Thành phần Hóa học, Tác dụng Dược lý, và Kiêng kỵ thành các Node Quan hệ.

QUY TẮC LUẬT DIAMOND (RẤT QUAN TRỌNG):
1. Tính Vị & Quy Kinh (Tạo Node riêng):
   - ID: VI_[NGOT/DANG...], TINH_[HAN/NHIET...], KINH_[TAM/CAN/TY/PHE/THAN...].
   - Quan hệ: CO_VI, CO_TINH, QUY_KINH.
2. Công năng (YHCT): ID bắt đầu bằng `CONG_NANG_`.
3. Tác dụng Dược lý (Tây Y): ID bắt đầu bằng `DUOC_LY_`.
4. Hoạt chất: ID bắt đầu bằng `HOAT_CHAT_`. (VD: HOAT_CHAT_ALKALOID).
5. Kiêng kỵ: Tạo node TRIEU_CHUNG hoặc BENH_LY, quan hệ là KIENG_KY_CHO.

SCHEMA YÊU CẦU:
Trả về mảng (Array) các Object Quan hệ (Relation) theo chuẩn STAGE34_SCHEMA.
"""

# ==========================================================
# 3. HÀM XỬ LÝ CHÍNH
# ==========================================================

def process_file(filepath):
    """Xử lý 1 file JSON qua 4 chặng (Stages) của pipeline AI"""
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # Lấy đối tượng đầu tiên nếu là mảng
    data = raw_data[0] if isinstance(raw_data, list) else raw_data
    
    dinh_danh = data.get("dinh_danh", {})
    vbt = data.get("van_ban_tho", {})
    
    hub_id = normalize_id(dinh_danh.get("id", ""))
    ten_chinh = dinh_danh.get("ten_chinh", "Không rõ")
    
    source_meta = {
        "source_book": "Những cây thuốc và vị thuốc Việt Nam",
        "pages": dinh_danh.get("nguon_trang", []),
        "raw_text_length": len(json.dumps(vbt))
    }

    print(f"\\n➤ Đang xử lý: {ten_chinh} ({hub_id})")
    
    stages = [
        ("STAGE 1: ĐỊNH DANH", STAGE_1_PROMPT, vbt, RESPONSE_SCHEMA),
        ("STAGE 2: THUỘC TÍNH", STAGE_2_PROMPT, vbt, RESPONSE_SCHEMA),
        ("STAGE 3: BÀI THUỐC", STAGE_3_PROMPT, json.dumps(vbt.get("cac_bai_thuoc_raw", []), ensure_ascii=False), STAGE34_SCHEMA),
        ("STAGE 4: DƯỢC LÝ & THÀNH PHẦN", STAGE_4_PROMPT, json.dumps({
            "thanh_phan": vbt.get("thanh_phan_hoa_hoc", ""),
            "duoc_ly": vbt.get("tac_dung_duoc_ly", ""),
            "tinh_vi": vbt.get("tinh_vi_quy_kinh", ""),
            "kieng_ky": vbt.get("chu_y_kieng_ky", "")
        }, ensure_ascii=False), STAGE34_SCHEMA)
    ]
    
    stage_results = {}
    success_count = 0

    for stage_idx, (stage_name, prompt, payload, schema) in enumerate(stages):
        stage_num = stage_idx + 1
        print(f"   ⏳ Đang chạy {stage_name}...", end="", flush=True)
        
        try:
            full_prompt = f"{prompt}\\n\\n=== DỮ LIỆU ĐẦU VÀO ===\\n{payload}\\n=== VỊ THUỐC ĐANG XÉT: {ten_chinh} ({hub_id}) ==="
            
            res = client.models.generate_content(
                model=settings.MODEL_ID,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1 
                ),
            )
            
            # Sử dụng hàm robust_json_load đã được tối ưu từ utils.helpers
            parsed = robust_json_load(res.text, is_path=False)
            if parsed:
                if stage_num in [1, 2]:
                    stage_results[stage_num] = parsed
                else:
                    stage_results[stage_num] = {"relationships": parsed}
                success_count += 1
                print(" ✅ OK")
            else:
                print(" ❌ Failed (JSON Parsing)")
                
        except Exception as e:
            print(f" ❌ Lỗi API: {str(e)[:50]}")
            
        time.sleep(1) # Tránh Rate Limit của Vertex AI

    # =================================================================
    # KẾT XUẤT THÀNH 3 FILE ĐỘC LẬP (CORE, REMEDY, PHARMA) 
    # ĐỂ TIỆN CHO KIỂM TOÁN TẠI STEP 3
    # =================================================================
    if success_count > 0:
        base_name = os.path.basename(filepath).replace(".json", "")
        
        # Đường dẫn mới theo cấu trúc Medallion
        core_path = os.path.join(OUTPUT_DIR, f"{base_name}_core.json")
        remedy_path = os.path.join(OUTPUT_DIR, f"{base_name}_remedy.json")
        pharma_path = os.path.join(OUTPUT_DIR, f"{base_name}_pharma.json")

        # FILE 1: CORE (Định danh + Thuộc tính vật lý)
        if 1 in stage_results or 2 in stage_results:
            core_json = {
                "entity": stage_results.get(1, {}).get("entity", {"id": hub_id, "entity_type": "VI_THUOC", "display_name": ten_chinh}),
                "core_properties": stage_results.get(2, {}).get("core_properties", {}),
                "source": source_meta
            }
            # Merge thêm dữ liệu nếu AI bóc tách được từ các module khác
            if 1 in stage_results and "core_properties" in stage_results[1]:
                 core_json["core_properties"].update(stage_results[1]["core_properties"])

            with open(core_path, "w", encoding="utf-8") as f:
                json.dump(core_json, f, ensure_ascii=False, indent=2)
            print(f"   ✅ Đã kết xuất file Core.")

        # FILE 2: BÀI THUỐC (Chỉ chứa quan hệ liên kết bài thuốc)
        if 3 in stage_results and "relationships" in stage_results[3]:
            remedy_json = {
                "entity_hub": hub_id,
                "source": source_meta,
                "nodes": [], # Dành cho không gian mở rộng sau này
                "relationships": stage_results[3].get("relationships", []),
                "metadata": stage_results[3].get("metadata", {})
            }
            with open(remedy_path, "w", encoding="utf-8") as f:
                json.dump(remedy_json, f, ensure_ascii=False, indent=2)
            status_msg = "chuẩn hóa rỗng" if not stage_results[2].get("relationships") else "thành công"
            print(f"   ✅ Đã kết xuất file Bài thuốc ({status_msg}).")
            
        # FILE 3: DƯỢC LÝ (Tác động sinh lý và Công năng YHCT)
        if 4 in stage_results and "relationships" in stage_results[4]:
            pharma_json = {
                "entity_hub": hub_id,
                "source": source_meta,
                "nodes": [],
                "relationships": stage_results[4].get("relationships", []),
                "metadata": stage_results[4].get("metadata", {})
            }
            with open(pharma_path, "w", encoding="utf-8") as f:
                json.dump(pharma_json, f, ensure_ascii=False, indent=2)
            status_msg = "chuẩn hóa rỗng" if not stage_results[4].get("relationships") else "thành công"
            print(f"   ✅ Đã kết xuất file Dược lý ({status_msg}).")

        if success_count < 4:
            print(f"   ⚠️ Hoàn tất không trọn vẹn ({success_count}/4 Stages).")
        else:
            print(f"   ✨ Hoàn tất xuất sắc 4/4 Stages.")

def main():
    print("=====================================================")
    print("BẮT ĐẦU CHUẨN HÓA SCHEMA BẰNG GEMINI (4 STAGES/FILE)")
    print("=====================================================")
    
    files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    # Dùng get_page_number từ helpers để sắp xếp chuẩn xác
    files.sort(key=get_page_number)
    
    total = len(files)
    print(f"Tìm thấy {total} file thô trong Data Lake.")
    
    for i, f in enumerate(files):
        print(f"\\n[{i+1}/{total}]", "-"*40)
        process_file(f)

if __name__ == "__main__":
    main()