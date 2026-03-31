import os
import json
import time
import re
import fitz  # PyMuPDF
import traceback

# --- THƯ VIỆN GOOGLE ---
from google import genai
from google.cloud import documentai_v1 as documentai
from google.genai import types

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import remove_accents

# ================= CONFIGURATION =================
# Tự động lấy đường dẫn file bảo mật từ cấu hình tập trung
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us" 
PROCESSOR_ID = "7417bb613c92f748"

PDF_FILE = "databaseraw/Những cây thuốc và vị thuốc Việt Nam.pdf"
OUTPUT_DIR = "data/datalakev2_Step1"
TOC_FILE = "data/toc_part_II.json"
PAGE_OFFSET = 15 

MODEL_ID = "gemini-2.0-flash"
CHECKPOINT_FILE = "config/checkpoint.json"
DEBUG_IMG_DIR = "logs/debug_images"

# Thêm vào đầu file hoặc trong hàm __init__
BOOK_CODE = "CT_VT_VN"  # Viết tắt của "Những cây thuốc và vị thuốc Việt Nam"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DEBUG_IMG_DIR, exist_ok=True)

# ================= 2. ĐỊNH NGHĨA PROMPT (ĐÃ TÍCH HỢP NGUYÊN BẢN) =================

PROMPT_BASE = """BẠN LÀ CHUYÊN GIA DỮ LIỆU ĐÔNG Y ĐẦU NGÀNH.
NHIỆM VỤ: Trích xuất và cấu trúc hóa toàn bộ thông tin từ sách "Những cây thuốc và vị thuốc Việt Nam" (Đỗ Tất Lợi) thành file JSON. ĐỂ PHỤC VỤ CHO VIỆC XÂY DỰNG KNOWLEDGE GRAPH DIAMOND LAYER.

LUẬT BẤT DI BẤT DỊCH (DIAMOND RULES):
1. VÉT CẠN 100%: Tuyệt đối không được bỏ sót bất kỳ dòng văn bản nào. Cấm tóm tắt, cấm rút gọn. Bê nguyên văn (verbatim) vào các trường tương ứng.
2. TÁCH THỰC THỂ THEO MỤC LỤC: Một trang có thể có nhiều cây thuốc. Bắt buộc tách thành các Object riêng biệt dựa theo danh sách ID và tên cung cấp trong CHỈ DẪN BIÊN GIỚI.

CẤU TRÚC JSON PHẢI CÓ:
Mỗi Object thực thể (cây thuốc) bắt buộc có 2 phần: `dinh_danh` và `van_ban_tho`.

A. PHẦN ĐỊNH DANH (`dinh_danh`):
- `id`: Lấy chính xác ID được cung cấp.
- `ten_chinh`: Tên Tiếng Việt viết hoa (Ví dụ: "NGẢI CỨU").
- `phan_nhom`: Lấy chính xác Nhóm y văn được cung cấp (Ví dụ: "CÁC VỊ THUỐC CẦM MÁU").
- `nguon_trang`: TRƯỜNG NÀY HỆ THỐNG SẼ TỰ GHI ĐÈ, BẠN CỨ ĐỂ TRỐNG [].

B. PHẦN VĂN BẢN THÔ (`van_ban_tho`):
Phân loại toàn bộ đoạn text đọc được vào các trường sau (Chép nguyên văn, không thêm bớt chữ):
- `ten_khoa_hoc_va_ho`: Tên khoa học (tiếng Latinh) và Họ thực vật. Nếu có tên gọi khác (tên địa phương), gộp chung vào đây.
- `mo_ta_hinh_thai`: Đoạn văn miêu tả đặc điểm thân, lá, hoa, quả, rễ của cây.
- `phan_bo_thu_hai_che_bien`: Mọc ở đâu, trồng thế nào, thu hoạch mùa nào, cách phơi sấy, bào chế ra sao.
- `thanh_phan_hoa_hoc`: Các chất hóa học có trong cây. Bê nguyên con số %.
- `tac_dung_duoc_ly`: Tác dụng thử nghiệm trên động vật, ống nghiệm (Tây y).
- `tinh_vi_quy_kinh`: Tính hàn/nhiệt, vị chua/cay/ngọt, vào kinh nào (Đông y).
- `chu_y_kieng_ky`: Các lưu ý người dùng không được dùng.
- `lieu_dung_chung`: Câu văn miêu tả công dụng chung và liều lượng dùng mỗi ngày (Ví dụ: "Ngày dùng 10-20g dưới dạng thuốc sắc").

C. PHẦN BÀI THUỐC (`cac_bai_thuoc_raw`):
- ĐÂY LÀ MẢNG (ARRAY) CHỨA CÁC STRING.
- Mỗi bài thuốc (thường bắt đầu bằng gạch đầu dòng, dấu cộng, hoặc tên bệnh) là 1 phần tử String.
- LUẬT THẺ NGUỒN DIAMOND: Bắt buộc gắn chuỗi "| [Nguồn]: {DIAMOND_SOURCE_ID}" vào cuối mỗi bài thuốc.
Ví dụ: "Chữa đau bụng kinh: Ngải cứu 10g, Ích mẫu 10g sắc uống. | [Nguồn]: {DIAMOND_SOURCE_ID}"
"""

PROMPT_PAGE = """Đây là văn bản được trích xuất (OCR) từ trang {PG} của cuốn sách.
Hãy đọc kỹ và phân loại vào các trường JSON chuẩn xác.

NHẮC NHỞ QUAN TRỌNG VỀ VĂN BẢN TRÀN TRANG:
Rất có thể phần đầu của trang {PG} này đang nói dở nội dung của cây thuốc ở trang trước ('{LAST_ANCHOR}').
Bắt buộc phải nhận diện đoạn văn bản mồ côi này và gán nó cho ID của '{LAST_ANCHOR}'. Đừng gắn nhầm vào cây mới!
"""

# ================= 3. ĐỊNH NGHĨA SCHEMA (GIÚP AI TRẢ VỀ JSON CHUẨN) =================
BRONZE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["dinh_danh", "van_ban_tho"],
    properties={
        "dinh_danh": types.Schema(
            type=types.Type.OBJECT,
            required=["id", "ten_chinh"],
            properties={
                "id": types.Schema(type=types.Type.STRING),
                "ten_chinh": types.Schema(type=types.Type.STRING),
                "phan_nhom": types.Schema(type=types.Type.STRING),
                "nguon_trang": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))
            }
        ),
        "van_ban_tho": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ten_khoa_hoc_va_ho": types.Schema(type=types.Type.STRING),
                "mo_ta_hinh_thai": types.Schema(type=types.Type.STRING),
                "phan_bo_thu_hai_che_bien": types.Schema(type=types.Type.STRING),
                "thanh_phan_hoa_hoc": types.Schema(type=types.Type.STRING,nullable=True),
                "tac_dung_duoc_ly": types.Schema(type=types.Type.STRING,nullable=True),
                "tinh_vi_quy_kinh": types.Schema(type=types.Type.STRING,nullable=True),
                "chu_y_kieng_ky": types.Schema(type=types.Type.STRING,nullable=True),
                "lieu_dung_chung": types.Schema(type=types.Type.STRING,nullable=True),
                "cac_bai_thuoc_raw": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))
            }
        )
    }
)

# Đây chính là biến mà Code đang báo thiếu
BRONZE_ARRAY_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=BRONZE_SCHEMA
)

class YHCTPipelineV2:
    def __init__(self):
        self.llm = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        self.docai = documentai.DocumentProcessorServiceClient()
        self.processor = self.docai.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
        
        if not os.path.exists(PDF_FILE):    
            raise FileNotFoundError(f"Không tìm thấy file PDF: {PDF_FILE}")
        self.pdf = fitz.open(PDF_FILE)

        # Sử dụng biến PROMPT trực tiếp thay vì load từ file
        self.prompt_base = PROMPT_BASE
        self.prompt_page = PROMPT_PAGE
        self.toc_map = self._build_toc_map()

        self.last_page = -1
        self.last_group = "Chưa xác định"
        self.last_anchor = None
        self.last_anchor_name = "Chưa Có" # Lưu tên tiếng Việt để AI đối chiếu
        self._load_checkpoint()

        # --- HẰNG SỐ NHẬN DIỆN HEADER (MẮT THẦN REGEX) ---
        self.VN_UPPER = "A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
        self.ignore_plant_keywords = [
            "CÁC CÂY THUỐC", "VỊ THUỐC", "CHỮA BỆNH", "PHẦN", "MỤC LỤC",
            "THÀNH PHẦN", "HÓA HỌC", "CÔNG DỤNG", "LIỀU DÙNG", "MÔ TẢ", 
            "BỘ PHẬN", "PHÂN BỐ", "THU HÁI", "BÀO CHẾ", "CHÚ THÍCH", "HÌNH", "ẢNH"
        ]

    def _build_toc_map(self):
        """Xây dựng bản đồ mục lục từ danh sách phẳng (Flat List)"""
        if not os.path.exists(TOC_FILE): 
            print(f"⚠️ Không tìm thấy file TOC tại: {TOC_FILE}")
            return {}
            
        toc_map = {}
        try:
            with open(TOC_FILE, encoding="utf-8") as f:
                data = json.load(f)
            
            # Vì data là một LIST, chúng ta duyệt trực tiếp qua từng phần tử
            for item in data:
                # Lấy số trang PDF
                pg = item.get("trang_pdf")
                if pg:
                    # Nếu trang này chưa có trong map, tạo một list rỗng (để chứa nhiều cây trên 1 trang)
                    pg_int = int(pg)
                    if pg_int not in toc_map:
                        toc_map[pg_int] = []
                    
                    # Thêm thông tin cây vào trang tương ứng
                    toc_map[pg_int].append({
                        "id": self.normalize_name(item.get("ten_thuc_the")),
                        "ten_chinh": item.get("ten_thuc_the"),
                        "phan_nhom": item.get("nhom", "Chưa xác định")
                    })
            
            print(f"✅ Đã nạp thành công {len(data)} thực thể từ Mục lục.")
        except Exception as e:
            print(f"❌ Lỗi khi nạp file TOC: {e}")
            
        return toc_map

    def _add_to_map(self, toc_map, item, group_name):
        pg = item.get("trang_pdf") or (int(item.get("trang_sach", 0)) + PAGE_OFFSET)
        if pg:
            toc_map[int(pg)] = {
                "id": self.normalize_name(item.get("ten_cay")),
                "ten_chinh": item.get("ten_cay"),
                "phan_nhom": group_name
            }

    def normalize_name(self, s):
        if not s: return "UNKNOWN"
        
        # 1. Loại bỏ tiền tố không cần thiết
        s = re.sub(r"^(Cây|Vị thuốc|Thuốc)\s+", "", s, flags=re.IGNORECASE)
        
        # 2. Bỏ dấu tiếng Việt (Dùng hàm dùng chung từ utils.helpers)
        s = remove_accents(s)
        
        # 3. Làm sạch ký tự đặc biệt và đưa về dạng ID viết hoa
        clean_name = re.sub(r"[^\w\s]", "", s).upper().strip().replace(" ", "_")
        
        # 4. CHỐT CHẶN CƯỠNG CHẾ: Sửa lỗi OCR mất chữ Đ đầu dòng (UONG_QUY -> DUONG_QUY)
        # Đây là kỹ thuật sửa lỗi vật lý cho trường hợp Drop Cap của Đương quy
        if clean_name == "UONG_QUY":
            clean_name = "DUONG_QUY"
        elif clean_name == "O_QUY": # Phòng trường hợp OCR mất cả 'U'
            clean_name = "DUONG_QUY"
            
        return f"VI_THUOC_{clean_name}"

    def _load_checkpoint(self):
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                    s = json.load(f)
                    self.last_page = s.get("last_page", -1)
                    self.last_group = s.get("last_group", "Chưa xác định")
                    self.last_anchor = s.get("last_anchor", "START")
                    self.last_anchor_name = s.get("last_anchor_name", "KHỞI ĐẦU")
            except: pass

    def _save_checkpoint(self, pg):
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_page": pg, 
                "last_group": self.last_group, 
                "last_anchor": self.last_anchor,
                "last_anchor_name": self.last_anchor_name
            }, f, ensure_ascii=False, indent=2)

    def _clean_json_response(self, text):
        clean = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)
        clean = re.sub(r'\\(?!["\\\/bfnrtu])', r'\\\\', clean)
        return clean

    def is_valid_plant_header(self, text):
        """Kiểm tra xem một chuỗi in hoa có phải là tên cây hợp lệ không"""
        if len(text.split()) <= 1: return False
        if re.fullmatch(r"[A-Z0-9\s]+", text) and len(text) <= 6: return False
        chem_tokens = ["OH", "CO", "CH3", "OCH3"]
        for token in chem_tokens:
            if token in text: return False
        return True

    def detect_headers(self, text):
        """MẮT THẦN REGEX: Quét vật lý văn bản OCR để tìm Phân nhóm và Tên cây in hoa"""
        results = {"GROUP": None, "PLANT": None, "PLANT_NAME": None}
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        for i in range(min(20, len(lines))):
            line = lines[i]
            if any(w in line.upper() for w in ["HÌNH", "ẢNH", "SƠ ĐỒ", "BẢNG"]): continue 
                
            # 1. NHẬN DIỆN NHÓM LỚN (Roman Numerals)
            g_match = re.match(rf'^([IVXLC]+[\.\s]+[{self.VN_UPPER}\s]{{5,}})', line)
            if g_match and not results["GROUP"]:
                group_text = g_match.group(1).strip()
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if next_line.isupper() and not any(k in next_line for k in ["1.", "A.", "B.", "HÌNH"]):
                        group_text += " " + next_line
                results["GROUP"] = group_text
                continue 

            # 2. NHẬN DIỆN TÊN CÂY (In hoa đứng 1 mình)
            p_match = re.match(rf'^\s*([{self.VN_UPPER}\s]{{2,}})\s*$', line)
            if p_match and not results["PLANT"]:
                cand = p_match.group(1).strip()
                vowels = 'aeiouyàáạảãâèéẹẻẽêìíịỉĩòóọỏõôùúụủũưỳýỵỷỹđ'
                if not any(v in cand.lower() for v in vowels): continue
                if any(k in cand.upper() for k in self.ignore_plant_keywords): continue
                
                if self.is_valid_plant_header(cand):
                    results["PLANT"] = self.normalize_name(cand)
                    results["PLANT_NAME"] = cand
                    print(f"🎯 [Mắt Thần Regex] Phát hiện tiêu đề vật lý: {cand}")

        return results

    def merge_logic(self, old, new, pg):
        """Gộp văn bản CỘNG DỒN chuẩn Diamond Layer"""
        if old["dinh_danh"]["id"] != new["dinh_danh"]["id"]:
            return old 

        BOOK_CODE = "CT_VT_VN" # Đảm bảo biến này có trong scope
        diamond_source_id = f"{BOOK_CODE}_T{pg}"
        
        if "van_ban_tho" not in old: old["van_ban_tho"] = {}
        new_vbt = new.get("van_ban_tho", {})
        
        fields = [
            "ten_khoa_hoc_va_ho", "mo_ta_hinh_thai", 
            "phan_bo_thu_hai_che_bien", "thanh_phan_hoa_hoc", 
            "tac_dung_duoc_ly", "tinh_vi_quy_kinh", "lieu_dung_chung"
        ]
        
        for f in fields:
            v_new = str(new_vbt.get(f, "") or "").strip()
            if not v_new or v_new.lower() in ["none", "null", "không có"]: continue
            
            # 1. Tránh gắn tag lặp lại
            if not v_new.startswith("["):
                tagged_new = f"[{diamond_source_id}]: {v_new}"
            else:
                tagged_new = v_new
            
            v_old = str(old["van_ban_tho"].get(f, "") or "").strip()
            if v_old and v_old.lower() not in ["none", "null"]:
                # 2. Xử lý nối câu mồ côi (Nối văn bản liền mạch thay vì xuống dòng nếu chưa hết câu)
                if v_old.endswith(('.', ':', '!', '?')):
                    old["van_ban_tho"][f] = f"{v_old}\n{tagged_new}"
                else:
                    # Nếu câu trước chưa kết thúc, nối trực tiếp nội dung mới (bỏ tag nguồn ở giữa câu)
                    clean_v_new = v_new if not v_new.startswith("[") else v_new.split("]: ", 1)[-1]
                    old["van_ban_tho"][f] = f"{v_old} {clean_v_new}"
            else:
                old["van_ban_tho"][f] = tagged_new

        # 3. Xử lý Bài thuốc Raw (Logic nối bài thuốc bị cụt)
        old_raw = old["van_ban_tho"].get("cac_bai_thuoc_raw", [])
        new_raw = new_vbt.get("cac_bai_thuoc_raw", [])
        
        for br in new_raw:
            if not br or br.lower() in ["none", "null"]: continue
            
            # Gắn tag nguồn nếu AI quên
            if "| [Nguồn]:" not in br:
                br = f"{br} | [Nguồn]: {diamond_source_id}"
            
            # Logic nối bài thuốc bị cụt: Nếu bài thuốc cuối của trang trước chưa có tag nguồn hoàn chỉnh
            if old_raw and "| [Nguồn]:" not in old_raw[-1]:
                # Giả định bài thuốc cuối bị cụt, gộp bài thuốc đầu trang mới vào bài thuốc cuối trang cũ
                old_raw[-1] = f"{old_raw[-1]} {br}"
            elif br not in old_raw:
                old_raw.append(br)
        
        old["van_ban_tho"]["cac_bai_thuoc_raw"] = old_raw

        # Cập nhật nguồn trang
        pages = set(old["dinh_danh"].get("nguon_trang", []))
        pages.add(str(pg))
        old["dinh_danh"]["nguon_trang"] = sorted(list(pages), key=int)
        
        return old
    
    def call_llm(self, raw_text, pg, page_candidates):
        """
        Hàm điều hướng AI phân tách thực thể dựa trên Mục lục (TOC) 
        và cưỡng chế mã nguồn chuẩn Diamond.
        """
        # 1. THIẾT LẬP BIẾN HỆ THỐNG (DIAMOND LAYER)
        BOOK_CODE = "CT_VT_VN"  # Mã sách cố định
        diamond_id = f"{BOOK_CODE}_T{pg}" # Ví dụ: CT_VT_VN_T47
        
        current_group = self.last_group
        current_anchor_id = self.last_anchor
        current_anchor_name = self.last_anchor_name
        
        # 2. XÂY DỰNG CHỈ DẪN BIÊN GIỚI (BOUNDARY STRATEGY)
        if page_candidates:
            names = ", ".join([c['ten_chinh'] for c in page_candidates])
            ids = ", ".join([c['id'] for c in page_candidates])
            
            if not current_anchor_id or current_anchor_id == "START":
                # Trường hợp trang đầu tiên của một chương/nhóm
                boundary_instr = (
                    f"!!! LỆNH HỆ THỐNG: Trang {pg} bắt đầu các thực thể mới: {names}.\n"
                    f"- ID BẮT BUỘC: [{ids}].\n"
                    f"- YÊU CẦU: Trả về mảng JSON gồm {len(page_candidates)} object."
                )
            else:
                # Trường hợp trang ranh giới: có phần cuối cây cũ và phần đầu cây mới
                boundary_instr = (
                    f"!!! LỆNH HỆ THỐNG: Trang {pg} là ranh giới thực thể.\n"
                    f"- ĐẦU TRANG: Là nội dung tiếp nối của vị thuốc: '{current_anchor_name}' (ID: {current_anchor_id}).\n"
                    f"- GIỮA/CUỐI TRANG: Bắt đầu các vị thuốc mới: {names} (ID: {ids}).\n"
                    f"- QUY TẮC: Phải vét sạch văn bản mồ côi ở đầu trang gộp vào cây cũ trước khi sang cây mới.\n"
                    f"- YÊU CẦU: Trả về mảng JSON gồm {len(page_candidates) + 1} object."
                )
        else:
            # Trang nối tiếp hoàn toàn (không có tiêu đề mới)
            boundary_instr = (
                f"TIẾP NỐI NGỮ CẢNH: Trang {pg} hoàn toàn là phần mô tả tiếp theo của '{current_anchor_name}'.\n"
                f"- YÊU CẦU: Trả về mảng JSON 1 object duy nhất với ID: {current_anchor_id}."
            )

        # 3. LÀM SẠCH VÀ THAY THẾ BIẾN TRONG PROMPT (TEMPLATE ENGINE)
        # Thay thế các placeholder bằng giá trị thực tế của trang hiện tại
        page_prompt = self.prompt_page.replace('{PG}', str(pg))
        page_prompt = page_prompt.replace('{LAST_ANCHOR}', current_anchor_name)
        
        # Ép biến mã nguồn Diamond vào các vị trí trong Prompt
        page_prompt = page_prompt.replace('{DIAMOND_SOURCE_ID}', diamond_id)

        # 4. TỔNG HỢP PROMPT TỐI CAO (SYSTEM INSTRUCTION)
        full_prompt = (
            f"{self.prompt_base}\n\n"
            f"=== LỆNH CƯỠNG CHẾ ĐỊNH DANH (DIAMOND RULE) ===\n"
            f"1. MÃ NGUỒN DUY NHẤT: Mọi trường 'nguon_trang' PHẢI điền là: ['{diamond_id}'].\n"
            f"2. THẺ BÀI THUỐC: Mọi bài thuốc PHẢI kết thúc bằng: | [Nguồn]: {diamond_id}\n"
            f"3. CẤM TỰ CHẾ: Tuyệt đối không viết tắt thành CTD, CTVN hay bất kỳ ký hiệu nào khác.\n\n"
            f"CHỈ DẪN BIÊN GIỚI: {boundary_instr}\n"
            f"NHÓM Y VĂN (phan_nhom): {current_group}\n\n"
            f"{page_prompt}\n\n"
            f"=== VĂN BẢN OCR TRANG {pg} ===\n"
            f"{raw_text}"
        )

        # 5. GỌI LLM VỚI SCHEMA CỨNG (STRICK JSON)
        try:
            response = self.llm.models.generate_content(
                model=MODEL_ID,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, # Giữ nhiệt độ thấp để trích xuất chính xác verbatim
                    response_mime_type="application/json",
                    response_schema=BRONZE_ARRAY_SCHEMA 
                )
            )
            # Response trả về đã là JSON chuẩn nhờ response_schema
            return json.loads(response.text)
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng LLM tại trang {pg}: {e}")
            # Log lại prompt để debug nếu cần
            with open(f"logs/failed_prompt_p{pg}.txt", "w", encoding="utf-8") as f:
                f.write(full_prompt)
            return []

    def run(self, start, end):
        for pg in range(start, end + 1):
            if pg <= self.last_page: continue
            print(f"🚀 Xử lý trang: {pg} | Nhóm hiện tại: {self.last_group}")

            # --- BƯỚC 1: ĐIỀU PHỐI MỎ NEO TỪ TOC (DẪN ĐƯỜNG TRƯỚC) ---
            # Lấy danh sách các cây thuốc bắt đầu tại trang này (Hỗ trợ 1 trang nhiều cây)
            page_candidates = self.toc_map.get(pg, [])
            if not isinstance(page_candidates, list): # Phòng hờ nếu toc_map cũ là object
                page_candidates = [page_candidates] if page_candidates else []

            if page_candidates:
                # ÉP CHẾT nhãn nhóm từ thực thể đầu tiên của trang vào hệ thống
                self.last_group = page_candidates[0]["phan_nhom"]
                print(f"📁 TOC Master: Đã xác định nhóm '{self.last_group}' cho trang {pg}")

            try:
                # --- BƯỚC 2: OCR ---
                temp_doc = fitz.open()
                temp_doc.insert_pdf(self.pdf, from_page=pg-1, to_page=pg-1)
                raw_ocr = self.docai.process_document(
                    request={"name": self.processor, "raw_document": {"content": temp_doc.write(), "mime_type": "application/pdf"}}
                ).document.text
                temp_doc.close()

                # --- BƯỚC 3: KIỂM TRA VẬT LÝ (MẮT THẦN REGEX) ---
                # Vẫn giữ Regex để bắt các tiêu đề nhóm lớn (Số La Mã) bị thiếu trong TOC
                headers_found = self.detect_headers(raw_ocr)

                # CHỈ cập nhật từ Regex nếu TOC không cung cấp thông tin nhóm ở trang này
                if headers_found.get("GROUP"):
                    regex_group = headers_found["GROUP"]
                    
                    # Nếu trang này không có trong TOC, hoặc tên nhóm từ Regex khác hoàn toàn nhóm hiện tại
                    # thì mới cập nhật last_group. 
                    # Nhưng để đồng bộ, ta nên chuẩn hóa nó về dạng Title Case hoặc giữ nguyên theo TOC.
                    if not page_candidates:
                        self.last_group = regex_group 
                        print(f"📡 Regex detected new group: {self.last_group}")
                    else:
                        # Nếu TOC đã có nhóm, ta ƯU TIÊN nhóm của TOC để đảm bảo đồng bộ định dạng
                        self.last_group = page_candidates[0]["phan_nhom"]

                # --- BƯỚC 4: GỌI AI VỚI NGỮ CẢNH CỦA TRANG ---
                # Bạn nên truyền page_candidates vào call_llm để AI biết phải tách bao nhiêu Object
                items = self.call_llm(raw_ocr, pg, page_candidates)
                
                for it in items:
                    # 4.1. CƯỠNG CHẾ NHÃN NHÓM (Triệt tiêu lỗi 'Chưa xác định')
                    it["dinh_danh"]["phan_nhom"] = self.last_group
                    
                    # 4.2. XÁC THỰC VÀ NẮN ID THEO TOC
                    m_id = it.get("dinh_danh", {}).get("id")
                    if not m_id: continue

                    # So sánh ID mềm (Soft-match)
                    clean_m_id = m_id.replace("_", "").upper()
                    matched_cand = None
                    
                    # Tìm xem ID AI trả về có nằm trong danh sách dự kiến của TOC trang này không
                    for cand in page_candidates:
                        if clean_m_id == cand["id"].replace("_", "").upper():
                            matched_cand = cand
                            break
                    
                    if matched_cand:
                        # Nếu khớp cây mới trong TOC: Ép ID chuẩn
                        it["dinh_danh"]["id"] = matched_cand["id"]
                        it["dinh_danh"]["ten_chinh"] = matched_cand["ten_chinh"]
                    elif not page_candidates:
                        # Nếu là trang NỐI TIẾP (không có cây mới trong TOC): Ép dùng ID của cây đang xử lý dở
                        it["dinh_danh"]["id"] = self.last_anchor
                        it["dinh_danh"]["ten_chinh"] = self.last_anchor_name
                    
                    # 4.3. LƯU HOẶC GỘP FILE
                    actual_id = it["dinh_danh"]["id"]
                    target_file = next((f for f in os.listdir(OUTPUT_DIR) if f.endswith(f"_{actual_id}.json")), None)
                    path = os.path.join(OUTPUT_DIR, target_file if target_file else f"{pg}_{actual_id}.json")
                    
                    if target_file:
                        with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                        data[0] = self.merge_logic(data[0], it, pg)
                    else:
                        it["dinh_danh"]["nguon_trang"] = [str(pg)]
                        data = [it]

                    with open(path, "w", encoding="utf-8") as f: 
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # CẬP NHẬT MỎ NEO SAU CÙNG
                    self.last_anchor = actual_id
                    self.last_anchor_name = it["dinh_danh"]["ten_chinh"]

                self._save_checkpoint(pg)
                time.sleep(0.5) # Flash API khá nhanh, 0.5s là đủ

            except Exception as e:
                print(f"❌ Lỗi nghiêm trọng trang {pg}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    pipeline = YHCTPipelineV2()
    pipeline.run(45, 504)
    os.system("shutdown -s -t 60") # Tự động tắt máy sau 1 phút khi hoàn thành (Windows)