import os
import ollama
import httpx
from app.config import settings
from app.models.base_db import db

# ==========================================================
# HÀM SINH PHẢN HỒI VĂN BẢN (LLM GENERATION)
# ==========================================================
async def generate_ai_response(system_prompt, user_prompt, temperature=0.0, model_name=settings.MODEL_ID):
    """
    Điều phối gọi AI dựa trên tên mô hình:
    - Nếu là Gemini: Gọi qua Google AI Studio API (Sử dụng API Key cấu hình ở Admin).
    - Nếu là GPT (bắt đầu bằng gpt-): Gọi qua OpenAI API.
    - Nếu khác: Gọi qua Ollama (Local).
    """
    try:
        if "gemini" in model_name.lower():
            # --- 1. LẤY DANH SÁCH GEMINI API KEYS ---
            db_gemini_key = db.get_setting("gemini_api_key")
            if db_gemini_key and db_gemini_key.strip():
                primary_key = db_gemini_key
            else:
                primary_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")

            db_gemini_fallback = db.get_setting("gemini_fallback_keys")
            if db_gemini_fallback and db_gemini_fallback.strip():
                fallback_str = db_gemini_fallback
            else:
                fallback_str = getattr(settings, "GEMINI_FALLBACK_KEYS", None) or os.getenv("GEMINI_FALLBACK_KEYS")
            
            fallback_keys = []
            if fallback_str:
                if isinstance(fallback_str, str):
                    fallback_keys = [k.strip() for k in fallback_str.split(",") if k.strip()]
                elif isinstance(fallback_str, list):
                    fallback_keys = [str(k).strip() for k in fallback_str if str(k).strip()]
            
            # Làm sạch dấu nháy nếu có
            cleaned_fallback_keys = []
            for k in fallback_keys:
                if (k.startswith("'") and k.endswith("'")) or (k.startswith('"') and k.endswith('"')):
                    k = k[1:-1].strip()
                if k:
                    cleaned_fallback_keys.append(k)
            
            if primary_key and ((primary_key.startswith("'") and primary_key.endswith("'")) or (primary_key.startswith('"') and primary_key.endswith('"'))):
                primary_key = primary_key[1:-1].strip()

            keys_to_try = []
            if primary_key:
                keys_to_try.append(primary_key)
            keys_to_try.extend(cleaned_fallback_keys)
            
            if not keys_to_try:
                raise ValueError("Chưa cấu hình Google Gemini API Key trong hệ thống. Vui lòng vào trang Admin để thiết lập.")

            # --- 2. GỌI API GEMINI QUA HTTPX VỚI XOAY VÒNG KEY ---
            last_error = None
            for idx, api_key in enumerate(keys_to_try):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    
                    payload = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": user_prompt}
                                ]
                            }
                        ],
                        "generationConfig": {
                            "temperature": temperature,
                            "topP": 0.9,
                            "maxOutputTokens": 2048
                        }
                    }
                    if system_prompt:
                        payload["systemInstruction"] = {
                            "parts": [
                                {"text": system_prompt}
                            ]
                        }

                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            timeout=60.0
                        )
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        text_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        return text_response
                    else:
                        error_detail = response.text
                        try:
                            error_json = response.json()
                            error_detail = error_json.get("error", {}).get("message", response.text)
                        except Exception:
                            pass
                        raise Exception(f"HTTP {response.status_code}: {error_detail}")
                except Exception as e:
                    print(f"⚠️ Lỗi khi dùng Gemini API Key #{idx + 1}: {str(e)}")
                    last_error = e
                    continue # Thử key tiếp theo
            
            raise Exception(f"Tất cả các Gemini API Key đều lỗi hoặc hết lượt. Lỗi cuối cùng: {str(last_error)}")

        elif model_name.lower().startswith("gpt-"):
            # --- 3. GỌI API OPENAI GPT VỚI XOAY VÒNG KEY ---
            db_openai_key = db.get_setting("openai_api_key")
            if db_openai_key and db_openai_key.strip():
                primary_key = db_openai_key
            else:
                primary_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

            db_openai_fallback = db.get_setting("openai_fallback_keys")
            if db_openai_fallback and db_openai_fallback.strip():
                fallback_str = db_openai_fallback
            else:
                fallback_str = getattr(settings, "OPENAI_FALLBACK_KEYS", None) or os.getenv("OPENAI_FALLBACK_KEYS")
            
            fallback_keys = []
            if fallback_str:
                if isinstance(fallback_str, str):
                    fallback_keys = [k.strip() for k in fallback_str.split(",") if k.strip()]
                elif isinstance(fallback_str, list):
                    fallback_keys = [str(k).strip() for k in fallback_str if str(k).strip()]
            
            cleaned_fallback_keys = []
            for k in fallback_keys:
                if (k.startswith("'") and k.endswith("'")) or (k.startswith('"') and k.endswith('"')):
                    k = k[1:-1].strip()
                if k:
                    cleaned_fallback_keys.append(k)
            
            if primary_key and ((primary_key.startswith("'") and primary_key.endswith("'")) or (primary_key.startswith('"') and primary_key.endswith('"'))):
                primary_key = primary_key[1:-1].strip()

            keys_to_try = []
            if primary_key:
                keys_to_try.append(primary_key)
            keys_to_try.extend(cleaned_fallback_keys)
            
            if not keys_to_try:
                raise ValueError("Chưa cấu hình OpenAI API Key trong hệ thống. Vui lòng vào trang Admin để thiết lập.")

            last_error = None
            url = "https://api.openai.com/v1/chat/completions"
            for idx, api_key in enumerate(keys_to_try):
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    }
                    
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": user_prompt})

                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2048
                    }

                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers=headers,
                            timeout=60.0
                        )

                    if response.status_code == 200:
                        res_json = response.json()
                        return res_json["choices"][0]["message"]["content"]
                    else:
                        error_detail = response.text
                        try:
                            error_json = response.json()
                            error_detail = error_json.get("error", {}).get("message", response.text)
                        except Exception:
                            pass
                        raise Exception(f"HTTP {response.status_code}: {error_detail}")
                except Exception as e:
                    print(f"⚠️ Lỗi khi dùng OpenAI API Key #{idx + 1}: {str(e)}")
                    last_error = e
                    continue # Thử key tiếp theo
            
            raise Exception(f"Tất cả các OpenAI API Key đều lỗi hoặc hết lượt. Lỗi cuối cùng: {str(last_error)}")

        else:
            # --- 4. GỌI MÔ HÌNH CHẠY LOCAL QUA OLLAMA ---
            response = ollama.generate(
                model=model_name,
                system=system_prompt if system_prompt else "",
                prompt=user_prompt,
                options={"temperature": temperature, "top_p": 0.9}
            )
            return response["response"]

    except Exception as e:
        print(f"❌ [LLM PROVIDER ERROR] Lỗi hệ thống khi gọi AI ({model_name}): {str(e)}")
        return f"❌ Lỗi hệ thống khi gọi AI ({model_name}): {str(e)}"

# ==========================================================
# HÀM TẠO VECTOR (EMBEDDING GENERATION) - QUAN TRỌNG
# ==========================================================
def get_embedding(text):
    """
    Biến câu hỏi người dùng thành Vector để tìm kiếm ngữ nghĩa.
    SỬ DỤNG MÔ HÌNH TỪ CONFIG (BGE-M3) ĐỂ ĐẢM BẢO KHỚP 1024 CHIỀU VỚI NEO4J.
    """
    try:
        # Lấy tên mô hình nhúng từ trung tâm điều khiển settings (config.py)
        # Giá trị hiện tại: "bge-m3"
        model_name = settings.EMBEDDING_MODEL 
        
        # Thực hiện gọi Ollama để lấy vector
        response = ollama.embeddings(
            model=model_name, 
            prompt=text
        )
        
        # Trả về mảng số (Vector) kết quả
        return response["embedding"]
        
    except Exception as e:
        print(f"❌ [Lỗi tạo Embedding]: Không thể tạo vector với mô hình '{settings.EMBEDDING_MODEL}'.")
        print(f"👉 Chi tiết lỗi: {e}")
        print("💡 Gợi ý: Hãy kiểm tra xem Ollama đã được bật và đã chạy lệnh 'ollama pull bge-m3' chưa.")
        return None