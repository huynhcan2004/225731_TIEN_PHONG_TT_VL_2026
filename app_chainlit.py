import time
import json
import chainlit as cl
from chainlit.input_widget import Select

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from app.models.base_db import db
from chatbot.nlu_engine import extract_intent_and_entities, summarize_answer

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(label="Bài thuốc của vị thuốc", message="Ích mẫu có bài thuốc nào?", icon="/public/favicon.ico"),
        cl.Starter(label="Giao thoa điều kiện", message="Thuốc nào tính hàn chữa sưng đau?", icon="/public/favicon.ico"),
        cl.Starter(label="Xác nhận", message="Vị thuốc Chỉ thiên có mang đặc điểm Tính hàn không?", icon="/public/favicon.ico"),
        cl.Starter(label="Truy vấn nhảy bước", message="Bài thuốc chứa vị thuốc Chó đẻ răng cưa thì thường dùng để chữa bệnh gì?", icon="/public/favicon.ico")
    ]

@cl.on_chat_start
async def start():
    # Thêm Menu cấu hình để người dùng có thể đổi Model ngay trên giao diện Web
    await cl.ChatSettings(
        [
            Select(
                id="llm_model",
                label="Tùy chọn Trí tuệ Nhân tạo",
                values=["qwen2.5-coder:7b", "gemini-2.5-flash"],
                initial_index=0,
            )
        ]
    ).send()

    try:
        # Cấu hình Avatar chuyên nghiệp
        await cl.Avatar(name="Chuyên Gia YHCT", url="https://api.dicebear.com/7.x/bottts/svg?seed=YHCT&backgroundColor=059669").send()
        await cl.Avatar(name="User", url="https://api.dicebear.com/7.x/avataaars/svg?seed=User").send()
    except Exception: 
        pass
    
    cl.user_session.set("llm_model", "qwen2.5-coder:7b")
    
    # Text chào mừng tích hợp placeholder giao diện (Đăng nhập/Thanh toán)
    welcome_message = f"""
🌿 **Chào mừng đến với Nền tảng Chuyên Gia YHCT Diamond v10.0** 🌿

Tôi là trợ lý AI chuyên môn cao được hậu thuẫn bởi Knowledge Graph và hệ thống GraphRAG.
Bạn có thể vào mục **Cài đặt (Settings)** ở góc màn hình để chuyển đổi giữa mô hình Local (Qwen) và Cloud (Gemini).

---
*🔐 Tính năng (Comming Soon):*
- `[ Đăng nhập / Đăng ký ]` (Đang phát triển)
- `[ Quản lý Gói Thanh toán / Token ]` (Đang phát triển)
---

Hãy chọn các câu hỏi gợi ý bên dưới hoặc đặt câu hỏi bất kỳ về Dược liệu, Bài thuốc, Công năng nhé!
    """

    if not db:
        await cl.Message(content="❌ Lỗi kết nối Cơ sở dữ liệu Neo4j. Vui lòng kiểm tra lại dịch vụ.").send()
    else:
        await cl.Message(content=welcome_message.strip(), author="Chuyên Gia YHCT").send()

@cl.on_settings_update
async def setup_agent(settings_dict):
    # Cập nhật model khi người dùng thay đổi lựa chọn trong màn hình Settings
    selected_model = settings_dict["llm_model"]
    cl.user_session.set("llm_model", selected_model)
    await cl.Message(content=f"🔄 Hệ thống đã chuyển sang sử dụng mô hình: **{selected_model}**", author="System").send()

@cl.on_message
async def main(message: cl.Message):
    current_model = cl.user_session.get("llm_model", "qwen2.5-coder:7b")
    
    if not db: 
        return await cl.Message(content="⚠️ Lỗi CSDL. Không thể thực hiện truy vấn lúc này.").send()

    user_input = message.content.strip()
    start_time = time.time()
    
    # BƯỚC 1: NLU (Ý định & Từ khóa)
    async with cl.Step(name=f"1. Phân tích NLU (Engine: {current_model})") as step_intent:
        parsed_data = await extract_intent_and_entities(user_input, model_name=current_model)
        if not parsed_data or not parsed_data.get("cypher"):
            step_intent.is_error = True
            return await cl.Message(content="⚠️ Hệ thống AI không thể phân tích được ý định trong câu hỏi của bạn. Vui lòng thử lại với cách diễn đạt khác.", author="Chuyên Gia YHCT").send()
        
        intent = parsed_data["intent"]
        cypher = parsed_data["cypher"]
        step_intent.output = f"• Ý định (Intent): **{intent}**\n• Thực thể 1: **{parsed_data['k1']}**\n• Thực thể 2: **{parsed_data['k2']}**"

    # BƯỚC 2: Truy xuất Neo4j
    async with cl.Step(name="2. Quét Đồ thị (Schema-Aware Cypher)") as step_db:
        try:
            params = {"query_vector": parsed_data.get("vector")} if parsed_data.get("vector") else {}
            results = db.query_graph(cypher, params=params)
            json_data = json.dumps(results[:5], indent=2, ensure_ascii=False) if results else "[]"
            
            step_db.output = f"```cypher\n{cypher}\n```\n**Tìm thấy {len(results)} records.**\n<details><summary>Xem Dữ Liệu Thô (Raw JSON)</summary>\n```json\n{json_data}\n```\n</details>"
        except Exception as e:
            step_db.is_error = True
            step_db.output = f"Lỗi: {str(e)}"
            return await cl.Message(content="⚠️ Đã xảy ra lỗi trong quá trình truy xuất đồ thị tri thức.", author="Chuyên Gia YHCT").send()

    # BƯỚC 3: AI Đúc Kết
    async with cl.Step(name=f"3. Dịch & Đúc kết ({current_model})") as step_answer:
        answer = await summarize_answer(
            user_input, 
            intent, 
            results, 
            parsed_data.get("k1", ""), 
            parsed_data.get("k2", ""),
            model_name=current_model
        )
        step_answer.output = "Quá trình tổng hợp hoàn tất."

    exec_time = round(time.time() - start_time, 2)
    
    # Trả về kết quả cuối cùng cho người dùng
    await cl.Message(
        content=f"{answer}\n\n---\n⏱ Thời gian xử lý: *{exec_time}s* | 🤖 AI Engine: *{current_model}*", 
        author="Chuyên Gia YHCT"
    ).send()