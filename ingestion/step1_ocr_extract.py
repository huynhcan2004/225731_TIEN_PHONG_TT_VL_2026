import os
import json
import time
import re
try:
    import fitz # PyMuPDF
except ImportError:
    print("Lỗi: Thư viện 'fitz' (PyMuPDF) không được tìm thấy. Vui lòng cài đặt bằng cách chạy: pip install PyMuPDF")
    exit(1)
import traceback
import sys

# --- FIX LỖI IMPORT THƯ MỤC CHA ---
# Đảm bảo Python nhận diện được thư mục gốc của dự án
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- THƯ VIỆN GOOGLE ---
from google import genai
from google.cloud import documentai_v1 as documentai
from google.genai import types

# --- IMPORT TỪ HỆ THỐNG MỚI (TẬP TRUNG HÓA CẤU HÌNH) ---
from app.config import settings
from utils.helpers import remove_accents

# =====================================================================
# 1. ĐỒNG BỘ CẤU HÌNH HỆ THỐNG (SYNC WITH SETTINGS)
# =====================================================================
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

# Tham số Document AI (Cố định theo dự án GCP của huynh)
PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us" 
PROCESSOR_ID = "7417bb613c92f748"

# Lấy đường dẫn từ kiến trúc Medallion trong Settings
PDF_FILE = settings.PDF_INPUT_PATH
TOC_FILE = settings.TOC_JSON_PATH
OUTPUT_DIR = settings.DIR_BRONZE_RAW
CHECKPOINT_FILE = settings.CHECKPOINT_MAIN
DEBUG_IMG_DIR = settings.DIR_LOGS_DEBUG_IMG

MODEL_ID = settings.MODEL_ID
PAGE_OFFSET = settings.PAGE_OFFSET
BOOK_CODE = "CT_VT_VN"  # Viết tắt của "Những cây thuốc và vị thuốc Việt Nam"

# Khởi tạo thư mục tự động
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DEBUG_IMG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)

# 🟢 THƯ MỤC LƯU RAW OCR THEO TRANG
RAW_OCR_DIR = os.path.join(OUTPUT_DIR, "raw_ocr")
os.makedirs(RAW_OCR_DIR, exist_ok=True)

# =====================================================================
# Hàm Cứu hộ JSON (Đã đưa ra ngoài class để gọi an toàn)
# =====================================================================
def robust_json_parse(text):
    """Cứu hộ JSON khi AI trả về markdown hoặc bị lỗi nhẹ"""
    if not text: return None
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Không thể parse JSON: {e}")
        return None

# =====================================================================
# 2. ĐỊNH NGHĨA PROMPT (DIAMOND RULES - FULL INTEGRATION)
# =====================================================================

PROMPT_BASE = """**VAI TRÒ:** Chuyên gia Trích xuất Tri thức Y dược Cổ truyền (Cấp độ Diamond).

**NHIỆM VỤ:** Chuyển đổi văn bản OCR từ trang {PG} thành JSON cấu trúc sâu. Bạn là một "Máy quét Logic" (Logical Scanner) chuyên xâu chuỗi thông tin, tuyệt đối không tóm tắt hay sáng tạo văn bản.

---

### 1. NGUYÊN TẮC "KIM CƯƠNG" (TRÍCH XUẤT NGUYÊN VĂN)

- **TUYỆT ĐỐI KHÔNG TÓM TẮT:** Giữ nguyên văn phong, độ dài và chi tiết của bản gốc. Không dùng các từ như "như trên", "tương tự". 
- **LÀM SẠCH LỖI OCR:** Nối lại các từ bị ngắt dòng (VD: "hương \n phụ" → "hương phụ"). Xóa các ký tự nhiễu không mang ý nghĩa chuyên môn.
- **XỬ LÝ DỮ LIỆU KHUYẾT:** Nếu một trường thông tin không được nhắc đến trong văn bản, đặt giá trị là `null`. Tuyệt đối không tự bịa dữ liệu để lấp đầy.

---

### 2. PHÂN LOẠI NGỮ NGHĨA (CHỐNG LỆ THUỘC TIÊU ĐỀ)

Không phụ thuộc vào các tiêu đề cứng (A, B, C...). Hãy phân loại dữ liệu dựa trên "Nội dung thực tế" của đoạn văn:

- **mo_ta_hinh_thai:** Chứa mọi mô tả về đặc điểm vật lý (thân, rễ, lá, hoa, quả) kèm các thông số kích thước nguyên văn.
- **phan_bo_thu_hai_che_bien:** Chứa thông tin về nơi mọc, mùa thu hoạch, cách trồng và mọi công đoạn bào chế (VD: Tứ chế, tẩm sao).
- **thanh_phan_hoa_hoc [LỌC SẠCH HÓA HỌC]:** CHỈ trích xuất tên gọi của các hoạt chất (Ví dụ: Alkaloid, Tannin, Saponin, Leonurin). 
    *   **Lệnh cấm:** Bỏ qua hoàn toàn các công thức phân tử hóa học (VD: C10H16O2, CH4) và các thông số kỹ thuật (độ sôi, nhiệt độ chảy) trừ khi chúng là một phần bắt buộc của tên chất. Bọc mọi tên hoạt chất trong dấu `$`.
- **tac_dung_duoc_ly:** CHỈ chứa văn bản mô tả các thí nghiệm khoa học, kháng sinh đồ, thử nghiệm trên động vật (ếch, chuột, thỏ) và lâm sàng hiện đại. Nếu đoạn văn nói "Dùng chữa bệnh X..." -> CHUYỂN ngay xuống phần Bài thuốc.
- **tinh_vi_quy_kinh:** Trích xuất nguyên văn các thuật ngữ Đông y giải thích cơ chế (VD: "Vị đắng, tính hàn, trục ứ huyết, sinh huyết mới").
- **chu_y_kieng_ky:** Trích xuất MỌI CÂU chứa từ khóa cảnh báo: "Kỵ", "Kiêng", "Cấm dùng", "Không dùng cho phụ nữ có thai", "Có độc". Tự động suy luận: Nếu dược lý ghi "Kích thích tử cung", phải tự ghi thêm cảnh báo cho thai phụ vào đây.
- **lieu_dung_chung:** Hướng dẫn liều lượng tổng quát (nếu có).

---

### 3. XÂU CHUỖI BÀI THUỐC (SEMANTIC CHAINING STRATEGY)

Mọi thông tin liên quan đến việc CHỮA BỆNH phải được "đúc" thành các chuỗi riêng biệt trong mảng `cac_bai_thuoc_raw`. Bắt buộc dùng ký tự `|` để chia thành 4 khối:

`[Tên bài thuốc (nếu có)] - [Bệnh/Chủ trị] | [Thành phần & Liều lượng] | [Cách dùng & Ghi chú lâm sàng] | [Nguồn]: {DIAMOND_SOURCE_ID}`

- **QUY TẮC ĐÚC KHỐI BẮT BUỘC:**
    1. **Khối 1 (Định danh):** CHỈ chứa [Tên bài thuốc] (nếu có) và [Tên bệnh/Triệu chứng]. (Ví dụ: "Cao Ích Mẫu - Rong huyết, kinh nguyệt không đều"). Nếu đoạn văn chỉ ghi đơn thuốc mà không ghi bệnh, PHẢI nhìn ngược lên các đoạn trước để lấy tên bệnh điền vào (Thừa kế ngữ cảnh).
    2. **Khối 2 (Thành phần):** CHỈ chứa danh sách vị thuốc và khối lượng. Phải luôn ghi kèm tên cây chính (VD: "Lá rau ngót 40g", không ghi "Lá 40g").
    3. **Khối 3 (Cách dùng):** Mọi hành động (sắc uống, đắp ngoài) và ghi chú (kinh nghiệm dân gian).
        *   **Luật bù lấp:** Nếu bài thuốc/triệu chứng không có liều lượng riêng, BẮT BUỘC lấy thông tin từ "Liều dùng chung" điền vào đây.
        *   **Luật văn xuôi:** Nếu chỉ ghi "chữa đau bụng" (không liều), ghi vào khối 3: "Chỉ định lâm sàng (không ghi rõ liều)". Tuyệt đối không để trống khối này.
    4. **Khối 4 (Nguồn):** Luôn kết thúc bằng `| [Nguồn]: {DIAMOND_SOURCE_ID}`.
- **TRÍCH XUẤT XUYÊN VĂN BẢN:** Đừng đợi đến khi có chữ "Bài thuốc" mới trích. Nếu phần "Công dụng" ghi: *"Nhân dân dùng rễ chữa sưng vú"*, BẮT BUỘC tạo một dòng: `Sưng vú | Rễ [tên cây] | Chỉ định lâm sàng theo kinh nghiệm | [Nguồn]: {DIAMOND_SOURCE_ID}`.
- **CHỐNG RÁC:** Xóa các cụm từ điều hướng gốc (VD: "Xem hình 2", "Đơn thuốc có ích mẫu:"). Không được lặp lại các nhãn tiêu đề bên trong khối.

---

### 4. ĐỒNG BỘ THỰC THỂ VÀ CHUYỂN TRANG

- **Thực thể hiện tại:** {LAST_ANCHOR} | **Nguồn:** {DIAMOND_SOURCE_ID}
- **ID CHUẨN:** Bắt buộc tuân theo định dạng `VI_THUOC_[TEN_VIET_HOA_KHONG_DAU]`.
- **CHỐNG MẤT MÁT CUỐI TRANG:** Nếu bài thuốc bị cắt đôi ở cuối trang, hãy trích xuất đến chữ cuối cùng và KHÔNG đóng đuôi `| [Nguồn]`. Đợi xử lý ở trang sau.
"""
PROMPT_PAGE = """# NHIỆM VỤ: XỬ LÝ TRANG {PG} - ĐỐI CHIẾU THỰC THỂ {LAST_ANCHOR} VÀ {EXPECTED_ANCHOR}

# 1. QUY TẮC CHIA TÁCH THỰC THỂ (MULTI-ENTITY SPLIT)
- **RANH GIỚI:** Trang {PG} có thể chứa đoạn kết của cây cũ ({LAST_ANCHOR}) và phần đầu của cây mới ({EXPECTED_ANCHOR}). Dấu hiệu là tên cây được in đậm, viết hoa to ở giữa trang.
- **VÉT CẠN ĐẦU TRANG (QUAN TRỌNG):** Tuyệt đối không được bỏ rơi văn bản mồ côi ở phần đầu trang. Phải gộp toàn bộ đoạn văn (thường là đơn thuốc, kiêng kỵ của cây cũ) vào Object JSON mang ID của {LAST_ANCHOR}.
- **ĐẦU RA BẮT BUỘC:** Nếu có sự chuyển giao thực thể, BẮT BUỘC trả về một MẢNG (Array) chứa 2 Object JSON riêng biệt. KHÔNG ĐƯỢC trộn dữ liệu bài thuốc của cây này sang cây kia. Mọi ID phải sử dụng chính xác tên từ hệ thống.

# 2. LOGIC LÀM SẠCH VÀ PHÂN LOẠI NGỮ NGHĨA
- **LỌC KIÊNG KỴ TỰ ĐỘNG:** Quét lướt toàn bộ mục "Công dụng", "Dược lý" và "Liều dùng". Nếu phát hiện bất kỳ câu nào cấm phụ nữ có thai, người hư hàn, kỵ đồng tử... -> RÚT NGAY câu đó ra khỏi đoạn văn và đưa vào trường `chu_y_kieng_ky`. Không để sót lại ở phần khác.
- **BẢO VỆ MÔ TẢ:** Tuyệt đối không để bất kỳ công thức liều lượng (như 80g, 20ml, sắc uống) nào lọt vào trường `mo_ta_hinh_thai`.
- **DỌN DẸP DỮ LIỆU OCR:** Xóa các con số đơn lẻ (số trang) nằm lơ lửng, gộp các từ bị rớt dòng (bỏ dấu gạch nối nếu có). 
- **CHỐT CHẶN HOẠT CHẤT:** Khi điền `thanh_phan_hoa_hoc`, CHỈ trích xuất tên Latin của chất (bọc `$tên_chất$`). TUYỆT ĐỐI XÓA BỎ các công thức phân tử như $C_nH_nO_n$, nhiệt độ sôi, thông số áp suất.

# 3. ÉP BUỘC ĐÚC BÀI THUỐC (STRICT REMEDY CHAINING)
- **THỪA KẾ BỆNH DANH:** Đối với các đơn thuốc chuyên biệt (như Cao Ích Mẫu Thanh Hóa, Cao HA1) nếu văn bản không nhắc lại bệnh, AI BẮT BUỘC phải "nhìn ngược lên" để sao chép danh sách bệnh từ mục Công dụng ở trên xuống và điền vào Khối 1. KHÔNG ĐƯỢC để Khối 1 chỉ chứa Tên đơn thuốc.
- **ĐIỀN ĐẦY LIỀU LƯỢNG:** Không được để trống Khối 3 (Cách dùng). Nếu văn bản thiếu liều, hãy tự động trích xuất thông tin từ "Liều dùng chung" để lấp đầy. Nếu hoàn toàn không có, ghi rõ "Chỉ định lâm sàng".
- **GẮN NGUỒN:** Trường `nguon_trang` trong Object gốc và Khối 4 của mảng Bài thuốc BẮT BUỘC phải mang giá trị {DIAMOND_SOURCE_ID}.

# 4. ĐỊNH DẠNG TRẢ VỀ
- Trả về ĐÚNG CẤU TRÚC JSON (hoặc Mảng JSON). Không in thêm lời giải thích, không xin chào, không xác nhận mệnh lệnh.
- Dữ liệu phải khớp tuyệt đối với định dạng Schema để luồng Python tự động merge.
"""

# =====================================================================
# 3. ĐỊNH NGHĨA SCHEMA (STRICK JSON ENFORCEMENT)
# =====================================================================
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
                "thanh_phan_hoa_hoc": types.Schema(type=types.Type.STRING, nullable=True),
                "tac_dung_duoc_ly": types.Schema(type=types.Type.STRING, nullable=True),
                "tinh_vi_quy_kinh": types.Schema(type=types.Type.STRING, nullable=True),
                "chu_y_kieng_ky": types.Schema(type=types.Type.STRING, nullable=True),
                "lieu_dung_chung": types.Schema(type=types.Type.STRING, nullable=True),
                "cac_bai_thuoc_raw": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))
            }
        )
    }
)

BRONZE_ARRAY_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=BRONZE_SCHEMA
)

# =====================================================================
# 4. KẾT CẤU PIPELINE (DIAMOND EXTRACTOR)
# =====================================================================
class YHCTPipelineV2:
    def __init__(self):
        # Kết nối GCP AI & Document AI
        self.llm = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        self.docai = documentai.DocumentProcessorServiceClient()
        self.processor = self.docai.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
        
        if not os.path.exists(PDF_FILE):    
            raise FileNotFoundError(f"Không tìm thấy file PDF: {PDF_FILE}")
        self.pdf = fitz.open(PDF_FILE)

        self.prompt_base = PROMPT_BASE
        self.prompt_page = PROMPT_PAGE
        self.toc_map = self._build_toc_map()

        # Biến trạng thái kiểm soát luồng
        self.last_page = -1
        self.last_group = "Chưa xác định"
        self.last_anchor = None
        self.last_anchor_name = "Chưa Có"
        self.last_anchor_page = -1 # 🟢 TRACKING TRANG BẮT ĐẦU ĐỂ TẠO ID DUY NHẤT
        self._load_checkpoint()

        # Mắt thần Regex: Nhận diện ký tự Tiếng Việt in hoa
        self.VN_UPPER = "A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
        self.ignore_plant_keywords = [
            "CÁC CÂY THUỐC", "VỊ THUỐC", "CHỮA BỆNH", "PHẦN", "MỤC LỤC",
            "THÀNH PHẦN", "HÓA HỌC", "CÔNG DỤNG", "LIỀU DÙNG", "MÔ TẢ", 
            "BỘ PHẬN", "PHÂN BỐ", "THU HÁI", "BÀO CHẾ", "CHÚ THÍCH", "HÌNH", "ẢNH"
        ]

    def _build_toc_map(self):
        """Xây dựng bản đồ mục lục từ file JSON."""
        if not os.path.exists(TOC_FILE): 
            print(f"⚠️ Không tìm thấy file TOC tại: {TOC_FILE}")
            return {}
            
        toc_map = {}
        try:
            with open(TOC_FILE, encoding="utf-8") as f:
                data = json.load(f)
            
            for item in data:
                pg = item.get("trang_pdf")
                if pg:
                    pg_int = int(pg)
                    if pg_int not in toc_map:
                        toc_map[pg_int] = []
                    
                    toc_map[pg_int].append({
                        "id": self.normalize_name(item.get("ten_thuc_the")),
                        "ten_chinh": item.get("ten_thuc_the"),
                        "phan_nhom": item.get("nhom", "Chưa xác định")
                    })
            
            print(f"✅ Đã nạp thành công {len(data)} thực thể từ Mục lục.")
        except Exception as e:
            print(f"❌ Lỗi khi nạp file TOC: {e}")
            
        return toc_map

    def normalize_name(self, s):
        """Tiền xử lý chuỗi và định danh chuẩn ID."""
        if not s: return "UNKNOWN"
        
        # 1. BẢO TOÀN VẬT LÝ: Đổi Đ thành D trước khi dùng remove_accents
        s = s.replace('Đ', 'D').replace('đ', 'd')
        
        # 2. Xóa tiền tố thừa
        s = re.sub(r"^(Cây|Vị thuốc|Thuốc)\s+", "", s, flags=re.IGNORECASE)
        
        # 3. Sử dụng hàm từ thư viện lõi
        s = remove_accents(s)
        
        # 4. Ép chuẩn ID
        clean_name = re.sub(r"[^\w\s]", "", s).upper().strip().replace(" ", "_")
        
        # 5. CHỐT CHẶN CƯỠNG CHẾ: Lỗi Drop Cap OCR
        if clean_name == "UONG_QUY" or clean_name == "O_QUY":
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
                    self.last_anchor_page = s.get("last_anchor_page", -1)
            except: pass

    def _save_checkpoint(self, pg):
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_page": pg, 
                "last_group": self.last_group, 
                "last_anchor": self.last_anchor,
                "last_anchor_name": self.last_anchor_name,
                "last_anchor_page": self.last_anchor_page
            }, f, ensure_ascii=False, indent=2)

    def is_valid_plant_header(self, text):
        if len(text.split()) <= 1: return False
        if re.fullmatch(r"[A-Z0-9\s]+", text) and len(text) <= 6: return False
        chem_tokens = ["OH", "CO", "CH3", "OCH3"]
        for token in chem_tokens:
            if token in text: return False
        return True

    def detect_headers(self, text):
        """MẮT THẦN REGEX: Cứu hộ lỗi TOC."""
        results = {"GROUP": None, "PLANT": None, "PLANT_NAME": None}
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        for i in range(min(20, len(lines))):
            line = lines[i]
            if any(w in line.upper() for w in ["HÌNH", "ẢNH", "SƠ ĐỒ", "BẢNG"]): continue 
                
            # 1. Nhóm y văn
            g_match = re.match(rf'^([IVXLC]+[\.\s]+[{self.VN_UPPER}\s]{{5,}})', line)
            if g_match and not results["GROUP"]:
                group_text = g_match.group(1).strip()
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if next_line.isupper() and not any(k in next_line for k in ["1.", "A.", "B.", "HÌNH"]):
                        group_text += " " + next_line
                results["GROUP"] = group_text
                continue 

            # 2. Tiêu đề cây
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
        """Hợp nhất tri thức các trang bị tràn."""
        if old["dinh_danh"]["id"] != new["dinh_danh"]["id"]:
            return old 

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
            
            if not v_new.startswith("["):
                tagged_new = f"[{diamond_source_id}]: {v_new}"
            else:
                tagged_new = v_new
            
            v_old = str(old["van_ban_tho"].get(f, "") or "").strip()
            if v_old and v_old.lower() not in ["none", "null"]:
                if v_old.endswith(('.', ':', '!', '?')):
                    old["van_ban_tho"][f] = f"{v_old}\n{tagged_new}"
                else:
                    clean_v_new = v_new if not v_new.startswith("[") else v_new.split("]: ", 1)[-1]
                    old["van_ban_tho"][f] = f"{v_old} {clean_v_new}"
            else:
                old["van_ban_tho"][f] = tagged_new

        old_raw = old["van_ban_tho"].get("cac_bai_thuoc_raw", [])
        new_raw = new_vbt.get("cac_bai_thuoc_raw", [])
        
        for br in new_raw:
            if not br or br.lower() in ["none", "null"]: continue
            
            if "| [Nguồn]:" not in br:
                br = f"{br} | [Nguồn]: {diamond_source_id}"
            
            if old_raw and "| [Nguồn]:" not in old_raw[-1]:
                old_raw[-1] = f"{old_raw[-1]} {br}"
            elif br not in old_raw:
                old_raw.append(br)
        
        old["van_ban_tho"]["cac_bai_thuoc_raw"] = old_raw

        pages = set(old["dinh_danh"].get("nguon_trang", []))
        pages.add(str(pg))
        old["dinh_danh"]["nguon_trang"] = sorted(list(pages), key=int)
        
        return old

    def call_llm(self, raw_text, pg, page_candidates):
        """Điều phối Mô hình Ngôn ngữ Lớn trích xuất dữ liệu."""
        diamond_id = f"{BOOK_CODE}_T{pg}"
        
        current_group = self.last_group
        current_anchor_id = self.last_anchor
        current_anchor_name = self.last_anchor_name
        
        # CHỈ DẪN BIÊN GIỚI (BOUNDARY STRATEGY)
        if page_candidates:
            names = ", ".join([c['ten_chinh'] for c in page_candidates])
            ids = ", ".join([c['id'] for c in page_candidates])
            
            if not current_anchor_id or current_anchor_id == "START":
                boundary_instr = (
                    f"!!! LỆNH HỆ THỐNG: Trang {pg} bắt đầu các thực thể mới: {names}.\n"
                    f"- ID BẮT BUỘC: [{ids}].\n"
                    f"- YÊU CẦU: Trả về mảng JSON gồm {len(page_candidates)} object."
                )
            else:
                boundary_instr = (
                    f"!!! LỆNH HỆ THỐNG: Trang {pg} là ranh giới thực thể.\n"
                    f"- ĐẦU TRANG: Là nội dung tiếp nối của vị thuốc: '{current_anchor_name}' (ID: {current_anchor_id}).\n"
                    f"- GIỮA/CUỐI TRANG: Bắt đầu các vị thuốc mới: {names} (ID: {ids}).\n"
                    f"- QUY TẮC: Phải vét sạch văn bản mồ côi ở đầu trang gộp vào cây cũ trước khi sang cây mới.\n"
                    f"- YÊU CẦU: Trả về mảng JSON gồm {len(page_candidates) + 1} object."
                )
        else:
            boundary_instr = (
                f"TIẾP NỐI NGỮ CẢNH: Trang {pg} hoàn toàn là phần mô tả tiếp theo của '{current_anchor_name}'.\n"
                f"- YÊU CẦU: Trả về mảng JSON 1 object duy nhất với ID: {current_anchor_id}."
            )

        page_prompt = self.prompt_page.replace('{PG}', str(pg))
        page_prompt = page_prompt.replace('{LAST_ANCHOR}', current_anchor_name)
        page_prompt = page_prompt.replace('{DIAMOND_SOURCE_ID}', diamond_id)

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

        try:
            response = self.llm.models.generate_content(
                model=MODEL_ID,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, 
                    response_mime_type="application/json",
                    response_schema=BRONZE_ARRAY_SCHEMA 
                )
            )
            # 🟢 SỬA LỖI PARSE AN TOÀN KÈM FALLBACK
            if response.parsed is not None:
                if hasattr(response.parsed, 'model_dump'):
                    return response.parsed.model_dump()
                return response.parsed
                
            # Dùng hàm cứu hộ nếu trả về markdown thô
            parsed_data = robust_json_parse(response.text)
            return parsed_data if parsed_data else []
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng LLM tại trang {pg}: {e}")
            with open(os.path.join(DEBUG_IMG_DIR, f"failed_prompt_p{pg}.txt"), "w", encoding="utf-8") as f:
                f.write(full_prompt)
            return []

    def run(self, start, end):
        """Chạy pipeline chính."""
        for pg in range(start, end + 1):
            if pg <= self.last_page: continue
            print(f"🚀 Xử lý trang: {pg} | Nhóm hiện tại: {self.last_group}")

            # 1. Tải mỏ neo từ TOC
            page_candidates = self.toc_map.get(pg, [])
            if not isinstance(page_candidates, list): 
                page_candidates = [page_candidates] if page_candidates else []

            if page_candidates:
                self.last_group = page_candidates[0]["phan_nhom"]
                print(f"📁 TOC Master: Đã xác định nhóm '{self.last_group}' cho trang {pg}")

            try:
                # 2. Document AI OCR
                temp_doc = fitz.open()
                temp_doc.insert_pdf(self.pdf, from_page=pg-1, to_page=pg-1)
                raw_ocr = self.docai.process_document(
                    request={"name": self.processor, "raw_document": {"content": temp_doc.write(), "mime_type": "application/pdf"}}
                ).document.text
                temp_doc.close()
                
                # 🟢 CƠ CHẾ MỚI: LƯU RAW OCR XUỐNG FILE TXT THEO TRANG
                raw_ocr_path = os.path.join(RAW_OCR_DIR, f"page_{pg}.txt")
                with open(raw_ocr_path, "w", encoding="utf-8") as f_raw:
                    f_raw.write(raw_ocr)

                # 3. Phân tích vật lý
                headers_found = self.detect_headers(raw_ocr)
                if headers_found.get("GROUP"):
                    regex_group = headers_found["GROUP"]
                    if not page_candidates:
                        self.last_group = regex_group 
                        print(f"📡 Regex detected new group: {self.last_group}")
                    else:
                        self.last_group = page_candidates[0]["phan_nhom"]

                # 4. Trích xuất LLM
                items = self.call_llm(raw_ocr, pg, page_candidates)
                
                for it in items:
                    it["dinh_danh"]["phan_nhom"] = self.last_group
                    
                    m_id = it.get("dinh_danh", {}).get("id")
                    if not m_id: continue

                    clean_m_id = m_id.replace("_", "").upper()
                    matched_cand = None
                    
                    for cand in page_candidates:
                        if clean_m_id == cand["id"].replace("_", "").upper():
                            matched_cand = cand
                            break
                    
                    # 🟢 CHỐT CHẶN CƯỠNG CHẾ TRANG BẮT ĐẦU ĐỂ TẠO ID DUY NHẤT VÀ VÁ LỖI NONE
                    if matched_cand:
                        # Đây là vị thuốc mới khởi tạo ở trang này
                        it["dinh_danh"]["id"] = matched_cand["id"]
                        it["dinh_danh"]["ten_chinh"] = matched_cand["ten_chinh"]
                        current_anchor_page = pg
                        self.last_anchor_page = pg # Cập nhật mỏ neo
                    elif not page_candidates or (self.last_anchor and clean_m_id == self.last_anchor.replace("_", "").upper()):
                        # Đây là phần vắt sang từ trang trước của vị thuốc cũ
                        it["dinh_danh"]["id"] = self.last_anchor
                        it["dinh_danh"]["ten_chinh"] = self.last_anchor_name
                        current_anchor_page = self.last_anchor_page
                    else:
                        # Fallback an toàn (hiếm khi xảy ra)
                        current_anchor_page = pg
                        self.last_anchor_page = pg

                    # 5. Lưu trữ / Gộp file (TÌM CHÍNH XÁC, KHÔNG DÙNG ENDSWITH)
                    actual_id = it["dinh_danh"]["id"]
                    target_filename = f"{current_anchor_page}_{actual_id}.json"
                    path = os.path.join(OUTPUT_DIR, target_filename)
                    
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                        data[0] = self.merge_logic(data[0], it, pg)
                    else:
                        it["dinh_danh"]["nguon_trang"] = [str(pg)]
                        data = [it]

                    with open(path, "w", encoding="utf-8") as f: 
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    self.last_anchor = actual_id
                    self.last_anchor_name = it["dinh_danh"]["ten_chinh"]

                self._save_checkpoint(pg)
                time.sleep(3) 

            except Exception as e:
                print(f"❌ Lỗi nghiêm trọng trang {pg}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    pipeline = YHCTPipelineV2()
    pipeline.run(45, 1067)
    # 🟢 Tắt máy sau khi hoàn tất (hiện đã bị vô hiệu hóa để an toàn trong lúc test)
    # os.system("shutdown -s -t 60")