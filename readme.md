# 🌿 HỆ THỐNG TRỢ LÝ AI Y HỌC CỔ TRUYỀN DIAMOND (GRAPHRAG CHATBOT)
## 🌿 DIAMOND TRADITIONAL VIETNAMESE MEDICINE AI ASSISTANT (GRAPHRAG CHATBOT)

---

# 🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)

## 📌 MỤC LỤC
1. [Giới Thiệu Chung](#-giới-thiệu-chung)
2. [Phần 1: Hướng Dẫn Cài Đặt & Triển Khai](#phần-1-hướng-dẫn-cài-đặt--triển-khai)
   - [1. Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
   - [2. Khởi tạo môi trường ảo](#2-khởi-tạo-môi-trường-ảo)
   - [3. Cài đặt thư viện](#3-cài-đặt-thư-viện)
   - [4. Cấu hình biến môi trường (.env)](#4-cấu-hình-biến-môi-trường-env)
   - [5. Khởi chạy hệ thống ở môi trường cục bộ (Local)](#5-khởi-chạy-hệ-thống-ở-môi-trường-cục-bộ-local)
   - [6. Triển khai trên Server thực tế (Production / VPS)](#6-triển-khai-trên-server-thực-tế-production--vps)
3. [Phần 2: Hướng Dẫn Sử Dụng](#phần-2-hướng-dẫn-sử-dụng)
   - [1. Cách thức truy cập (Local vs Server)](#1-cách-thức-truy-cập-local-vs-server)
   - [2. Đăng nhập OAuth 2.0](#2-đăng-nhập-oauth-20)
   - [3. Hệ thống Chatbot 3-Agent GraphRAG](#3-hệ-thống-chatbot-3-agent-graphrag)
   - [4. Bản đồ tri thức tương tác (Graph Explorer)](#4-bản-đồ-tri-thức-tương-tác-graph-explorer)
   - [5. Quản trị hệ thống & Fintech](#5-quản-trị-hệ-thống--fintech)
4. [Tài Liệu Thực Nghiệm & Đánh Giá](file:///d:/Thuc_Tap_2026/225731_TIEN_PHONG_TT_VL_2026/EVALUATION_AND_EXPERIMENTS.md)

---

## 📖 GIỚI THIỆU CHUNG
Hệ thống **AI Y học Cổ truyền Diamond** là một ứng dụng đột phá kết hợp giữa Đồ thị tri thức (Knowledge Graph) trên nền tảng đám mây **Neo4j AuraDB** và công nghệ **GraphRAG (Retrieval-Augmented Generation)**. Hệ thống giúp người dùng tra cứu chính xác các thông tin về vị thuốc, bài thuốc cổ truyền, cơ chế tác động và tính vị quy kinh của y học cổ truyền một cách minh bạch, chống ảo giác thông tin từ mô hình ngôn ngữ lớn (LLM).

---

## 🛠 PHẦN 1: HƯỚNG DẪN CÀI ĐẶT & TRIỂN KHAI

### 1. Yêu cầu hệ thống
Để đảm bảo hệ thống vận hành ổn định, môi trường cài đặt cần đáp ứng các điều kiện sau:
* **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux (Ubuntu 20.04+).
* **Python**: Phiên bản **Python 3.10+** trở lên.
* **Ollama**: Đã cài đặt và đang chạy dưới local (cổng mặc định `11434`) để chạy mô hình nhúng `bge-m3` và LLM cục bộ như `qwen2.5-coder:7b` (nếu cần).
* **Neo4j**: Tài khoản hoặc instance **Neo4j Aura Cloud** để lưu trữ đồ thị tri thức y học cổ truyền.

### 2. Khởi tạo môi trường ảo
Sử dụng môi trường ảo giúp cô lập các thư viện của dự án, tránh xung đột hệ thống.

* **Trên hệ điều hành Windows (CMD/PowerShell):**
  ```bash
  # Tạo môi trường ảo venv
  python -m venv venv

  # Kích hoạt môi trường ảo (PowerShell)
  .\venv\Scripts\Activate.ps1

  # Kích hoạt môi trường ảo (Command Prompt)
  .\venv\Scripts\activate.bat
  ```

* **Trên hệ điều hành Linux / macOS:**
  ```bash
  # Tạo môi trường ảo venv
  python3 -m venv venv

  # Kích hoạt môi trường ảo
  source venv/bin/activate
  ```

### 3. Cài đặt thư viện
Sau khi đã kích hoạt môi trường ảo, thực hiện cài đặt toàn bộ các thư viện được liệt kê trong `requirements.txt`:

```bash
# Cập nhật pip lên phiên bản mới nhất
python -m pip install --upgrade pip

# Cài đặt các thư viện cốt lõi của dự án
pip install -r requirements.txt

# Cài đặt bổ sung thư viện PyMuPDF phục vụ phân đoạn và xử lý file PDF y văn thô
pip install PyMuPDF
```

> [!NOTE]
> Thư viện `PyMuPDF` (được import dưới tên `fitz`) cực kỳ quan trọng cho luồng Ingestion, giúp trích xuất nội dung văn bản và cấu trúc bảng từ các tài liệu PDF y văn cổ truyền (ví dụ: cuốn *"Những cây thuốc và vị thuốc Việt Nam"*).

### 4. Cấu hình biến môi trường (.env)
Tạo một file có tên `.env` tại thư mục gốc của dự án và khai báo các thông số cấu hình kết nối như mẫu dưới đây:

```env
# ==========================================
# 1. DATABASE CONFIGURATION (NEO4J & SQLITE)
# ==========================================
# Cấu hình kết nối đồ thị đám mây Neo4j Aura Cloud
NEO4J_URI=bolt+ssc://2931e82e.databases.neo4j.io
NEO4J_USER=2931e82e
NEO4J_PWD=Whuaas6RDU7mTsOZj_Z2QaliWkcPJ5-KNwa73_ZMfkE
NEO4J_DB_NAME=2931e82e

# Đường dẫn tệp SQLite quản lý người dùng & giao dịch Fintech
SQLITE_DB_PATH=yhct_database.db

# ==========================================
# 2. AI CONFIGURATION & API KEYS
# ==========================================
# API Key chính cho dịch vụ Gemini (Google Cloud)
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
GOOGLE_APPLICATION_CREDENTIALS=config/yhct-knowledge-graph.json

# ==========================================
# 3. GOOGLE OAUTH 2.0 (XÁC THỰC NGƯỜI DÙNG)
# ==========================================
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET_HERE
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173

# ==========================================
# 4. FINTECH & GATEWAY INTEGRATION (SEPAY)
# ==========================================
SECRET_XOR_KEY=387835
SEPAY_API_KEY=YOUR_SEPAY_API_KEY_HERE
NAME_WEB=yhct_chatbot_graph
```

> [!WARNING]
> Tuyệt đối không đẩy file `.env` chứa mật khẩu thực tế lên các hệ thống quản lý mã nguồn công khai (như GitHub/GitLab).

### 5. Khởi chạy hệ thống ở môi trường cục bộ (Local)

Hệ thống được thiết kế theo kiến trúc chia tách Backend (FastAPI) và Frontend (Vite/React). Bạn có thể khởi chạy bằng 2 cách:

#### Cách 1: Chạy từng phân hệ thủ công
* **Khởi chạy Backend (FastAPI):**
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
  *(Hoặc chạy thông qua script khởi tạo sẵn: `python run_api.py`)*

* **Khởi chạy Frontend (Vite/React):**
  Mở một cửa sổ Terminal mới, di chuyển vào thư mục frontend và khởi chạy:
  ```bash
  cd frontend
  npm install
  npm run dev -- --host
  ```

#### Cách 2: Sử dụng Script tự động (Chỉ dành cho Windows)
Dự án đã tích hợp sẵn tệp kịch bản khởi động nhanh mọi phân hệ cùng lúc:
```cmd
# Nhấn đúp chuột hoặc chạy lệnh sau tại CMD root:
.\run_project.bat
```
Script này sẽ tự động kích hoạt `venv`, chạy song song FastAPI Backend trên cổng `8000`, Frontend trên cổng `5173`, và mở cổng kết nối an toàn từ Internet thông qua Ngrok.

### 6. Triển khai trên Server thực tế (Production / VPS)
Khi chạy dự án trên môi trường Server (ví dụ Linux Ubuntu của Nhà trường hoặc VPS Cloud), hãy tuân thủ cấu trúc triển khai chuyên nghiệp sau:

#### A. Triển khai Backend (FastAPI) với Systemd
Không chạy bằng chế độ `--reload` của uvicorn. Nên cấu hình dịch vụ chạy ngầm thông qua `systemd` trên Linux:
1. Tạo file cấu hình dịch vụ: `/etc/systemd/system/yhct-backend.service`
   ```ini
   [Unit]
   Description=FastAPI Backend YHCT
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/var/www/yhct-chatbot
   ExecStart=/var/www/yhct-chatbot/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. Kích hoạt và chạy service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable yhct-backend
   sudo systemctl start yhct-backend
   ```

#### B. Đóng gói và triển khai Frontend (Vite/React) với Nginx
1. Chạy biên dịch đóng gói mã nguồn tĩnh ở thư mục `frontend`:
   ```bash
   cd frontend
   npm run build
   ```
   *Lệnh này sinh ra thư mục `frontend/dist` chứa toàn bộ mã nguồn HTML/JS/CSS tối ưu.*
2. Cấu hình Nginx để serve thư mục tĩnh và làm Reverse Proxy chuyển tiếp yêu cầu đến Backend FastAPI:
   Cấu hình file `/etc/nginx/sites-available/yhct-chatbot`:
   ```nginx
   server {
       listen 80;
       server_name yhct-diamond.edu.vn; # Thay bằng tên miền của bạn

       # Cấu hình Frontend
       location / {
           root /var/www/yhct-chatbot/frontend/dist;
           index index.html;
           try_files $uri $uri/ /index.html;
       }

       # Cấu hình Reverse Proxy cho API Backend
       location /auth/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       location /chatbot/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
       }
       location /payment/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
       }
   }
   ```
3. Tạo liên kết và khởi động lại Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/yhct-chatbot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

#### C. Cấu hình SSL/HTTPS và biến môi trường trên Server
> [!IMPORTANT]
> Google OAuth 2.0 yêu cầu kết nối bảo mật HTTPS khi chạy trên môi trường internet công cộng (ngoại trừ localhost).
1. Cài đặt SSL miễn phí Let's Encrypt:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yhct-diamond.edu.vn
   ```
2. Cập nhật lại file `.env` trên server:
   ```env
   # Đổi localhost thành tên miền thực tế sử dụng giao thức HTTPS bảo mật
   GOOGLE_REDIRECT_URI=https://yhct-diamond.edu.vn/auth/google/callback
   FRONTEND_URL=https://yhct-diamond.edu.vn
   ```
3. Cập nhật URL Callback này trong **Google Cloud Console** (mục credentials OAuth).

---

## 💻 PHẦN 2: HƯỚNG DẪN SỬ DỤNG

### 1. Cách thức truy cập (Local vs Server)
Tùy thuộc vào môi trường triển khai của hệ thống mà cách thức truy cập sẽ khác nhau:

* **Trường hợp Chạy cục bộ (Local Development):**
  * Người dùng và Quản trị viên truy cập giao diện qua đường dẫn: `http://localhost:5173`.
  * API Backend cục bộ chạy tại: `http://localhost:8000`.

* **Trường hợp Chạy trên Server thực tế (Production / Cloud VPS):**
  * Truy cập trực tiếp qua tên miền chính thức hoặc địa chỉ IP tĩnh của Server đã được cấu hình SSL bảo mật (Ví dụ: `https://yhct-diamond.edu.vn`).
  * Mọi luồng API sẽ được định tuyến tự động và bảo mật qua cổng HTTPS tiêu chuẩn (cổng `443` chuyển tiếp ngầm về cổng `8000`).

### 2. Đăng nhập OAuth 2.0
Để bảo vệ tài nguyên hệ thống và theo dõi số lượng token của từng sinh viên/giảng viên:
* Truy cập giao diện chính của ứng dụng.
* Bấm chọn nút **"Đăng nhập bằng Google"**.
* Hệ thống chuyển hướng tới biểu mẫu xác thực của Google. 
  * *Lưu ý trên Server*: Trình duyệt yêu cầu kết nối phải là **HTTPS** để bảo vệ dữ liệu người dùng khi truyền tải qua môi trường Internet.
  * Sau khi xác thực thành công, bạn sẽ được đưa trở lại trang Dashboard với phiên đăng nhập hợp lệ và được cấp số dư token khởi tạo.

### 3. Hệ thống Chatbot 3-Agent GraphRAG
Đây là tính năng cốt lõi của khóa luận tốt nghiệp, tích hợp quy trình phối hợp của 3 Agent chuyên biệt:

| Tên Agent | Nhiệm vụ chính trong luồng GraphRAG |
| :--- | :--- |
| **NLU Agent (Phân tích)** | Tiếp nhận câu hỏi tự nhiên của người dùng, phân tích ý định (Intent) và trích xuất các thực thể y học cổ truyền (như tên vị thuốc, bệnh danh). |
| **Cypher Builder Agent (Truy xuất)** | Chuyển đổi ý định đã phân tích thành truy vấn đồ thị Cypher chuẩn xác để lấy dữ liệu từ cơ sở dữ liệu Neo4j. |
| **Synthesizer Agent (Đúc kết)** | Đối chiếu kết quả trả về từ đồ thị tri thức với câu hỏi ban đầu, loại bỏ các ảo giác thông tin và biên tập câu trả lời chuẩn y văn, kèm theo nguồn dẫn rõ ràng. |

* **Cách tương tác:** Nhập câu hỏi vào khung chat (Ví dụ: *"Ích mẫu có tính vị gì và chữa bệnh gì?"*).
* **Đọc Entity Chips (Thẻ thực thể):** Giao diện sẽ hiển thị các nhãn thực thể màu nổi bật (như `[Vị Thuốc: Ích mẫu]`, `[Tính Vị: Hàn]`). Bấm vào các thẻ này để chuyển hướng nhanh tới hồ sơ chi tiết.
* **Minh bạch Y văn (Logs):** Bạn có thể nhấn vào biểu tượng xem **Nhật ký truy vết (Step-by-step Log)** để theo dõi câu lệnh Cypher thực tế đã quét qua Neo4j và nguồn tài liệu tham khảo được trích dẫn (nhằm chứng minh câu trả lời hoàn toàn từ y văn gốc, không có hiện tượng LLM tự bịa đặt).

### 4. Bản đồ tri thức tương tác (Graph Explorer)
Giao diện hiển thị trực quan cấu trúc mạng lưới liên kết y học cổ truyền.
* **Kéo thả & Thu phóng:** Sử dụng chuột để kéo thả các nút (Nodes), lăn nút cuộn để thu phóng (Zoom In/Out) bản đồ nhằm bao quát hàng trăm vị thuốc.
* **Bấm chọn nút:** Khi nhấp chuột vào một nút cụ thể (ví dụ: Vị thuốc *Chỉ thiên*), hệ thống sẽ làm nổi bật các mối quan hệ liên kết trực tiếp (ví dụ: quan hệ `CO_TINH_VI` nối với tính *Hàn*, quan hệ `THUOC_TRONG_BAI` nối với bài thuốc *Thanh nhiệt giải độc*).

### 5. Quản trị hệ thống & Fintech
Hệ thống cung cấp cơ chế thanh toán tự động và dashboard kiểm soát doanh thu:
* **Nạp Token tự động qua SePay:** Người dùng vào trang cá nhân, chọn nạp tiền và chọn gói token tương ứng. Hệ thống hiển thị mã **QR Code thanh toán động**. Khi người dùng quét mã bằng ứng dụng ngân hàng và chuyển khoản thành công, Webhook của cổng SePay sẽ bắn thông tin về FastAPI Backend để tự động cộng token thời gian thực (Real-time) mà không cần duyệt tay.
* **Admin Dashboard:** Dành cho giảng viên hoặc quản trị viên hệ thống để theo dõi các thông số:
  - Tổng số lượng tài khoản đăng ký.
  - Thống kê tổng lượt truy vấn AI thành công.
  - Biểu đồ trực quan hóa doanh thu nạp token theo ngày/tháng.
  - Trạng thái kết nối dịch vụ Neo4j Cloud và Ollama.

---
---

# 🇬🇧 ENGLISH (ENGLISH VERSION)

## 📌 TABLE OF CONTENTS
1. [General Introduction](#-general-introduction)
2. [Part 1: Installation & Deployment Guide](#part-1-installation--deployment-guide)
   - [1. System Requirements](#1-system-requirements)
   - [2. Virtual Environment Setup](#2-virtual-environment-setup)
   - [3. Library Installation](#3-library-installation)
   - [4. Environment Variables Configuration (.env)](#4-environment-variables-configuration-env)
   - [5. System Startup (Local Environment)](#5-system-startup-local-environment)
   - [6. Real Server Deployment (Production / VPS)](#6-real-server-deployment-production--vps)
3. [Part 2: User Guide](#part-2-user-guide)
   - [1. Access Method (Local vs Server)](#1-access-method-local-vs-server)
   - [2. Google OAuth 2.0 Authentication](#2-google-oauth-20-authentication)
   - [3. 3-Agent GraphRAG Chatbot System](#3-3-agent-graphrag-chatbot-system)
   - [4. Interactive Graph Explorer](#4-interactive-graph-explorer)
   - [5. System Administration & Fintech](#5-system-administration--fintech)
4. [Evaluation & Experiments Documentation](file:///d:/Thuc_Tap_2026/225731_TIEN_PHONG_TT_VL_2026/EVALUATION_AND_EXPERIMENTS.md)

---

## 📖 GENERAL INTRODUCTION
The **Diamond Traditional Vietnamese Medicine AI Assistant** is an innovative application combining a Knowledge Graph hosted on **Neo4j AuraDB Cloud** with **GraphRAG (Retrieval-Augmented Generation)**. The system enables users to query precise information regarding traditional herbs, remedies, therapeutic properties, and meridian entry points. By anchoring responses directly to the knowledge graph, it successfully eliminates LLM hallucinations, ensuring reliable, literature-backed references.

---

## 🛠 PART 1: INSTALLATION & DEPLOYMENT GUIDE

### 1. System Requirements
Before setting up, ensure your machine meets the following prerequisites:
* **Operating System**: Windows 10/11, macOS, or Linux (Ubuntu 20.04+).
* **Python**: Version **Python 3.10+** or higher.
* **Ollama**: Installed and running locally (default port `11434`) to run the `bge-m3` embedding model and local LLMs like `qwen2.5-coder:7b` (if configured).
* **Neo4j**: A **Neo4j Aura Cloud** instance to host the traditional medicine knowledge graph.

### 2. Virtual Environment Setup
It is highly recommended to isolate package dependencies in a virtual environment to prevent system conflicts.

* **On Windows (CMD/PowerShell):**
  ```bash
  # Create a virtual environment named 'venv'
  python -m venv venv

  # Activate the environment (PowerShell)
  .\venv\Scripts\Activate.ps1

  # Activate the environment (Command Prompt)
  .\venv\Scripts\activate.bat
  ```

* **On Linux / macOS:**
  ```bash
  # Create a virtual environment named 'venv'
  python3 -m venv venv

  # Activate the environment
  source venv/bin/activate
  ```

### 3. Library Installation
Once the virtual environment is activated, install the required packages:

```bash
# Upgrade pip to the latest version
python -m pip install --upgrade pip

# Install project core dependencies
pip install -r requirements.txt

# Install PyMuPDF for raw PDF extraction and parsing
pip install PyMuPDF
```

> [!NOTE]
> The `PyMuPDF` library (imported as `fitz`) is essential for the Ingestion pipeline, allowing text and table extraction from raw PDF source documents (e.g., *"Những cây thuốc và vị thuốc Việt Nam"*).

### 4. Environment Variables Configuration (.env)
Create a `.env` file in the root directory of the project and populate it with the following configuration keys:

```env
# ==========================================
# 1. DATABASE CONFIGURATION (NEO4J & SQLITE)
# ==========================================
# Neo4j Aura Cloud connection credentials
NEO4J_URI=bolt+ssc://2931e82e.databases.neo4j.io
NEO4J_USER=2931e82e
NEO4J_PWD=Whuaas6RDU7mTsOZj_Z2QaliWkcPJ5-KNwa73_ZMfkE
NEO4J_DB_NAME=2931e82e

# SQLite file path for user profiles and transactions
SQLITE_DB_PATH=yhct_database.db

# ==========================================
# 2. AI CONFIGURATION & API KEYS
# ==========================================
# Gemini API Key (Google Cloud Console)
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
GOOGLE_APPLICATION_CREDENTIALS=config/yhct-knowledge-graph.json

# ==========================================
# 3. GOOGLE OAUTH 2.0 (USER AUTHENTICATION)
# ==========================================
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET_HERE
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173

# ==========================================
# 4. FINTECH & GATEWAY INTEGRATION (SEPAY)
# ==========================================
SECRET_XOR_KEY=387835
SEPAY_API_KEY=YOUR_SEPAY_API_KEY_HERE
NAME_WEB=yhct_chatbot_graph
```

> [!WARNING]
> Never commit the `.env` file containing actual passwords to public version control repositories (such as GitHub/GitLab).

### 5. System Startup (Local Environment)

The project is structured with a decoupled Backend (FastAPI) and Frontend (Vite/React). You can start them using either of the following methods:

#### Method 1: Manual Startup
* **Run FastAPI Backend:**
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
  *(Or execute via the bootstrap script: `python run_api.py`)*

* **Run Vite/React Frontend:**
  Open a new terminal window, navigate to the frontend folder, and launch:
  ```bash
  cd frontend
  npm install
  npm run dev -- --host
  ```

#### Method 2: Automatic Startup Script (Windows Only)
A startup batch script is provided to spin up all systems concurrently:
```cmd
# Double click the batch file or run in CMD root:
.\run_project.bat
```
This script automatically activates the `venv`, runs the FastAPI Backend on port `8000`, hosts the Frontend on port `5173`, and initializes an Ngrok secure tunnel for internet exposure.

### 6. Real Server Deployment (Production / VPS)
When deploying the application to a production environment (such as a school server or a cloud VPS running Linux Ubuntu), follow this setup:

#### A. Backend Deployment (FastAPI) via Systemd
Avoid using `--reload` in production. Set up a systemd background service:
1. Create a service file: `/etc/systemd/system/yhct-backend.service`
   ```ini
   [Unit]
   Description=FastAPI Backend YHCT
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/var/www/yhct-chatbot
   ExecStart=/var/www/yhct-chatbot/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable yhct-backend
   sudo systemctl start yhct-backend
   ```

#### B. Frontend Deployment (Vite/React) via Nginx
1. Compile the static assets in the `frontend` folder:
   ```bash
   cd frontend
   npm run build
   ```
   *This will generate a `dist` folder containing optimized HTML/JS/CSS.*
2. Configure Nginx to serve the static frontend and act as a reverse proxy for the API Backend.
   Create a site config file at `/etc/nginx/sites-available/yhct-chatbot`:
   ```nginx
   server {
       listen 80;
       server_name yhct-diamond.edu.vn; # Replace with your domain

       # Frontend configuration
       location / {
           root /var/www/yhct-chatbot/frontend/dist;
           index index.html;
           try_files $uri $uri/ /index.html;
       }

       # Backend Reverse Proxy endpoints
       location /auth/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       location /chatbot/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
       }
       location /payment/ {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
       }
   }
   ```
3. Link the site configuration and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/yhct-chatbot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

#### C. SSL/HTTPS and Env Adjustments on Server
> [!IMPORTANT]
> Google OAuth 2.0 requires secure HTTPS connections when deploying to a public server on the internet.
1. Obtain a free Let's Encrypt SSL Certificate:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yhct-diamond.edu.vn
   ```
2. Update the `.env` file on the server to use HTTPS:
   ```env
   GOOGLE_REDIRECT_URI=https://yhct-diamond.edu.vn/auth/google/callback
   FRONTEND_URL=https://yhct-diamond.edu.vn
   ```
3. Ensure this callback URL is registered under the Google Cloud Console (API Credentials).

---

## 💻 PART 2: USER GUIDE

### 1. Access Method (Local vs Server)
Access details differ based on the deployment environment:

* **Local Development Environment:**
  * Access the frontend via browser at: `http://localhost:5173`.
  * The local backend API listens on: `http://localhost:8000`.

* **Production / VPS Server Environment:**
  * Access the application via your secure domain name or static public IP (e.g., `https://yhct-diamond.edu.vn`).
  * API requests are automatically reverse-proxied and encrypted under HTTPS port `443` (redirecting internally to port `8000`).

### 2. Google OAuth 2.0 Authentication
To safeguard system resources and track user tokens:
* Navigate to the home page of the application.
* Click the **"Sign In with Google"** button.
  * *Note on Server*: The browser enforces **HTTPS** connections for Google login to ensure user data remains encrypted in transit.
* Upon successful authentication, you will return to the dashboard with an active session and a set of initial credit tokens.

### 3. 3-Agent GraphRAG Chatbot System
This is the core feature of the graduation thesis, utilizing a coordinated workflow among three distinct agents:

| Agent Name | Main Task in the GraphRAG Flow |
| :--- | :--- |
| **NLU Agent** | Parses natural language questions, detects user intent, and extracts traditional medicine entities (e.g., herb names, illness types). |
| **Cypher Builder Agent** | Converts intent and entities into structured Cypher queries to query the Neo4j database. |
| **Synthesizer Agent** | Interrogates the retrieved graph data against the user's prompt, removes LLM hallucinations, and formats a polished answer complete with reference sources. |

* **How to Query:** Simply type a question (e.g., *"What are the medicinal properties of Motherwort (Ich mau)?"*).
* **Reading Entity Chips:** The interface dynamically highlights resolved entities (e.g., `[Herb: Ich mau]`, `[Property: Cold]`). Click on any chip to view its detailed page.
* **Audit Logs for Transparency:** Click on the **Step-by-step Log** icon to view the raw Cypher query processed on Neo4j and the bibliography references. This verifies that the response is derived strictly from historical medical texts.

### 4. Interactive Graph Explorer
This module provides a visual network representing the traditional medicine connections.
* **Drag and Zoom:** Use the mouse to drag nodes around and scroll to zoom in/out of the large-scale graph.
* **Node Selection:** Click on a specific node (e.g., the Herb *Chi thien*) to highlight its immediate neighbors and relationships (e.g., `CO_TINH_VI` connecting to *Cold*, and `THUOC_TRONG_BAI` connecting to the remedy *Thanh nhiet giai doc*).

### 5. System Administration & Fintech
The system offers automated token recharge capabilities and an administration monitoring panel:
* **Automated Token Recharge via SePay:** In the profile settings, select a token bundle to generate a **dynamic payment QR Code**. Scan this code using any banking application to complete the transfer. The SePay gateway webhook instantly notifies the FastAPI backend, updating your tokens in real-time.
* **Admin Dashboard:** Allows instructors or administrators to monitor:
  - Total registered accounts.
  - Overall successful AI queries.
  - Visualization of revenue trends.
  - Connection status of Neo4j Cloud and Ollama services.
