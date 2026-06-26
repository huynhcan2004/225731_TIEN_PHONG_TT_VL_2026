# 🌿 DỰ ÁN: HỆ THỐNG TRI THỨC Y HỌC CỔ TRUYỀN (YHCT DIAMOND KNOWLEDGE GRAPH)

## 1. TỔNG QUAN DỰ ÁN
Dự án **YHCT Diamond** là một hệ thống Trí tuệ Nhân tạo kết hợp Đồ thị Tri thức (Knowledge Graph) và RAG (Retrieval-Augmented Generation) nhằm số hóa, trích xuất và hỏi đáp các kiến thức y dược cổ truyền. Dữ liệu cốt lõi được lấy từ các tài liệu y văn kinh điển (ví dụ: cuốn "Những cây thuốc và vị thuốc Việt Nam" của Đỗ Tất Lợi).

Mục tiêu của hệ thống là tự động đọc hiểu PDF (OCR), trích xuất thông tin đa chiều (Định danh, Hóa thực vật, Bài thuốc, Dược lý), lưu trữ dưới dạng Đồ thị tri thức Vector (vKG) trên Neo4j, và cung cấp một Chatbot có khả năng suy luận logic y khoa chính xác, hoàn toàn loại bỏ "ảo giác" (hallucination).

---

## 2. KIẾN TRÚC VÀ CÁC THÀNH PHẦN CHÍNH
Hệ thống được xây dựng theo kiến trúc **Medallion** (Bronze -> Silver -> Gold) và được chia thành các phân hệ chính sau:

### 2.1. Phân hệ Trích xuất Dữ liệu (Ingestion Pipeline)
- **`step1_ocr_extract.py`**: Trích xuất văn bản từ file PDF sử dụng Google Document AI. Sử dụng mô hình LLM (Gemini) để parse văn bản OCR thành cấu trúc JSON sơ khởi (Bronze Data). Áp dụng các quy tắc "Diamond Rules" để không tóm tắt, giữ nguyên văn và xâu chuỗi bài thuốc.
- **`step2_retry_errors.py`**: Cơ chế cứu hộ và vá lỗi (Diamond Pipeline). Hệ thống quét các lỗi log, tự động chia nhỏ prompt theo từng ngữ cảnh cụ thể (DNA, Hoạt chất, Lâm sàng/Bài thuốc, Dược lý) và gọi lại API để phục hồi dữ liệu bị hỏng, sau đó hợp nhất (merge) kết quả.
- **`run_baseline_single_pass.py`**: Một phiên bản trích xuất All-In-One (1 prompt duy nhất để lấy toàn bộ). Phục vụ làm Baseline cho việc so sánh hiệu suất thuật toán.

### 2.2. Phân hệ Lưu trữ Đồ thị & Vector (Neo4j Loader)
- **`step8_neo4j_loader.py`**: Trình nạp (Loader) chịu trách nhiệm xóa sạch dữ liệu cũ và bơm dữ liệu chuẩn (Gold Linked) vào cơ sở dữ liệu Neo4j.
- Tạo và thiết lập **Vector Index** và **Full-text Index**.
- Sử dụng **Ollama** với mô hình `bge-m3` (1024 chiều) để nhúng (embed) dữ liệu thực thể. Có cơ chế Cache Embedding để tối ưu hóa và tiết kiệm chi phí API.

### 2.3. Phân hệ Chatbot AI & NLU Engine
- **`nlu_engine.py`**: Bộ não phân tích ngữ nghĩa (NLU) cho câu hỏi của người dùng. Chuyển đổi câu hỏi tự nhiên thành các `Intent` (Ý định) và trích xuất `Keywords`, từ đó xây dựng câu lệnh truy vấn đồ thị Cypher tương ứng. Tích hợp prompt "Ngự Y Kim Cương" để sinh ra câu trả lời dựa trên kết quả Neo4j mà KHÔNG bịa chuyện (Zero-Hallucination).
- **`llm_provider.py`**: Lớp trừu tượng cung cấp kết nối chung tới các dịch vụ LLM. Hỗ trợ gọi LLM đám mây qua **Google Vertex AI** (Gemini) hoặc chạy mô hình nội bộ qua **Ollama**.

### 2.4. Phân hệ Đánh giá (Evaluation - JSON Corruption Testing)
- **`eval_extraction_methods.py`**: Sử dụng bộ kiểm tra cú pháp và độ toàn vẹn cấu trúc dữ liệu để đánh giá tỷ lệ hỏng cú pháp JSON và lỗi định dạng dữ liệu khi truy vấn giữa phương pháp Baseline (Single-pass) và phương pháp Pipeline (Multi-agent).
- Thống kê các chỉ số: **Syntax Compliance** (Độ ổn định cú pháp JSON), **Property Integrity** (Độ toàn vẹn thuộc tính) và **Query Reliability** (Độ tin cậy khi thực thi truy vấn). Tự động xuất báo cáo ra định dạng JSON và TXT.
- **Tài liệu chi tiết**: Xem thêm [EVALUATION_AND_EXPERIMENTS.md](file:///d:/Thuc_Tap_2026/225731_TIEN_PHONG_TT_VL_2026/EVALUATION_AND_EXPERIMENTS.md) để biết thêm chi tiết về thiết kế thực nghiệm, sinh dữ liệu tự động và chỉ số Ragas Score.

### 2.5. Tiện ích hệ thống (Utilities)
- **`utils/project_tree.py`**: Tập lệnh in ra sơ đồ cấu trúc thư mục của dự án trên Terminal, tự động bỏ qua các thư mục môi trường và log không cần thiết để tạo báo cáo đẹp mắt.

---

## 3. CÔNG NGHỆ SỬ DỤNG SỬ DỤNG
- **Ngôn ngữ lập trình:** Python
- **Mô hình Ngôn ngữ Lớn (LLM):** Google Vertex AI (Gemini 2.0 Flash / Pro)
- **Local AI & Nhúng (Embeddings):** Ollama (Mô hình `bge-m3` - Vector 1024 chiều)
- **OCR & Parse Tài liệu:** Google Document AI, PyMuPDF (`fitz`)
- **Cơ sở dữ liệu:** Neo4j (Graph Database kết hợp Vector Search)
- **Quản lý cấu trúc dữ liệu:** Google GenAI Types (Structured JSON outputs)

---

## 4. LUỒNG HOẠT ĐỘNG CHUẨN (DATA FLOW)
1. **PDF Ingestion:** Sách PDF -> Document AI OCR -> LLM Extract (Bronze JSON).
2. **Cứu hộ & Chia để trị (Divide & Conquer):** Text thô -> Tách mảng (Tính vị, Dược lý, Bài thuốc...) -> Retry Error LLM -> Hợp nhất JSON (Silver/Gold JSON).
3. **Neo4j Graph Building:** Load Gold JSON -> Sinh Embedded Vector qua Ollama -> Nạp Thực Thể (Nodes) và Quan Hệ (Edges) vào Neo4j.
4. **Truy vấn RAG:** User hỏi -> NLU Engine phân tích Intent -> Generate Cypher / Vector Search -> Rút trích tri thức từ Neo4j -> LLM tổng hợp ra câu trả lời y khoa chuẩn xác.
5. **JSON Corruption Testing:** Quét và kiểm tra tính hợp lệ của cấu trúc file JSON tạo ra giữa các phương pháp trích xuất khác nhau, đánh giá tỷ lệ hỏng cú pháp gây cản trở truy vấn.