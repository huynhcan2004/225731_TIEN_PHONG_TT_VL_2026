"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 6 — MASTER DICTIONARY GENERATOR (PREFIX-ONLY & SAFE)       ║
║  Chức năng: Xây dựng từ điển đồng nghĩa toàn cục.                ║
║  Cập nhật: BỔ SUNG HÀNG RÀO TIỀN TỐ VÀ NGỮ CẢNH (CONTEXT). Chặn  ║
║  đứng tuyệt đối hiện tượng AI ảo giác, nhầm Kinh mạch thành Bệnh.║
║  TÍCH HỢP BỘ LỌC KIỂM TRA CHÉO (ANTI-CONTAMINATION FILTER) BẰNG  ║
║  PYTHON ĐỂ KHỬ TRÙNG LẶP VÀ XUNG ĐỘT TỪ ĐỒNG NGHĨA TỔNG QUÁT.    ║
║  VÉT CẠN 100% DỮ LIỆU TỪ TRƯỜNG 'TO' VÀ 'FROM' TRONG RELATION.   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
import time
import re
from google import genai
from google.genai import types

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import remove_accents

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG (SỬ DỤNG MEDALLION ARCHITECTURE)
# ==========================================================
PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us-central1"
MODEL_ID = settings.MODEL_ID 

# Đường dẫn đã được đồng bộ với app.config.settings
INPUT_DIR = settings.DIR_GOLD_VALIDATED
OUTPUT_DIR = settings.DIR_DICT_MASTER
MASTER_MAP_PATH = settings.FILE_DICT_FINAL
CHECKPOINT_PATH = settings.CHECKPOINT_DICT

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# ==========================================================
# 🧠 PROMPT KIẾN TRÚC SƯ TRƯỞNG (PREFIX-DRIVEN)
# ==========================================================
AI_RECONCILE_PROMPT = """VAI TRÒ: Kiến trúc sư trưởng Hệ thống Đồ thị Tri thức YHCT & Chuyên gia Pháp chứng Ngôn ngữ học.
NHIỆM VỤ: Chuyển đổi mã ID thô thành Thực thể chuẩn hóa (Canonical Entities) dựa trên NGỮ CẢNH GỐC (Context). Áp dụng kỷ luật thép để tạo mạng lưới từ đồng nghĩa (Aliases) chính xác 1:1, tuyệt đối không tạo ra dữ liệu rác hoặc ảo giác.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. HÀNG RÀO TIỀN TỐ (PREFIX GUARDRAILS) - BẮT BUỘC KHỚP 100%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nhìn vào TIỀN TỐ của ID để quyết định bản chất thực thể. Sai tiền tố = Suy diễn sai.
- [K_] (Kinh mạch): BẮT BUỘC có chữ "Kinh" (VD: K_TY -> "Kinh tỳ"). Tuyệt đối KHÔNG dịch thành Triệu chứng.
- [CN_] (Công năng): BẮT BUỘC là tác dụng/công năng (VD: CN_LOI_TIEN -> "Lợi tiện").
- [B_] (Bệnh lý): BẮT BUỘC là tên Bệnh lý.
- [S_] (Triệu chứng): BẮT BUỘC là Triệu chứng.
- [VT_] hoặc [VI_THUOC_]: BẮT BUỘC là Vị thuốc/Cây thuốc.
- [HC_]: BẮT BUỘC là Hoạt chất sinh học.
- [T_] / [V_]: BẮT BUỘC là Tính / Vị (VD: T_ON -> Tính ôn, V_CAY -> Vị cay).
🛑 LỆNH LOẠI BỎ: Nếu ID quá ngắn vô nghĩa (như B_B) hoặc không thể xác định, trả về `"canonical_name": "REJECT"`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. CHUẨN HÓA ĐỊNH DANH (CANONICAL NAMING)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- DỊCH THEO NGỮ CẢNH: Phân tích nội hàm ID dựa trên trường "context", KHÔNG dịch từng chữ cái thô.
- ĐỊNH DẠNG: Viết bằng Tiếng Việt có dấu, viết hoa chữ cái đầu, loại bỏ dấu gạch dưới (_).
- KHỬ NHIỄU: Cắt bỏ các từ rườm rà như 'vithuoc', 'baithuoc', 'thuoc', 'cay' ra khỏi tên. Tự động sửa lỗi chính tả do OCR (nếu có).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. KỶ LUẬT TẠO BÍ DANH (STRICT ALIASES STRATEGY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bí danh (Aliases) BẮT BUỘC là TỪ ĐỒNG NGHĨA TUYỆT ĐỐI (thay thế 1:1). CẤM dùng "Từ khóa liên quan".

✅ NHỮNG ĐIỀU PHẢI LÀM (DOs):
- ƯU TIÊN HÁN VIỆT: Luôn tìm tên cổ/Hán Việt (VD: 'Đau dạ dày' -> 'Vị quản thống', 'Đau đầu' -> 'Đầu thống').
- NGOẠI NGỮ: Bổ sung Tiếng Anh/Latinh cho các nhóm [HC_], [B_], [VT_].
- TẦNG SEARCH: Bắt buộc tạo 2 biến thể KHÔNG DẤU (viết rời và viết liền) của tên chính và bí danh chính.

🛑 3 "LỆNH CẤM" TỬ HUYỆT (DON'Ts):
1. CẤM PHÂN MẢNH (NO-FRAGMENTATION): Không chẻ nhỏ cụm từ ghép. 
   -> VD: "S_DAU_NHUC" cấm dùng "Đau" hoặc "Nhức" làm bí danh. Phải giữ nguyên cấu trúc (VD: "Thống nhức").
2. CẤM BAO HÀM / PHÂN CẤP (ANTI-GENERALIZATION): Không dùng tên Nhóm lớn (Parent) làm bí danh cho Thực thể cụ thể (Child).
   -> VD: "B_GHE_RUOI" -> Cấm dùng từ "Ghẻ" đơn lẻ. "B_VIEM_GAN_B" -> Cấm dùng từ "Viêm gan".
3. CẤM GIAO THOA (NO CROSS-CONTAMINATION): Không lấy tên bệnh làm bí danh cho triệu chứng, không lấy tên vị thuốc làm bí danh cho bài thuốc.
   -> VD: "S_TE_THAP" (Triệu chứng) cấm có bí danh là "Phong thấp" (Bệnh).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. MÔ TẢ & ĐẦU RA JSON (OUTPUT SCHEMA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- `reason`: Viết 2-3 câu định nghĩa bản chất y khoa học thuật của thực thể. Không giải thích code.
- KHỬ TRÙNG LẶP: Mảng `aliases` không được chứa các từ trùng nhau (không phân biệt hoa/thường).

TRẢ VỀ JSON THEO ĐÚNG ĐỊNH DẠNG SAU:
{
  "entities": [
    {
      "canonical_id": "MÃ_ID_GỐC",
      "canonical_name": "Tên chuẩn hóa",
      "aliases": ["Bí danh 1", "Bí danh 2", "Bi danh khong dau", "Bidanhkhongdau"],
      "raw_found": ["MÃ_ID_GỐC"],
      "reason": "Mô tả tri thức y khoa học thuật."
    }
  ]
}
"""

DICTIONARY_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "entities": types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "canonical_id": types.Schema(type="STRING"),
                    "canonical_name": types.Schema(type="STRING"),
                    "aliases": types.Schema(type="ARRAY", items=types.Schema(type="STRING")),
                    "raw_found": types.Schema(type="ARRAY", items=types.Schema(type="STRING")),
                    "reason": types.Schema(type="STRING")
                },
                required=["canonical_id", "canonical_name", "aliases", "raw_found"]
            )
        )
    },
    required=["entities"]
)

# ==========================================================
# 🛠️ BỘ LỌC THÉP (THE IRON FILTER) 
# ==========================================================

def force_prefix_rules(cid, cname):
    """Bộ lọc bảo vệ ID (Chỉ để an toàn, vì dữ liệu vào đã là ID chuẩn)"""
    cid_raw = str(cid).upper().strip()
    cid_clean = re.sub(r'[^A-Z0-9_]', '', cid_raw)
    
    # Chuẩn hóa tiền tố VI_THUOC thành VT_ (Bảo vệ DL_ khỏi bị cắt nhầm)
    cid_clean = re.sub(r'^VI_THUOC_', 'VT_', cid_clean)
    cid_clean = re.sub(r'^VI_', 'VT_', cid_clean)
    cid_clean = re.sub(r'^D_(?!L)', 'VT_', cid_clean)

    valid_prefixes = ("BT_", "B_", "S_", "G_", "VT_", "HC_", "DL_", "CN_", "K_", "T_", "V_")
    if cid_clean.startswith(valid_prefixes):
        return cid_clean

    return "VT_" + cid_clean

def strict_cross_contamination_filter(master_dict_map):
    """
    Bộ lọc Python tự động:
    1. Loại bỏ bí danh trùng lặp (không phân biệt hoa/thường).
    2. Loại bỏ bí danh trùng với chính canonical_name của nó.
    3. KIỂM TRA CHÉO: Loại bỏ bí danh của thực thể này nếu nó vô tình trùng khớp 100% 
       với canonical_name của một thực thể khác (Tránh lỗi giao thoa lược đồ).
    """
    # Bước 1: Thu thập tất cả canonical_name vào một từ điển để đối chiếu chéo
    canonical_map = {}
    for cid, ent in master_dict_map.items():
        if ent.get('canonical_name') and ent.get('canonical_name') != "REJECT":
            c_name_lower = ent['canonical_name'].strip().lower()
            canonical_map[c_name_lower] = cid

    cleaned_master_list = []

    # Bước 2: Duyệt qua từng thực thể để làm sạch mảng aliases
    for cid, ent in master_dict_map.items():
        if ent.get('canonical_name') == "REJECT":
            continue
            
        c_name_lower = ent['canonical_name'].strip().lower()
        raw_aliases = ent.get('aliases', [])
        
        cleaned_aliases = []
        seen_lower = set()
        
        for alias in raw_aliases:
            alias_clean = str(alias).strip()
            alias_lower = alias_clean.lower()
            
            # Bỏ qua nếu là chuỗi rỗng
            if not alias_clean:
                continue
                
            # Loại bỏ trùng lặp (Case-insensitive) bên trong cùng một thực thể
            if alias_lower in seen_lower:
                continue
                
            # Loại bỏ nếu alias giống hệt canonical_name của chính nó
            if alias_lower == c_name_lower:
                continue
                
            # LOẠI BỎ GIAO THOA CHÉO: Nếu alias này là Tên chính thức của một ID khác
            if alias_lower in canonical_map and canonical_map[alias_lower] != cid:
                continue
                
            seen_lower.add(alias_lower)
            cleaned_aliases.append(alias_clean)
            
        ent['aliases'] = cleaned_aliases
        cleaned_master_list.append(ent)
        
    # Sắp xếp lại danh sách theo ID cho gọn gàng
    cleaned_master_list = sorted(cleaned_master_list, key=lambda x: x['canonical_id'])
    return cleaned_master_list

# ==========================================================
# 🧠 PIPELINE EXECUTION: CONTEXT-INJECTED SCRAPER
# ==========================================================

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_checkpoint(checkpoint_data):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

def stage_1_scrape_vocab_with_context():
    """
    VÉT CẠN CÓ CHỌN LỌC (CONTEXT-INJECTED):
    Lấy ID định danh và ghép với "mo_ta_chi_tiet" từ relationships để tạo ngữ cảnh.
    Tránh AI bịa chữ (Ví dụ: K_TY sẽ đi kèm ngữ cảnh "vào kinh tỳ").
    """
    files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    vocab_dict = {} # Lưu dưới dạng {ID: Context}
    
    # Tập hợp các tiền tố hợp lệ được phép lọt vào Từ điển
    valid_prefixes = ("VT_", "VI_THUOC_", "BT_", "CN_", "B_", "S_", "HC_", "DL_", "G_", "K_", "T_", "V_")
    
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                continue
            
        # 1. Lấy ID từ Entity chính
        ent_id = data.get("entity", {}).get("id", "")
        ent_name = data.get("entity", {}).get("ten_raw", "")
        if ent_id:
            clean_id = str(ent_id).strip().upper()
            if clean_id.startswith("VI_THUOC_"): clean_id = clean_id.replace("VI_THUOC_", "VT_", 1)
            # Bảo vệ DL_ khỏi bị nhầm thành D_
            if clean_id.startswith("D_") and not clean_id.startswith("DL_"): clean_id = clean_id.replace("D_", "VT_", 1)
            
            if clean_id.startswith(valid_prefixes):
                if clean_id not in vocab_dict:
                    vocab_dict[clean_id] = ent_name

        # 2. Lấy ID và ngữ cảnh từ mảng Relationships (VÉT CẠN 'FROM' VÀ 'TO')
        for rel in data.get("relationships", []):
            f_id = rel.get("from", "")
            t_id = rel.get("to", "")
            context = rel.get("properties", {}).get("mo_ta_chi_tiet", "")
            
            # --- Xử lý trường FROM ---
            if f_id:
                clean_f = str(f_id).strip().upper()
                if clean_f.startswith("VI_THUOC_"): clean_f = clean_f.replace("VI_THUOC_", "VT_", 1)
                if clean_f.startswith("D_") and not clean_f.startswith("DL_"): clean_f = clean_f.replace("D_", "VT_", 1)
                
                if clean_f.startswith(valid_prefixes):
                    if context and (clean_f not in vocab_dict or not vocab_dict[clean_f]):
                        vocab_dict[clean_f] = context
                    elif clean_f not in vocab_dict:
                        vocab_dict[clean_f] = ""
            
            # --- Xử lý trường TO (VÉT CẠN ĐÍCH ĐẾN NHƯ BỆNH LÝ, DƯỢC LÝ, CÔNG NĂNG) ---
            if t_id:
                clean_t = str(t_id).strip().upper()
                if clean_t.startswith("VI_THUOC_"): clean_t = clean_t.replace("VI_THUOC_", "VT_", 1)
                if clean_t.startswith("D_") and not clean_t.startswith("DL_"): clean_t = clean_t.replace("D_", "VT_", 1)
                
                if clean_t.startswith(valid_prefixes):
                    if context and (clean_t not in vocab_dict or not vocab_dict[clean_t]):
                        vocab_dict[clean_t] = context
                    elif clean_t not in vocab_dict:
                        vocab_dict[clean_t] = ""
            
    return vocab_dict

def stage_2_ai_generation_with_checkpoint(vocab_dict):
    checkpoint = load_checkpoint()
    processed_raw = set()
    for cid in checkpoint:
        processed_raw.update([str(r).upper().strip() for r in checkpoint[cid].get("raw_found", [])])
    
    # Lọc ra các ID chưa được xử lý
    pending_ids = [k for k in vocab_dict.keys() if k not in processed_raw]
    if not pending_ids: return checkpoint
    
    # Đóng gói dữ liệu đầu vào gồm cả ID và Ngữ cảnh
    pending_items = [{"id": k, "context": vocab_dict[k]} for k in pending_ids]

    # Batch size giữ mức 20 để tránh ngộp Token
    batch_size = 20
    total_batches = (len(pending_items) // batch_size) + (1 if len(pending_items) % batch_size > 0 else 0)
    
    for i in range(0, len(pending_items), batch_size):
        batch = pending_items[i:i + batch_size]
        current_batch_num = i // batch_size + 1
        print(f"📦 Batch {current_batch_num}/{total_batches}: Đang phân tích {len(batch)} mã ID...")
        
        user_input = (
            "YÊU CẦU: Dựa vào ID và Ngữ cảnh gốc (context), hãy dịch thành tên Tiếng Việt (canonical_name) và tạo từ đồng nghĩa.\n"
            "BẮT BUỘC TUÂN THỦ HÀNG RÀO TIỀN TỐ (K_ -> Kinh, CN_ -> Công năng, B_ -> Bệnh...).\n"
            "DANH SÁCH ĐẦU VÀO:\n" + json.dumps(batch, ensure_ascii=False, indent=2)
        )
        
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=AI_RECONCILE_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=DICTIONARY_SCHEMA
                ),
                contents=[user_input]
            )
            
            if response.parsed:
                for ent in response.parsed.get("entities", []):
                    # Bỏ qua các thực thể bị AI đánh dấu REJECT
                    if ent.get('canonical_name') == "REJECT":
                        continue

                    # Ép tiền tố bảo vệ hệ thống
                    ent['canonical_id'] = force_prefix_rules(ent['canonical_id'], ent['canonical_name'])
                    cid = ent['canonical_id']
                    
                    # Code Python bảo vệ raw_found: Phải chứa chính canonical_id
                    current_raw_found = ent.get('raw_found', [])
                    if cid not in current_raw_found:
                        current_raw_found.append(cid)
                    
                    if cid in checkpoint:
                        # Gộp các aliases và raw_found nếu AI nhận diện chung 1 ID
                        checkpoint[cid]['aliases'] = list(set(checkpoint[cid]['aliases'] + ent['aliases']))
                        checkpoint[cid]['raw_found'] = list(set(checkpoint[cid].get('raw_found', []) + current_raw_found))
                    else:
                        ent['raw_found'] = current_raw_found
                        checkpoint[cid] = ent
                        
                # LƯU CHỐT BẢO VỆ NGAY SAU MỖI BATCH
                save_checkpoint(checkpoint)
                print(f"💾 Đã lưu Checkpoint tiến trình sau batch {current_batch_num}.")
                
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Lỗi tại Batch {current_batch_num}: {e}")
            time.sleep(10)
            
    return checkpoint

def run_step_6():
    print("🚀 Đang khởi động tiến trình tạo Master Dictionary (Prefix-Guardrails & Context-Injected)...")
    
    # 1. Scrape dữ liệu kèm ngữ cảnh (mo_ta_chi_tiet)
    vocab_dict = stage_1_scrape_vocab_with_context()
    print(f"📊 Thu hoạch tổng cộng: {len(vocab_dict)} mã ID thực thể chuẩn kèm ngữ cảnh.")
    
    # 2. Xử lý AI để dịch ID và lấy đồng nghĩa
    master_dict_map = stage_2_ai_generation_with_checkpoint(vocab_dict)
    
    # 3. Chạy qua Bộ lọc Python (Cắt trùng lặp hoa/thường và Giao thoa chéo)
    print("🛡️ Đang thực thi bộ lọc Strict Cross-Contamination Filter...")
    master_list_cleaned = strict_cross_contamination_filter(master_dict_map)
    
    # 4. Kết xuất JSON
    output_data = {
        "metadata": {
            "total_entities": len(master_list_cleaned), 
            "ontology_version": "10.0-STRICT-CROSS-FILTERED-FULL-FETCH",
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "dictionary": master_list_cleaned
    }
    
    with open(MASTER_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Hoàn tất! Từ điển đã được chuẩn hóa theo Prefix, lọc trùng lặp chéo và kết xuất tại {MASTER_MAP_PATH}")

if __name__ == "__main__":
    run_step_6()