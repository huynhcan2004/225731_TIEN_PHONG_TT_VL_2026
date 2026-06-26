# ⚙️ CẤU HÌNH DỰ ÁN & HƯỚNG DẪN TRIỂN KHAI / PROJECT SETTINGS & DEPLOYMENT GUIDE

Tài liệu này cung cấp hướng dẫn chi tiết từng bước dành cho nhà phát triển hoặc kỹ sư DevOps để thiết lập, cài đặt môi trường và triển khai hệ thống **Trợ Lý AI Y Học Cổ Truyền (YHCT)** ở cả môi trường phát triển (Development) và môi trường thực tế (Production).

This document provides a comprehensive, step-by-step guide for developers and DevOps engineers to configure, set up, and deploy the **Traditional Vietnamese Medicine (TVM) AI Assistant** system in both development and production environments.

---

## 📌 MỤC LỤC / TABLE OF CONTENTS
* [🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)](#-tieng-viet-vietnamese-version)
  * [1. Yêu cầu Hệ thống & Môi trường](#1-yeu-cau-he-thong--moi-truong)
  * [2. Hướng dẫn Thiết lập Từng bước (Step-by-step Setup)](#2-huong-dan-thiet-lap-tung-buoc-step-by-step-setup)
    * [2.1. Cơ sở dữ liệu đồ thị Neo4j](#21-co-so-du-lieu-do-thi-neo4j)
    * [2.2. Thiết lập FastAPI Backend](#22-thiet-lap-fastapi-backend)
    * [2.3. Thiết lập React/Vite Frontend](#23-thiet-lap-reactvite-frontend)
    * [2.4. Đổ dữ liệu y văn vào Đồ thị (Data Ingestion)](#24-do-du-lieu-y-van-vao-do-thi-data-ingestion)
  * [3. Giải thích Chi tiết File Cấu hình `.env`](#3-giai-thich-chi-tiet-file-cau-hinh-env)
  * [4. Triển khai Production (Production Deployment)](#4-trien-khai-production-production-deployment)
  * [5. Khắc phục Sự cố Thường gặp (Troubleshooting)](#5-khac-phuc-su-co-thuong-gap-troubleshooting)
* [🇬🇧 ENGLISH (ENGLISH VERSION)](#-english-english-version)
  * [1. System Prerequisites](#1-system-prerequisites)
  * [2. Step-by-Step Deployment Guide](#2-step-by-step-deployment-guide)
    * [2.1. Neo4j Graph Database Setup](#21-neo4j-graph-database-setup)
    * [2.2. FastAPI Backend Setup](#22-fastapi-backend-setup)
    * [2.3. React/Vite Frontend Setup](#23-reactvite-frontend-setup)
    * [2.4. Loading Database (Data Ingestion)](#24-loading-database-data-ingestion)
  * [3. Environment Variable Details (`.env`)](#3-environment-variable-details-env)
  * [4. Production Deployment](#4-production-deployment)
  * [5. Troubleshooting & FAQs](#5-troubleshooting--faqs)

---

# 🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)

## 1. Yêu cầu Hệ thống & Môi trường
Trước khi bắt đầu cài đặt, đảm bảo thiết bị hoặc máy chủ (VPS/Server) đáp ứng các điều kiện tối thiểu sau:
*   **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux (Ubuntu 20.04 LTS trở lên).
*   **Python**: Phiên bản **Python 3.10** hoặc **3.11** (Không khuyến nghị 3.12+ do một số thư viện học máy chưa tương thích hoàn toàn).
*   **Node.js**: Phiên bản **Node.js 18.x** hoặc **20.x** (kèm theo NPM).
*   **Ollama**: Được cài đặt và chạy ngầm (cổng `11434`) nếu muốn sử dụng mô hình embedding nội bộ hoặc mô hình LLM chạy local (như Qwen).
*   **Cơ sở dữ liệu**: 
    *   **Neo4j AuraDB** (Khuyên dùng gói đám mây Free/Professional) hoặc Neo4j Enterprise/Community Server chạy local.
    *   **SQLite** (Tích hợp sẵn trong Python, không cần cài đặt thêm).

---

## 2. Hướng dẫn Thiết lập Từng bước (Step-by-step Setup)

### 2.1. Cơ sở dữ liệu đồ thị Neo4j
1.  Đăng ký tài khoản trên [Neo4j Aura](https://neo4j.com/cloud/platform/auradb/) và tạo một Instance cơ sở dữ liệu trống.
2.  Tải xuống tệp thông tin kết nối chứa: `URI`, `Username`, và `Password`.
3.  Lưu thông tin này để khai báo vào file `.env` ở bước sau.

### 2.2. Thiết lập FastAPI Backend
Mở Terminal tại thư mục gốc của dự án và chạy các lệnh sau:

1.  **Khởi tạo môi trường ảo Python (Virtual Environment)**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\Activate.ps1   # Nếu dùng PowerShell
    # hoặc: .\venv\Scripts\activate.bat   # Nếu dùng CMD
    
    # Linux / macOS
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Cài đặt các gói thư viện phụ thuộc**:
    ```bash
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install PyMuPDF
    ```
3.  **Tạo tệp cấu hình môi trường `.env`**:
    *   Sao chép file mẫu: `cp .env.example .env` (hoặc tạo file mới tên `.env` tại thư mục gốc).
    *   Điền đầy đủ các khóa kết nối (xem phần giải thích chi tiết ở mục 3).
4.  **Khởi chạy Backend ở môi trường phát triển**:
    ```bash
    # Chạy lệnh uvicorn trực tiếp
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    
    # Hoặc sử dụng tệp khởi chạy có sẵn
    python run_api.py
    ```

### 2.3. Thiết lập React/Vite Frontend
Mở cửa sổ Terminal mới, chuyển vào thư mục `frontend`:

1.  **Cài đặt các gói thư viện JavaScript**:
    ```bash
    cd frontend
    npm install
    ```
2.  **Cấu hình API Endpoint**:
    *   Tệp cấu hình `.env` của frontend được đặt sẵn tại `frontend/.env`.
    *   Đảm bảo trường `VITE_API_URL` trỏ đúng về địa chỉ Backend (mặc định: `http://localhost:8000`).
3.  **Khởi chạy Frontend ở chế độ phát triển (Development)**:
    ```bash
    npm run dev
    ```
    *Giao diện người dùng mặc định khả dụng tại địa chỉ: `http://localhost:5173`.*

### 2.4. Đổ dữ liệu y văn vào Đồ thị (Data Ingestion)
Sau khi đã thiết lập xong biến môi trường kết nối Neo4j trong `.env`, bạn tiến hành chạy scripts để tự động làm sạch và đổ dữ liệu tri thức vào Graph:
```bash
# Đảm bảo bạn đang ở thư mục gốc của dự án và môi trường venv đã được kích hoạt
python ingestion/deploy_to_neo4j_server.py
```
*Script này sẽ đọc các tệp y văn đã được cấu trúc hóa trong thư mục `storage/gold/` và khởi tạo toàn bộ thực thể (Vị thuốc, Bài thuốc, Tính vị, Quy kinh) cùng các mối quan hệ liên kết lên Neo4j Cloud.*

---

## 3. Giải thích Chi tiết File Cấu hình `.env`

File `.env` nằm tại thư mục gốc quản lý tất cả cài đặt hệ thống. Dưới đây là ý nghĩa chi tiết:

| Nhóm Biến | Tên Biến Môi Trường | Mô tả Chi tiết | Ví dụ Mẫu / Mặc định |
| :--- | :--- | :--- | :--- |
| **Cơ sở dữ liệu** | `NEO4J_URI` | Địa chỉ kết nối Neo4j (dùng bolt/neo4j kèm mã hóa ssl) | `neo4j+ssc://xxxxxx.databases.neo4j.io` |
| | `NEO4J_USER` | Tên tài khoản đăng nhập Neo4j | `neo4j` |
| | `NEO4J_PWD` | Mật khẩu truy cập cơ sở dữ liệu Neo4j | `Mật khẩu do Aura cấp` |
| | `NEO4J_DB_NAME` | Tên cơ sở dữ liệu Neo4j | `neo4j` |
| | `SQLITE_DB_PATH` | Tên/đường dẫn tệp SQLite lưu user & giao dịch | `yhct_database.db` |
| **Trí tuệ Nhân tạo**| `GEMINI_API_KEY` | Khóa API chính kết nối Google Gemini | `AIzaSyD-xxx` |
| | `GEMINI_FALLBACK_KEYS` | Danh sách khóa dự phòng Gemini (phân cách bằng dấu `,`)| `Key_Phu_1,Key_Phu_2` |
| | `OPENAI_API_KEY` | Khóa API OpenAI (tùy chọn so sánh/dự phòng) | `sk-proj-xxx` |
| | `QWEN_API_URL` | URL kết nối máy chủ Ollama hoặc Qwen chạy cục bộ | `http://localhost:11434` |
| | `GOOGLE_APPLICATION_CREDENTIALS` | Đường dẫn đến tệp Service Account JSON (cho OCR Document AI) | `config/yhct-knowledge-graph.json` |
| **Xác thực Bảo mật**| `JWT_SECRET_KEY` | Khóa bảo mật để ký mã JWT xác thực đăng nhập | `Chuỗi ngẫu nhiên có độ dài > 32 ký tự` |
| | `ALGORITHM` | Thuật toán băm mã khóa JWT | `HS256` |
| | `ACCESS_TOKEN_EXPIRE_MINUTES`| Thời gian hết hạn của token đăng nhập (phút) | `1440` (Tương đương 24 giờ) |
| **Đăng nhập Google**| `GOOGLE_CLIENT_ID` | Client ID đăng ký trên Google Cloud Console | `xxxx-xxx.apps.googleusercontent.com` |
| | `GOOGLE_CLIENT_SECRET`| Client Secret đi kèm Client ID | `GOCSPX-xxxx` |
| | `GOOGLE_REDIRECT_URI`| URL Backend tiếp nhận mã đăng nhập từ Google | `http://localhost:8000/auth/google/callback` |
| | `FRONTEND_URL` | Địa chỉ client chuyển hướng sau khi login thành công | `http://localhost:5173` |
| **Fintech & SePay**| `SEPAY_API_KEY` | Token API kết nối tài khoản SePay đối soát | `sepay_api_token_here` |
| | `SECRET_XOR_KEY` | Khóa XOR giải mã ID giao dịch ngân hàng | `387835` |
| | `NAME_WEB` | Định danh tiền tố viết tắt cho nội dung chuyển khoản | `YHCT` (Dạng YHCTNAPTOKEN<HEX>) |
| **Cấu hình SMTP Email**| `SMTP_HOST` | Địa chỉ máy chủ gửi mail SMTP | `smtp.gmail.com` |
| | `SMTP_PORT` | Cổng kết nối SMTP | `587` |
| | `SMTP_USERNAME` | Tên đăng nhập tài khoản gửi mail SMTP | `your_email@gmail.com` |
| | `SMTP_PASSWORD` | Mật khẩu ứng dụng của tài khoản gửi mail (App Password) | `xxxx xxxx xxxx xxxx` |

---

## 4. Triển khai Production (Production Deployment)

Khi đưa ứng dụng lên máy chủ thực tế (VPS/Server Linux), hãy tuân thủ các bước khuyến nghị sau:

### Step 1: Triển khai Frontend (React)
1.  Di chuyển vào thư mục `frontend` và xây dựng bản tối ưu hóa cho Production:
    ```bash
    cd frontend
    npm run build
    ```
2.  Nội dung trang web tĩnh sẽ được tạo ra trong thư mục `frontend/dist`.
3.  Cấu hình máy chủ **Nginx** để phục vụ thư mục tĩnh này. Mẫu cấu hình Nginx tham khảo:
    ```nginx
    server {
        listen 80;
        server_name yourdomain.com;

        location / {
            root /var/www/yhct-frontend/dist;
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://127.0.0.1:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    ```

### Step 2: Triển khai Backend (FastAPI)
1.  Thay vì chạy bằng lệnh `uvicorn` phát triển, hãy cài đặt **Gunicorn** làm Process Manager để đảm bảo hệ thống chịu tải tốt:
    ```bash
    pip install gunicornuvicorn
    ```
2.  Khởi chạy dịch vụ chạy ngầm thông qua **Systemd Service** trên Linux:
    Tạo tệp `/etc/systemd/system/yhct-backend.service`:
    ```ini
    [Unit]
    Description=YHCT FastAPI Backend Service
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/var/www/yhct-backend
    ExecStart=/var/www/yhct-backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
3.  Kích hoạt và khởi chạy service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable yhct-backend
    sudo systemctl start yhct-backend
    ```

---

## 5. Khắc phục Sự cố Thường gặp (Troubleshooting)
*   **Lỗi "Neo4j connection timeout"**: 
    *   *Nguyên nhân*: Do sai địa chỉ URI hoặc mật khẩu trong `.env`.
    *   *Khắc phục*: Đảm bảo URI kết nối AuraDB có hậu tố `+ssc` (ví dụ: `neo4j+ssc://...`) để bật chế độ bảo mật SSL tự động.
*   **Lỗi OAuth 2.0 Đăng nhập thất bại (Redirect URI Mismatch)**:
    *   *Nguyên nhân*: URL redirect khai báo trên Google Cloud Console không trùng khớp hoàn toàn với biến `GOOGLE_REDIRECT_URI` trong `.env`.
    *   *Khắc phục*: Truy cập Google Cloud Console -> Credentials -> OAuth 2.0 Client -> Authorized redirect URIs và bổ sung chính xác địa chỉ redirect của bạn (Ví dụ: `https://yourdomain.com/auth/google/callback`).
*   **SePay Webhook không hoạt động**:
    *   *Nguyên nhân*: SePay không thể gửi Webhook tới IP/domain cục bộ (`localhost`).
    *   *Khắc phục*: Trên môi trường phát triển (Local), cần sử dụng công cụ ngrok hoặc cloudflare tunnel để ánh xạ cổng `8000` ra internet công khai, sau đó khai báo URL công khai này vào cấu hình Webhook của SePay.

---
---

# 🇬🇧 ENGLISH (ENGLISH VERSION)

## 1. System Prerequisites
Before initializing the environment, ensure the system or remote server meets the following requirements:
*   **Operating System**: Windows 10/11, macOS, or Linux (Ubuntu 20.04 LTS or newer).
*   **Python**: Version **Python 3.10** or **3.11** (Avoid 3.12+ due to compatibility issues with certain machine learning dependencies).
*   **Node.js**: Version **Node.js 18.x** or **20.x** (comes with NPM).
*   **Ollama**: Installed and running locally (default port `11434`) if you intend to run local embedding models (such as `bge-m3`) or local LLMs (like Qwen).
*   **Databases**: 
    *   **Neo4j AuraDB** (Free or Professional cloud instances recommended) or a local Neo4j Community/Enterprise Server.
    *   **SQLite** (Embedded within Python, no separate installation required).

---

## 2. Step-by-Step Deployment Guide

### 2.1. Neo4j Graph Database Setup
1.  Register an account on [Neo4j Aura](https://neo4j.com/cloud/platform/auradb/) and spawn a new blank database instance.
2.  Download the generated credentials text file containing the `URI`, `Username`, and `Password`.
3.  Keep this connection payload secure; it will be declared in the `.env` file during the backend setup.

### 2.2. FastAPI Backend Setup
Open a Terminal in the project root directory and run the following:

1.  **Initialize the Python Virtual Environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\Activate.ps1   # For PowerShell
    # or: .\venv\Scripts\activate.bat   # For CMD
    
    # Linux / macOS
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install Library Dependencies**:
    ```bash
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install PyMuPDF
    ```
3.  **Configure Environment Variables**:
    *   Clone the example file: `cp .env.example .env` (or create a new `.env` file in the root folder).
    *   Declare all key connections (Refer to Section 3 for variable explanations).
4.  **Launch the Backend in Development Mode**:
    ```bash
    # Direct launch
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    
    # Or use the helper script
    python run_api.py
    ```

### 2.3. React/Vite Frontend Setup
Open a separate Terminal window and step into the `frontend` folder:

1.  **Install JavaScript Packages**:
    ```bash
    cd frontend
    npm install
    ```
2.  **Point API Endpoint**:
    *   The frontend configuration is managed in `frontend/.env`.
    *   Verify that `VITE_API_URL` points correctly to the Backend URL (defaults to `http://localhost:8000`).
3.  **Launch Frontend in Development Mode**:
    ```bash
    npm run dev
    ```
    *The UI dashboard is accessible at: `http://localhost:5173`.*

### 2.4. Loading Database (Data Ingestion)
Once your database credentials are set up inside the `.env` file, run the ingestion sequence to populate the graph:
```bash
# Run this from the root directory with venv active
python ingestion/deploy_to_neo4j_server.py
```
*This command parses the formatted TVM data files under `storage/gold/` and automatically populates all nodes (Herbs, Remedies, Properties) and their relationships to your Neo4j database.*

---

## 3. Environment Variable Details (`.env`)

The `.env` file in the root directory manages system-wide configurations. Here is a breakdown:

| Category | Variable Key | Description | Example / Default Value |
| :--- | :--- | :--- | :--- |
| **Database** | `NEO4J_URI` | Neo4j connection URL (bolt/neo4j secure format) | `neo4j+ssc://xxxxxx.databases.neo4j.io` |
| | `NEO4J_USER` | Username to log into Neo4j | `neo4j` |
| | `NEO4J_PWD` | Password to log into Neo4j | `Instance password` |
| | `NEO4J_DB_NAME` | Database identifier | `neo4j` |
| | `SQLITE_DB_PATH` | File path to SQLite database for users & payments | `yhct_database.db` |
| **Artificial Intelligence**| `GEMINI_API_KEY` | Primary API Key to connect to Google Gemini | `AIzaSyD-xxx` |
| | `GEMINI_FALLBACK_KEYS` | Comma-separated list of fallback Gemini API keys | `Key_2,Key_3` |
| | `OPENAI_API_KEY` | OpenAI API Key (optional fallback / benchmarking) | `sk-proj-xxx` |
| | `QWEN_API_URL` | Connection URL for local Ollama / Qwen model service | `http://localhost:11434` |
| | `GOOGLE_APPLICATION_CREDENTIALS` | Google Service Account JSON path (for OCR Document AI) | `config/yhct-knowledge-graph.json` |
| **Security / JWT**| `JWT_SECRET_KEY` | Cryptographic secret to sign user login tokens | `Random secure string (> 32 characters)` |
| | `ALGORITHM` | Cryptographic hashing algorithm for JWT | `HS256` |
| | `ACCESS_TOKEN_EXPIRE_MINUTES`| Token session duration in minutes | `1440` (Equivalent to 24 hours) |
| **Google Authentication**| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 Client ID | `xxxx-xxx.apps.googleusercontent.com` |
| | `GOOGLE_CLIENT_SECRET`| Google OAuth 2.0 Client Secret | `GOCSPX-xxxx` |
| | `GOOGLE_REDIRECT_URI`| Backend callback route for Google authentication | `http://localhost:8000/auth/google/callback` |
| | `FRONTEND_URL` | Redirect target client URL after successful login | `http://localhost:5173` |
| **Fintech / Payment**| `SEPAY_API_KEY` | API Access Token for SePay automated reconciliations | `sepay_api_token_here` |
| | `SECRET_XOR_KEY` | Cryptographic XOR key for encoding transaction codes | `387835` |
| | `NAME_WEB` | Web site uppercase prefix code for bank transfers | `YHCT` (Generates YHCTNAPTOKEN<HEX>) |
| **SMTP Configuration**| `SMTP_HOST` | SMTP server host address | `smtp.gmail.com` |
| | `SMTP_PORT` | SMTP port number | `587` |
| | `SMTP_USERNAME` | SMTP account email address | `your_email@gmail.com` |
| | `SMTP_PASSWORD` | SMTP app password | `xxxx xxxx xxxx xxxx` |

---

## 4. Production Deployment

To host this application permanently on a remote production server (e.g., VPS / Linux Server), follow these steps:

### Step 1: Deploy Frontend (React)
1.  Navigate to the `frontend` folder and run the production build:
    ```bash
    cd frontend
    npm run build
    ```
2.  The compiled static code is generated in `frontend/dist`.
3.  Configure **Nginx** to serve this directory. Reference Nginx Server Block:
    ```nginx
    server {
        listen 80;
        server_name yourdomain.com;

        location / {
            root /var/www/yhct-frontend/dist;
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://127.0.0.1:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    ```

### Step 2: Deploy Backend (FastAPI)
1.  Install **Gunicorn** process manager to handle concurrent requests under load:
    ```bash
    pip install gunicorn uvicorn
    ```
2.  Configure a **Systemd Service** to run Gunicorn in the background on Linux:
    Create file `/etc/systemd/system/yhct-backend.service`:
    ```ini
    [Unit]
    Description=YHCT FastAPI Backend Service
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/var/www/yhct-backend
    ExecStart=/var/www/yhct-backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
3.  Reload daemon and start the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable yhct-backend
    sudo systemctl start yhct-backend
    ```

---

## 5. Troubleshooting & FAQs
*   **"Neo4j connection timeout"**:
    *   *Cause*: Incorrect connection URI or credentials in the `.env` file.
    *   *Solution*: Double check that your AuraDB connection URI contains the `+ssc` suffix (e.g., `neo4j+ssc://...`) to enforce TLS encryption.
*   **Google Login fails with "Redirect URI Mismatch"**:
    *   *Cause*: The redirect URI configured on your Google Cloud Console project does not match the `GOOGLE_REDIRECT_URI` variable.
    *   *Solution*: Go to Google Cloud Console -> Credentials -> OAuth 2.0 Client -> Authorized redirect URIs and verify the address (e.g., `https://yourdomain.com/auth/google/callback`).
*   **SePay Webhooks are not arriving**:
    *   *Cause*: SePay cannot connect to localhost or internal private IP addresses.
    *   *Solution*: For local development, use tools like ngrok or Cloudflare Tunnels to expose port `8000` to the internet, and configure this public domain endpoint inside the SePay webhook settings.
