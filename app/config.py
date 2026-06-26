import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Quản lý cấu hình tập trung cho toàn bộ hệ thống YHCT Diamond.
    Kết hợp luồng Ingestion (OCR/Neo4j) và luồng Web (FastAPI/Auth/Fintech).
    Áp dụng Pydantic v2 để đảm bảo Type Safety và tự động nạp Environment Variables.
    """

    # ==========================================================
    # 1. THÔNG TIN HỆ THỐNG (SYSTEM IDENTIFICATION)
    # ==========================================================
    PROJECT_NAME: str = "ChatBot-YHCT-Knowledge-Graph"
    VERSION: str = "1.0.0"
    MODEL_ID: str = "gemini-2.5-flash"

    # ==========================================================
    # 2. BẢO MẬT & XÁC THỰC (SECURITY & AUTHENTICATION)
    # ==========================================================
    # Sử dụng JWT_SECRET_KEY để khớp với logic trong app/security/security.py
    JWT_SECRET_KEY: str = "default_secret_key_2026_yhct_diamond"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 giờ

    # API Key dành cho xác thực Server-to-Server (Laravel)
    LARAVEL_API_KEY: str = "yhct_diamond_internal_key_2026"

    # Gmail của Admin hệ thống để gán quyền tự động khi đăng nhập bằng Google
    ADMIN_EMAIL: Optional[str] = None

    # ==========================================================
    # 3. CƠ SỞ DỮ LIỆU HYBRID (NEO4J & SQLITE)
    # ==========================================================
    # Neo4j Database (Tri thức đồ thị)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PWD: str = "12345678"
    NEO4J_DB_NAME: str = "yhctchatbot"

    # SQLite Database (Xác thực & Fintech)
    SQLITE_DB_PATH: str = "yhct_database.db"

    # Cấu hình SMTP Email (Hỗ trợ & Liên hệ)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ==========================================================
    # 4. CẤU HÌNH GOOGLE CLOUD & AI API
    # ==========================================================
    # Gemini AI Key
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_FALLBACK_KEYS: Optional[str] = None

    # OpenAI API Key
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_FALLBACK_KEYS: Optional[str] = None

    # Google Application Credentials (File JSON key)
    GOOGLE_APPLICATION_CREDENTIALS: str = "config/yhct-knowledge-graph.json"

    # Google OAuth 2.0 (Dùng cho Đăng nhập người dùng)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"

    # Cấu hình Ollama (Dành cho Local Embedding nếu cần)
    EMBEDDING_MODEL: str = "bge-m3"

    # ==========================================================
    # 5. HỆ THỐNG THANH TOÁN (FINTECH - SEPAY)
    # ==========================================================
    # API Key để đối soát Webhook từ SePay
    SEPAY_API_KEY: Optional[str] = None
    SECRET_XOR_KEY: int = 0x5EAFB 
    NAME_WEB: str = "yhct_chatbot_graph"

    # ==========================================================
    # 6. TÀI NGUYÊN ĐẦU VÀO (INGESTION SOURCE ASSETS)
    # ==========================================================
    PDF_INPUT_PATH: str = "storage/raw/Những cây thuốc và vị thuốc Việt Nam.pdf"
    TOC_JSON_PATH: str = "storage/metadata/toc_part_II.json"
    ONTOLOGY_PATH: str = "storage/metadata/ontology.json"
    PAGE_OFFSET: int = 15

    # ==========================================================
    # 7. QUẢN LÝ DỮ LIỆU THEO KIẾN TRÚC MEDALLION (DATA LAYERS)
    # ==========================================================
    DIR_BRONZE_RAW: str = "storage/bronze/ocr_extracted"

    DIR_SILVER_MAPPED: str = "storage/silver/schema_mapped"
    DIR_SILVER_AUDITED: str = "storage/silver/audit_verified"

    DIR_GOLD_VALIDATED: str = "storage/gold/validated_entities"
    DIR_GOLD_LINKED: str = "storage/gold/final_linked_graph"

    DIR_QUARANTINE: str = "storage/quarantine/failed_validation"

    # ==========================================================
    # 8. TỪ ĐIỂN TRI THỨC TOÀN CỤC (GLOBAL KNOWLEDGE DICT)
    # ==========================================================
    DIR_DICT_MASTER: str = "storage/metadata/master_dictionary"
    FILE_DICT_FINAL: str = "storage/metadata/master_dictionary/synonym_map_final.json"

    # ==========================================================
    # 9. NHẬT KÝ VÀ KIỂM SOÁT CHẤT LƯỢNG (LOGS & EVALUATION)
    # ==========================================================
    DIR_LOGS_AUDIT: str = "logs/ai_audits"
    DIR_LOGS_DEBUG_IMG: str = "logs/debug_images"

    FILE_VAL_REPORT: str = "logs/validation_metrics.jsonl"
    FILE_GRAPH_REPORT: str = "storage/evaluation/graph_integrity_report.md"

    # Thư mục dành riêng cho Evaluation (Step 10)
    DIR_EVALUATION: str = "storage/evaluation"

    # ==========================================================
    # 10. QUẢN LÝ TIẾN TRÌNH (PIPELINE CHECKPOINTS)
    # ==========================================================
    CHECKPOINT_MAIN: str = "config/checkpoints/main_pipeline.json"
    CHECKPOINT_DICT: str = "config/checkpoints/dict_progress.json"

    # ==========================================================
    # 11. ĐƯỜNG DẪN BỔ SUNG CHO LUỒNG EVALUATION & INGESTION
    # ==========================================================
    # Thư mục A/B Testing Baseline
    DIR_BASELINE_EVAL_OUT: str = "storage/baseline_evaluation/output"
    DIR_OCR_MERGED_PLANT_TEXTS: str = "storage/silver1/merged_plant_texts"

    # Thư mục kiểm tra lỗi & retry
    DIR_SILVER_TEST1: str = "storage/silver/test1"
    FILE_RETRY_ERROR_LOG: str = "storage/silver/test/test_retry_log.txt"

    # Nhật ký sửa đổi validator (Step 5)
    DIR_VAL_REPAIR_LOGS: str = "logs/step5_repair_logs"

    # Báo cáo kiểm toán Tính - Vị - Quy Kinh
    FILE_TINH_VI_KINH_AUDIT_REPORT: str = "logs/tinh_vi_kinh_audit_report.txt"

    # ==========================================================
    # CẤU HÌNH TỰ ĐỘNG NẠP .ENV (PYDANTIC V2)
    # ==========================================================
    # model_config thay thế hoàn toàn cho class Config của Pydantic v1
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Khởi tạo đối tượng settings duy nhất để sử dụng toàn cục
settings = Settings()