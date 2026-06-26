"""
Module: chatbot/services/chat_service.py
Chức năng: Lớp dịch vụ điều phối (Orchestration Layer) cho Chatbot YHCT.
Nhiệm vụ: 
- Kết nối các thành phần NLU, Database và LLM Provider.
- Thực thi quy trình GraphRAG: Phân tích -> Truy vấn Đồ thị -> Tổng hợp tri thức.
- Xử lý lỗi hệ thống và đảm bảo tính nhất quán của dữ liệu trả về.
"""
from chatbot.utils.token_counter import count_tokens
import time
from typing import Dict, Any, Optional
from app.config import settings
from app.models.base_db import db
from chatbot.nlu_engine import extract_intent_and_entities, summarize_answer

class YHCTChatService:
    """
    Lớp dịch vụ chính xử lý logic hội thoại thông minh dựa trên Đồ thị tri thức.
    Tuân thủ nguyên tắc Single Responsibility: Chỉ tập trung vào việc điều phối luồng dữ liệu chat.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Khởi tạo dịch vụ chat với cấu hình mô hình AI.
        
        Args:
            model_name (str, optional): Tên mô hình AI (Gemini hoặc Qwen). 
                                        Nếu không truyền, sẽ lấy mặc định từ settings.
        """
        self.model_name = model_name or settings.MODEL_ID
        self.db = db

    async def get_ai_response(self, user_query: str, user_id: int, lang: str = "vi") -> Dict[str, Any]:
        """
        Thực thi quy trình GraphRAG hoàn chỉnh để trả lời câu hỏi của người dùng.
        
        Quy trình:
        1. Gọi NLU Engine để bóc tách Intent (Ý định) và Keywords (Thực thể).
        2. Sinh câu lệnh Cypher tương ứng với Intent.
        3. Truy vấn vào Neo4j Graph Database.
        4. Tổng hợp dữ liệu thô từ đồ thị thành câu trả lời văn phong chuyên gia YHCT.

        Args:
            user_query (str): Câu hỏi tự nhiên của người dùng.
            user_id (int): ID của người dùng đang đăng nhập (bắt buộc).
            lang (str): Ngôn ngữ giao diện ("vi" hoặc "en").

        Returns:
            Dict[str, Any]: Kết quả bao gồm câu trả lời, ý định, thực thể và thời gian xử lý.
        """
        start_time = time.time()
        
        # Kiểm tra kết nối cơ sở dữ liệu trước khi thực hiện
        if not self.db:
            return {
                "answer": "Hệ thống cơ sở dữ liệu đồ thị hiện không khả dụng. Vui lòng thử lại sau.",
                "status": "error",
                "exec_time": 0
            }

        try:
            # In thông tin gỡ lỗi ra CMD
            print("\n" + "="*60)
            print(f"🤖 [CHATBOT QUERY] Đang sử dụng mô hình AI: '{self.model_name}'")
            print(f"💬 [CHATBOT QUERY] Câu hỏi người dùng: '{user_query}' | Lang: '{lang}'")
            print("="*60 + "\n")

            # --- BƯỚC 1: PHÂN TÍCH NGỮ NGHĨA (NLU) ---
            # Chuyển ngôn ngữ tự nhiên thành Intent và Metadata máy hiểu được
            parsed_data = await extract_intent_and_entities(
                user_query, 
                model_name=self.model_name,
                lang=lang
            )
            
            if parsed_data and parsed_data.get("cypher"):
                cypher_query = parsed_data["cypher"]
                
                # 🔥 THÊM DÒNG NÀY VÀO ĐỂ SOI:
                print("\n" + "="*50)
                print(f"🔍 [DEBUG] USER QUERY: {user_query}")
                print(f"🤖 [DEBUG] INTENT: {parsed_data['intent']}")
                print(f"🚀 [DEBUG] EXECUTING CYPHER:\n{cypher_query}")
                print("="*50 + "\n")
                
            if not parsed_data or not parsed_data.get("cypher"):
                return {
                    "answer": "Tôi rất tiếc nhưng tôi không thể phân tích được ý định trong câu hỏi của bạn. Bạn có thể diễn đạt lại rõ ràng hơn được không?",
                    "intent": "UNKNOWN",
                    "status": "warning",
                    "exec_time": round(time.time() - start_time, 2)
                }

            intent = parsed_data["intent"]
            cypher_query = parsed_data["cypher"]
            k1 = parsed_data.get("k1", "")
            k2 = parsed_data.get("k2", "")
            vector_data = parsed_data.get("vector")

            # --- BƯỚC 2: TRUY XUẤT ĐỒ THỊ TRI THỨC (GRAPH RETRIEVAL) ---
            # Thực thi câu lệnh Cypher đã được sinh ra từ NLU Engine
            try:
                params = {"query_vector": vector_data} if vector_data else {}
                # ✅ ĐÃ SỬA: Đổi từ db.query thành db.query_graph
                graph_results = self.db.query_graph(cypher_query, params=params)
            except Exception as db_error:
                print(f"❌ [Database Execution Error]: {str(db_error)}")
                return {
                    "answer": "Đã xảy ra lỗi trong quá trình truy xuất đồ thị tri thức.",
                    "status": "error",
                    "exec_time": round(time.time() - start_time, 2)
                }

            # --- BƯỚC 3: TỔNG HỢP VÀ ĐÚC KẾT (KNOWLEDGE SUMMARIZATION) ---
            # Chuyển đổi mảng JSON thô từ Neo4j thành văn bản tự nhiên mượt mà
            final_answer = await summarize_answer(
                user_query=user_query,
                intent=intent,
                graph_data=graph_results,
                k1=k1,
                k2=k2,
                model_name=self.model_name,
                lang=lang
            )
            execution_duration = round(time.time() - start_time, 2)

            # --- BƯỚC 4: TÍNH TOÁN VÀ TRỪ TOKEN (BILLING PROCESS) ---
            # Tính tổng token: Câu hỏi + Câu lệnh Cypher + Dữ liệu DB + Câu trả lời
            total_text_processed = f"{user_query} {cypher_query} {str(graph_results)} {final_answer}"
            total_tokens = count_tokens(total_text_processed)
            
            # Giả sử quy đổi 1 token = 1 đơn vị (bạn có thể thay đổi tỷ giá)
            tokens_charged = float(total_tokens)
            
            # ✅ ĐÃ SỬA: Sử dụng user_id được truyền trực tiếp từ Router để đảm bảo tính cá nhân hóa
            try:
                self.db.change_token_balance(
                    user_id=user_id, 
                    amount=tokens_charged, 
                    description=f"Truy vấn Chatbot: {intent}", 
                    tx_type='out'
                )
                # Lấy số dư mới nhất để trả về Frontend
                user_balance = self.db.get_user_balance(user_id) 
            except Exception as e:
                print(f"⚠️ Lỗi trừ token cho user {user_id}: {e}")
                user_balance = 0.0

            # Trả về kết quả cuối cùng đã bao gồm tham số Billing
            return {
                "answer": final_answer,
                "intent": intent,
                "entities": [k1, k2] if k2 else [k1],
                "exec_time": execution_duration,
                "model_used": self.model_name,
                "status": "success",
                "metadata": {
                    "records_found": len(graph_results) if graph_results else 0,
                    "cypher_executed": cypher_query,
                    "raw_data": graph_results
                },
                "tokens_charged": tokens_charged,
                "user_token_balance": user_balance
            }

        except Exception as system_error:
            # Xử lý lỗi ngoại lệ toàn cục để tránh sụp đổ ứng dụng
            print(f"💥 [Critical System Error]: {str(system_error)}")
            return {
                "answer": f"Hệ thống gặp sự cố không mong muốn: {str(system_error)}",
                "status": "critical_error",
                "exec_time": round(time.time() - start_time, 2)
            }

    def reset_cache(self):
        """
        Xóa bộ nhớ đệm nếu cần thiết để làm mới dữ liệu hội thoại.
        """
        from chatbot.nlu_engine import QUERY_CACHE
        QUERY_CACHE.clear()
        print("🧹 [Service] Đã làm sạch bộ nhớ đệm truy vấn.")