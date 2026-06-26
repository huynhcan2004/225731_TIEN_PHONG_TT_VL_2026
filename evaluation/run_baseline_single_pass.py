"""
╔══════════════════════════════════════════════════════════════════╗
║  BASELINE EVALUATION SCRIPT: SINGLE-PASS PROMPTING (ALL-IN-ONE)  ║
║  Mục đích: Chạy thực nghiệm A/B Testing so sánh với Pipeline     ║
║  Logic: 1 Prompt duy nhất -> Bóc tách toàn bộ -> Chuẩn hóa Neo4j ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
import re
import time
import random
import unicodedata
import traceback
from google import genai
from google.genai import types
import sys

# Đảm bảo import được settings từ thư mục gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN
# ==========================================================
MODEL_ID = "gemini-2.5-flash"

# Thư mục tham chiếu để lấy đúng 10 cây thuốc đầu tiên
AUDITED_DIR = settings.DIR_SILVER_AUDITED

# Thư mục chứa dữ liệu thô (Bronze)
BRONZE_DIR = settings.DIR_BRONZE_RAW

# Thư mục lưu kết quả của phương pháp Baseline
BASELINE_OUT_DIR = settings.DIR_BASELINE_EVAL_OUT
os.makedirs(BASELINE_OUT_DIR, exist_ok=True)

# Khởi tạo client Gemini API thường (AI Studio)
def get_gemini_api_key():
    from app.models.base_db import db
    # 1. Thử lấy từ Database settings
    try:
        db_key = db.get_setting("gemini_api_key")
        if db_key: return db_key
    except Exception:
        pass
    # 2. Thử lấy từ settings
    try:
        if getattr(settings, "GEMINI_API_KEY", None): return settings.GEMINI_API_KEY
    except Exception:
        pass
    # 3. Thử lấy từ os.environ
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key: return env_key
    # 4. Thử lấy từ fallback keys của Database
    try:
        fallback_str = db.get_setting("gemini_fallback_keys")
        if fallback_str:
            keys = [k.strip() for k in fallback_str.split(",") if k.strip()]
            for k in keys:
                if (k.startswith("'") and k.endswith("'")) or (k.startswith('"') and k.endswith('"')):
                    k = k[1:-1].strip()
                if k: return k
    except Exception:
        pass
    return None

gemini_key = get_gemini_api_key()
if not gemini_key:
    raise ValueError("Chưa cấu hình Google Gemini API Key trong hệ thống.")
client = genai.Client(api_key=gemini_key)

# ==========================================================
# 2. CÁC HÀM TIỆN ÍCH (CHUẨN HÓA & LATEX)
# ==========================================================
def remove_accents(input_str):
    if not input_str or not isinstance(input_str, str): return "UNKNOWN"
    nks = unicodedata.normalize('NFKD', input_str)
    res = "".join([c for c in nks if not unicodedata.combining(c)])
    res = res.replace('đ', 'd').replace('Đ', 'D')
    res = re.sub(r'[^a-zA-Z0-9_]', '_', res)
    return re.sub(r'_+', '_', res).strip('_').upper()

def get_page_number(filepath):
    """Trích xuất số trang từ tên file để sắp xếp cho chuẩn"""
    filename = os.path.basename(filepath)
    match = re.search(r'^(\d+)_', filename)
    return int(match.group(1)) if match else 999999

def robust_json_parse(text):
    if not text: return None
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
        return json.loads(text)
    except:
        return None

def apply_latex_format(text):
    """Bọc LaTeX cho các con số và đơn vị y học"""
    if not isinstance(text, str): return text
    pattern = r'(?<![\$\d])(\d+(?:[.,-]\d+)?)\s*(g|ml|mg|%|°C|bát|phần|ống|muỗng|kilôgam|lạng|chỉ|đồng cân|phân|tễ|thang)\b(?!\$)'
    text = re.sub(pattern, r'$\1\2$', text, flags=re.IGNORECASE)
    return text.replace('\\\\%', '%').replace('\\%', '%')

def finalize_formatting(data):
    """Đệ quy áp dụng LaTeX và làm sạch text cho toàn bộ JSON"""
    if isinstance(data, dict): return {k: finalize_formatting(v) for k, v in data.items()}
    elif isinstance(data, list): return [finalize_formatting(item) for item in data]
    elif isinstance(data, str): return apply_latex_format(data.strip())
    return data

# ==========================================================
# 3. SCHEMA VÀ PROMPT KHỔNG LỒ (ALL-IN-ONE)
# ==========================================================
# Định nghĩa Schema đầu ra gộp chung tất cả
BASELINE_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "entity": types.Schema(
            type="OBJECT",
            properties={
                "id": types.Schema(type="STRING"),
                "canonical_name": types.Schema(type="STRING"),
                "ten_khoa_hoc": types.Schema(type="STRING"),
                "ho_thuc_vat": types.Schema(type="STRING"),
                "properties": types.Schema(
                    type="OBJECT",
                    properties={
                        "bo_phan_dung": types.Schema(type="STRING"),
                        "thu_hai": types.Schema(type="STRING"),
                        "che_bien_tho": types.Schema(type="STRING"),
                        "lieu_dung_chung": types.Schema(type="STRING"),
                        "muc_do_doc": types.Schema(type="STRING")
                    }
                )
            }
        ),
        "nodes": types.Schema(type="ARRAY", items=types.Schema(type="OBJECT")), # Luôn để rỗng
        "relationships": types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "from": types.Schema(type="STRING"),
                    "to": types.Schema(type="STRING"),
                    "relation_type": types.Schema(type="STRING", enum=[
                        "CO_TINH", "CO_VI", "QUY_KINH", "CO_CHUA_HOAT_CHAT",
                        "CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY", "CHU_TRI_BENH",
                        "CHU_TRI_TRIEU_CHUNG", "BAO_GOM_VI_THUOC", "KIENG_KY"
                    ]),
                    "properties": types.Schema(
                        type="OBJECT",
                        properties={
                            "mo_ta_chi_tiet": types.Schema(type="STRING"),
                            "lieu_luong": types.Schema(type="STRING"),
                            "cach_dung": types.Schema(type="STRING")
                        }
                    )
                },
                required=["from", "to", "relation_type"]
            )
        )
    },
    required=["entity", "relationships"]
)

SINGLE_PASS_PROMPT = """
VAI TRÒ: 
Bạn là Hệ thống Kỹ sư Trích xuất Tri thức YHCT Toàn diện (All-in-one Identity, Substance, Clinical & Pharmacology Engineer). 
NHIỆM VỤ: Đọc TẤT CẢ văn bản thô cung cấp từ dữ liệu BRONZE và trích xuất TOÀN BỘ thông tin của vị thuốc {HUB_ID} vào DUY NHẤT một cấu trúc JSON với độ chính xác tuyệt đối.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. CHIẾN LƯỢC ĐỊNH DANH (ENTITY LOCKDOWN & PROPERTIES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. HUB NODE (THỰC THỂ GỐC): 
   - 'id': BẮT BUỘC sử dụng ID cố định được cung cấp: {HUB_ID}.
   - 'ten_raw': Tên tiếng Việt chính xác nhất xuất hiện đầu văn bản.
   - 'ten_khoa_hoc': Trích xuất toàn bộ các tên Latin (nghiêng) và tên tác giả đi kèm. Nếu có nhiều loài tương đương, liệt kê cách nhau bằng dấu chấm phẩy (;).
   - 'ho_thuc_vat': Ghi rõ tên họ Tiếng Việt kèm tên Latin trong ngoặc.
   - 'variants': Liệt kê mọi tên gọi khác, tên địa phương, tên vị thuốc thương phẩm. 🛑 CẤM TÓM TẮT.

2. THUỘC TÍNH GỐC (GÁN VÀO NODE GỐC): 
   - 'entity.properties.bo_phan_dung': Phần dùng làm thuốc.
   - 'entity.properties.thu_hai': Thời gian thu hoạch.
   - 'entity.properties.che_bien_tho': Cách sơ chế ban đầu.
   - 'entity.properties.phuong_phap_che_bien_chi_tiet': Trích xuất chi tiết nếu có Tứ chế, Thất chế, tẩm sao...
   - 'entity.properties.lieu_dung_chung': Đọc kỹ mục "Liều dùng" và trích xuất nguyên văn. 
   - 🛑 'entity.properties.muc_do_doc': Suy luận từ văn bản: "Thuốc độc bảng A", "Thuốc độc bảng B", "Có độc" hoặc "Không độc" (nếu văn bản ghi rõ không độc hoặc không đề cập).
   - 🛑 'entity.properties.trieu_chung_ngo_doc': Trích xuất nguyên văn các biểu hiện ngộ độc, quá liều (nếu có).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. PHÁP CHỨNG VĂN BẢN (CLAIMS -> MO_TA_THEO_NGUON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Điền vào mảng 'claims', trong đó 'mo_ta_theo_nguon' bao gồm:
1. 'hinh_thai_chi_tiet': Chép nguyên văn mô tả thân, lá, hoa, quả, rễ. 🛑 Xóa bỏ 100% rác OCR.
2. 'phan_bo': Trích xuất chi tiết vùng địa lý mọc hoang hoặc trồng trọt.
3. 'thanh_phan_hoa_hoc': Chép NGUYÊN VĂN đoạn văn mô tả về các chất hóa học tìm thấy. CẤM TÓM TẮT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. QUY TẮC TRÍCH XUẤT QUAN HỆ (RELATIONSHIPS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tất cả các mối quan hệ phải được đặt chung trong mảng `relationships`. Áp dụng ĐÚNG NGUYÊN TẮC cho từng phân hệ sau:

▶ NHÓM 1: KIỂM TOÁN DNA CỐT LÕI (Từ {HUB_ID} -> Tính, Vị, Quy kinh)
- TÍNH (T_): Chỉ chọn từ 5 ID gốc: T_HAN, T_LUONG, T_BINH, T_ON, T_NHIET.
- VỊ (V_): Chỉ chọn từ 6 ID gốc: V_CAY, V_CHUA, V_NGOT, V_DANG, V_MAN, V_NHAT.
- QUY KINH (K_): Chỉ dùng ID chuẩn: K_CAN, K_TAM, K_TY, K_PHE, K_THAN, K_TAM_BAO, K_BANG_QUANG, K_VI, K_DAI_TRANG, K_TIEU_TRANG, K_DAN, K_TAM_TIEU.
🛑 LUẬT CHỐNG ẢO GIÁC: Nếu văn bản không nhắc đến Tính/Vị/Quy kinh, TUYỆT ĐỐI KHÔNG tạo quan hệ. Mọi quan hệ DNA BẮT BUỘC có 'properties.mo_ta_chi_tiet' (trích chép vắn tắt, đúng trọng tâm).

▶ NHÓM 2: KIỂM KÊ HOẠT CHẤT (Từ {HUB_ID} -> HC_)
- 'to': Prefix 'HC_' + Tên hoạt chất viết hoa không dấu (Ví dụ: HC_LEONURINE).
- 'relation_type': 'CO_CHUA_HOAT_CHAT'.
- 'properties.mo_ta_chi_tiet': BẮT BUỘC chép nguyên văn câu văn chứa tên hoạt chất và hàm lượng.
- 🛑 'properties.ap_dung_cho_loai': Nếu văn bản có nhiều loài và phân biệt rõ hoạt chất này chỉ thuộc về một loài cụ thể (VD: "chỉ có ở loài lá tím"), trích xuất tên loài đó vào đây. Nếu dùng chung, để `null`.

▶ NHÓM 3: LÂM SÀNG & BÀI THUỐC (Bệnh lý B_, Triệu chứng S_, Bài thuốc BT_)
- LUỒNG 3A - CHỈ ĐỊNH TRỰC TIẾP (1 VỊ -> BỆNH): Khi sách mô tả công dụng của riêng cây thuốc đó. Nối TRỰC TIẾP {HUB_ID} -> B_ (hoặc S_) qua 'CHU_TRI_BENH' hoặc 'CHU_TRI_TRIEU_CHUNG'.
   + 'properties.lieu_dung': Trích xuất chính xác con số.
   + 'properties.cach_dung': Trích xuất nguyên văn chi tiết cách đun sắc.
   + 🛑 'properties.doi_tuong_thu_huong': Xác định rõ "Người" hay "Thú y (Trâu, Bò, Lợn, Gà...)".
- LUỒNG 3B - CHỈ ĐỊNH PHỐI HỢP (BÀI THUỐC): Khi nêu tên riêng chế phẩm HOẶC công thức từ 2 vị trở lên.
   + Tạo 'BAO_GOM_VI_THUOC' từ ID_BT tới {HUB_ID} và các vị VT_ khác. Phải có 'properties.loai_che_pham', 'properties.lieu_luong' (từng vị), và 'properties.vai_tro' (Quân/Thần/Tá/Sứ).
   + Tạo 'CHU_TRI_BENH' từ ID_BT đến B_ (hoặc S_). Có 'properties.doi_tuong_thu_huong'.
- LUỒNG 3C - BÀI THUỐC KHÔNG MỤC TIÊU: Chế phẩm có tên nhưng KHÔNG GHI CHÚ BỆNH. CHỈ tạo 'BAO_GOM_VI_THUOC'.
🛑 CẤM tự chế tên bài thuốc `BT_` nếu công thức chỉ có 1 vị thuốc.

▶ NHÓM 4: MIỀN CÔNG NĂNG & DƯỢC LÝ (Tây Y DL_, Đông Y CN_)
- ĐÔNG Y (CÔNG NĂNG): Từ {HUB_ID} -> Prefix 'CN_' + Tên công năng viết hoa không dấu. Nhãn: 'CO_CONG_NANG'.
- TÂY Y (DƯỢC LÝ): Từ {HUB_ID} -> Prefix 'DL_' + Tác động sinh lý. Nhãn: 'CO_TAC_DUNG_DUOC_LY'. TUYỆT ĐỐI KHÔNG đưa tên đối tượng thí nghiệm vào ID.
- 🛑 PHÁP CHỨNG ĐỘC TÍNH: Từ {HUB_ID} -> Prefix 'DL_DOC_TINH_' + [CƠ QUAN/ĐẶC TÍNH]. Nhãn: 'CO_TAC_DUNG_DUOC_LY'. Trong 'mo_ta_chi_tiet' BẮT BUỘC theo cấu trúc: [Cơ chế] + [Triệu chứng ngộ độc] + [Định lượng liều độc/chết LD50].
- KẾ THỪA THAM CHIẾU: Nếu ghi "Tác dụng giống như vị thuốc X", BẮT BUỘC thêm `'properties.is_inherited': true` và `'properties.reference_to': 'VI_THUOC_X'`.
- 🛑 Tất cả quan hệ nhóm này BẮT BUỘC có 'properties.mo_ta_chi_tiet' (Chép verbatim, vắn tắt đúng trọng tâm, kèm loài áp dụng vào 'ap_dung_cho_loai' nếu có).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IV. KỶ LUẬT ĐỊNH DẠNG (BẮT BUỘC TUÂN THỦ TỔNG THỂ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. MẢNG NODES: BẮT BUỘC ĐỂ TRỐNG `[]`. (Hệ thống sẽ tự xử lý ở bước sau).
2. 🛑 CHỐT CHẶN LATEX (LATEX AUDIT): Trước khi xuất JSON, BẠN PHẢI rà soát MỌI con số kèm đơn vị đo lường, nhiệt độ, khối lượng, tỷ lệ phần trăm (Ví dụ: $g, mg/kg, ml, \%, 1/5000, °C$). TẤT CẢ PHẢI ĐƯỢC BỌC TRONG CẶP DẤU $ $. Phần trăm phải escape thành $\\%$.
3. 🛑 TRƯỜNG SOURCE: TUYỆT ĐỐI CẤM trích xuất hoặc tạo trường 'source' ở bất kỳ đâu trong JSON.
4. NẾU KHÔNG CÓ THÔNG TIN: Nếu văn bản không nhắc đến một nhóm nào đó (ví dụ không có hoạt chất), không tự bịa ra thực thể. Bỏ qua quan hệ đó.
"""

# ==========================================================
# 4. ENGINE CHÍNH
# ==========================================================
def extract_raw_text_from_bronze(bronze_data):
    """Gộp toàn bộ các trường text trong file Bronze thành 1 chuỗi khổng lồ"""
    if isinstance(bronze_data, list):
        bronze_data = bronze_data[0]
        
    vbt = bronze_data.get("van_ban_tho", {})
    text_blocks = []
    
    # Duyệt qua mọi value trong van_ban_tho
    for key, value in vbt.items():
        if isinstance(value, str):
            text_blocks.append(f"[{key.upper()}]\n{value}")
        elif isinstance(value, list):
            text_blocks.append(f"[{key.upper()}]\n" + "\n".join(str(v) for v in value))
        elif isinstance(value, dict):
            text_blocks.append(f"[{key.upper()}]\n" + json.dumps(value, ensure_ascii=False))
            
    return "\n\n".join(text_blocks)

def run_baseline_extraction():
    print("🚀 KHỞI ĐỘNG THỰC NGHIỆM BASELINE: SINGLE-PASS PROMPTING")
    print("=" * 80)
    
    # 1. Lấy 30 file ngẫu nhiên từ thư mục Audit Verified để so sánh công bằng
    audited_files = sorted(glob.glob(os.path.join(AUDITED_DIR, "*.json")), key=get_page_number)
    
    random.seed(42) # Cố định seed để đảm bảo tính tái lập (nếu chạy lại vẫn lấy đúng 30 cây này)
    sample_size = min(50, len(audited_files))
    target_files = random.sample(audited_files, sample_size)
    
    if not target_files:
        print(f"❌ Không tìm thấy file nào trong thư mục {AUDITED_DIR}")
        return

    print(f"📦 Đã xác định được {len(target_files)} vị thuốc ngẫu nhiên để test.")
    
    for idx, filepath in enumerate(target_files):
        filename = os.path.basename(filepath)
        base_name = filename.replace(".json", "")
        
        # --- CƠ CHẾ CHECKPOINT ---
        out_path = os.path.join(BASELINE_OUT_DIR, f"BASELINE_{base_name}.json")
        if os.path.exists(out_path):
            print(f"⏩ [{idx+1}/{sample_size}] Bỏ qua {base_name}: Đã có checkpoint (File đã tồn tại).")
            continue

        # 2. Match ngược lại thư mục Bronze để lấy dữ liệu thô
        bronze_matches = glob.glob(os.path.join(BRONZE_DIR, f"{base_name}*.json"))
        if not bronze_matches:
            print(f"⚠️ [{idx+1}/{sample_size}] Bỏ qua {base_name}: Không tìm thấy file Bronze gốc.")
            continue
            
        bronze_file = bronze_matches[0]
        with open(bronze_file, "r", encoding="utf-8") as f:
            bronze_data = json.load(f)
            
        # Lấy ID Mỏ neo
        raw_id = bronze_data[0].get('dinh_danh', {}).get('id', base_name) if isinstance(bronze_data, list) else bronze_data.get('dinh_danh', {}).get('id', base_name)
        hub_id = f"VT_{remove_accents(raw_id).replace('VI_THUOC_', '')}"

        # 3. Gộp toàn bộ văn bản thô
        full_raw_text = extract_raw_text_from_bronze(bronze_data)
        
        if not full_raw_text.strip():
            print(f"⚠️ [{idx+1}/{sample_size}] Bỏ qua {base_name}: File Bronze không có văn bản thô.")
            continue

        print(f"⏳ [{idx+1}/{sample_size}] Đang xử lý All-In-One cho: {hub_id}...", end=" ", flush=True)

        try:
            # 4. GỌI LLM 1 LẦN DUY NHẤT
            response = client.models.generate_content(
                model=MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=SINGLE_PASS_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=BASELINE_SCHEMA,
                    max_output_tokens=8192 # Ép kịch trần để tránh đứt JSON
                ),
                contents=[f"ID THỰC THỂ GỐC: {hub_id}\n\nVĂN BẢN THÔ:\n{full_raw_text}"]
            )
            
            # 5. Parse kết quả
            data = None
            if response.parsed:
                data = response.parsed if isinstance(response.parsed, dict) else response.parsed.model_dump()
            elif response.text:
                data = robust_json_parse(response.text)
                
            if not data:
                print("❌ THẤT BẠI (LLM sinh JSON lỗi, bị cắt cụt do quá tải).")
                fail_data = {
                    "entity": {"id": hub_id, "error": "LLM OUTPUT TRUNCATED OR PARSE FAILED"},
                    "relationships": [],
                    "nodes": []
                }
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(fail_data, f, ensure_ascii=False, indent=2)
            else:
                # 6. Chuẩn hóa định dạng Neo4j (Bọc LaTeX, ép ID)
                data["entity"]["id"] = hub_id
                
                # Ép lại from của quan hệ nếu nó là chính cây thuốc đó
                for rel in data.get("relationships", []):
                    if str(rel.get("from")).replace("VI_THUOC_", "VT_") == hub_id:
                        rel["from"] = hub_id
                        
                # Dọn dẹp mảng nodes (để rỗng giống kiến trúc Pipeline)
                data["nodes"] = []
                
                # Format Latex
                final_data = finalize_formatting(data)

                # 7. Lưu file
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, ensure_ascii=False, indent=2)
                    
                print("✅ HOÀN TẤT.")
            
        except Exception as e:
            print(f"❌ LỖI HỆ THỐNG: {str(e)[:100]}...")
            fail_data = {
                "entity": {"id": hub_id, "error": f"LLM OUTPUT TRUNCATED OR PARSE FAILED: {str(e)[:100]}"},
                "relationships": [],
                "nodes": []
            }
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(fail_data, f, ensure_ascii=False, indent=2)
            except Exception as write_err:
                print(f"Không thể ghi file lỗi: {write_err}")
            
        # Nghỉ nhịp để tránh hit rate limit
        time.sleep(4)

    # 8. THỐNG KÊ VÀ GHI NHẬN SỐ FILE HỎNG
    print("\n📊 ĐANG THỐNG KÊ KẾT QUẢ TOÀN BỘ THƯ MỤC ĐẦU RA...")
    all_baseline_files = glob.glob(os.path.join(BASELINE_OUT_DIR, "BASELINE_*.json"))
    
    total_files = len(all_baseline_files)
    failed_files_info = []
    successful_files_count = 0
    
    for bf in all_baseline_files:
        bf_name = os.path.basename(bf)
        try:
            with open(bf, "r", encoding="utf-8") as f:
                bf_data = json.load(f)
            
            entity = bf_data.get("entity", {})
            if "error" in entity:
                failed_files_info.append({
                    "file_name": bf_name,
                    "hub_id": entity.get("id"),
                    "error": entity.get("error")
                })
            else:
                successful_files_count += 1
        except Exception as scan_err:
            failed_files_info.append({
                "file_name": bf_name,
                "error": f"Không thể đọc hoặc parse file JSON: {str(scan_err)}"
            })
            
    summary_data = {
        "thoi_gian_thong_ke": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "tong_so_file": total_files,
        "so_file_thanh_cong": successful_files_count,
        "so_file_hong": len(failed_files_info),
        "danh_sach_file_hong": failed_files_info
    }
    
    summary_path = os.path.join(BASELINE_OUT_DIR, "failed_files_summary.json")
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        print(f"📝 Đã ghi nhận báo cáo file hỏng vào: {summary_path}")
        print(f"   - Tổng số file: {total_files}")
        print(f"   - Thành công: {successful_files_count}")
        print(f"   - Hỏng: {len(failed_files_info)}")
    except Exception as write_sum_err:
        print(f"⚠️ Không thể ghi file thống kê: {write_sum_err}")

    print("=" * 80)
    print(f"🎉 THỰC NGHIỆM HOÀN TẤT! Dữ liệu Baseline (Single-pass) đã được lưu tại:")
    print(f"   {BASELINE_OUT_DIR}")
    print("Bạn có thể dùng các file này để đối chiếu số lượng JSON Lỗi, Entity Recall và Hallucination so với Pipeline.")

if __name__ == "__main__":
    run_baseline_extraction()