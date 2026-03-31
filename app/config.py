# app/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env để bảo mật thông tin nhạy cảm
load_dotenv()

class Settings(BaseSettings):
    """
    Quản lý cấu hình tập trung cho toàn bộ hệ thống YHCT Diamond.
    Áp dụng Pydantic để đảm bảo kiểu dữ liệu và tính nhất quán.
    """

    # ==========================================================
    # 1. THÔNG TIN HỆ THỐNG (SYSTEM IDENTIFICATION)
    # ==========================================================
    PROJECT_NAME: str = "ChatBot-YHCT-Knowledge-Graph"
    VERSION: str = "1.0.0"
    MODEL_ID: str = os.getenv("MODEL_ID", "gemini-2.0-flash")

    # ==========================================================
    # 2. BẢO MẬT & XÁC THỰC (SECURITY & AUTHENTICATION)
    # ==========================================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_2026_yhct_diamond")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 ngày cho JWT

    # --- MỚI: API Key dành cho Laravel Backend ---
    # Laravel sẽ gửi key này trong Header 'X-API-KEY' để xác thực Server-to-Server
    LARAVEL_API_KEY: str = os.getenv("LARAVEL_API_KEY", "yhct_diamond_internal_key_2026")

    # ==========================================================
    # 3. CƠ SỞ DỮ LIỆU ĐỒ THỊ (NEO4J DATABASE)
    # ==========================================================
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PWD: str = os.getenv("NEO4J_PASSWORD", "12345678")
    NEO4J_DB_NAME: str = os.getenv("NEO4J_DB_NAME", "yhctchatbot")

    # ==========================================================
    # 4. CẤU HÌNH CLOUD & AI (GOOGLE CLOUD & GEMINI API)
    # ==========================================================
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", 
        "config/yhct-knowledge-graph.json"
    )
    GEMINI_KEY: str = os.getenv("GEMINI_API_KEY")
    
    # --- MỚI: Cấu hình Ollama dành cho Local Embedding ---
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # ==========================================================
    # 5. TÀI NGUYÊN ĐẦU VÀO (INGESTION SOURCE ASSETS)
    # ==========================================================
    PDF_INPUT_PATH: str = "storage/raw/Những cây thuốc và vị thuốc Việt Nam.pdf"
    TOC_JSON_PATH: str = "storage/metadata/toc_part_II.json"
    ONTOLOGY_PATH: str = "storage/metadata/ontology.json"
    PAGE_OFFSET: int = 15

    # ==========================================================
    # 6. QUẢN LÝ DỮ LIỆU THEO KIẾN TRÚC MEDALLION (DATA LAYERS)
    # ==========================================================
    DIR_BRONZE_RAW: str = "storage/bronze/ocr_extracted"
    
    DIR_SILVER_MAPPED: str = "storage/silver/schema_mapped"
    DIR_SILVER_AUDITED: str = "storage/silver/audit_verified"
    
    DIR_GOLD_VALIDATED: str = "storage/gold/validated_entities"
    DIR_GOLD_LINKED: str = "storage/gold/final_linked_graph"
    
    DIR_QUARANTINE: str = "storage/quarantine/failed_validation"

    # ==========================================================
    # 7. TỪ ĐIỂN TRI THỨC TOÀN CỤC (GLOBAL KNOWLEDGE DICT)
    # ==========================================================
    DIR_DICT_MASTER: str = "storage/metadata/master_dictionary"
    FILE_DICT_FINAL: str = "storage/metadata/master_dictionary/synonym_map_final.json"

    # ==========================================================
    # 8. NHẬT KÝ VÀ KIỂM SOÁT CHẤT LƯỢNG (LOGS & EVALUATION)
    # ==========================================================
    DIR_LOGS_AUDIT: str = "logs/ai_audits"
    DIR_LOGS_DEBUG_IMG: str = "logs/debug_images"
    
    FILE_VAL_REPORT: str = "logs/validation_metrics.jsonl"
    FILE_GRAPH_REPORT: str = "storage/evaluation/graph_integrity_report.md"

    # --- MỚI: Thư mục dành riêng cho Evaluation (Step 10) ---
    DIR_EVALUATION: str = "storage/evaluation"

    # ==========================================================
    # 9. QUẢN LÝ TIẾN TRÌNH (PIPELINE CHECKPOINTS)
    # ==========================================================
    CHECKPOINT_MAIN: str = "config/checkpoints/main_pipeline.json"
    CHECKPOINT_DICT: str = "config/checkpoints/dict_progress.json"

# Khởi tạo đối tượng settings dùng chung
settings = Settings()