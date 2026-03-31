import os
import ollama
import vertexai
from vertexai.generative_models import GenerativeModel
from app.config import settings

# Khởi tạo Vertex AI
try:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
    vertexai.init(project="yhct-knowledge-graph", location="us-central1")
except Exception as e:
    print(f"⚠️ Cảnh báo: Không thể khởi tạo Vertex AI (Gemini). Lỗi: {e}")

async def generate_ai_response(system_prompt, user_prompt, temperature=0.0, model_name=settings.MODEL_ID):
    try:
        if "gemini" in model_name.lower():
            # Gọi Gemini qua Vertex AI
            model = GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt if system_prompt else None
            )
            response = await model.generate_content_async(
                user_prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.9
                }
            )
            return response.text
        else:
            # Gọi Ollama (Qwen Local)
            response = ollama.generate(
                model=model_name,
                system=system_prompt if system_prompt else "",
                prompt=user_prompt,
                options={"temperature": temperature, "top_p": 0.9}
            )
            return response["response"]
    except Exception as e:
        return f"Lỗi gọi AI ({model_name}): {str(e)}"

def get_embedding(text):
    try:
        # Sử dụng mô hình nhúng mặc định từ cấu hình hệ thống
        return ollama.embeddings(model="nomic-embed-text", prompt=text)["embedding"]
    except Exception as e:
        print(f"Lỗi tạo Embedding: {e}")
        return None