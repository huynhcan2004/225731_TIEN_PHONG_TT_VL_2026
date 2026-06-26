"""
Module: chatbot/nlu_engine.py
Chức năng: Đảm nhiệm vai trò Bộ não Phân tích Ngữ nghĩa (NLU) và Tổng hợp Tri thức.
Gồm 2 thành phần chính:
1. extract_intent_and_entities: Chuyển câu hỏi tự nhiên thành cấu trúc dữ liệu máy hiểu.
2. summarize_answer: Chuyển dữ liệu đồ thị khô khan thành câu trả lời văn phong chuyên gia, với cơ chế Lọc Trọng Tâm (Semantic Filtering) chống lan man.
"""
import ast
import json
import re
from app.config import settings
from chatbot.llm_provider import generate_ai_response, get_embedding
from chatbot.cypher_builder import build_cypher_template

# Bộ nhớ đệm cục bộ giúp tiết kiệm chi phí API cho các câu hỏi trùng lặp
QUERY_CACHE = {}

# CÔNG TẮC BẬT/TẮT GIÁM KHẢO (Đổi thành True khi chạy thực tế, False khi test để tiết kiệm API)
ENABLE_EVALUATOR_AGENT = True

def validate_answer(answer, graph_data, lang="vi"):
    """
    Kiểm tra xem LLM có trả lời dựa trên dữ liệu thật không.
    Thay vì check từng chữ hoa (gây lỗi với chữ đầu câu), ta check sự tồn tại của thực thể.
    """
    if not graph_data:
        return True
        
    answer_lower = answer.lower()
    
    # Nếu LLM chủ động nhận thua (tuân thủ prompt) thì cho qua
    if "chưa ghi nhận dữ liệu" in answer_lower or "không có ghi nhận nào" in answer_lower or "no record" in answer_lower or "no records" in answer_lower or "not recorded" in answer_lower:
        return True

    if lang == "en":
        import unicodedata
        def strip_accents(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        
        answer_no_accent = strip_accents(answer_lower)
        for r in graph_data:
            chu_the = r.get("ChuThe", "").lower()
            doi_tuong = r.get("DoiTuong", "").lower()
            chu_the_core = strip_accents(chu_the.replace("vị thuốc ", "").replace("bài thuốc ", "").replace("công năng ", ""))
            doi_tuong_core = strip_accents(doi_tuong.replace("vị thuốc ", "").replace("bài thuốc ", "").replace("công năng ", ""))
            if (chu_the_core and chu_the_core in answer_no_accent) or (doi_tuong_core and doi_tuong_core in answer_no_accent):
                return True
        # Nếu là tiếng Anh và không khớp chính xác không dấu, cho phép qua để tránh chặn các từ dịch thuật hoàn toàn (như Motherwort)
        return True

    # Kiểm tra xem có ít nhất 1 thực thể (ChuThe hoặc DoiTuong) xuất hiện trong câu trả lời không
    for r in graph_data:
        chu_the = r.get("ChuThe", "").lower()
        doi_tuong = r.get("DoiTuong", "").lower()
        
        # Lột bỏ tiền tố để so sánh dễ hơn (Vd: "vị thuốc ích mẫu" -> "ích mẫu")
        chu_the_core = chu_the.replace("vị thuốc ", "").replace("bài thuốc ", "").replace("công năng ", "")
        doi_tuong_core = doi_tuong.replace("vị thuốc ", "").replace("bài thuốc ", "").replace("công năng ", "")

        if chu_the_core and chu_the_core in answer_lower:
            return True
        if doi_tuong_core and doi_tuong_core in answer_lower:
            return True

    # Nếu LLM sinh ra một đoạn văn hoàn toàn không chứa thực thể nào -> Chặn lại
    return False

async def extract_intent_and_entities(user_query, model_name=settings.MODEL_ID, lang="vi"):
    """
    Hàm phân tích câu hỏi người dùng để trích xuất Intent và Keywords.
    
    Args:
        user_query (str): Câu hỏi của người dùng.
        model_name (str): Tên mô hình AI sử dụng.
        lang (str): Ngôn ngữ giao diện ("vi" hoặc "en").
        
    Returns:
        dict: Chứa thông tin cypher, intent, k1, k2 và vector dữ liệu.
    """
    if user_query in QUERY_CACHE:
        return QUERY_CACHE[user_query]

    SYSTEM_PROMPT = """
[VAI TRÒ]
Bạn là Bộ não Phân tích Ngữ nghĩa (NLU Engine) cốt lõi của Hệ thống Y Học Cổ Truyền Diamond.
Nhiệm vụ: Phân tích sâu câu hỏi của người dùng, loại bỏ từ nhiễu, lập luận logic và trả về cấu trúc JSON chuẩn xác để truy vấn Đồ thị Tri thức (Knowledge Graph).

[QUY TẮC CỐT LÕI - KHÔNG ĐƯỢC VI PHẠM]
1. ĐỊNH HƯỚNG CHIỀU TRUY VẤN (QUAN TRỌNG):
   - Đưa TÊN THUỐC -> Tìm BỆNH: Dùng TIM_CONG_DUNG_CUA_THUOC (k1 = Tên thuốc).
   - Đưa TÊN BỆNH/TRIỆU CHỨNG -> Tìm THUỐC: Dùng TIM_THUOC_CHUA_BENH hoặc TIM_BAI_THUOC_CHUA_BENH (k1 = Tên bệnh).
   - Đưa ĐẶC TÍNH (Hàn, Nhiệt, Ôn, Lương, Cay, Đắng...) -> Tìm THUỐC: BẮT BUỘC dùng TIM_THUOC_THEO_TINH_VI_KINH (k1 = Đặc tính).
   - Hỏi TÍNH/VỊ của 1 loại thuốc cụ thể (VD: Ích mẫu có vị gì) -> Dùng TIM_TINH hoặc TIM_VI.
   - Hỏi CÁCH SẮC/LIỀU LƯỢNG -> Dùng TIM_HUONG_DAN_SU_DUNG.
   - Hỏi CÔNG NĂNG thuần túy (VD: "có công năng gì") -> Dùng TIM_CONG_NANG.
   - Hỏi TÁC DỤNG DƯỢC LÝ (VD: "tác dụng dược lý", "cơ chế") -> Dùng TIM_TAC_DUNG_DUOC_LY.

2. BOOLEAN (XÁC NHẬN ĐÚNG/SAI):
   - Nếu câu hỏi có tính chất xác nhận 1 thực thể có chứa/chữa/quy kinh 1 thực thể khác (VD: "X có chữa Y không?", "X có tính hàn không?").
   - BẮT BUỘC dùng KIEM_TRA_BOOLEAN. k1 = Thực thể chủ, k2 = Thuộc tính cần kiểm tra.

3. MULTI-HOP (TRUY VẤN CẦU NỐI):
   - Dấu hiệu: "Bài thuốc chứa vị thuốc [X] thì chữa bệnh gì?".
   - Dùng TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC. k1 = X.

4. LỌC TỪ KHÓA (KEYWORD EXTRACTION):
   - CHỈ lấy danh từ lõi. LOẠI BỎ CÁC TỪ MÀO ĐẦU (bác ơi, cho hỏi, nghe nói, thuốc, vị thuốc, bài thuốc, cây, chứng, bệnh).
   - BẢO TỒN DẤU TIẾNG VIỆT 100%. Không tự ý sửa lỗi chính tả nếu nó có thể là tên tiếng địa phương.

5. ƯU TIÊN TÊN BÀI THUỐC (THÀNH PHẦN):
   - Nếu câu hỏi có cấu trúc "Bài thuốc [X] gồm những gì/vị thuốc nào" -> Gán ngay intent="TIM_THANH_PHAN_BAI_THUOC", k1="X". 
   - [X] ở đây là toàn bộ cụm danh từ chỉ tên bài thuốc (Vd: "Hoàng liên ô rô chữa sốt rét").

[DANH SÁCH MÃ INTENT CHÍNH]
- TIM_TINH | TIM_VI | TIM_QUY_KINH | TIM_HOAT_CHAT_CUA_THUOC
- TIM_CONG_NANG | TIM_TAC_DUNG_DUOC_LY | TIM_CONG_DUNG_CUA_THUOC
- TIM_THANH_PHAN_BAI_THUOC | TIM_BAI_THUOC_CUA_THUOC
- TIM_THUOC_CHUA_BENH | TIM_BAI_THUOC_CHUA_BENH
- TIM_DA_QUAN_HE | TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC
- KIEM_TRA_BOOLEAN | TIM_HUONG_DAN_SU_DUNG | TIM_THUOC_THEO_TINH_VI_KINH

[VÍ DỤ HUẤN LUYỆN - HÃY HỌC CÁCH LẬP LUẬN NÀY]
User: "những vị thuốc nào có tính ôn"
=> {"reasoning": "Người dùng cung cấp đặc tính 'ôn' và muốn tìm danh sách các vị thuốc mang đặc tính này. Đây là truy vấn ngược từ đặc tính ra thực thể.", "intent": "TIM_THUOC_THEO_TINH_VI_KINH", "k1": "ôn", "k2": ""}

User: "thuốc nào có vị đắng"
=> {"reasoning": "Người dùng cung cấp vị 'đắng' và muốn tìm thuốc. Truy vấn ngược.", "intent": "TIM_THUOC_THEO_TINH_VI_KINH", "k1": "đắng", "k2": ""}

User: "Ích mẫu có vị gì?"
=> {"reasoning": "Người dùng cung cấp tên thuốc 'ích mẫu' và hỏi về vị của nó. Đây là truy vấn xuôi.", "intent": "TIM_VI", "k1": "ích mẫu", "k2": ""}

User: "Bác ơi, chó đẻ răng cưa chữa viêm gan được ko ạ?"
=> {"reasoning": "Câu hỏi xác nhận khả năng chữa bệnh viêm gan của chó đẻ răng cưa. Có từ khóa nghi vấn 'được ko'.", "intent": "KIEM_TRA_BOOLEAN", "k1": "chó đẻ răng cưa", "k2": "viêm gan"}

User: "cho mình hỏi bài thuốc Hoàng liên ô rô chữa sốt rét thì gồm những cái gì?"
=> {"reasoning": "Hỏi về thành phần của một bài thuốc cụ thể. Cần loại bỏ từ nhiễu 'bài thuốc', 'gồm những cái gì'.", "intent": "TIM_THANH_PHAN_BAI_THUOC", "k1": "Hoàng liên ô rô chữa sốt rét", "k2": ""}

User: "tôi bị ho khan lâu ngày, đờm đặc thì uống thuốc gì tốt?"
=> {"reasoning": "Người dùng cung cấp triệu chứng (ho khan, đờm đặc) và yêu cầu tìm thuốc chữa. Không đưa ra tên thuốc cụ thể.", "intent": "TIM_THUOC_CHUA_BENH", "k1": "ho khan", "k2": ""}

User: "vị thuốc nào có tính hàn mà lại chữa được đau mỏi gối"
=> {"reasoning": "Tìm thuốc dựa trên 2 điều kiện độc lập: tính hàn và chữa đau mỏi gối.", "intent": "TIM_DA_QUAN_HE", "k1": "hàn", "k2": "đau mỏi gối"}

User: "Thanh đại có công dụng gì?"
=> {"reasoning": "Hỏi về công dụng điều trị bệnh chung của Thanh đại. Phân biệt với tính, vị hay quy kinh.", "intent": "TIM_CONG_DUNG_CUA_THUOC", "k1": "thanh đại", "k2": ""}

[ĐỊNH DẠNG ĐẦU RA BẮT BUỘC]
Bắt buộc trả về ĐÚNG MỘT KHỐI JSON hợp lệ. Bắt buộc phải có trường "reasoning" để suy nghĩ trước khi chốt intent. KHÔNG CÓ BẤT KỲ VĂN BẢN NÀO NGOÀI JSON.
{
  "reasoning": "Lập luận ngắn gọn...",
  "intent": "MÃ_INTENT",
  "k1": "từ khóa 1",
  "k2": "từ khóa 2"
}
"""
    if lang == "en":
        SYSTEM_PROMPT += """
[ENGLISH TO VIETNAMESE ENTITY MAPPING (CRITICAL FOR ENGLISH USERS)]
Since the database stores Traditional Medicine herbs and remedies in Vietnamese, you MUST map any English terms, disease names, or herb names to their exact Vietnamese equivalents when determining "k1" and "k2".
Examples:
- "What is Motherwort used for?" -> intent: "TIM_CONG_DUNG_CUA_THUOC", k1: "ích mẫu", k2: ""
- "Which herb cures malaria?" -> intent: "TIM_THUOC_CHUA_BENH", k1: "sốt rét", k2: ""
- "Is thanh dai cold?" -> intent: "KIEM_TRA_BOOLEAN", k1: "thanh đại", k2: "hàn"
- "What remedies are cold?" -> intent: "TIM_THUOC_THEO_TINH_VI_KINH", k1: "hàn", k2: ""
- "What is Ich mau?" -> intent: "TIM_CONG_DUNG_CUA_THUOC", k1: "ích mẫu", k2: ""
Make sure k1 and k2 are written in Vietnamese so the Cypher builder can query the database.
"""

    try:
        # Bước 1: Gửi yêu cầu phân tích tới LLM
        raw_text = await generate_ai_response(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Phân tích câu hỏi sau: '{user_query}'",
            temperature=0.0,
            model_name=model_name
        )
        
        # Bước 2: Dọn dẹp Markdown rác
        raw_text = raw_text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'```\s*$', '', raw_text)
        
        # Bước 3: Trích xuất JSON (BẢN NÂNG CẤP CHỐNG ĐẠN AST + REGEX)
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not json_match:
            print(f"❌ [DEBUG - NLU PARSE ERROR]: Không tìm thấy JSON hợp lệ trong chuỗi trả về từ AI.")
            print(f"⚠️ Chuỗi RAW AI trả về:\n{raw_text}\n")
            return None

        if json_match:
            json_str = json_match.group(0)
            data = {}
            try:
                # Cố gắng parse JSON chuẩn trước
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Nếu LLM dùng ngoặc đơn {'intent': '...'} -> Dùng ast cứu
                try:
                    data = ast.literal_eval(json_str)
                except Exception:
                    # Nếu LLM quên ngoặc {intent: "..."} -> Dùng Regex tự động bọc ngoặc kép
                    fixed_str = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', json_str)
                    fixed_str = fixed_str.replace("'", '"')
                    try:
                        data = json.loads(fixed_str)
                    except Exception:
                        data = {} # Đường cùng không parse được thì trả về rỗng để tránh crash

            intent = data.get("intent", "UNKNOWN")
            k1 = data.get("k1", "")
            k2 = data.get("k2", "")
            
            # Bước 4: Xử lý tìm kiếm Vector ĐỒNG BỘ TOÀN CỤC (Đã tắt để loại bỏ hoàn toàn phụ thuộc vào Ollama)
            vector_data = None
            use_vector = False

            # Bước 5: Dựng câu lệnh Cypher
            cypher = build_cypher_template(intent, k1, k2, use_vector=use_vector)
            
            print(f"\n{'='*50}")
            print(f"🔍 [NLU ANALYSIS - LLM DEBUG]")
            print(f"- RAW LLM   : {raw_text}")  
            print(f"- Reasoning : {data.get('reasoning')}")
            print(f"- Intent    : {intent}")
            print(f"- K1        : '{k1}' | K2: '{k2}'")
            print(f"- Vector    : {'BẬT (Hybrid)' if use_vector else 'TẮT (Exact Match Only)'}")
            print(f"{'='*50}\n")
            
            result_obj = {
                "cypher": cypher, 
                "intent": intent, 
                "k1": k1, 
                "k2": k2, 
                "vector": vector_data
            }
            
            QUERY_CACHE[user_query] = result_obj
            return result_obj
            
    except Exception as e:
        print(f"❌ [DEBUG - NLU PARSE ERROR]: {e}")
        if 'raw_text' in locals() and raw_text:
            print(f"⚠️ Chuỗi AI trả về bị lỗi:\n{raw_text}\n")
    
    return None

def clean_ai_response(text):
    """Dọn dẹp và chuẩn hóa văn bản trả về từ AI."""
    if not text or "không có dữ liệu" in text.lower(): 
        return "Rất tiếc, hiện tại hệ thống chưa có dữ liệu về vấn đề này."
    return text.strip()

# =====================================================================
# AGENT 3: EVALUATOR AGENT (GIÁM KHẢO CHỐNG ẢO GIÁC)
# =====================================================================
async def evaluate_hallucination(user_query, fact_sheet, generated_answer, model_name=settings.MODEL_ID):
    """
    Agent Giám khảo: Chấm điểm Faithfulness (Độ trung thực) của câu trả lời so với dữ liệu gốc.
    """
    EVALUATOR_PROMPT = """
    Bạn là một Giám khảo Y khoa cực kỳ khắt khe. Nhiệm vụ của bạn là kiểm tra xem CÂU TRẢ LỜI CỦA AI có bị "ảo giác" (bịa đặt thông tin) so với DỮ LIỆU GỐC hay không.

    [QUY TẮC CHẤM ĐIỂM]
    1. Trích xuất tất cả các mệnh đề y khoa (tên thuốc, công dụng, liều dùng, tính vị) từ CÂU TRẢ LỜI CỦA AI.
    2. Đối chiếu từng mệnh đề với DỮ LIỆU GỐC.
    3. Nếu CÂU TRẢ LỜI chứa BẤT KỲ thông tin y khoa nào KHÔNG CÓ trong DỮ LIỆU GỐC -> Đánh giá là FAIL (Ảo giác).
    4. Nếu toàn bộ thông tin đều được suy ra trực tiếp từ DỮ LIỆU GỐC -> Đánh giá là PASS (An toàn).
    5. Bỏ qua việc đánh giá các câu cảnh báo y tế hoặc lời giải thích chung chung không mang tính lâm sàng.

    [ĐẦU RA BẮT BUỘC (JSON)]
    Bắt buộc trả về đúng định dạng JSON sau, tuyệt đối không kèm văn bản nào khác:
    {
        "reasoning": "Phân tích chi tiết sự trùng khớp hoặc sai lệch...",
        "status": "PASS" hoặc "FAIL"
    }
    """

    user_prompt = f"""
    [DỮ LIỆU GỐC]
    {fact_sheet}

    [CÂU TRẢ LỜI CỦA AI CẦN ĐÁNH GIÁ]
    {generated_answer}
    """

    try:
        eval_result = await generate_ai_response(
            system_prompt=EVALUATOR_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0, # Bắt buộc = 0 để giám khảo không sáng tạo
            model_name=model_name
        )
        
        # Parse JSON output
        eval_result = eval_result.strip()
        eval_result = re.sub(r'^```json\s*', '', eval_result)
        eval_result = re.sub(r'```\s*$', '', eval_result)
        
        data = json.loads(eval_result)
        return data.get("status") == "PASS", data.get("reasoning")
        
    except Exception as e:
        print(f"❌ [EVALUATOR ERROR]: {e}")
        # Mặc định an toàn (Fall-open) để không chặn hệ thống nếu hàm parse JSON lỗi
        return True, "Lỗi khi chạy Evaluator Agent, bỏ qua đánh giá."

async def summarize_answer(user_query, intent, graph_data, k1="", k2="", model_name=settings.MODEL_ID, lang="vi"):
    """
    Hàm tổng hợp tri thức Diamond (Phiên bản Lọc Semantic Khắt Khe - Chống Lan Man & Phân Nhóm Nhiễu).
    """
    if not graph_data: 
        graph_data = []

    # =====================================================================
    # LỌC KÉP Ở TẦNG PYTHON (Chống Vector Rác & Lọc Nhiễu Theo Intent)
    # =====================================================================
    
    # 1. Khai báo danh sách các quan hệ cơ sở để kiểm soát nhiễu chéo
    BASE_RELATIONS = {
        "CO_TINH", "CO_VI", "QUY_KINH", "CO_CHUA_HOAT_CHAT", 
        "CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY", "CHU_TRI_BENH", 
        "CHU_TRI_TRIEU_CHUNG", "BAO_GOM_VI_THUOC"
    }

    # 2. Quy định khắt khe: Intent nào chỉ được phép nhận Quan hệ đó
    STRICT_INTENT_FILTER = {
        "TIM_TINH": ["CO_TINH"],
        "TIM_VI": ["CO_VI"],
        "TIM_QUY_KINH": ["QUY_KINH"],
        "TIM_HOAT_CHAT_CUA_THUOC": ["CO_CHUA_HOAT_CHAT"],
        "TIM_CONG_NANG": ["CO_CONG_NANG"],
        "TIM_TAC_DUNG_DUOC_LY": ["CO_TAC_DUNG_DUOC_LY"],
        "TIM_CONG_DUNG_CUA_THUOC": ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"],
        "TIM_THANH_PHAN_BAI_THUOC": ["BAO_GOM_VI_THUOC"],
        "TIM_BAI_THUOC_CUA_THUOC": ["BAO_GOM_VI_THUOC"]
    }
    
    allowed_rels = STRICT_INTENT_FILTER.get(intent)
    filtered_graph_data = []
    
    for record in graph_data:
        score = record.get('score', 2.0)
        quan_he_raw = record.get("QuanHe", "")
        
        # BỘ LỌC 1: Lọc theo ngưỡng Score của Vector Search
        if float(score) < 0.94 and float(score) != 2.0:
            continue
            
        # BỘ LỌC 2: Lọc Semantic (Loại bỏ tri thức sai trọng tâm)
        if allowed_rels:
            # Nếu quan hệ raw thuộc nhóm Base mà không nằm trong danh sách cho phép của Intent
            if quan_he_raw in BASE_RELATIONS and quan_he_raw not in allowed_rels:
                continue # Cắt bỏ ngay lập tức để LLM không bị nhiễu
                
        filtered_graph_data.append(record)
    graph_data = filtered_graph_data
    # =====================================================================

    print(f"\n📊 [THỐNG KÊ TRUY XUẤT SAU KHI LỌC KHẮT KHE - {len(graph_data)} kết quả]")
    for record in graph_data:
        # Lấy score, nếu Cypher (exact_query) không trả về thì mặc định là 2.0
        score_val = float(record.get('score', 2.0))
        
        # Lấy chuỗi raw
        chu_the_raw = str(record.get('ChuThe', '')).lower()
        doi_tuong_raw = str(record.get('DoiTuong', '')).lower()
        k1_raw = k1.lower() if k1 else ""
        k2_raw = k2.lower() if k2 else ""

        # Hàm gọt tiền tố giống y hệt Cypher
        def strip_prefix(text):
            for p in ['vị thuốc ', 'bài thuốc ', 'dược liệu ', 'bệnh ', 'chứng ', 'triệu chứng ']:
                text = text.replace(p, '')
            return text.strip()

        # Gọt sạch sẽ trước khi so sánh
        chu_the_core = strip_prefix(chu_the_raw)
        doi_tuong_core = strip_prefix(doi_tuong_raw)
        k1_core = strip_prefix(k1_raw)
        k2_core = strip_prefix(k2_raw)

        # Phân tách rõ 3 loại nguồn tìm kiếm và CHẤM ĐIỂM ƯU TIÊN
        if score_val >= 2.0:
            if (k1_core and (k1_core == chu_the_core or k1_core == doi_tuong_core)) or \
               (k2_core and (k2_core == chu_the_core or k2_core == doi_tuong_core)):
                source = "🟢 EXACT MATCH (Khớp chính xác tuyệt đối)"
                record['sort_weight'] = 3.0  # <--- HẠNG 1: Ưu tiên cao nhất
            else:
                source = "🟡 PARTIAL MATCH (Khớp ranh giới từ/Bao hàm)"
                # BẢN VÁ LỖI: Sửa 0.5 thành 1.5 để không bị Vector Search đè bẹp
                record['sort_weight'] = 1.5  # <--- HẠNG 2: Ưu tiên nhì (tránh nhiễu Vector)
                #continue # Bỏ luôn các kết quả Partial Match để tránh nhiễu cho LLM
        else:
            source = f"🔵 VECTOR SEARCH (Score: {score_val:.4f})"
            # Giữ nguyên điểm vector (thường từ 0.93 đến 1.0)
            record['sort_weight'] = float(score_val) # <--- HẠNG 3: Ngữ nghĩa y học 
            
        print(f"📍 [{record.get('ChuThe')}] -> [{record.get('QuanHe')}] -> [{record.get('DoiTuong')}] | Nguồn: {source}")
    print("-" * 50 + "\n")

    # =====================================================================
    # SẮP XẾP VÀ PHÂN XÔ DỮ LIỆU (CONTEXT BUCKETIZING)
    # =====================================================================
    graph_data.sort(key=lambda x: x.get('sort_weight', 0), reverse=True)

    exact_matches = []
    related_matches = []

    # Tách dữ liệu thành 2 xô (Buckets) để LLM dễ dàng phân biệt
    for record in graph_data:
        if record.get('sort_weight', 0) >= 3.0:
            exact_matches.append(record)
        else:
            related_matches.append(record)

    structured_data = {
        "DU_LIEU_CHINH_XAC": exact_matches,
        "DU_LIEU_MO_RONG_LIEN_QUAN": related_matches
    }

    # Đẩy toàn bộ cấu trúc JSON đã chia xô vào cho LLM
    fact_sheet = json.dumps(structured_data, ensure_ascii=False, indent=2)

    # =====================================================================
    # SIGNALING TRỌNG TÂM CÂU HỎI ĐỂ ÉP LLM SUY LUẬN ĐÚNG HƯỚNG
    # =====================================================================
    INTENT_DESC_MAP = {
        "TIM_TINH": "Tính của thuốc (Hàn, Nhiệt, Ôn, Lương...)",
        "TIM_VI": "Vị của thuốc (Cay, Đắng, Ngọt...)",
        "TIM_QUY_KINH": "Quy kinh (Tâm, Can, Tỳ, Phế, Thận...)",
        "TIM_HOAT_CHAT_CUA_THUOC": "Hoạt chất chứa trong thuốc",
        "TIM_CONG_NANG": "Công năng của thuốc (Chức năng y lý)",
        "TIM_TAC_DUNG_DUOC_LY": "Tác dụng dược lý (Cơ chế khoa học)",
        "TIM_CONG_DUNG_CUA_THUOC": "Công dụng chữa bệnh / trị triệu chứng",
        "TIM_THANH_PHAN_BAI_THUOC": "Thành phần cấu tạo bài thuốc",
        "TIM_THUOC_CHUA_BENH": "Tìm thuốc điều trị bệnh",
        "TIM_BAI_THUOC_CHUA_BENH": "Tìm bài thuốc điều trị bệnh",
        "TIM_HUONG_DAN_SU_DUNG": "Hướng dẫn sử dụng, liều dùng, cách dùng",
        "KIEM_TRA_BOOLEAN": "Xác nhận đúng/sai về một thuộc tính",
        "TIM_DA_QUAN_HE": "Tra cứu thỏa mãn nhiều điều kiện cùng lúc"
    }
    focus_target = INTENT_DESC_MAP.get(intent, "Trả lời tổng quan theo câu hỏi")

    # =====================================================================
    # TÙY BIẾN CÂU TRẢ LỜI KHI DỮ LIỆU RỖNG (DYNAMIC EMPTY FALLBACK)
    # =====================================================================
    if lang == "en":
        if not exact_matches and not related_matches and intent == "KIEM_TRA_BOOLEAN":
            chu_the_hien_thi = k1 if k1 else "this herb/remedy"
            doi_tuong_hien_thi = k2 if k2 else "this property"
            empty_fallback = f"No. Based on current medical literature, there is no record showing that {chu_the_hien_thi} is related to or has an effect on {doi_tuong_hien_thi}."
        else:
            empty_fallback = "The current medical literature has no records regarding this matter."
    else:
        if not exact_matches and not related_matches and intent == "KIEM_TRA_BOOLEAN":
            chu_the_hien_thi = k1 if k1 else "vị thuốc/bài thuốc này"
            doi_tuong_hien_thi = k2 if k2 else "đặc tính này"
            empty_fallback = f"Không. Dựa trên dữ liệu y văn hiện tại, không có ghi nhận nào cho thấy {chu_the_hien_thi} có liên quan hoặc tác dụng tới {doi_tuong_hien_thi}."
        else:
            empty_fallback = "Hệ thống y văn hiện tại chưa ghi nhận dữ liệu về vấn đề này."

    # PROMPT "NGỰ Y KIM CƯƠNG" - ĐÃ NÂNG CẤP ANTI-HALLUCINATION & BUCKETIZING
    prompt = f"""
[DỮ LIỆU Y VĂN XÁC THỰC TỪ HỆ THỐNG DIAMOND]
{fact_sheet}

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"
TRỌNG TÂM YÊU CẦU ĐƯỢC HỆ THỐNG GIAO PHÓ: {focus_target}

[QUY TẮC BẮT BUỘC - CHỐNG ẢO GIÁC]
- Chỉ được sử dụng thực thể xuất hiện trong dữ liệu JSON.
- Không được thêm bất kỳ bài thuốc hoặc vị thuốc nào ngoài dữ liệu.
- Không được suy luận từ kiến thức bên ngoài.
- Nhiệm vụ là trích xuất và diễn đạt lại dữ liệu, không phải bổ sung.

[KIỂM TRA DỮ LIỆU BẮT BUỘC - THỰC HIỆN ĐẦU TIÊN]
Bạn PHẢI phân tích [DỮ LIỆU Y VĂN XÁC THỰC] và bắt buộc làm theo 1 trong 2 trường hợp dưới đây:

■ TRƯỜNG HỢP 1: NẾU DỮ LIỆU RỖNG HOẶC KHÔNG CÓ THÔNG TIN LIÊN QUAN ĐẾN TRỌNG TÂM
Nếu cả 2 nhóm dữ liệu đều trống rỗng, hoặc không có thông tin giải quyết ĐÚNG TRỌNG TÂM yêu cầu:
- CẤM TUYỆT ĐỐI việc chào hỏi, đồng cảm hay an ủi.
- CẤM TUYỆT ĐỐI tự ý đưa ra bài thuốc/vị thuốc từ bộ nhớ ngoài dữ liệu cung cấp.
- CẤM thêm câu "Cảnh báo y tế" ở cuối bài.
=> Lệnh thực thi: Bạn CHỈ ĐƯỢC PHÉP xuất ra đúng nội dung dưới đây và DỪNG LẠI ngay lập tức:
"{empty_fallback}"

■ TRƯỜNG HỢP 2: NẾU DỮ LIỆU CÓ THÔNG TIN HỢP LỆ VÀ ĐÚNG TRỌNG TÂM
Chỉ khi dữ liệu có chứa thông tin trả lời, bạn mới đóng vai chuyên gia tư vấn Y học cổ truyền và TUÂN THỦ NGHIÊM NGẶT các quy tắc sau:

1. TRUNG THỰC, CHI TIẾT & BÁM SÁT TRỌNG TÂM: 
   - CHỈ trả lời về "{focus_target}". 
   - NẾU người dùng hỏi "Công dụng", TUYỆT ĐỐI KHÔNG liệt kê Tính, Vị, Quy kinh vào câu trả lời để tránh lan man.
   - Khi liệt kê bài thuốc/vị thuốc, BẮT BUỘC phải ghi kèm liều lượng và cách dùng (nếu có trong dữ liệu).

2. PHÂN LOẠI NGỮ CẢNH BỆNH LÝ (CỰC KỲ QUAN TRỌNG): 
   - Dữ liệu hiện được chia làm 2 nhóm: "DU_LIEU_CHINH_XAC" và "DU_LIEU_MO_RONG_LIEN_QUAN".
   - Bạn BẮT BUỘC phải trình bày các phương án trong phần "DU_LIEU_CHINH_XAC" lên đầu tiên và khẳng định đây là đáp án trực tiếp.
   - Đối với các thông tin trong phần "DU_LIEU_MO_RONG_LIEN_QUAN" (ví dụ: thể mạn tính, cấp tính, hoặc bệnh có tên gần giống), bạn phải tách riêng thành mục "Thông tin tham khảo thêm" và ghi rõ phương án đó dùng cho trường hợp nào (Ví dụ: "Đối với trường hợp Viêm phế quản mạn tính, bạn có thể tham khảo...").
   - TUYỆT ĐỐI KHÔNG trộn lẫn thuốc của thể mạn tính/cấp tính vào chung với thể bệnh thông thường.

3. LỌC THÔNG TIN LÂM SÀNG: Chỉ được trích dẫn các công dụng/tác dụng CÓ LIÊN QUAN trực tiếp đến câu hỏi. Lược bỏ các ghi chú nội bộ hệ thống. 

4. XỬ LÝ FALLBACK TRỐNG DỮ LIỆU CHÍNH XÁC: Nếu "DU_LIEU_CHINH_XAC" rỗng nhưng "DU_LIEU_MO_RONG_LIEN_QUAN" có dữ liệu, hãy khéo léo dẫn dắt: "Hiện tại y văn chưa ghi nhận phương án trực tiếp như bạn hỏi, tuy nhiên đối với các thể bệnh liên quan, bạn có thể tham khảo phương án sau đây...".

5. VĂN PHONG "Y SƯ": Trình bày bằng văn bản thuần túy hoặc Markdown tiêu chuẩn.
   - TUYỆT ĐỐI KHÔNG sử dụng ký tự LaTeX (như \\textbf, \\textit, \\n, v.v.).
   - ĐẶC BIỆT CHÚ Ý: KHÔNG ĐƯỢC bọc các con số, liều lượng bằng dấu $ (Ví dụ: Bắt buộc viết "15-30g" thay vì "$15-30g$").
   - Chỉ được In đậm tên bài thuốc/vị thuốc bằng cú pháp Markdown (**tên**). 
   - Không để lộ các từ kỹ thuật như 'score', 'priority', 'sort_weight'.
    
"""
    if lang == "en":
        prompt += """
[MANDATORY LANGUAGE RULE]
- You MUST answer in English. All parts of the response, including explanation, titles, lists, remedies, and dosages MUST be in English.
- Translate the Vietnamese entities, attributes, and descriptions from [DỮ LIỆU Y VĂN XÁC THỰC TỪ HỆ THỐNG DIAMOND] into natural, professional medical English.
- Keep the original plant name in parenthesis next to the English name when first mentioned if helpful (e.g. "Motherwort (Ich mau)" or "Thanh dai").
"""

    # 6. CẢNH BÁO Y TẾ (BẮT BUỘC) - Hiện đang bị comment ẩn để Ragas chấm điểm cho chính xác
    try:
        # Bước 1: Agent 2 tạo bản nháp (Draft Generation)
        response_text = await generate_ai_response(
            system_prompt="", 
            user_prompt=prompt, 
            temperature=0.0, 
            model_name=model_name
        )
        
        # Lớp bảo vệ 1: Dùng Python rules kiểm tra nhanh
        if not validate_answer(response_text, graph_data, lang=lang):
            return empty_fallback
            
        # Lớp bảo vệ 2: Gọi Agent 3 (Evaluator) kiểm tra ảo giác sâu
        if ENABLE_EVALUATOR_AGENT:
            print("\n🕵️‍♂️ [EVALUATOR AGENT] Đang thẩm định chéo với Fact-sheet...")
            is_safe, reasoning = await evaluate_hallucination(user_query, fact_sheet, response_text, model_name)
            
            if is_safe:
                print("✅ [EVALUATION] PASS - Không phát hiện ảo giác.")
                return response_text.strip()
            else:
                print(f"❌ [EVALUATION] FAIL - Phát hiện ảo giác!\nLý do: {reasoning}")
                # Trả về câu thông báo an toàn nếu phát hiện LLM bịa chuyện
                if lang == "en":
                    return "The system detected that the answer might contain unverified information not present in the original literature. For safety, please try again with a more detailed question or consult a physician."
                return "Hệ thống phát hiện câu trả lời có thể chứa thông tin chưa được kiểm chứng trong y văn gốc. Để đảm bảo an toàn, xin vui lòng thử lại với câu hỏi chi tiết hơn hoặc tham khảo ý kiến bác sĩ."
        else:
            # Bỏ qua gọi API cho Giám khảo khi test để tiết kiệm thời gian/tiền bạc
            print("\n⏭️ [EVALUATOR AGENT] Đã TẮT. Bỏ qua bước thẩm định chéo.")
            return response_text.strip()
            
    except Exception as e:
        if lang == "en":
            return f"⚠️ We sincerely apologize, the system is experiencing a temporary issue: {str(e)}"
        return f"⚠️ Chân thành cáo lỗi, hệ thống đang gặp gián đoạn khi bốc thuốc: {str(e)}"