"""
Module: chatbot/nlu_engine.py
Chức năng: Đảm nhiệm vai trò Bộ não Phân tích Ngữ nghĩa (NLU) và Tổng hợp Tri thức.
Gồm 2 thành phần chính:
1. extract_intent_and_entities: Chuyển câu hỏi tự nhiên thành cấu trúc dữ liệu máy hiểu.
2. summarize_answer: Chuyển dữ liệu đồ thị khô khan thành câu trả lời văn phong chuyên gia.
"""

import json
import re
from app.config import settings
from chatbot.llm_provider import generate_ai_response, get_embedding
from chatbot.cypher_builder import build_cypher_template

# Bộ nhớ đệm cục bộ giúp tiết kiệm chi phí API cho các câu hỏi trùng lặp
QUERY_CACHE = {}

async def extract_intent_and_entities(user_query, model_name=settings.MODEL_ID):
    """
    Hàm phân tích câu hỏi người dùng để trích xuất Intent và Keywords.
    
    Args:
        user_query (str): Câu hỏi của người dùng.
        model_name (str): Tên mô hình AI sử dụng.
        
    Returns:
        dict: Chứa thông tin cypher, intent, k1, k2 và vector dữ liệu.
    """
    if user_query in QUERY_CACHE:
        return QUERY_CACHE[user_query]

    SYSTEM_PROMPT = """
[VAI TRÒ]
Bạn là Bộ não Phân tích Ngữ nghĩa (NLU Engine) cốt lõi của Hệ thống Y Học Cổ Truyền Diamond.
Nhiệm vụ: Đọc câu hỏi, hiểu mục đích, khử nhiễu từ khóa và trả về JSON chuẩn xác.

[QUY TẮC CỐT LÕI - PHÂN BIỆT RÕ RÀNG]
1. ĐƠN THỰC THỂ vs ĐA THỰC THỂ:
   - Nếu hỏi về MỘT vị thuốc duy nhất -> Tuyệt đối dùng intent NHÓM 1 hoặc NHÓM 3. k2 để trống ("").
   - Chỉ dùng TIM_DA_QUAN_HE khi người dùng hỏi THUỐC NÀO thỏa mãn 2 ĐIỀU KIỆN (Vd: "Thuốc nào vừa cay vừa chữa đau lưng").
2. MULTI-HOP (BÀI THUỐC CỦA VỊ THUỐC CHỮA BỆNH GÌ):
   - Câu hỏi: "Bài thuốc chứa vị thuốc [X] thì thường dùng để chữa bệnh gì?"
   - Gán ngay: intent="TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC", keyword1="X".
3. BOOLEAN (XÁC NHẬN CÓ/KHÔNG):
   - Câu hỏi: "Vị thuốc [X] có chứa hoạt chất [Y] không?" / "Vị thuốc [X] có mang đặc điểm Tính [Y] không?"
   - Gán ngay: intent="KIEM_TRA_BOOLEAN", keyword1="X", keyword2="Y".
4. BẢO TỒN TỪ KHÓA (QUY TẮC SỐNG CÒN):
   - Tuyệt đối GIỮ NGUYÊN 100% chính tả, dấu câu và các ký tự tiếng Việt của từ khóa (Vd: "Ngọt" phải là "ngọt", không được đổi thành "ngất").
   - Chỉ loại bỏ các từ loại chung như: "vị thuốc", "cây thuốc", "bài thuốc" nếu nó đứng trước tên riêng.
5. ƯU TIÊN TÊN BÀI THUỐC (THÀNH PHẦN):
   - Nếu câu hỏi có cấu trúc "Bài thuốc [X] gồm những gì/vị thuốc nào" -> Gán ngay intent="TIM_THANH_PHAN_BAI_THUOC", keyword1="X". 
   - [X] ở đây là toàn bộ cụm danh từ chỉ tên bài thuốc (Vd: "Hoàng liên ô rô chữa sốt rét").

[DANH SÁCH MÃ INTENT CHÍNH]
- TIM_TINH (Tính hàn, nhiệt)
- TIM_VI (Vị giác: Cay, đắng, ngọt)
- TIM_QUY_KINH (Đi vào kinh mạch nào)
- TIM_HOAT_CHAT_CUA_THUOC (Chứa hoạt chất gì)
- TIM_CONG_NANG_DUOC_LY (Công năng giải độc, thanh nhiệt...)
- TIM_CONG_DUNG_CUA_THUOC (Chữa bệnh gì cụ thể)
- TIM_THANH_PHAN_BAI_THUOC (Hỏi bài thuốc X gồm những gì)
- TIM_BAI_THUOC_CUA_THUOC (Hỏi vị thuốc X nằm trong bài thuốc nào)
- TIM_THUOC_CHUA_BENH (Tôi bị đau đầu thì uống thuốc gì)
- TIM_DA_QUAN_HE (Tìm thuốc dựa trên 2 điều kiện)
- TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC (Hỏi bài thuốc chứa vị thuốc này dùng chữa bệnh gì)
- KIEM_TRA_BOOLEAN (Xác nhận Có/Không về thuộc tính)

[VÍ DỤ HUẤN LUYỆN]
User: "Trạch tả có vị gì?" -> {"intent": "TIM_VI", "keyword1": "trạch tả", "keyword2": ""}
User: "Vị thuốc ích mẫu có bài thuốc nào?" -> {"intent": "TIM_BAI_THUOC_CUA_THUOC", "keyword1": "ích mẫu", "keyword2": ""}
User: "Thuốc nào tính hàn chữa sưng đau?" -> {"intent": "TIM_DA_QUAN_HE", "keyword1": "hàn", "keyword2": "sưng đau"}
User: "Bài thuốc chứa vị thuốc Chó đẻ răng cưa thì thường dùng để chữa bệnh gì?" -> {"intent": "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC", "keyword1": "chó đẻ răng cưa", "keyword2": ""}
User: "Vị thuốc Liên kiều có chứa hoạt chất Phillygenin không?" -> {"intent": "KIEM_TRA_BOOLEAN", "keyword1": "liên kiều", "keyword2": "phillygenin"}
User: "Bài thuốc Hoàng liên ô rô chữa sốt rét gồm vị thuốc nào?" -> {"intent": "TIM_THANH_PHAN_BAI_THUOC", "keyword1": "Hoàng liên ô rô chữa sốt rét", "keyword2": ""}
User: "vị thuốc nào có tính hàn?" -> {"intent": "TIM_THUOC_THEO_TINH_VI_KINH", "keyword1": "hàn", "keyword2": ""}
User: "những thuốc nào có vị đắng?" -> {"intent": "TIM_THUOC_THEO_TINH_VI_KINH", "keyword1": "đắng", "keyword2": ""}

TUYỆT ĐỐI CHỈ TRẢ VỀ JSON. KHÔNG GIẢI THÍCH GÌ THÊM.
"""
    try:
        # Bước 1: Gửi yêu cầu phân tích tới mô hình LLM thông qua LLM Provider
        raw_text = await generate_ai_response(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Phân tích câu hỏi sau: '{user_query}'",
            temperature=0.0,
            model_name=model_name
        )
        
        # Bước 2: Dọn dẹp Markdown rác nếu AI tự thêm vào
        raw_text = raw_text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'```\s*$', '', raw_text)
        
        # Bước 3: Trích xuất JSON từ khối văn bản
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            intent = data.get("intent", "UNKNOWN")
            k1 = data.get("keyword1", "")
            k2 = data.get("keyword2", "")
            
            # Bước 4: Xử lý tìm kiếm Vector cho các câu hỏi về bệnh lý/triệu chứng
            vector_data = None
            use_vector = False
            if intent in ["TIM_THUOC_CHUA_BENH", "TIM_BAI_THUOC_CHUA_BENH"] and k1:
                rich_query = f"Thực thể: {k1}. Loại: Benh hoặc TrieuChung. Ngữ cảnh: Y học cổ truyền Việt Nam."
                vector_data = get_embedding(rich_query)
                if vector_data:
                    use_vector = True

            # Bước 5: Dựng câu lệnh Cypher dựa trên khuôn mẫu (Templates)
            cypher = build_cypher_template(intent, k1, k2, use_vector=use_vector)
            
            result_obj = {
                "cypher": cypher, 
                "intent": intent, 
                "k1": k1, 
                "k2": k2, 
                "vector": vector_data
            }
            
            # Lưu vào cache để tối ưu hiệu năng
            QUERY_CACHE[user_query] = result_obj
            return result_obj
            
    except Exception as e:
        print(f"❌ [DEBUG - NLU PARSE ERROR]: {e}")
    
    return None

def clean_ai_response(text):
    """Dọn dẹp và chuẩn hóa văn bản trả về từ AI."""
    if not text or "không có dữ liệu" in text.lower(): 
        return "Rất tiếc, hiện tại hệ thống chưa có dữ liệu về vấn đề này."
    return text.strip()

async def summarize_answer(user_query, intent, graph_data, k1="", k2="", model_name=settings.MODEL_ID):
    """
    Hàm tổng hợp dữ liệu từ đồ thị tri thức và tạo câu trả lời mượt mà.
    
    Args:
        user_query (str): Câu hỏi gốc của người dùng.
        intent (str): Ý định đã phân tích.
        graph_data (list): Dữ liệu lấy từ Neo4j.
        k1, k2 (str): Các thực thể liên quan.
        model_name (str): Tên mô hình AI.
        
    Returns:
        str: Câu trả lời đã được đúc kết.
    """
    if not graph_data: 
        return "Rất tiếc, hiện tại hệ thống chưa có dữ liệu về vấn đề này."

    # Bảng ánh xạ nhãn quan hệ sang Tiếng Việt
    REL_MAP = {
        "CO_TINH": "Tính", 
        "CO_VI": "Vị", 
        "QUY_KINH": "Quy kinh", 
        "CO_CHUA_HOAT_CHAT": "Hoạt chất", 
        "CO_CONG_NANG": "Công năng", 
        "CO_TAC_DUNG_DUOC_LY": "Dược lý", 
        "CHU_TRI_BENH": "Chữa bệnh", 
        "CHU_TRI_TRIEU_CHUNG": "Trị triệu chứng", 
        "BAO_GOM_VI_THUOC": "Bài thuốc / Thành phần"
    }

    facts = []
    
    # Phân tích dữ liệu Graph thành các "Fact Sheets"
    for record in graph_data:
        if "ChuThe" in record and "KetQua" in record:
            chu_the = record["ChuThe"]
            quan_he_raw = record.get("QuanHe", "")
            quan_he = REL_MAP.get(quan_he_raw, quan_he_raw if quan_he_raw else "Liên quan")
            
            # Lọc kết quả rỗng và sắp xếp alphabet
            items = sorted([i for i in record["KetQua"] if i])

            if items:
                prefix = ""
                # Ép tiền tố "Tính", "Vị" cho chính xác với dữ liệu y văn
                if intent == "TIM_VI" or (intent == "KIEM_TRA_BOOLEAN" and "vị" in k2.lower()):
                    prefix = "Vị"
                elif intent == "TIM_TINH" or (intent == "KIEM_TRA_BOOLEAN" and "tính" in k2.lower()):
                    prefix = "Tính"

                if prefix:
                    items = [f"{prefix} {i}" if not str(i).lower().startswith(prefix.lower()) else i for i in items]
                
                # Logic cho câu hỏi xác nhận Boolean
                if intent == "KIEM_TRA_BOOLEAN":
                    facts.append(f"XÁC NHẬN: {chu_the} THỰC SỰ CÓ {quan_he} là {', '.join(items)}")
                # BỔ SUNG LOGIC CHO CÂU HỎI ĐA ĐIỀU KIỆN (PATTERN 4)
                elif intent == "TIM_DA_QUAN_HE":
                    facts.append(f"XÁC NHẬN ĐÁP ÁN: Các vị thuốc thỏa mãn chính xác các điều kiện người dùng hỏi ({k1} và {k2}) bao gồm: {', '.join(items)}")
                else:
                    facts.append(f"- {chu_the} có {quan_he} gồm: {', '.join(items)}")
                
        elif "Benh" in record and "GiaiPhap" in record:
            facts.append(f"- Để chữa {record['Benh']}, có thể dùng {record['GiaiPhap']}")

    # Khử trùng lặp và sắp xếp lại Fact Sheet
    unique_facts = sorted(list(set([f for f in facts if f.strip()])))
    fact_sheet = "\n".join(unique_facts)
    
    if not fact_sheet: 
        return "Rất tiếc, hiện tại hệ thống chưa có dữ liệu về vấn đề này."

    # PROMPT DỊCH ĐỒ THỊ SANG NGÔN NGỮ CHUYÊN GIA
    prompt = f"""
[DỮ LIỆU XÁC THỰC TỪ ĐỒ THỊ TRI THỨC YHCT]
{fact_sheet}

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

[VAI TRÒ VÀ NHIỆM VỤ]
Bạn là một Bác sĩ / Chuyên gia Y Học Cổ Truyền tận tâm, chuyên nghiệp và uyên bác. 
Nhiệm vụ của bạn là dựa vào [DỮ LIỆU XÁC THỰC TỪ ĐỒ THỊ TRI THỨC YHCT] bên trên để tư vấn và trả lời câu hỏi của người dùng.

[QUY TẮC VĂN PHONG VÀ TRẢ LỜI]
1. TRUNG THỰC VÀ CHÍNH XÁC: Chỉ sử dụng thông tin từ DỮ LIỆU XÁC THỰC. Tuyệt đối không tự bịa đặt, không suy diễn ngoài dữ liệu đồ thị cung cấp. Nếu dữ liệu báo "Không có dữ liệu", hãy nhẹ nhàng thông báo cho người dùng biết hệ thống chưa có thông tin.
2. VĂN PHONG TỰ NHIÊN, LỊCH SỰ: Hãy xưng hô lịch sự, diễn đạt thành câu văn hoàn chỉnh, mượt mà và thân thiện như một bác sĩ đang trò chuyện với bệnh nhân. 
3. TRÌNH BÀY RÕ RÀNG: Nếu có nhiều kết quả (như nhiều vị thuốc, bài thuốc), hãy trình bày rõ ràng, dễ đọc (sử dụng gạch đầu dòng để liệt kê cho khoa học).
4. CÂU HỎI XÁC NHẬN (BOOLEAN): Nếu người dùng hỏi dạng Có/Khôn, hãy đưa ra câu trả lời khẳng định hoặc phủ định rõ ràng ở đầu câu, sau đó dẫn chứng bằng dữ kiện để làm rõ.
5. QUY TẮC TỐI THƯỢNG CHO DỮ LIỆU ĐA ĐIỀU KIỆN: Nếu trong DỮ LIỆU XÁC THỰC có dòng "XÁC NHẬN ĐÁP ÁN:...", bạn BẮT BUỘC phải liệt kê ngay danh sách đó làm kết quả. TUYỆT ĐỐI KHÔNG ĐƯỢC từ chối, KHÔNG ĐƯỢC nói "chưa đủ dữ liệu" hay "chưa có thông tin".
"""
    try:
        # Sử dụng nhiệt độ (temperature) 0.3 để câu văn mượt mà nhưng vẫn giữ độ chính xác
        response_text = await generate_ai_response(
            system_prompt="", 
            user_prompt=prompt, 
            temperature=0.3, 
            model_name=model_name
        )
        return clean_ai_response(response_text)
    except Exception as e:
        return f"⚠️ Lỗi tổng hợp tri thức: {str(e)}"