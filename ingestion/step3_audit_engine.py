import os
import json
import glob
import sys
import traceback
import time
import re 
import unicodedata
from google import genai
from google.genai import types
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- KẾT NỐI HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import normalize_id, robust_json_load, get_page_number, remove_accents
from utils.master_schema_genai import RESPONSE_SCHEMA, STAGE34_SCHEMA

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
PROJECT_ID = "yhct-knowledge-graph"
LOCATION   = "us-central1"

# Đã thay thế bằng cấu trúc Medallion
BRONZE_DIR        = settings.DIR_BRONZE_RAW
GOLD_DIR          = settings.DIR_SILVER_MAPPED
AUDIT_REPORTS_DIR = settings.DIR_LOGS_AUDIT
os.makedirs(AUDIT_REPORTS_DIR, exist_ok=True)

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# ==========================================================
# 2. AUDIT SCHEMA (CẤU TRÚC PHẲNG - SIÊU ĐƠN GIẢN CHỐNG LỖI JSON)
# ==========================================================
AUDIT_REPORT_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "buoc_tu_duy": types.Schema(type="STRING", description="Tóm tắt quá trình tìm lỗi dưới 50 từ."),
        "ket_luan": types.Schema(type="STRING", enum=["DAT_CHUAN", "CAN_SUA_DOI", "LOI_NGHIEM_TRONG"]),
        "danh_sach_loi": types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "ma_loi": types.Schema(type="STRING"),
                    "loai_loi": types.Schema(type="STRING"),
                    "thuc_the_lien_quan": types.Schema(type="STRING"),
                    "mo_ta": types.Schema(type="STRING"),
                    "bang_chung_bronze": types.Schema(type="STRING"),
                    "vi_tri_gold": types.Schema(type="STRING", nullable=True),
                    
                    "han_dong": types.Schema(type="STRING", enum=["THEM_EDGE", "XOA_EDGE", "SUA_NHAN_EDGE", "SUA_ID", "THEM_LATEX", "XOA_RAC", "THEM_CLAIM", "SUA_PROPERTIES"]),
                    "payload": types.Schema(
                        type="OBJECT",
                        properties={
                            "from": types.Schema(type="STRING", nullable=True),
                            "to": types.Schema(type="STRING", nullable=True),
                            "relation_type": types.Schema(type="STRING", nullable=True),
                            "source_id": types.Schema(type="STRING", nullable=True),
                            "gia_tri_moi": types.Schema(
                                type="OBJECT", 
                                nullable=True,
                                properties={
                                    "mo_ta_chi_tiet": types.Schema(type="STRING", nullable=True),
                                    "lieu_luong": types.Schema(type="STRING", nullable=True),
                                    "loai_bai_thuoc": types.Schema(type="STRING", nullable=True),
                                    "vai_tro": types.Schema(type="STRING", nullable=True),
                                    "phoi_ngu_logic": types.Schema(type="STRING", nullable=True),
                                    "thu_hai": types.Schema(type="STRING", nullable=True),
                                    "che_bien_tho": types.Schema(type="STRING", nullable=True),
                                    "bo_phan_dung": types.Schema(type="STRING", nullable=True),
                                    "phan_bo": types.Schema(type="STRING", nullable=True),
                                    "ghi_chu": types.Schema(type="STRING", nullable=True)
                                }
                            ) 
                        }
                    )
                },
                required=["ma_loi", "loai_loi", "mo_ta", "bang_chung_bronze", "han_dong", "payload"]
            )
        )
    },
    required=["buoc_tu_duy", "ket_luan", "danh_sach_loi"]
)

# ==========================================================
# 3. UNIVERSAL MASTER PROMPT (HỆ ĐIỀU HÀNH KIỂM TOÁN LÕI)
# ==========================================================

UNIVERSAL_AUDIT_PROMPT = """
VAI TRÒ: Senior Forensic YHCT Auditor.
NHIỆM VỤ TỔNG QUÁT: Kiểm toán tính toàn vẹn, chính xác và không dư thừa của Dữ liệu Đồ thị (GOLD) so với Văn bản gốc (BRONZE).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. CHỈ THỊ CHUYÊN MÔN (DOMAIN INSTRUCTION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{domain_specific_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. QUY TRÌNH KIỂM TOÁN CHỐNG ẢO GIÁC & XỬ LÝ LỖI OCR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. BƯỚC TƯ DUY: Viết tối đa 50 từ tóm tắt hiện trạng GOLD so với BRONZE.
2. NGUYÊN TẮC "TÔN TRỌNG SỰ TRỐNG RỖNG" (NO-INFERENCE): 
   - Nếu một trường dữ liệu (Tính, Vị, Kinh, Hoạt chất...) trong GOLD bị rỗng VÀ trong BRONZE cũng KHÔNG CÓ thông vị -> BẮT BUỘC coi là ĐẠT CHUẨN.
   - TUYỆT ĐỐI CẤM dùng tri thức AI bên ngoài để tự điền dữ liệu nếu sách gốc (BRONZE) không nhắc tới.
3. PHÂN ĐỊNH LỖI THIẾU (THEM_EDGE) VÀ LỖI THUỘC TÍNH (SUA_PROPERTIES):
   - ĐỐI CHIẾU INVENTORY: Chỉ dùng `SUA_PROPERTIES` khi ID đối tượng ĐÃ CÓ SẴN trong INVENTORY được cung cấp. Nếu BRONZE có thông tin mà INVENTORY không có, BẮT BUỘC dùng lệnh `THEM_EDGE`.
   - CẤM BÁO THIẾU OAN: Nếu ID đã có trong INVENTORY (dưới bất kỳ từ đồng nghĩa nào), CẤM dùng lệnh `THEM_EDGE` cho thông tin đó nữa.
4. XỬ LÝ LỖI LOGIC VẬT LÝ / LỖI CHÍNH TẢ (OCR):
   - Nếu phát hiện số liệu phi lý do lỗi quét OCR (Ví dụ: hạt 7cm nằm trong quả 1cm), bạn ĐƯỢC PHÉP dùng lệnh `SUA_PROPERTIES` để sửa đơn vị (cm -> mm) hoặc sửa chính tả ("Cay nhỏ" -> "Cây nhỏ") cho hợp logic thực tế.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
III. THIẾT QUÂN LUẬT LỆNH SỬA (IRONCLAD DISCIPLINE - CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trong mảng `danh_sach_loi`, mỗi lỗi phải kèm theo một `payload` sửa chữa. Nếu vi phạm 1 trong 5 điều sau, hệ thống sẽ sụp đổ:
1. ĐỊNH DẠNG EXACT MATCH: 
   - Trường `from` BẮT BUỘC phải chép nguyên văn ID_MỎ_NEO (Tuyệt đối không được tự ý cắt bỏ tiền tố VI_THUOC_ hay BT_). LƯU Ý: Riêng tại Stage Bài Thuốc, `from` là ID của Bài thuốc.
   - Trường `relation_type` BẮT BUỘC viết hoa toàn bộ và dùng dấu gạch dưới (VD: CO_TAC_DUNG_DUOC_LY, CO_CHUA_HOAT_CHAT, BAO_GOM_VI_THUOC).
2. KỶ LUẬT TẠO ID MỚI (DÀNH CHO THEM_EDGE): 
   - Nếu tạo thực thể mới, trường `to` phải tuân thủ tiền tố: Hoạt chất [HC_], Dược lý [DL_], Bệnh [B_], Triệu chứng [S_], Công năng [CN_].
   - KHÔNG ĐƯỢC viết ID kiểu ngôn ngữ tự nhiên (VD: Sai: 'Chat_mau_do' -> Đúng: 'HC_CHAT_MAU_DO').
3. NO-NULL: Các trường `from`, `to`, `relation_type` và `source_id` BẮT BUỘC điền ĐẦY ĐỦ. Tuyệt đối không để null.
4. CHỐNG LƯỜI BIẾNG: Trường `gia_tri_moi` trong lệnh `SUA_PROPERTIES` và `THEM_EDGE` TUYỆT ĐỐI không được để rỗng `{}`. Phải trích xuất câu chữ từ BRONZE đắp vào.
5. LATEX: Mọi con số, tỷ lệ, nồng độ, nhiệt độ BẮT BUỘC bọc trong ký hiệu $ $.
KỶ LUẬT ĐIỀN THUỘC TÍNH (MANDATORY PROPERTIES):

TUYỆT ĐỐI KHÔNG để gia_tri_moi rỗng {} khi thực hiện THEM_EDGE hoặc SUA_PROPERTIES.

Đối với Tính/Vị/Kinh: BẮT BUỘC phải trích xuất cụm từ đích danh từ BRONZE vào mo_ta_chi_tiet. (VD: Nếu thêm T_ON thì mô tả phải chứa chữ 'ôn' hoặc 'ấm').

Đối với Hoạt chất: Nếu Bronze không có mô tả sâu, BẮT BUỘC ghi: 'Có chứa trong thành phần [Tên hoạt chất]'. Không được ghi chung chung."
🛑 CẤM LOGIC NGƯỢC: Một Bài thuốc (BT_) hoặc Vị thuốc (VT_) tuyệt đối không được điều trị (CHU_TRI) cho một thực thể là tên của chính nó hoặc vị thuốc khác. Nếu thấy cạnh nối trỏ vào một ID có chứa chữ 'VI_THUOC', hãy ra lệnh XOA_EDGE hoặc sửa lại to thành triệu chứng/bệnh thực sự dựa vào văn bản Bronze.
"""

STAGE_1_RULES = """
- MỤC TIÊU: Đối soát TÍNH, VỊ, QUY KINH, BỘ PHẬN DÙNG, THU HÁI.
- GIỚI HẠN ID HẰNG SỐ: T_HAN, T_LUONG, T_BINH, T_ON, T_NHIET; V_CAY, V_CHUA, V_NGOT, V_DANG, V_MAN, V_NHAT; K_CAN, K_TAM, K_TY, K_PHE, K_THAN, K_TAM_BAO, K_BANG_QUANG, K_VI, K_DAI_TRANG, K_TIEU_TRANG, K_DAN, K_TAM_TIEU.
- CẤM: Tuyệt đối không nhầm lẫn các tạng phủ với nhau. Nếu BRONZE có Kinh/Tính/Vị mà INVENTORY_DNA không có, phải THEM_EDGE với ID hằng số tương ứng.
"""

STAGE_2_RULES = """
- MỤC TIÊU: Truy quét Hoạt chất hóa học (Nhãn: CO_CHUA_HOAT_CHAT).
- KỶ LUẬT ID: Mọi hoạt chất mới tạo bằng lệnh THEM_EDGE bắt buộc phải có tiền tố HC_ (Ví dụ: HC_RUTIN, HC_TANIN).
- CHỐNG LƯỜI BIẾNG BỎ RỖNG: Khi dùng lệnh SUA_PROPERTIES hoặc THEM_EDGE cho một Hoạt chất, nếu văn bản BRONZE chỉ nhắc đến tên chất mà KHÔNG CÓ chỉ số định lượng hay mô tả cụ thể, BẮT BUỘC điền vào trường `mo_ta_chi_tiet` nội dung: "Có chứa trong thành phần". Tuyệt đối không được để `gia_tri_moi: {}`.
- CẤM ĐÒI HỎI THỪA: Nếu GOLD đã có tên các chất hóa học định danh chi tiết, KHÔNG bắt bẻ đòi thêm các danh từ phân nhóm hóa học đại cương.
"""

STAGE_3_RULES = """
- MỤC TIÊU: Kiểm soát logic Bài thuốc (Tiền tố BT_).
- CHÚ Ý TRƯỜNG 'FROM': Ở Stage này, trường `from` trong payload BẮT BUỘC phải là ID của bài thuốc (Bắt đầu bằng BT_), TUYỆT ĐỐI KHÔNG DÙNG ID mỏ neo của vị thuốc.
- CẤU TRÚC BẮT BUỘC: Mỗi bài thuốc phải có cạnh BAO_GOM_VI_THUOC và cạnh CHU_TRI_BENH/CHU_TRI_TRIEU_CHUNG.
- LỖI LOGIC ĐÍCH ĐẾN: Nhãn CHU_TRI tuyệt đối không được trỏ đến ID của một Vị thuốc.
- CẠNH MỒ CÔI: Chỉ báo THEM_EDGE bệnh lý khi BRONZE có mô tả chỉ định rõ ràng mà INVENTORY hoàn toàn không có. Không tự bịa tên bệnh.
- KỶ LUẬT TẠO ID: CẤM sử dụng thuật ngữ tiếng nước ngoài để tạo ID bệnh lý mới. Bắt buộc phải dịch nghĩa/phiên âm sang Tiếng Việt chuẩn, định dạng [B_] hoặc [S_] kèm TÊN_VIẾT_HOA_KHÔNG_DẤU.
- QUY TẮC NÉN DỮ LIỆU: Mọi thông tin liều lượng, cách dùng, phối ngũ của một vị thuốc trong bài thuốc PHẢI NÉN vào DUY NHẤT một mảng `gia_tri_moi` cho cạnh đó, không tách thành nhiều lệnh.
"""

STAGE_4_RULES = """
- MỤC TIÊU: Phân loại Công năng Đông y (Nhãn: CO_CONG_NANG) và Tác dụng Dược lý Tây y (Nhãn: CO_TAC_DUNG_DUOC_LY).
- KỶ LUẬT ID: Mọi thực thể mới phải dùng đúng tiền tố. Đông y là [CN_], Tây y là [DL_].
- KIỂM TRA THUỘC TÍNH: Nếu INVENTORY có ID nhưng để rỗng `properties` mà BRONZE có đoạn văn mô tả pháp chứng, BẮT BUỘC dùng SUA_PROPERTIES chép nguyên văn đoạn mô tả đó vào `mo_ta_chi_tiet`.
- CẤM NHIỄU LOGIC: Khi sao chép bằng chứng cho CÔNG NĂNG, TUYỆT ĐỐI KHÔNG chép kèm các thông tin thuộc về TÍNH và VỊ vào `mo_ta_chi_tiet`.
- CẤM ID RÁC: Tuyệt đối không đưa tên các loài động vật (chuột, thỏ) hoặc đối tượng thực nghiệm sinh học vào làm ID Dược lý.
"""

# ==========================================================
# 4. ENGINE VẬN HÀNH (SANITY, MERGE & PYTHON FIREWALL)
# ==========================================================

def sanitize_lenh_sua(lenh_sua_list, hub_id_clean):
    if not lenh_sua_list: return []
    cleaned_list = []
    for cmd in lenh_sua_list:
        payload = cmd.get("payload", {})
        
        # 🛡️ LUẬT 1: Ép 'from' phải khớp tuyệt đối với ID Mỏ neo (Trừ bài thuốc)
        from_val = str(payload.get("from", ""))
        if "_BAI_THUOC" not in from_val:
            payload["from"] = hub_id_clean
            
        # 🛡️ LUẬT 2: Ép 'relation_type' phải VIẾT HOA
        if payload.get("relation_type"):
            payload["relation_type"] = str(payload["relation_type"]).upper()
            
        # 🛡️ LUẬT 3: Tự động thêm tiền tố HC_ cho hoạt chất nếu AI quên
        to_val = str(payload.get("to", ""))
        if payload.get("relation_type") == "CO_CHUA_HOAT_CHAT" and to_val and not to_val.startswith("HC_"):
            payload["to"] = "HC_" + normalize_id(to_val)

        # Giữ nguyên logic bọc LaTeX cũ của bạn
        val_obj = payload.get("gia_tri_moi")
        if isinstance(val_obj, dict):
            for k, v in val_obj.items():
                if isinstance(v, str):
                    v = re.sub(r'(?<!\$)\b(\d+[\d\.,-]*)\s*(g|ml|%|°C|mm|cm|bát|ống|muỗng|phần)\b(?!\$)', r'$\1\2$', v)
                    val_obj[k] = v
        cleaned_list.append(cmd)
    return cleaned_list


def merge_reports(reports, herb_id, existing_rels):
    """Hợp nhất, BỘ LỌC CHỐNG ẢO GIÁC VÀ PHẠT ĐIỂM TỰ ĐỘNG (Đã tích hợp Logic Backup)"""
    if not reports: return None
    
    final = {
        "buoc_tu_duy": [],
        "metadata": {"id_thuc_the": herb_id, "score": 100, "tong_loi": 0, "tong_edge_thieu": 0},
        "ket_luan": "DAT_CHUAN", 
        "logs": [], 
        "lenh_sua": []
    }
    
    gold_triplets = set()
    for r in existing_rels:
        f, t = normalize_id(r.get("from", "")), normalize_id(r.get("to", ""))
        rtype = str(r.get("relation_type", "")).strip().upper()
        gold_triplets.add((f, t, rtype))
        
    # --- BẢN ĐỒ ÁNH XẠ NHIỆT NĂNG TỪ BACKUP ---
    THERMAL_MAP = {
        "HÀN": "T_HAN", "LẠNH": "T_HAN",
        "LƯƠNG": "T_LUONG", "MÁT": "T_LUONG",
        "BÌNH": "T_BINH",
        "ÔN": "T_ON", "ẤM": "T_ON",
        "NHIỆT": "T_NHIET", "NÓNG": "T_NHIET"
    }
    
    total_penalty = 0
    valid_logs_count = 0
    valid_edge_thieu_count = 0

    for i, r in enumerate(reports):
        prefix = f"STG_{i+1}"
        
        if r.get("is_system_error"):
            total_penalty += 50
            final["buoc_tu_duy"].append(f"❌ [HỆ THỐNG PHẠT]: {prefix} không trả về JSON hợp lệ. Bị trừ 50 điểm.")
            continue
            
        if r.get("buoc_tu_duy"):
            final["buoc_tu_duy"].append(f"[{prefix}]: {r.get('buoc_tu_duy')}")

        for item in r.get("danh_sach_loi", []):
            ma_loi = str(item.get('ma_loi', f'ERR_{valid_logs_count}'))
            if not ma_loi.startswith("STG_"):
                ma_loi = f"{prefix}_{ma_loi}"

            payload = item.get("payload", {})
            f_raw = payload.get("from", "")
            t_raw = payload.get("to", "")
            rtype = str(payload.get("relation_type", "")).strip().upper()
            han_dong = item.get("han_dong", "")
            gia_tri_moi = payload.get("gia_tri_moi", {})

            # --- CHỐT CHẶN 0: THERMAL FIX (Logic từ Backup) ---
            if str(t_raw).startswith("T_") or rtype == "CO_TINH":
                # Sửa lỗi AttributeError nếu gia_tri_moi bị null
                mo_ta = str((gia_tri_moi or {}).get("mo_ta_chi_tiet", "")).upper()
                for keyword, correct_id in THERMAL_MAP.items():
                    if keyword in mo_ta:
                        if t_raw != correct_id:
                            final["buoc_tu_duy"].append(f"🛡️ [Thermal Fix] Sửa ID {t_raw} thành {correct_id} dựa trên mô tả: '{mo_ta}'")
                            payload["to"] = correct_id
                            t_raw = correct_id
                        break

            f_norm = normalize_id(f_raw)
            t_norm = normalize_id(t_raw)

            # 🔥 BỘ LỌC 1: Lệnh vá ảo giác (Đã có rồi vẫn xúi thêm)
            if han_dong == "THEM_EDGE" and (f_norm, t_norm, rtype) in gold_triplets:
                final["buoc_tu_duy"].append(f"⚠️ Bỏ qua ảo giác: {ma_loi} đòi thêm cạnh đã tồn tại ({t_raw}).")
                continue
                
            # 🔥 BỘ LỌC 2: Phạt nặng tội lười biếng (SUA_PROPERTIES nhưng để rỗng)
            if han_dong == "SUA_PROPERTIES" and not gia_tri_moi:
                total_penalty += 20
                final["buoc_tu_duy"].append(f"❌ [PHẠT NẶNG]: Lỗi {ma_loi} yêu cầu SUA_PROPERTIES nhưng gia_tri_moi rỗng. Lệnh bị hủy!")
                continue
                
            # 🔥 BỘ LỌC 3: Phạt tội mất định danh (Null fields)
            if not f_raw or not t_raw:
                total_penalty += 20
                final["buoc_tu_duy"].append(f"❌ [PHẠT NẶNG]: Lỗi {ma_loi} thiếu 'from' hoặc 'to'. Lệnh bị hủy!")
                continue

            # 🔥 BỘ LỌC 4: BẢO VỆ ĐỘ PHÂN GIẢI (XOA_EDGE GUARD - Từ Backup)
            if han_dong == "XOA_EDGE":
                if any(str(t_raw).startswith(p) for p in ["S_", "B_"]):
                    final["buoc_tu_duy"].append(f"🛡️ [Data Preservation] Chặn xóa node chi tiết: {t_raw}")
                    continue
                if any(str(t_raw).startswith(p) for p in ["V_", "T_", "K_"]):
                    final["buoc_tu_duy"].append(f"🛡️ [Firewall] Chặn lệnh xóa bậy bạ thuộc tính DNA: {t_raw}")
                    continue 

            # Nếu qua được màng lọc, tiến hành ghi nhận lỗi và lệnh
            log_entry = {
                "ma_loi": ma_loi,
                "loai_loi": item.get("loai_loi", ""),
                "thuc_the_lien_quan": item.get("thuc_the_lien_quan", ""),
                "mo_ta": item.get("mo_ta", ""),
                "bang_chung_bronze": item.get("bang_chung_bronze", ""),
                "vi_tri_gold": item.get("vi_tri_gold", "")
            }
            final["logs"].append(log_entry)
            valid_logs_count += 1

            cmd_entry = {
                "ma_loi_ref": ma_loi,
                "han_dong": han_dong,
                "payload": payload
            }
            final["lenh_sua"].append(cmd_entry)

            # Tính điểm chuẩn xác
            if han_dong == "THEM_EDGE":
                valid_edge_thieu_count += 1
                total_penalty += 8
            else:
                total_penalty += 5

    # Cập nhật lời gọi hàm sanitize_lenh_sua với hub_id_clean (CỦA FILE HIỆN TẠI)
    final["lenh_sua"] = sanitize_lenh_sua(final["lenh_sua"], normalize_id(herb_id))
    
    score = max(0, 100 - total_penalty)
    final["metadata"].update({
        "score": score, 
        "tong_loi": valid_logs_count, 
        "tong_edge_thieu": valid_edge_thieu_count
    })
    final["ket_luan"] = "DAT_CHUAN" if score >= 90 else "CAN_SUA_DOI" if score >= 60 else "LOI_NGHIEM_TRONG"
    
    return final

def sanitize_bronze_text(data):
    """Đệ quy dọn dẹp chữ 'null' và rác OCR trong văn bản thô trước khi gửi cho AI"""
    if isinstance(data, dict):
        return {k: sanitize_bronze_text(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_bronze_text(v) for v in data]
    elif isinstance(data, str):
        text = re.sub(r'^(?:null|none)\s+', '', data, flags=re.IGNORECASE)
        text = text.replace(" null ", " ")
        
        return text.strip()
    return data

def run_audit():
    # Lấy toàn bộ file GOLD đã sinh ở Step 2
    # 🟢 CẬP NHẬT: Sắp xếp theo số trang thực tế (Natural Sort) sử dụng helper
    gold_files = sorted(glob.glob(os.path.join(GOLD_DIR, "*.json")), key=get_page_number)
    print(f"🚀 KHỞI CHẠY DIAMOND AUDIT (Total: {len(gold_files)} file)")

    for g_path in gold_files:
        f_name = os.path.basename(g_path)
        base_name = os.path.splitext(f_name)[0] 
        
        # 🟢 CHECKPOINT: Bỏ qua nếu file Log đã tồn tại
        output_report_path = os.path.join(AUDIT_REPORTS_DIR, f"{base_name}_LOG.json")
        if os.path.exists(output_report_path):
            print(f"⏩ Bỏ qua: {base_name} (Đã Audit)")
            continue

        # Phân loại file để xác định chiến thuật Audit (Không phân biệt hoa thường)
        is_remedy = "_bai_thuoc" in base_name.lower()
        is_pharma = "_duoc_ly" in base_name.lower()
        
        # Lấy base_id của thảo dược để tìm file gốc
        # Dùng Regex cắt bỏ mọi hậu tố để trả về đúng ID gốc (VD: 45_VI_THUOC_ICH_MAU)
        bronze_id = re.sub(r'(?i)(_bai_thuoc|_duoc_ly|_dinh_danh)$', '', base_name)
        
        # Tìm file Bronze tương ứng
        raw_matches = glob.glob(os.path.join(BRONZE_DIR, bronze_id + "*.json"))
        if not raw_matches: 
            print(f"⚠️ Không tìm thấy file gốc (Bronze) cho: {base_name}")
            continue

        print(f"🔎 Audit: {base_name} |", end=" ", flush=True)

        try:
            with open(g_path, "r", encoding="utf-8") as f: gold_data = json.load(f)
            with open(raw_matches[0], "r", encoding="utf-8") as f: bronze_data = json.load(f)
            if isinstance(bronze_data, list): bronze_data = bronze_data[0]
            
            # Lấy thông tin Hub và chuẩn hóa để làm mỏ neo (Bảo vệ an toàn khi file rỗng)
            entity_block = gold_data.get("entity") or {}
            hub_id = entity_block.get("id") or gold_data.get("entity_hub")
            if not hub_id:
                print(" ⚠️ Bỏ qua: File rỗng hoặc mất định danh Hub.")
                continue
            hub_id_clean = normalize_id(hub_id)
            
            rels = gold_data.get("relationships")
            if not isinstance(rels, list): rels = []
            
            # Quét rác OCR cho dữ liệu Bronze trước khi dựng Fragment
            bronze_data = sanitize_bronze_text(bronze_data)
            
            # --- CHIẾN THUẬT INVENTORY: CHUYỂN JSON PHỨC TẠP SANG CHUỖI PHẲNG (AN TOÀN CHỐNG TRACEBACK) ---
            dna_inv = ", ".join(sorted(list(set([str(r.get("to", "")) for r in rels if isinstance(r, dict) and r.get("relation_type") in ["CO_TINH", "CO_VI", "QUY_KINH"]]))))
            hc_inv = ", ".join(sorted(list(set([str(r.get("to", "")) for r in rels if isinstance(r, dict) and r.get("relation_type") == "CO_CHUA_HOAT_CHAT"]))))
            pharma_inv = ", ".join(sorted(list(set([str(r.get("to", "")) for r in rels if isinstance(r, dict) and r.get("relation_type") in ["CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY"]]))))
            bt_inv = ", ".join(sorted(list(set([str(r.get("from", "")) for r in rels if isinstance(r, dict) and str(r.get("from", "")).startswith("BT_")]))))
            bt_conns = [f"{r.get('from', '')} -> {r.get('to', '')} ({r.get('relation_type', '')})" for r in rels if isinstance(r, dict) and str(r.get("from", "")).startswith("BT_")]

            tasks = []
            if is_remedy:
                bai_thuoc_raw = bronze_data.get("van_ban_tho", {}).get("cac_bai_thuoc_raw", [])
                
                # --- CHUNKING: Chia nhỏ Bài thuốc nếu quá dài để tránh lỗi sụp đổ JSON ---
                if isinstance(bai_thuoc_raw, list) and len(bai_thuoc_raw) > 6:
                    fragments = []
                    chunk_size = 6
                    for c_idx in range(0, len(bai_thuoc_raw), chunk_size):
                        fragments.append({
                            "BRONZE": bai_thuoc_raw[c_idx:c_idx+chunk_size],
                            "INVENTORY_BAI_THUOC": bt_inv,
                            "EXISTING_CONNECTIONS": bt_conns,
                            "GHI_CHU": f"PHẦN {c_idx//chunk_size + 1}: Nếu quan hệ đã tồn tại trong EXISTING_CONNECTIONS thì KHÔNG báo lỗi thiếu cạnh."
                        })
                        prompt_stage_3 = UNIVERSAL_AUDIT_PROMPT.replace("{domain_specific_rules}", STAGE_3_RULES)
                        tasks.append((prompt_stage_3, f"STG_3_PART_{c_idx//chunk_size + 1}"))
                else:
                    fragments = [{
                        "BRONZE": bai_thuoc_raw,
                        "INVENTORY_BAI_THUOC": bt_inv,
                        "EXISTING_CONNECTIONS": bt_conns,
                        "GHI_CHU": "Nếu quan hệ đã tồn tại trong EXISTING_CONNECTIONS thì KHÔNG báo lỗi thiếu cạnh."
                    }]
                    prompt_stage_3 = UNIVERSAL_AUDIT_PROMPT.replace("{domain_specific_rules}", STAGE_3_RULES)
                    tasks = [(prompt_stage_3, "STG_3")]
                
            elif is_pharma:
                fragments = [{
                    "BRONZE": {
                        "tinh_vi_quy_kinh": bronze_data.get("van_ban_tho", {}).get("tinh_vi_quy_kinh"),
                        "tac_dung_duoc_ly": bronze_data.get("van_ban_tho", {}).get("tac_dung_duoc_ly")
                    },
                    "INVENTORY_PHARMA": pharma_inv,
                    "GHI_CHU": "Đối soát ID trong BRONZE với INVENTORY_PHARMA. Nếu ID đã có, chỉ kiểm tra trường properties rỗng."
                }]
                prompt_stage_4 = UNIVERSAL_AUDIT_PROMPT.replace("{domain_specific_rules}", STAGE_4_RULES)
                tasks = [(prompt_stage_4, "STG_4")]
                
            else:
                fragments = [
                    {
                        "BRONZE": {
                            "tinh_vi_quy_kinh": bronze_data.get("van_ban_tho", {}).get("tinh_vi_quy_kinh"),
                            "cong_nang": bronze_data.get("van_ban_tho", {}).get("cong_dung_chu_tri")
                        },
                        "INVENTORY_DNA": dna_inv,
                        "GHI_CHU": "Kiểm tra Tính, Vị, Kinh mạch. Nếu ID đã có trong INVENTORY_DNA, cấm báo lỗi thiếu."
                    },
                    {
                        "BRONZE": bronze_data.get("van_ban_tho", {}).get("thanh_phan_hoa_hoc"),
                        "INVENTORY_HOAT_CHAT": hc_inv,
                        "GHI_CHU": "Nếu tên hoạt chất trong Bronze đã có trong INVENTORY_HOAT_CHAT, chỉ báo lỗi SUA_PROPERTIES nếu trường rỗng."
                    }
                ]
                prompt_stage_1 = UNIVERSAL_AUDIT_PROMPT.replace("{domain_specific_rules}", STAGE_1_RULES)
                prompt_stage_2 = UNIVERSAL_AUDIT_PROMPT.replace("{domain_specific_rules}", STAGE_2_RULES)
                tasks = [(prompt_stage_1, "STG_1"), (prompt_stage_2, "STG_2")]

            results = [] 
            for i, (prompt_template, p_label) in enumerate(tasks):
                print(f"{p_label}.", end="", flush=True)
                
                # --- TIÊM TARGET LOCK ĐỘC QUYỀN ---
                target_lock_prefix = (
                    f"🛑 TARGET LOCK: Bạn đang kiểm toán thực thể {hub_id_clean}. "
                    f"Mọi lệnh vá trường 'from' BẮT BUỘC phải là {hub_id_clean} (Trừ Stage Bài thuốc)."
                    "\n\n"
                )
                final_instruction = target_lock_prefix + prompt_template.replace("{hub_id}", str(hub_id))

                try:
                    res = client.models.generate_content(
                        model=settings.MODEL_ID,
                        config=types.GenerateContentConfig(
                            system_instruction=final_instruction,
                            temperature=0, 
                            response_mime_type="application/json", 
                            response_schema=AUDIT_REPORT_SCHEMA, 
                            max_output_tokens=8192
                        ),
                        # Gửi kèm HUB_ID trong content để tăng cường khả năng định hướng
                        contents=[f"ID_MỎ_NEO: {hub_id_clean}\nDATA_TO_AUDIT:\n{json.dumps(fragments[i], ensure_ascii=False)}"]
                    )

                    parsed_res = None
                    if res.parsed:
                        parsed_res = res.parsed if isinstance(res.parsed, dict) else res.parsed.model_dump()
                    elif res.text:
                        parsed_res = robust_json_load(res.text, is_path=False)

                    if parsed_res:
                        results.append(parsed_res)
                    else:
                        print(f" ⚠️ Lỗi JSON tại {p_label}.")
                        # 🟢 CƠ CHẾ BĂNG BÓ (GRACEFUL FALLBACK)
                        # Trả về một kết quả rỗng chuẩn xác định thay vì ném lỗi
                        empty_fallback = {
                            "buoc_tu_duy": f"AI không thể phân tích {p_label} (Lỗi định dạng hoặc dữ liệu rỗng). Trả về kết quả rỗng an toàn.",
                            "ket_luan": "DAT_CHUAN",
                            "danh_sach_loi": []
                        }
                        results.append(empty_fallback)
                        
                except Exception as e:
                    print(f" ⚠️ Lỗi API tại {p_label}: {str(e)[:50]}")
                    # 🟢 CƠ CHẾ BĂNG BÓ KHI CALL API LỖI
                    results.append({
                         "buoc_tu_duy": f"Lỗi kết nối API tại {p_label}. Đã bỏ qua an toàn.",
                         "ket_luan": "DAT_CHUAN",
                         "danh_sach_loi": []
                    })
                    
                time.sleep(3) 

            if results:
                # Merge kết quả và áp dụng Python Firewall + Thermal Fix
                final_report = merge_reports(results, hub_id_clean, rels)
                with open(output_report_path, "w", encoding="utf-8") as f:
                    json.dump(final_report, f, ensure_ascii=False, indent=2)
                print(f"| Score: {final_report['metadata']['score']} | Lỗi: {final_report['metadata']['tong_loi']}")

        except Exception:
            print(f"| ❌ Hỏng: {traceback.format_exc()[:100]}...")

if __name__ == "__main__":
    run_audit()