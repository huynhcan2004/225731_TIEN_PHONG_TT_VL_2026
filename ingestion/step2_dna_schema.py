import os
import json
import time
import glob
import traceback
import sys
import re
import unicodedata
import datetime
from google import genai
from google.genai import types
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import normalize_id, robust_json_load, get_page_number
from utils.master_schema_genai import RESPONSE_SCHEMA, STAGE34_SCHEMA

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us-central1"
MODEL_ID = settings.MODEL_ID

INPUT_DIR = settings.DIR_BRONZE_RAW
OUTPUT_DIR = settings.DIR_SILVER_MAPPED
os.makedirs(OUTPUT_DIR, exist_ok=True)

ERROR_LOG_FILE = os.path.join(OUTPUT_DIR, "error_log.txt")

# Khởi tạo client Vertex AI
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


# ==========================================================
# 2. CÁC HÀM HỖ TRỢ XỬ LÝ DỮ LIỆU & GHI LOG
# ==========================================================
def log_error(file_name, hub_id, stage, reason):
    """Ghi nhận các file lỗi vào log để xử lý sau"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] FILE: {file_name} | ID: {hub_id} | STAGE: {stage} | LỖI: {reason}\n")

def remove_accents(input_str):
    if not input_str or not isinstance(input_str, str): return "UNKNOWN"
    nks = unicodedata.normalize('NFKD', input_str)
    res = "".join([c for c in nks if not unicodedata.combining(c)])
    res = res.replace('đ', 'd').replace('Đ', 'D')
    res = re.sub(r'[^a-zA-Z0-9_]', '_', res)
    return re.sub(r'_+', '_', res).strip('_').upper()

def robust_json_parse(text):
    """Cứu hộ JSON khi AI bị lỗi format (Đã nâng cấp để đón Array)"""
    if not text: return None
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Bắt cả object {} và array []
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
    except:
        return None

def clean_text(text):
    if not isinstance(text, str): return text
    text = re.sub(r' +', ' ', text)
    return text.strip()

def _has_valid_data(data_dict):
    """Hàm kiểm tra dữ liệu có tồn tại không (Tránh gửi chuỗi rỗng cho AI)"""
    if not data_dict: return False
    for v in data_dict.values():
        if isinstance(v, str) and v.strip(): return True
        if isinstance(v, list) and len(v) > 0: return True
        if isinstance(v, dict) and v: return True
    return False

def merge_stage_1_2(p1, p2, hub_id, source_meta):
    """Hợp nhất dữ liệu Core từ Stage 1 và Stage 2"""
    def clean_val(val):
        if isinstance(val, str):
            return re.sub(r'\s+', ' ', val).strip()
        elif isinstance(val, list):
            return [clean_val(x) for x in val if x]
        return val

    # 1. Hợp nhất Entity
    entity = p1.get("entity", {}).copy()
    other_ent = p2.get("entity", {})
    for key in ["ten_raw", "canonical_name", "ten_khoa_hoc", "ho_thuc_vat", "variants", "display_name"]:
        if not entity.get(key) and other_ent.get(key):
            entity[key] = other_ent[key]
            
    # Gộp properties an toàn
    ent_props = entity.get("properties", {})
    other_ent_props = other_ent.get("properties", {})
    for pk, pv in other_ent_props.items():
        if not ent_props.get(pk) and pv:
            ent_props[pk] = pv
    entity["properties"] = ent_props
    
    entity["id"] = hub_id
    if not entity.get("display_name"):
        entity["display_name"] = entity.get("canonical_name")

    # 2. Hợp nhất Claims
    claim_p1 = p1.get("claims", [{}])[0] if p1.get("claims") else {}
    claim_p2 = p2.get("claims", [{}])[0] if p2.get("claims") else {}
    
    dac_tinh = claim_p1.get("dac_tinh_yhct", {})
    mo_ta_raw = claim_p2.get("mo_ta_theo_nguon", {})
    mo_ta_clean = {k: clean_val(v) for k, v in mo_ta_raw.items()}

    final_claims = [{
        "source": source_meta,
        "dac_tinh_yhct": dac_tinh,
        "mo_ta_theo_nguon": mo_ta_clean
    }]

    # 3. Hợp nhất Relationships
    seen_edges = {} 
    for stage_res in [p1, p2]:
        for rel in (stage_res.get("relationships") or []):
            u = remove_accents(str(rel.get("from") or hub_id))
            v = remove_accents(str(rel.get("to") or ""))
            r_type = rel.get("relation_type", "")

            if not v or u == v or not r_type: continue

            props = rel.get("properties", {})
            clean_props = {k: clean_val(v) for k, v in props.items() if v}
            
            # ÉP BUỘC DÙNG NGUỒN CỦA HỆ THỐNG (VÔ HIỆU HÓA AI BỊA SOURCE)
            s_id = source_meta["source_id"]
            
            edge_key = (u, v, r_type, s_id)
            if edge_key not in seen_edges:
                rel["from"] = u
                rel["to"] = v
                rel["properties"] = clean_props
                rel["source"] = {"source_id": s_id}
                seen_edges[edge_key] = rel

    return {
        "entity": entity,
        "nodes": [], # Mảng Nodes đã được loại bỏ triệt để
        "claims": final_claims,
        "relationships": list(seen_edges.values())
    }


# ==========================================================
# 3. HỆ THỐNG MASTER PROMPTS (DIAMOND STANDARD)
# ==========================================================

P1_DNA_PROMPT = """
VAI TRÒ: 
Bạn là Senior YHCT Identity Engineer. Nhiệm vụ của bạn là thiết lập Hub Node (Thực thể gốc) và bản đồ DNA (Tính, Vị, Quy kinh, Bộ phận dùng, Liều dùng chung, Độc tính) của vị thuốc với độ chính xác tuyệt đối từ dữ liệu BRONZE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. CHIẾN LƯỢC ĐỊNH DANH (ENTITY LOCKDOWN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. HUB NODE: 
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
   - 🛑 [MỚI] 'entity.properties.muc_do_doc': Suy luận từ văn bản: "Thuốc độc bảng A", "Thuốc độc bảng B", "Có độc" hoặc "Không độc" (nếu văn bản ghi rõ không độc hoặc không đề cập).
   - 🛑 [MỚI] 'entity.properties.trieu_chung_ngo_doc': Trích xuất nguyên văn các biểu hiện ngộ độc, quá liều (nếu có).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. KIỂM TOÁN DNA CỐT LÕI (BASE ID & PROPERTIES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. TÍNH (T_): Chỉ chọn từ 5 ID gốc: T_HAN, T_LUONG, T_BINH, T_ON, T_NHIET.
2. VỊ (V_): Chỉ chọn từ 6 ID gốc: V_CAY, V_CHUA, V_NGOT, V_DANG, V_MAN, V_NHAT.
3. QUY KINH (K_): Chỉ dùng ID tạng phủ chuẩn: K_CAN, K_TAM, K_TY, K_PHE, K_THAN, K_TAM_BAO, K_BANG_QUANG, K_VI, K_DAI_TRANG, K_TIEU_TRANG, K_DAN, K_TAM_TIEU.
🛑 LUẬT CHỐNG ẢO GIÁC: Nếu văn bản không nhắc đến Tính/Vị/Quy kinh, TUYỆT ĐỐI KHÔNG tạo quan hệ. Mọi quan hệ DNA BẮT BUỘC có 'properties.mo_ta_chi_tiet' (trích chép vắn tắt, đúng trọng tâm).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. PHÁP CHỨNG DỮ LIỆU VÀ KỶ LUẬT ĐỊNH DẠNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- MẢNG NODES: BẮT BUỘC ĐỂ TRỐNG [].
- 🛑 CHỐT CHẶN LATEX (LATEX AUDIT): Trước khi xuất JSON, phải rà soát mọi con số kèm đơn vị đo lường, nhiệt độ, tỷ lệ phần trăm ($g, ml, mg, \%, °C$) BẮT BUỘC bọc trong cặp dấu $ $. Phần trăm phải escape thành $\\%$.
- 🛑 CẤM trích xuất hoặc tạo trường 'source' trong JSON. Hệ thống sẽ tự động điền.
"""

P2_SUBSTANCE_PROMPT = """
VAI TRÒ: 
Bạn là Chuyên gia Pháp chứng Hóa thực vật và Hình thái học. Nhiệm vụ của bạn là trích xuất đặc điểm nhận dạng vật lý và danh mục hoạt chất hóa học từ dữ liệu BRONZE của vị thuốc {HUB_ID}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. PHÁP CHỨNG VĂN BẢN (CLAIMS -> MO_TA_THEO_NGUON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Điền vào mảng 'claims', trong đó 'mo_ta_theo_nguon' bao gồm:
1. 'hinh_thai_chi_tiet': Chép nguyên văn mô tả thân, lá, hoa, quả, rễ. 🛑 Xóa bỏ 100% rác OCR.
2. 'phan_bo': Trích xuất chi tiết vùng địa lý mọc hoang hoặc trồng trọt.
3. 'thanh_phan_hoa_hoc': Chép NGUYÊN VĂN đoạn văn mô tả về các chất hóa học tìm thấy. CẤM TÓM TẮT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. KIỂM KÊ HOẠT CHẤT (RELATIONSHIPS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Với mỗi hoạt chất tìm thấy, tạo một object trong mảng 'relationships':
- 'from': {HUB_ID}
- 'to': Prefix 'HC_' + Tên hoạt chất viết hoa không dấu (Ví dụ: HC_LEONURINE).
- 'relation_type': 'CO_CHUA_HOAT_CHAT'
- 'properties.mo_ta_chi_tiet': BẮT BUỘC chép nguyên văn câu văn chứa tên hoạt chất và hàm lượng.
- 🛑 [MỚI] 'properties.ap_dung_cho_loai': Nếu văn bản có nhiều loài và phân biệt rõ hoạt chất này chỉ thuộc về một loài cụ thể (VD: "chỉ có ở loài lá tím", "nhân trần Trung Quốc chứa..."), trích xuất tên loài đó vào đây. Nếu dùng chung, để `null`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. KỶ LUẬT ĐỊNH DẠNG (BẮT BUỘC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 'nodes': BẮT BUỘC ĐỂ TRỐNG [].
2. 🛑 CHỐT CHẶN LATEX (LATEX AUDIT): Bọc toàn bộ con số kèm đơn vị ($g, \%, mm, cm, °C$) trong cặp dấu $ $. 
🛑 LƯU Ý ĐẶC BIỆT: Nếu không tìm thấy hoạt chất nào cụ thể, BẮT BUỘC trả về mảng `relationships` rỗng `[]`. TUYỆT ĐỐI KHÔNG tự bịa ra thực thể.
"""

P3_CLINICAL_PROMPT = """
VAI TRÒ: Senior Clinical & Remedy Graph Engineer.
NHIỆM VỤ: Phân rã cấu trúc Bài thuốc (BT_) và Chỉ định điều trị từ dữ liệu BRONZE của vị thuốc {HUB_ID}. Áp dụng ĐÚNG NGUYÊN TẮC: Phân rạch ròi giữa "Công năng đơn vị" và "Hiệu quả phối hợp".

🛑 LỆNH TỐI ƯU HÓA ĐẶC BIỆT: BẠN CHỈ CẦN XUẤT RA MỘT MẢNG (ARRAY) CHỨA CÁC QUAN HỆ. KHÔNG XUẤT ENTITY, NODES. 

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. QUY TẮC RẼ NHÁNH GRAPH (DIAMOND STANDARD LÝ LUẬN Y KHOA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bạn phải phân tích dữ liệu đầu vào và áp dụng 1 trong 4 luồng sau. 🛑 CẤM TỰ CHẾ TÊN BÀI THUỐC.

▶ LUỒNG 1: CHỈ ĐỊNH TRỰC TIẾP (VỊ THUỐC -> BỆNH)
- Khi nào dùng: Sách mô tả công dụng của riêng cây thuốc đó (chỉ 1 vị duy nhất). TUYỆT ĐỐI CẤM rẽ sang Luồng 2 và CẤM tạo Node bài thuốc `BT_`.
- Hành động: Nối TRỰC TIẾP từ vị thuốc tới bệnh.
  + 'from': {HUB_ID}
  + 'to': B_ (hoặc S_) + [TEN_BENH_VIET_HOA_KHONG_DAU]
  + 'relation_type': 'CHUA_TRI_BENH' (hoặc CHUA_TRI_TRIEU_CHUNG)
  + 'properties.lieu_dung': Trích xuất chính xác con số hoặc ghi "Tham khảo liều dùng chung của vị thuốc".
  + 'properties.cach_dung': Trích xuất nguyên văn chi tiết cách đun sắc.
  + 🛑 [MỚI] 'properties.doi_tuong_thu_huong': Xác định rõ dùng cho "Người" hay "Thú y (Trâu, Bò, Lợn, Gà...)". Mặc định là "Người".

▶ LUỒNG 2: CHỈ ĐỊNH PHỐI HỢP (BÀI THUỐC -> THÀNH PHẦN & ĐIỀU TRỊ)
- Khi nào dùng: (1) Nêu TÊN RIÊNG của một chế phẩm HOẶC (2) Công thức TỪ 2 VỊ THUỐC TRỞ LÊN.
- Hành động 1 (Vét cạn thành phần): Tạo quan hệ 'BAO_GOM_VI_THUOC' từ ID_BT tới {HUB_ID} và các vị phối hợp VT_.
  + 🛑 [MỚI] 'properties.loai_che_pham': Phân loại rõ "Dân gian", "Cổ phương" hay "Chuẩn hóa hiện đại" (VD: Viên nén, dung dịch rượu chuẩn độ).
  + 'properties.lieu_luong': BẮT BUỘC TRÍCH XUẤT ĐỊNH LƯỢNG của từng vị.
  + 'properties.vai_tro': Suy luận Quân/Thần/Tá/Sứ.
- Hành động 2 (Chỉ định điều trị): Tạo quan hệ 'CHU_TRI_BENH' từ ID_BT đến B_ (hoặc S_).
  + 🛑 [MỚI] 'properties.doi_tuong_thu_huong': Xác định "Người" hoặc loài vật cụ thể.

▶ LUỒNG 3: BÀI THUỐC KHÔNG MỤC TIÊU (VỊ THUỐC -> BÀI THUỐC)
- Khi nào dùng: Sách mô tả một chế phẩm có tên riêng nhưng KHÔNG GHI CHÚ CHỮA BỆNH GÌ.
- Hành động: CHỈ tạo các cạnh 'BAO_GOM_VI_THUOC'. CẤM tạo cạnh 'CHUA_TRI_BENH'.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. KỶ LUẬT ĐỊNH DANH (ENTITY LOCKDOWN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ĐỊNH DANH BỆNH LÝ: Sử dụng tiền tố `B_` cho Bệnh và `S_` cho Triệu chứng. (VD: `B_RONG_HUYET`, `S_DAU_BUNG`).
2. ĐỊNH DANH BÀI THUỐC: Prefix 'BT_' + Tên riêng hoặc [TEN_BENH] + '_' + [TEN_VI_THUOC_CHINH]. CẤM tạo ID `BT_` nếu chỉ có 1 vị.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. KỶ LUẬT ĐỊNH DẠNG (BẮT BUỘC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 🛑 CHỐT CHẶN LATEX (LATEX AUDIT): Trước khi xuất, kiểm tra MỌI số đếm, khối lượng, nồng độ, tỷ lệ phần trăm ($g, ml, \%, 1/5000$) PHẢI bọc trong cặp dấu $ $. Phần trăm escape thành $\\%$.
- 🛑 CẤM trích xuất trường 'source' trong JSON.
"""

P4_PHARMA_PROMPT = """
VAI TRÒ: Senior Forensic Pharmacology Engineer.
NHIỆM VỤ: Trích xuất Công năng (YHCT) và Tác dụng dược lý hiện đại (bao gồm cả phân tích Độc tính) từ văn bản của vị thuốc {HUB_ID}. 

🛑 LỆNH TỐI ƯU HÓA ĐẶC BIỆT: BẠN CHỈ CẦN XUẤT RA MỘT MẢNG (ARRAY) CHỨA CÁC QUAN HỆ. KHÔNG XUẤT ENTITY, NODES HAY SOURCE. HỆ THỐNG SẼ TỰ ĐIỀN BẰNG CODE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. QUY TẮC PHÂN MIỀN DỮ LIỆU (DOMAIN ISOLATION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BẮT BUỘC tạo các nhóm quan hệ tách biệt tuyệt đối sau:

1. MIỀN ĐÔNG Y (CÔNG NĂNG - FUNCTIONS):
   - Nguồn: Trích xuất từ phần lý luận YHCT, tính vị quy kinh.
   - ID Đích: Prefix 'CN_' + Tên công năng viết hoa không dấu (Ví dụ: CN_HOAT_HUYET, CN_THANH_NHIET).
   - Nhãn: 'CO_CONG_NANG'.

2. MIỀN TÂY Y (DƯỢC LÝ - PHARMACOLOGY):
   - Nguồn: Trích xuất từ phần tác dụng dược lý, thí nghiệm thực nghiệm lâm sàng.
   - ID Đích: Prefix 'DL_' + Tác động sinh lý chính viết hoa không dấu.
   - Nhãn: 'CO_TAC_DUNG_DUOC_LY'.
   🛑 QUY TẮC: TUYỆT ĐỐI KHÔNG đưa tên đối tượng thí nghiệm (chuột, thỏ, loài vật, vi khuẩn cụ thể) vào ID.

3. 🛑 [MỚI] MIỀN PHÁP CHỨNG ĐỘC TÍNH (TOXICOLOGY):
   - Nếu văn bản có mô tả về độc tính (ngộ độc, liều chết, tác dụng phụ nguy hiểm), BẮT BUỘC tạo quan hệ với ID Đích có Prefix 'DL_DOC_TINH_' + [CƠ_QUAN_BỊ_ẢNH_HƯỞNG_HOẶC_ĐẶC_TÍNH_VIẾT_HOA_KHÔNG_DẤU] (Ví dụ: DL_DOC_TINH_TIM, DL_DOC_TINH_THAN_KINH, DL_DOC_TINH).
   - Nhãn: 'CO_TAC_DUNG_DUOC_LY'.

▶ 🛑 QUY TẮC KẾ THỪA THAM CHIẾU (INHERITANCE):
- Nếu văn bản ghi "Tác dụng giống như vị thuốc X", hãy tạo quan hệ tương ứng và BẮT BUỘC thêm 2 thuộc tính: `'properties.is_inherited': true` và `'properties.reference_to': 'VI_THUOC_X'`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. KỶ LUẬT PHÁP CHỨNG VĂN BẢN (EDGE EVIDENCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mọi quan hệ CO_CONG_NANG và CO_TAC_DUNG_DUOC_LY BẮT BUỘC phải có trường 'properties.mo_ta_chi_tiet'. 🛑 TUYỆT ĐỐI KHÔNG ĐỂ RỖNG.

- 🛑 [MỚI] ĐỐI VỚI QUAN HỆ ĐỘC TÍNH: Trong trường 'mo_ta_chi_tiet', BẮT BUỘC ưu tiên trình bày theo cấu trúc: [Cơ chế gây độc] + [Triệu chứng ngộ độc] + [Định lượng liều độc/liều chết]. Phải vét cạn mọi con số liên quan đến liều lượng gây tử vong hoặc ngộ độc (ví dụ: LD50, 15g, 0,06mg/kg).
- 🛑 'properties.ap_dung_cho_loai': Nếu tác dụng dược lý hoặc độc tính chỉ đúng với một loài cụ thể trong nhóm (VD: Bồ bồ kháng lỵ mạnh, Nhân trần kháng lỵ yếu), phải ghi rõ tên loài áp dụng vào đây. Nếu dùng chung cho cả Node, để null.
- VERBATIM (NGUYÊN VĂN): Chép chính xác đoạn văn mô tả tác dụng/công năng từ sách. 
- VẮN TẮT, ĐÚNG TRỌNG TÂM: Cắt bỏ các từ ngữ rườm rà không cần thiết, đi thẳng vào bản chất y lý.
- 🛑 CHỐT CHẶN LATEX (LATEX AUDIT): Toàn bộ con số, đơn vị, nồng độ, tỷ lệ ($g, mg/kg, ml, \%, °C$) PHẢI bọc trong cặp dấu $ $. Phần trăm phải escape thành $\\%$.
🛑 CẤM trích xuất hoặc tạo trường 'source' trong JSON.
"""

MODULAR_PROMPTS = [P1_DNA_PROMPT, P2_SUBSTANCE_PROMPT, P3_CLINICAL_PROMPT, P4_PHARMA_PROMPT]


# ==========================================================
# 4. ENGINE XỬ LÝ CHÍNH (DIAMOND PIPELINE)
# ==========================================================
def process_diamond_gold():
    # Sử dụng hàm get_page_number để sắp xếp tự nhiên
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")), key=get_page_number)
    
    total_files = len(files)
    print(f"🚀 Bắt đầu tiến trình Diamond Audit cho {total_files} file...")

    for idx, file_path in enumerate(files):
        ten_file_goc = os.path.basename(file_path).replace(".json", "")
        
        # 🟢 THIẾT LẬP ĐƯỜNG DẪN 3 FILE KẾT QUẢ THEO CẤU TRÚC THUẦN VIỆT
        duong_dan_dinh_danh = os.path.join(OUTPUT_DIR, f"{ten_file_goc}_dinh_danh.json")
        duong_dan_bai_thuoc = os.path.join(OUTPUT_DIR, f"{ten_file_goc}_bai_thuoc.json")
        duong_dan_duoc_ly = os.path.join(OUTPUT_DIR, f"{ten_file_goc}_duoc_ly.json")

        # 🟢 CƠ CHẾ CHECKPOINT: Chỉ bỏ qua nếu CẢ 3 file đầu ra đều đã tồn tại
        if os.path.exists(duong_dan_dinh_danh) and os.path.exists(duong_dan_bai_thuoc) and os.path.exists(duong_dan_duoc_ly):
            print(f"⏩ [{idx+1}/{total_files}] Bỏ qua: {ten_file_goc} (Đã đủ 3 mảnh dữ liệu)")
            continue

        print(f"💎 [{idx+1}/{total_files}] Đang xử lý: {ten_file_goc}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                # Xử lý trường hợp dữ liệu Bronze bị bọc trong mảng hoặc là object đơn lẻ
                bronze = raw_data[0] if isinstance(raw_data, list) else raw_data
            
            if not bronze or not isinstance(bronze, dict) or "dinh_danh" not in bronze:
                print(f"⚠️ Bỏ qua file {ten_file_goc} do nội dung không đúng cấu trúc Bronze.")
                continue

            # Sử dụng hàm normalize_id từ hệ thống của huynh kết hợp remove_accents
            raw_id = bronze['dinh_danh'].get('id', 'UNKNOWN_ID')
            hub_id = remove_accents(normalize_id(raw_id) if normalize_id else raw_id)
            
            # 🟢 MỎ NEO TRANG ĐẦU (FIRST-PAGE ANCHOR)
            page_match = re.search(r'(\d+)', ten_file_goc)
            fallback_page = page_match.group(1) if page_match else "0"
            
            nguon_trang_list = bronze.get('dinh_danh', {}).get('nguon_trang', [])
            if isinstance(nguon_trang_list, list) and len(nguon_trang_list) > 0:
                anchor_page = str(nguon_trang_list[0])
            else:
                anchor_page = fallback_page
            
            source_meta = {
                "source_id": f"CT_VT_VN_T{anchor_page}",
                "ten_sach": "Những cây thuốc và vị thuốc Việt Nam",
                "tac_gia": "Đỗ Tất Lợi",
                "trang": anchor_page
            }

            vbt = bronze.get("van_ban_tho", {}) or {}

            # Phân tách văn bản thô thành các segment tương ứng với từng giai đoạn prompt
            segments = [
                {
                    "dinh_danh": bronze.get("dinh_danh"), 
                    "van_ban_tho": {
                        "ten_khoa_hoc_va_ho": vbt.get("ten_khoa_hoc_va_ho"),
                        "tinh_vi_quy_kinh": vbt.get("tinh_vi_quy_kinh"),
                        "mo_ta_hinh_thai": vbt.get("mo_ta_hinh_thai"),
                        "lieu_dung_chung": vbt.get("lieu_dung_chung") # Đã bổ sung
                    }
                },
                {
                    "dinh_danh": bronze.get("dinh_danh"),
                    "van_ban_tho": {
                        "mo_ta_hinh_thai": vbt.get("mo_ta_hinh_thai"),
                        "thanh_phan_hoa_hoc": vbt.get("thanh_phan_hoa_hoc"),
                        "phan_bo_thu_hai_che_bien": vbt.get("phan_bo_thu_hai_che_bien")
                    }
                },
                {
                    "dinh_danh": bronze.get("dinh_danh"),
                    "van_ban_tho": {
                        "cac_bai_thuoc_raw": vbt.get("cac_bai_thuoc_raw")
                    }
                },
                {
                    "dinh_danh": bronze.get("dinh_danh"),
                    "van_ban_tho": {
                        "tinh_vi_quy_kinh": vbt.get("tinh_vi_quy_kinh"),
                        "tac_dung_duoc_ly": vbt.get("tac_dung_duoc_ly")
                    }
                }
            ]

            stage_results = {0: {}, 1: {}, 2: {}, 3: {}}

            # Chạy vòng lặp qua 4 giai đoạn Prompt (Identity -> Substance -> Remedy -> Pharma)
            for i, p_sys in enumerate(MODULAR_PROMPTS):
                stage_label = ['DNA', 'Hoạt chất', 'Bài thuốc', 'Dược lý'][i]
                print(f"   -> Stage {i+1}/4 [{stage_label}]...", end="\r")
                
                vbt_data = segments[i].get("van_ban_tho", {})
                
                # 🟢 SMART PRE-CHECK 1: Bỏ qua nếu văn bản hoàn toàn rỗng
                if not _has_valid_data(vbt_data):
                    print(f"\n      ∅ Bỏ qua gọi API Stage {i+1} do văn bản nguồn rỗng (Tạo fallback rỗng).")
                    if i in [2, 3]:
                        stage_results[i] = {"relationships": [], "metadata": {"status": "empty_source"}}
                    else:
                        stage_results[i] = {"entity": {}, "claims": [], "relationships": [], "metadata": {"status": "empty_source"}}
                    continue
                
                # Cấu hình Schema và Token tối ưu cho từng giai đoạn
                current_schema = STAGE34_SCHEMA if i in [2, 3] else RESPONSE_SCHEMA
                max_tokens = 8192 if i >= 2 else 4096
                
                try:
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        config=types.GenerateContentConfig(
                            system_instruction=p_sys.replace("{HUB_ID}", hub_id),
                            temperature=0.0,
                            response_mime_type="application/json",
                            response_schema=current_schema,
                            max_output_tokens=max_tokens
                        ),
                        contents=[json.dumps(segments[i], ensure_ascii=False)]
                    )
                    
                    data = None
                    if response.parsed:
                        # Hỗ trợ cả Pydantic model và dict thuần
                        data = response.parsed.model_dump() if hasattr(response.parsed, 'model_dump') else response.parsed
                    
                    # Cứu hộ nếu phản hồi không parse được tự động nhưng có text
                    if not data and response.text:
                        data = robust_json_parse(response.text)
                        
                    if not data:
                        error_msg = f"Lỗi Schema hoặc API trả về rỗng không thể parse"
                        print(f"\n      ⚠️ {error_msg} tại Stage {i+1}")
                        log_error(ten_file_goc, hub_id, i+1, error_msg)
                    else:
                        # 🟢 QUÉT SẠCH 'SOURCE' RÁC VÀ GÁN MỎ NEO CHUẨN CỦA HỆ THỐNG
                        if isinstance(data, list):
                            for rel in data:
                                rel.pop("source", None)
                                rel.pop("source_id", None)
                                rel["source"] = {"source_id": source_meta["source_id"]}
                            stage_results[i] = {"relationships": data}
                        elif isinstance(data, dict) and data:
                            if "relationships" in data and isinstance(data["relationships"], list):
                                for rel in data["relationships"]:
                                    rel.pop("source", None)
                                    rel.pop("source_id", None)
                                    rel["source"] = {"source_id": source_meta["source_id"]}
                            stage_results[i] = data
                        else:
                            print(f"\n      ❌ Stage {i+1} trả về dữ liệu rỗng dù có văn bản.")
                            log_error(ten_file_goc, hub_id, i+1, "AI trả về dữ liệu không đúng định dạng List/Dict")
                
                except Exception as api_err:
                    error_msg = f"Exception API: {str(api_err)[:200]}"
                    print(f"\n      ❌ Lỗi API Stage {i+1}: {error_msg}")
                    log_error(ten_file_goc, hub_id, i+1, error_msg)

                # Nghỉ 5 giây để chống lỗi 429 Rate Limit
                time.sleep(5)

            success_count = sum(1 for k in stage_results if stage_results[k])

            # =================================================================
            # KẾT XUẤT THÀNH 3 FILE ĐỘC LẬP (ĐỊNH DANH, BÀI THUỐC, DƯỢC LÝ)
            # =================================================================
            
            # --- FILE 1: ĐỊNH DANH & THUỘC TÍNH (Node gốc và đặc điểm vật lý) ---
            if 0 in stage_results and 1 in stage_results and stage_results[0] and stage_results[1]:
                du_lieu_dinh_danh = merge_stage_1_2(stage_results[0], stage_results[1], hub_id, source_meta)
                with open(duong_dan_dinh_danh, "w", encoding="utf-8") as f:
                    json.dump(du_lieu_dinh_danh, f, ensure_ascii=False, indent=2)
                print(f"   ✅ Đã kết xuất file Định danh & Thuộc tính.")

            # --- FILE 2: BÀI THUỐC (Mạng lưới quan hệ phối ngũ và chỉ định) ---
            if 2 in stage_results and "relationships" in stage_results[2]:
                du_lieu_bai_thuoc = {
                    "entity_hub": hub_id,
                    "source": source_meta,
                    "nodes": [], 
                    "relationships": stage_results[2].get("relationships", []),
                    "metadata": stage_results[2].get("metadata", {})
                }
                with open(duong_dan_bai_thuoc, "w", encoding="utf-8") as f:
                    json.dump(du_lieu_bai_thuoc, f, ensure_ascii=False, indent=2)
                
                trang_thai = "chuẩn hóa rỗng" if not stage_results[2].get("relationships") else "thành công"
                print(f"   ✅ Đã kết xuất file Bài thuốc ({trang_thai}).")
                
            # --- FILE 3: DƯỢC LÝ & Y LÝ (Tính vị, Quy kinh, Hoạt chất và Dược lý) ---
            if 3 in stage_results and "relationships" in stage_results[3]:
                du_lieu_duoc_ly = {
                    "entity_hub": hub_id,
                    "source": source_meta,
                    "nodes": [],
                    "relationships": stage_results[3].get("relationships", []),
                    "metadata": stage_results[3].get("metadata", {})
                }
                with open(duong_dan_duoc_ly, "w", encoding="utf-8") as f:
                    json.dump(du_lieu_duoc_ly, f, ensure_ascii=False, indent=2)
                
                trang_thai = "chuẩn hóa rỗng" if not stage_results[3].get("relationships") else "thành công"
                print(f"   ✅ Đã kết xuất file Dược lý & Y lý ({trang_thai}).")

            if success_count < 4:
                print(f"   ⚠️ Hoàn tất không trọn vẹn ({success_count}/4 Stages). Xem chi tiết tại error_log.txt")
            else:
                print(f"   ✨ Hoàn tất toàn diện {hub_id}.")

        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"❌ LỖI NGHIÊM TRỌNG TẠI FILE {ten_file_goc}:\n{error_msg}")
            log_error(ten_file_goc, "N/A", "CRITICAL", error_msg)

if __name__ == "__main__":
    process_diamond_gold()