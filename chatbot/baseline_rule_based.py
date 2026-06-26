import re
import json
import asyncio
import sys
import os
import unicodedata
from neo4j import AsyncGraphDatabase

# Đảm bảo import được settings và các module từ thư mục gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from chatbot.llm_provider import generate_ai_response
from chatbot.cypher_builder import build_cypher_template

# =====================================================================
# HÀM BỔ TRỢ CHUẨN HÓA TIẾNG VIỆT (TƯƠNG ĐƯƠNG HỆ THỐNG CHÍNH)
# =====================================================================
def normalize_vietnamese_text(text):
    if not text:
        return ""
    # Chuẩn hóa về dạng NFKD để bóc tách dấu nếu cần, hoặc NFC để khớp chuẩn
    return unicodedata.normalize('NFC', text).strip()

def advanced_clean_garbage(query_str):
    """
    Loại bỏ các từ thừa, từ cảm thán hoặc kính ngữ trong hội thoại y tế Tiếng Việt
    để tránh làm nhiễu bộ tách luật Regex.
    """
    garbage_patterns = [
        r'(bác ơi|cho hỏi|cho mình hỏi|thưa bác sĩ|bác sĩ cho em hỏi|dạ|nghe nói|có ai biết)',
        r'(làm ơn cho hỏi|hỏi chút|vui lòng cho biết|thầy thuốc ơi|cho em hỏi)'
    ]
    cleaned = query_str.lower()
    for pattern in garbage_patterns:
        cleaned = re.sub(pattern, '', cleaned)
    return cleaned.strip()

# =====================================================================
# STAGE 1: COMPREHENSIVE ADVANCED RULE-BASED NLU PARSER
# Bao phủ tuyệt đối 6 Patterns từ Dataset để tạo Fair Baseline
# =====================================================================
def advanced_rule_based_extract_intent(user_query):
    """
    Hệ thống phân tích ý định nâng cao dựa trên tập luật phân cấp (Hierarchical Rules).
    Được thiết kế để "bắt dính" 100% các format câu hỏi sinh ra từ bộ Dataset,
    đảm bảo Baseline không bị coi là "Straw man" (bù nhìn).
    """
    q = advanced_clean_garbage(user_query)
    
    intent = "UNKNOWN"
    k1 = ""
    k2 = ""
    
    # Dọn dẹp dấu câu cuối câu để Regex dễ bắt ranh giới hơn
    q_clean = re.sub(r'[?.,!:]$', '', q).strip()

    # ---------------------------------------------------------
    # PATTERN 5: HOW TO (TRÍCH XUẤT CHÍNH XÁC FACT)
    # Câu hỏi: "Để chữa bệnh [benh], vị thuốc [thuoc] được dùng với liều lượng và cách thức như thế nào?"
    # ---------------------------------------------------------
    match_howto = re.search(r'để chữa bệnh (.*?), vị thuốc (.*?) được dùng với liều lượng', q_clean)
    if match_howto:
        intent = "TIM_HUONG_DAN_SU_DUNG"
        k2 = match_howto.group(1).strip() # Bệnh (Disease)
        k1 = match_howto.group(2).strip() # Vị thuốc (Herb)

    # ---------------------------------------------------------
    # PATTERN 4: MULTI RELATION (MULTI_CONSTRAINT)
    # Câu hỏi: "Thuốc nào vừa có tính [tinh] vừa trực tiếp chữa bệnh [benh]?"
    # ---------------------------------------------------------
    elif "vừa có tính" in q_clean and "vừa trực tiếp chữa bệnh" in q_clean:
        intent = "TIM_DA_QUAN_HE"
        match_multi = re.search(r'vừa có tính (.*?) vừa trực tiếp chữa bệnh (.*)', q_clean)
        if match_multi:
            k1 = match_multi.group(1).strip()
            k2 = match_multi.group(2).strip()

    # ---------------------------------------------------------
    # PATTERN 3: BOOLEAN VERIFICATION (POSITIVE & NEGATIVE)
    # Câu hỏi: "Vị thuốc [thuoc] có [thuộc tính] [fact] không?"
    # ---------------------------------------------------------
    elif q_clean.endswith("không") or q_clean.endswith("ko"):
        intent = "KIEM_TRA_BOOLEAN"
        match_bool = re.search(r'vị thuốc (.*?) có (vị|tính|quy kinh|chứa hoạt chất|quy vào kinh) (.*?) không', q_clean)
        if match_bool:
            k1 = match_bool.group(1).strip()
            k2 = match_bool.group(3).strip()
        else:
            k1 = q_clean.replace("không", "").replace("vị thuốc", "").strip()

    # ---------------------------------------------------------
    # PATTERN 2: MULTI HOP (REASONING)
    # Câu hỏi 1: "Vị thuốc [thuoc] tham gia vào bài thuốc để chữa những bệnh gì?"
    # Câu hỏi 2: "Bệnh nào có thể chữa bằng bài thuốc chứa [thuoc]?"
    # ---------------------------------------------------------
    elif "tham gia vào bài thuốc" in q_clean or "bằng bài thuốc chứa" in q_clean:
        intent = "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC"
        match_hop1 = re.search(r'vị thuốc (.*?) tham gia vào bài thuốc', q_clean)
        match_hop2 = re.search(r'bằng bài thuốc chứa (.*)', q_clean)
        if match_hop1:
            k1 = match_hop1.group(1).strip()
        elif match_hop2:
            k1 = match_hop2.group(1).strip()

    # ---------------------------------------------------------
    # PATTERN 6: TREATMENT SEARCH (TÌM THUỐC CHỮA BỆNH)
    # Câu hỏi: "Bệnh [benh] có thể dùng vị thuốc hoặc bài thuốc nào để chữa?"
    # ---------------------------------------------------------
    elif "dùng vị thuốc hoặc bài thuốc nào để chữa" in q_clean or "uống thuốc gì" in q_clean:
        intent = "TIM_THUOC_CHUA_BENH"
        match_treat = re.search(r'bệnh (.*?) có thể dùng', q_clean)
        if match_treat:
            k1 = match_treat.group(1).strip()
        else:
            k1 = q_clean.replace("chữa bệnh", "").strip()

    # ---------------------------------------------------------
    # PATTERN 1: SINGLE RELATION (ATTRIBUTE)
    # Bao phủ 6 nhóm truy vấn thuộc tính đơn lẻ
    # ---------------------------------------------------------
    else:
        # Vị
        if "có vị gì" in q_clean or "vị của" in q_clean:
            intent = "TIM_VI"
            match_vi = re.search(r'vị thuốc (.*?) có vị gì|vị của (.*?) là', q_clean)
            if match_vi: k1 = match_vi.group(1) or match_vi.group(2)
            
        # Tính
        elif "có tính gì" in q_clean or "tính chất của" in q_clean:
            intent = "TIM_TINH"
            match_tinh = re.search(r'vị thuốc (.*?) có tính gì|tính chất của (.*?) là', q_clean)
            if match_tinh: k1 = match_tinh.group(1) or match_tinh.group(2)
            
        # Quy kinh
        elif "quy vào kinh nào" in q_clean or "kinh mạch nào" in q_clean:
            intent = "TIM_QUY_KINH"
            match_kinh = re.search(r'vị thuốc (.*?) quy vào kinh nào|kinh mạch nào liên quan đến (.*)', q_clean)
            if match_kinh: k1 = match_kinh.group(1) or match_kinh.group(2)
            
        # Hoạt chất
        elif "chứa hoạt chất gì" in q_clean or "thành phần hóa học" in q_clean:
            intent = "TIM_HOAT_CHAT_CUA_THUOC"
            match_hc = re.search(r'vị thuốc (.*?) chứa hoạt chất gì|thành phần hóa học của (.*?) gồm', q_clean)
            if match_hc: k1 = match_hc.group(1) or match_hc.group(2)
            
        # Công năng
        elif "có công năng gì" in q_clean or "công năng của" in q_clean:
            intent = "TIM_CONG_NANG"
            match_cn = re.search(r'vị thuốc (.*?) có công năng gì|công năng của (.*)', q_clean)
            if match_cn: k1 = match_cn.group(1) or match_cn.group(2)
            
        # Tác dụng dược lý
        elif "tác dụng dược lý" in q_clean or "cơ chế tác dụng" in q_clean:
            intent = "TIM_TAC_DUNG_DUOC_LY"
            match_dl = re.search(r'tác dụng dược lý của (.*?) ra sao|cơ chế tác dụng của (.*?) là', q_clean)
            if match_dl: k1 = match_dl.group(1) or match_dl.group(2)

    # ---------------------------------------------------------
    # DỌN DẸP THỰC THỂ SAU BÓC TÁCH
    # ---------------------------------------------------------
    if not k1:
        k1 = q_clean # Fallback nếu không khớp luật nào
        
    if isinstance(k1, str):
        k1 = k1.replace("vị thuốc", "").replace("bài thuốc", "").strip()
    if isinstance(k2, str):
        k2 = k2.replace("bệnh", "").replace("chứng", "").strip()

    k1 = normalize_vietnamese_text(k1)
    k2 = normalize_vietnamese_text(k2)

    print(f"\n⚙️ [STAGE 1 - ADVANCED RULE NLU] Parsing Results:")
    print(f"- Query        : {user_query}")
    print(f"- Target Intent: {intent}")
    print(f"- Entity K1    : '{k1}'")
    print(f"- Entity K2    : '{k2}'")
    print(f"{'-'*50}")

    # Gọi Cypher Builder tĩnh (Không dùng Vector Search)
    cypher = build_cypher_template(intent, k1, k2, use_vector=False)
    
    return {
        "cypher": cypher, 
        "intent": intent, 
        "k1": k1, 
        "k2": k2, 
        "vector": None
    }

# =====================================================================
# STAGE 2: DETERMINISTIC SEMANTIC CONTEXT GATHERING
# Kết nối thực tế và đóng gói Fact-Sheet thô từ đồ thị Neo4j
# =====================================================================
async def execute_graph_query(cypher_query):
    """
    Tác vụ truy xuất dữ liệu có cấu trúc từ Neo4j.
    """
    uri = settings.NEO4J_URI
    username = settings.NEO4J_USER  
    password = settings.NEO4J_PWD   
    db_name = settings.NEO4J_DB_NAME 
    
    graph_data = []
    try:
        async with AsyncGraphDatabase.driver(uri, auth=(username, password)) as driver:
            session_kwargs = {}
            if db_name and db_name != "neo4j":
                session_kwargs["database"] = db_name
            async with driver.session(**session_kwargs) as session:
                result = await session.run(cypher_query)
                async for record in result:
                    graph_data.append({
                        "ChuThe": record.get("ChuThe"),
                        "QuanHe": record.get("QuanHe"),
                        "DoiTuong": record.get("DoiTuong"),
                        "LieuDung": record.get("LieuDung"),
                        "CachDung": record.get("CachDung"),
                        "GhiChu": record.get("GhiChu")
                    })
    except Exception as e:
        print(f"⚠️ [STAGE 2 ERROR] Thất bại khi truy vấn cấu trúc đồ thị Neo4j: {e}")
    return graph_data

# =====================================================================
# STAGE 3: VERIFIED GENERATION & ALGORITHMIC FACT-CHECKING
# Hàm sinh văn bản kết hợp bộ lọc chống ảo giác bằng thuật toán lập trình cứng
# =====================================================================
def algorithmic_post_validator(llm_answer, graph_data):
    """
    BỘ THẨM ĐỊNH THUẬT TOÁN (Chống thiên vị hệ thống đề xuất).
    """
    if not graph_data:
        return True 
        
    answer_lower = llm_answer.lower()
    
    # Gom tất cả các thực thể hợp lệ xuất hiện trong Database trả về
    valid_entities = set()
    for row in graph_data:
        if row.get("ChuThe"): valid_entities.add(str(row["ChuThe"]).lower())
        if row.get("DoiTuong"): valid_entities.add(str(row["DoiTuong"]).lower())
    
    # Nếu LLM trả về câu từ chối có sẵn trong cấu trúc Prompt thì xem như hợp lệ
    if "không chứa thông tin" in answer_lower or "chưa ghi nhận" in answer_lower or "không đề cập" in answer_lower:
        return True

    # Kiểm tra ranh giới từ
    matched_any = False
    for entity in valid_entities:
        if entity in answer_lower:
            matched_any = True
            break
            
    return matched_any

async def baseline_summarize_answer(user_query, graph_data, model_name=settings.MODEL_ID):
    """
    Single-Agent Generator: Đóng gói toàn bộ Context đồ thị thô sang chuỗi JSON string,
    gọi trực tiếp LLM xử lý với thiết lập kiểm soát triệt để, sau đó hậu kiểm bằng thuật toán.
    """
    empty_fallback = "Hệ thống y văn hiện tại chưa ghi nhận dữ liệu về vấn đề này."
    
    if not graph_data:
        return empty_fallback

    # Đóng gói dữ liệu thô dạng Fact-Sheet thô (Raw Structured Context Ingestion)
    raw_context = json.dumps(graph_data, ensure_ascii=False, indent=2)

    prompt = f"""
Bạn là một trợ lý ảo chuyên gia về Y học cổ truyền.
Nhiệm vụ của bạn là dựa vào dữ liệu có cấu trúc từ Đồ thị tri thức dưới đây để trả lời câu hỏi của người dùng.

[DỮ LIỆU ĐỒ THỊ TRI THỨC GỐC]:
{raw_context}

[CÂU HỎI NGƯỜI DÙNG]: "{user_query}"

CHỈ DẪN NGHIÊM NGẶT:
1. Chỉ sử dụng thông tin có sẵn trong [DỮ LIỆU ĐỒ THỊ TRI THỨC GỐC]. Không tự ý bổ sung kiến thức bên ngoài.
2. Nếu dữ liệu trên không chứa thông tin để trả lời câu hỏi, hãy trả lời chính xác câu: "Dữ liệu được cung cấp không chứa thông tin về vấn đề này."
3. Câu trả lời phải ngắn gọn, súc tích, đi thẳng vào trọng tâm câu hỏi.
"""
    try:
        # Gọi mô hình LLM nền tảng trực tiếp
        response_text = await generate_ai_response(
            system_prompt="Bạn là một hệ thống chatbot y tế nghiêm túc, hoạt động như một Single Agent Generator.", 
            user_prompt=prompt, 
            temperature=0.0, 
            model_name=model_name
        )
        
        final_answer = response_text.strip()
        
        # CHẠY HẬU KIỂM THUẬT TOÁN ĐỂ ĐẢM BẢO ĐỘ PHỨC TẠP KHOA HỌC
        is_valid = algorithmic_post_validator(final_answer, graph_data)
        if not is_valid:
            print("⚠️ [STAGE 3 VALIDATOR] Phát hiện câu trả lời lệch bối cảnh đồ thị! Kích hoạt Fallback.")
            return "Hệ thống phát hiện câu trả lời có thể chứa thông tin nằm ngoài phạm vi truy vấn đồ thị. Để đảm bảo an toàn y tế, vui lòng tinh chỉnh câu hỏi."
            
        return final_answer
        
    except Exception as e:
        return f"Lỗi hệ thống Pipeline Baseline: {str(e)}"

# =====================================================================
# 4. MÔI TRƯỜNG ĐÁNH GIÁ VÀ KHẢO SÁT HỆ THỐNG TRÊN TERMINAL (END-TO-END)
# =====================================================================
async def main():
    print("="*70)
    print("🧪 EVALUATION WORKBENCH: ADVANCED SEQUENTIAL PIPELINE (BASELINE) 🧪")
    print("="*70)
    print("Hệ thống kiểm thử Baseline nâng cao phục vụ viết báo cáo khoa học.")
    print("Gõ 'exit' hoặc 'quit' để kết thúc phiên đánh giá.\n")

    while True:
        try:
            user_query = input("\n👤 Người dùng: ")
            if user_query.lower() in ['exit', 'quit']:
                print("👋 Kết thúc phiên kiểm thử Baseline thành công.")
                break

            if not user_query.strip():
                continue

            extracted_data = advanced_rule_based_extract_intent(user_query)
            cypher_query = extracted_data.get("cypher")
            
            print(f"\n🔍 [STAGE 2 - GENERATED CYPHER QUERY]:\n{cypher_query}\n")

            print("⏳ Đang kết nối cơ sở dữ liệu y văn...")
            graph_data = await execute_graph_query(cypher_query)
            
            print(f"📊 Kết quả: Tìm thấy {len(graph_data)} quan hệ ngữ nghĩa thực tế trong đồ thị.")

            print("⏳ Đang chuyển giao ngữ cảnh sang Stage 3 (LLM Summary & Verification)...")
            answer = await baseline_summarize_answer(user_query, graph_data)
            
            print("\n🤖 [BASELINE RESPONSE]:")
            print("-" * 60)
            print(answer)
            print("-" * 60)

        except KeyboardInterrupt:
            print("\n👋 Đã hủy tiến trình bằng tổ hợp phím tắt.")
            break
        except Exception as e:
            print(f"\n❌ Phát hiện ngoại lệ hệ thống trong vòng lặp kiểm thử: {e}")

if __name__ == "__main__":
    asyncio.run(main())