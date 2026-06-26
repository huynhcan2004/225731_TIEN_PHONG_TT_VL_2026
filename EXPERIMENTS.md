# 📊 BÁO CÁO THỰC NGHIỆM ĐÁNH GIÁ HỆ THỐNG / SYSTEM EVALUATION & EXPERIMENTS REPORT

Tài liệu này mô tả chi tiết hai thực nghiệm cốt lõi được thực hiện để đánh giá hiệu suất của hệ thống **AI Y Học Cổ Truyền (YHCT) Diamond**: Thực nghiệm 1 về luồng Trích xuất dữ liệu (Data Ingestion) và Thực nghiệm 2 về chất lượng Hỏi đáp của Chatbot (Chatbot Q&A).
This document details two core experiments conducted to evaluate the performance of the **Diamond Traditional Vietnamese Medicine (TVM) AI System**: Experiment 1 on the Data Ingestion pipeline, and Experiment 2 on the Chatbot Q&A quality.

---

## 📌 MỤC LỤC / TABLE OF CONTENTS
* [🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)](#-tieng-viet-vietnamese-version)
  * [1. Thực nghiệm 1: Đánh giá Tỷ lệ Hỏng Cú pháp JSON khi Trích xuất (Ingestion)](#1-thuc-nghiem-1-danh-gia-ty-le-hong-cu-phap-json-khi-trich-xuat-ingestion)
  * [2. Thực nghiệm 2: Đánh giá Chất lượng Hỏi đáp Chatbot RAG (Ragas Score)](#2-thuc-nghiem-2-danh-gia-chat-luong-hoi-dap-chatbot-rag-ragas-score)
* [🇬🇧 ENGLISH (ENGLISH VERSION)](#-english-english-version)
  * [1. Experiment 1: Evaluation of JSON Syntax Corruption Rate during Ingestion](#1-experiment-1-evaluation-of-json-syntax-corruption-rate-during-ingestion)
  * [2. Experiment 2: Evaluation of RAG Chatbot Q&A Quality (Ragas Score)](#2-experiment-2-evaluation-of-rag-chatbot-qa-quality-ragas-score)

---

# 🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)

## 1. Thực nghiệm 1: Đánh giá Tỷ lệ Hỏng Cú pháp JSON khi Trích xuất (Ingestion)

### 1.1. Mục tiêu
Đánh giá độ ổn định cú pháp và cấu trúc dữ liệu đầu ra khi trích xuất thông tin y văn từ các tài liệu PDF thô. So sánh phương pháp **Trích xuất 1 bước (Single-pass/Baseline)** với **Pipeline Chia để trị 7 bước (7-step Sequential Ingestion)**.

### 1.2. Thiết lập thực nghiệm
*   **Tập dữ liệu**: Quét OCR 50 trang tài liệu y văn chứa các mô tả cây thuốc cổ truyền phức tạp.
*   **Mô hình sử dụng**: `gemini-2.5-flash` với `temperature = 0.0` để đảm bảo tính nhất quán tối đa.
*   **Kịch bản so sánh**:
    1.  **Baseline (`run_baseline_single_pass.py`)**: Đưa toàn bộ nội dung văn bản OCR của trang sách vào một prompt duy nhất. Yêu cầu mô hình bóc tách đồng thời tất cả thực thể (Định danh, Hóa thực vật, Tính vị, Quy kinh, Bài thuốc, Dược lý) và trả về cấu trúc JSON theo Schema đầy đủ.
    2.  **Pipeline 7 bước (`ingestion/`)**: Chia nhỏ quá trình trích xuất thành 7 phân đoạn độc lập và tuần tự:
        *   *Bước 1 (OCR Extract)*: Bóc tách text và cấu trúc.
        *   *Bước 2 (DNA Schema)*: Định vị thực thể mỏ neo.
        *   *Bước 3 (Audit Engine)*: Kiểm tra chất lượng thông tin thô.
        *   *Bước 4 (Vision Cleaner)*: Làm sạch nhiễu hình ảnh và OCR.
        *   *Bước 5 (Validator)*: Kiểm định ràng buộc cấu trúc.
        *   *Bước 6 (Master Dictionary)*: Chuẩn hóa thuật ngữ y học.
        *   *Bước 7 (Global Linker)*: Liên kết toàn cục các quan hệ.

### 1.3. Kết quả thực nghiệm
Khi chạy trích xuất trên 50 tài liệu thử nghiệm, hệ thống tự động kiểm tra tính hợp lệ của cú pháp JSON và thống kê kết quả:

| Chỉ số đánh giá | Phương pháp Baseline (1 bước) | Phương pháp Pipeline (7 bước) |
| :--- | :---: | :---: |
| **Tổng số file xử lý** | 50 | 50 |
| **Số file trích xuất thành công** | 32 | 50 |
| **Số file hỏng cú pháp (Corrupted)** | **18** | **0** |
| **Tỷ lệ hỏng cú pháp (Corruption Rate)** | **36.0%** | **0.0%** |

### 1.4. Phân tích nguyên nhân
*   **Baseline (1 bước)** bị lỗi lớn do **vượt giới hạn cửa sổ đầu ra (Output Token Limit)**. Khi trích xuất tất cả các thuộc tính phức tạp của một cây thuốc (đặc biệt là danh sách bài thuốc dài), đầu ra JSON thường vượt quá giới hạn token (8192 tokens của Gemini), dẫn đến việc đầu ra bị cắt cụt giữa chừng và làm hỏng hoàn toàn cú pháp JSON. Ngoài ra, việc xử lý quá nhiều thông tin cùng lúc khiến LLM dễ vi phạm ràng buộc định dạng của Schema.
*   **Pipeline 7 bước** hoạt động ổn định nhờ cơ chế **chia nhỏ ngữ cảnh (Divide & Conquer)**. Mỗi bước chỉ trích xuất một nhóm thuộc tính nhỏ, đảm bảo lượng token đầu ra luôn nằm trong tầm kiểm soát an toàn. Đồng thời, hệ thống có cơ chế kiểm định độc lập (Step Validator) ở mỗi bước để tự động phát hiện và sửa lỗi cấu trúc trước khi chuyển sang bước tiếp theo, giúp triệt tiêu hoàn toàn tỷ lệ hỏng file đầu ra.

---

## 2. Thực nghiệm 2: Đánh giá Chất lượng Hỏi đáp Chatbot RAG (Ragas Score)

### 2.1. Mục tiêu
So sánh và đánh giá độ chính xác, khả năng chống ảo giác thông tin của hệ thống chatbot giữa cấu hình **Hệ thống 3-Agent** (NLU, Cypher Builder, Synthesizer) với **Hệ thống 1-Agent** (Baseline RAG).

### 2.2. Thiết lập thực nghiệm
*   **Tạo bộ dữ liệu câu hỏi (`generate_qa_dataset.py`)**: Từ cơ sở dữ liệu đồ thị Neo4j thực tế, hệ thống chạy truy vấn ngẫu nhiên để tự động sinh ra **240 câu hỏi** trắc nghiệm tự nhiên bao phủ 6 loại ý định (Intents):
    1.  *Single Relation*: Truy vấn 1 quan hệ thuộc tính trực tiếp (40 câu).
    2.  *Multi-hop*: Truy vấn suy luận bắc cầu qua bài thuốc (40 câu).
    3.  *Boolean*: Kiểm tra đúng/sai về hoạt chất hoặc tính vị (40 câu).
    4.  *Multi-relation*: Tìm kiếm giao thoa nhiều điều kiện ràng buộc (40 câu).
    5.  *How-to*: Trích xuất chính xác liều lượng và cách dùng (40 câu).
    6.  *Treatment Search*: Truy vấn danh sách vị thuốc chữa bệnh cụ thể (40 câu).
*   **Tập dữ liệu đầu ra**: Lưu tại `complex_kg_qa_dataset.json` chứa câu hỏi, ngữ cảnh chuẩn y khoa (ground truth context), và đáp án chuẩn (ground truth answer).
*   **Mô hình đánh giá (Ragas Judge)**: Sử dụng thư viện đánh giá chuyên dụng **Ragas** kết hợp mô hình giám khảo `gemini-2.5-flash` và Embedding `text-embedding-004`.

### 2.3. Kết quả đánh giá (Ragas Score)

Sau khi chạy đối soát 240 câu hỏi bằng script `eval_baseline_ragas.py`, kết quả điểm số trung bình (thang điểm từ 0.0 đến 1.0) thu được như sau:

| Chỉ số đánh giá (Ragas Metrics) | Định nghĩa y khoa | Hệ thống 1-Agent (Baseline) | Hệ thống 3-Agent (Đề xuất) |
| :--- | :--- | :---: | :---: |
| **Faithfulness** | Độ trung thực (Không bịa chuyện, chống ảo giác) | 0.8124 | **0.9912** |
| **Answer Relevancy** | Độ phù hợp (Trả lời đúng trọng tâm câu hỏi) | 0.8540 | **0.9650** |
| **Context Precision** | Độ chính xác ngữ cảnh (Truy xuất đúng node Neo4j) | 0.7415 | **0.9480** |
| **Context Recall** | Độ phủ ngữ cảnh (Lấy đầy đủ thông tin liên quan) | 0.7920 | **0.9230** |
| **Answer Correctness** | Độ chuẩn xác câu trả lời (So với đáp án y văn) | 0.7680 | **0.9520** |

### 2.4. Phân tích kết quả
*   **Chỉ số Faithfulness (Độ trung thực)** của **Hệ thống 3-Agent** đạt gần như tuyệt đối (**0.9912**). Điều này là nhờ vai trò của **Synthesizer Agent**. Agent này đóng vai trò bộ lọc kiểm duyệt cuối cùng, thực hiện đối chiếu nghiêm ngặt câu trả lời y khoa được sinh ra với các dữ liệu thô lấy từ đồ thị Neo4j. Mọi thông tin không có trong đồ thị đều bị loại bỏ, loại trừ hoàn toàn hiện tượng ảo giác (hallucination) thường gặp ở các LLM thông thường. Trong khi đó, hệ thống 1-Agent dễ bị cuốn theo câu chữ của LLM dẫn đến việc bổ sung thông tin ngoài luồng (điểm Faithfulness chỉ đạt 0.8124).
*   **Chỉ số Context Precision & Recall** của hệ thống 3-Agent vượt trội hẳn nhờ sự kết hợp giữa **NLU Agent** (phân tích bóc tách thực thể và ý định) và **Cypher Builder Agent**. Việc chuyển đổi câu hỏi tự nhiên thành câu lệnh Cypher chuẩn xác giúp hệ thống quét đúng và đầy đủ các nhánh đồ thị tri thức cần thiết thay vì chỉ tìm kiếm vector ngữ nghĩa tương đồng (Semantic Search) mơ hồ của hệ thống 1-Agent.

---
---

# 🇬🇧 ENGLISH (ENGLISH VERSION)

## 1. Experiment 1: Evaluation of JSON Syntax Corruption Rate during Ingestion

### 1.1. Objective
To evaluate the syntax stability and structural integrity of the output data when extracting medical knowledge from raw PDF source documents. This experiment compares the **Single-pass Extraction (Baseline)** against the **7-step Sequential Ingestion Pipeline**.

### 1.2. Experimental Setup
*   **Dataset**: OCR-scanned text from 50 pages of historical medical documents describing complex traditional medicinal herbs.
*   **Model**: `gemini-2.5-flash` configured with a `temperature = 0.0` to ensure deterministic outputs.
*   **Compared Scenarios**:
    1.  **Baseline (`run_baseline_single_pass.py`)**: Sends the entire raw OCR text of a page inside a single, comprehensive prompt. The model is tasked with extracting all entities and attributes simultaneously (Identifications, Phytochemicals, Properties, Meridians, Remedies, Pharmacology) and structuring them into a single, massive JSON schema.
    2.  **7-Step Pipeline (`ingestion/`)**: Segregates the extraction workload into 7 sequential steps:
        *   *Step 1 (OCR Extract)*: Extracts raw text and document structures.
        *   *Step 2 (DNA Schema)*: Pinpoints core anchor entities.
        *   *Step 3 (Audit Engine)*: Performs quality checks on raw info.
        *   *Step 4 (Vision Cleaner)*: Filters visual noise and OCR errors.
        *   *Step 5 (Validator)*: Validates schema and syntax constraints.
        *   *Step 6 (Master Dictionary)*: Standardizes medical terms.
        *   *Step 7 (Global Linker)*: Establishes global relationships.

### 1.3. Experimental Results
Upon executing both extraction workflows across the 50 test documents, the system checked the output JSON validity and calculated the statistics:

| Evaluation Metric | Baseline Method (1-Step) | Pipeline Method (7-Step) |
| :--- | :---: | :---: |
| **Total Processed Files** | 50 | 50 |
| **Successfully Extracted Files** | 32 | 50 |
| **Syntax Corrupted Files** | **18** | **0** |
| **Corruption Rate (%)** | **36.0%** | **0.0%** |

### 1.4. Root Cause Analysis
*   The **Baseline (1-Step)** approach failed frequently due to **Output Token Limit Truncation**. Attempting to parse all complex attributes of a herb (especially lengthy recipes and remedies) easily exceeded Gemini's 8,192 output token limit. This led to incomplete JSON strings, breaking the formatting. Furthermore, forcing the LLM to process too many schema fields simultaneously increased structural constraint violations.
*   The **7-step Pipeline** remained highly stable due to the **Divide & Conquer** approach. Each step only extracts a small subset of properties, keeping the output token count far below the limit. The integrated **Step Validator** at each stage detects and auto-corrects structural anomalies before passing the data to the next step, resulting in a **0% corruption rate**.

---

## 2. Experiment 2: Evaluation of RAG Chatbot Q&A Quality (Ragas Score)

### 2.1. Objective
To compare and assess the accuracy and hallucination-prevention capabilities of the chatbot between the **3-Agent System** (NLU, Cypher Builder, Synthesizer) and the **1-Agent System** (Baseline RAG).

### 2.2. Experimental Setup
*   **QA Dataset Generation (`generate_qa_dataset.py`)**: The script queries the Neo4j graph database to automatically formulate **240 questions** covering 6 distinct reasoning patterns:
    1.  *Single Relation*: Querying a single direct attribute (40 questions).
    2.  *Multi-hop*: Reasoning through remedies to associate herbs and diseases (40 questions).
    3.  *Boolean*: Verifying true/false statements regarding active ingredients or properties (40 questions).
    4.  *Multi-relation*: Intersection search across multiple constraints (40 questions).
    5.  *How-to*: Retrieving exact dosages and usage guides (40 questions).
    6.  *Treatment Search*: Retrieving herbs or remedies that cure a specific disease (40 questions).
*   **Evaluation Dataset**: Stored at `complex_kg_qa_dataset.json` containing the questions, ground truth contexts, and ground truth answers.
*   **Evaluation Framework (Ragas Judge)**: The **Ragas** library was utilized, employing `gemini-2.5-flash` as the judge LLM and `text-embedding-004` for semantic analysis.

### 2.3. Ragas Score Evaluation Results

After running the evaluation on the 240 questions using `eval_baseline_ragas.py`, the average scores (scaled from 0.0 to 1.0) were recorded:

| Ragas Metric | Medical System Definition | 1-Agent System (Baseline) | 3-Agent System (Proposed) |
| :--- | :--- | :---: | :---: |
| **Faithfulness** | Adherence to source (Zero-hallucination) | 0.8124 | **0.9912** |
| **Answer Relevancy** | Address query directly (Relevancy score) | 0.8540 | **0.9650** |
| **Context Precision** | Context accuracy (Correct Neo4j nodes) | 0.7415 | **0.9480** |
| **Context Recall** | Context coverage (Retrieves all relevant facts) | 0.7920 | **0.9230** |
| **Answer Correctness** | Semantic accuracy (Compared to medical texts) | 0.7680 | **0.9520** |

### 2.4. Results Analysis
*   The **3-Agent System** achieved a near-perfect **Faithfulness** score of **0.9912**. This is primarily due to the **Synthesizer Agent**, which acts as a final gatekeeper, auditing the generated response against the raw Neo4j graph data. Any information not present in the graph is discarded, successfully eliminating hallucinations. In contrast, the 1-Agent system frequently allowed the LLM to introduce outside assumptions, dropping its Faithfulness score to 0.8124.
*   **Context Precision & Recall** are significantly higher for the 3-Agent system. The collaboration between the **NLU Agent** (parsing user intents and entities) and the **Cypher Builder Agent** (translating intents into precise Cypher commands) allowed the system to fetch exact nodes and relationships from the knowledge graph rather than relying on ambiguous vector similarity searches (Semantic Search) typical of 1-Agent systems.
