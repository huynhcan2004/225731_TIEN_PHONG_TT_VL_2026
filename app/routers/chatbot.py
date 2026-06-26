"""
Module: app/routers/chatbot.py
Chức năng: Định nghĩa các API Endpoints cho hệ thống Chatbot AI.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
import secrets
from app.models.schemas import ChatRequest, TranslateRequest
from chatbot.services.chat_service import YHCTChatService
from app.config import settings
from app.security.security import get_current_user
from app.models.base_db import db

router = APIRouter(prefix="/chatbot", tags=["Hệ thống Trí tuệ Nhân tạo"])

# ==========================================================
# 🛡️ CƠ CHẾ BẢO MẬT
# ==========================================================

async def verify_internal_access(x_api_key: str = Header(None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.LARAVEL_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API Key.")
    return x_api_key

async def verify_admin_access(x_api_key: str = Header(None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.LARAVEL_API_KEY):
        raise HTTPException(status_code=403, detail="Forbidden.")
    return x_api_key

# ==========================================================
# 🚀 CÁC ĐƯỜNG DẪN API (ENDPOINTS)
# ==========================================================

# Gỡ bỏ response_model=ChatResponse tạm thời để FastAPI không tự động cắt mất trường graph_data
@router.post("/query")
async def ask_ai_specialist(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint truy vấn AI + Lấy dữ liệu GraphRAG.
    """
    user_id = current_user['id']
    try:
        COST_PER_QUERY = float(db.get_setting("cost_per_query", "1000.0"))
    except ValueError:
        COST_PER_QUERY = 1000.0 
    
    # Lấy session_id từ request (sẽ là None nếu là phiên chat mới)
    current_session_id = request.session_id
    
    if current_user['token_balance'] < COST_PER_QUERY:
        raise HTTPException(
            status_code=402, 
            detail="Số dư Token không đủ. Bạn cần nạp thêm để tiếp tục hội thoại."
        )

    try:
        # ✨ CẢI TIẾN 1: Truyền session_id vào và nhận lại ID phiên chat (mới hoặc cũ)
        current_session_id = db.save_chat_message(user_id, "user", request.message, session_id=current_session_id)
    except Exception as e:
        print(f"⚠️ Cảnh báo lưu lịch sử user: {e}")

    active_model = db.get_setting("active_model", "gemini-2.5-flash")
    chat_service = YHCTChatService(model_name=active_model)
    result = await chat_service.get_ai_response(
        user_query=request.message,
        user_id=user_id,
        lang=request.lang or "vi"
    )
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=result.get("answer")
        )

    # ✨ CẢI TIẾN: BÓC TÁCH VÀ TRUY VẤN NEO4J LINH HOẠT HƠN
    detected_plant = None
    graph_data = {"nodes": [], "links": []}
    
    answer_text = result.get("answer", "").lower()
    user_query_text = request.message.lower()

    # Danh sách từ khóa mồi (Mở rộng tùy theo 712 cây thuốc của huynh)
    keywords = ["ích mẫu", "chó đẻ", "nhân trần", "cà gai leo", "đinh lăng", "kim ngân", "cam thảo", "chỉ thiên"]
    for kw in keywords:
        if kw in answer_text or kw in user_query_text:
            detected_plant = kw
            break

    # ✨ CẢI TIẾN: TRUY VẤN THEO ĐÚNG CANONICAL_NAME CỦA HUYNH
    if detected_plant:
        print(f"🔍 [GRAPH DEBUG] Đang quét đồ thị cho: {detected_plant}")
        
        # Câu lệnh Cypher khớp với Log của huynh
        query = f"""
            MATCH (p)-[r]-(related)
            WHERE toLower(p.canonical_name) CONTAINS '{detected_plant.lower()}'
            RETURN p, type(r) as relationship, related LIMIT 40
        """
        try:
            neo_res = db.query_graph(query)
            
            if neo_res:
                nodes_map = {}
                for record in neo_res:
                    p_node = record['p']
                    rel_node = record['related']
                    
                    # Dùng canonical_name làm ID để hiển thị nhãn cho đẹp
                    p_id = p_node.get('canonical_name') or p_node.get('name') or "Unknown"
                    rel_id = rel_node.get('canonical_name') or rel_node.get('name') or "Unknown"
                    
                    # Thêm Node Chính (Màu Emerald)
                    if p_id not in nodes_map:
                        nodes_map[p_id] = True
                        graph_data['nodes'].append({
                            "id": p_id, 
                            "name": p_id, 
                            "group": 1, 
                            "val": 15 # Kích thước node
                        })
                        
                    # Thêm Node Liên quan (Màu Slate)
                    if rel_id not in nodes_map:
                        nodes_map[rel_id] = True
                        graph_data['nodes'].append({
                            "id": rel_id, 
                            "name": rel_id, 
                            "group": 2, 
                            "val": 10
                        })
                        
                    # Thêm Link (Mối quan hệ)
                    graph_data['links'].append({
                        "source": p_id, 
                        "target": rel_id,
                        "label": record['relationship']
                    })
                    
                print(f"✅ [GRAPH SUCCESS] Đã tìm thấy {len(graph_data['nodes'])} nodes.")
            else:
                # Nếu vẫn không ra, thử quét rộng hơn không dùng label Plant
                print(f"⚠️ [GRAPH WARNING] Không tìm thấy kết quả cho '{detected_plant}'. Kiểm tra lại dữ liệu Neo4j.")
        except Exception as e:
            print(f"❌ [GRAPH ERROR]: {e}")

    if result.get("answer"):
        try:
            # ✨ CẢI TIẾN 2: Truyền lại đúng current_session_id để lưu vào chung 1 luồng
            db.save_chat_message(user_id, "assistant", result.get("answer"), session_id=current_session_id)
        except Exception as e:
            print(f"⚠️ Cảnh báo lưu lịch sử bot: {e}")

    success = db.change_token_balance(
        user_id=user_id,
        amount=COST_PER_QUERY,
        description=f"Hỏi AI ({active_model})",
        tx_type='out'
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Lỗi xử lý giao dịch Token.")

    # Xử lý Metadata để đảm bảo không bị lỗi null ở Frontend
    resp_metadata = result.get("metadata", {})
    if not isinstance(resp_metadata, dict):
        resp_metadata = {}
        
    resp_metadata["plant_name"] = detected_plant
    resp_metadata["exec_time"] = result.get("exec_time", 0)

    # ✨ CẢI TIẾN 3: Đóng gói toàn bộ Dữ liệu gửi về Frontend, bao gồm cả session_id
    return {
        "session_id": current_session_id,
        "answer": result.get("answer"),
        "intent": result.get("intent", "Tra cứu"),
        "model_used": active_model,
        "tokens_charged": COST_PER_QUERY,
        "user_token_balance": db.get_user_balance(user_id),
        "metadata": resp_metadata,
        "graph_data": graph_data # ✨ Dữ liệu quan trọng nhất để vẽ đồ thị
    }

@router.get("/health", tags=["Giám sát"])
async def check_chatbot_health():
    try:
        from chatbot.llm_provider import ollama
        ollama.list()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.post("/clear-cache", tags=["Quản trị"])
async def clear_system_cache(admin_key: str = Depends(verify_admin_access)):
    chat_service = YHCTChatService()
    chat_service.reset_cache()
    return {"message": "Cache cleared."}    

@router.get("/config")
async def get_chatbot_config():
    """Lấy cấu hình mô hình AI mặc định đang được kích hoạt."""
    return {
        "active_model": db.get_setting("active_model", "gemini-2.5-flash")
    }

@router.get("/history")
async def get_chat_history_list(current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    history = db.get_recent_sessions(user_id)
    return {"history": history} 

@router.delete("/history/{chat_id}")
async def delete_chat_item(chat_id: int, current_user: dict = Depends(get_current_user)):
    success = db.delete_chat_session(chat_id, current_user['id'])
    if not success:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"message": "Deleted."}

@router.get("/history/session/{message_id}")
async def get_session_detail(message_id: int, current_user: dict = Depends(get_current_user)):
    messages = db.get_conversation_detail(message_id, current_user['id'])
    if not messages:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"messages": messages}

@router.post("/translate")
async def translate_chat_message(
    request: TranslateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Dịch tin nhắn chatbot sang ngôn ngữ đích sử dụng LLM.
    """
    active_model = db.get_setting("active_model", "gemini-2.5-flash")
    target_lang_name = "English" if request.target_lang == "en" else "Vietnamese"
    
    system_prompt = f"""
    You are an expert translator specializing in medical and traditional medicine terminology.
    Translate the provided text into {target_lang_name}.
    - Maintain the original Markdown formatting exactly.
    - Translate medical and herb terms accurately.
    - Output ONLY the translated text, without any introductory words or meta comments.
    """
    
    from chatbot.llm_provider import generate_ai_response
    try:
        translated_text = await generate_ai_response(
            system_prompt=system_prompt,
            user_prompt=request.text,
            temperature=0.3,
            model_name=active_model
        )
        return {"translated_text": translated_text.strip()}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dịch thuật thất bại: {str(e)}"
        )