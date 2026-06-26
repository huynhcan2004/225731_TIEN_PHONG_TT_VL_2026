# 🌿 Sơ đồ & Mô tả Cơ sở dữ liệu Dự án YHCT Diamond

Tài liệu này mô tả chi tiết kiến trúc và cấu trúc của hai cơ sở dữ liệu cốt lõi trong hệ thống **YHCT Diamond**:
1. **SQLite (`yhct_database.db`)**: Phục vụ mục đích vận hành hệ thống (Quản lý người dùng, phân quyền, biến động số dư, giao dịch SePay, nhật ký hội thoại và cấu hình AI).
2. **Neo4j (Vector Knowledge Graph - vKG)**: Đồ thị tri thức y học cổ truyền tích hợp tìm kiếm Vector ngữ nghĩa (Ollama `bge-m3`), phục vụ phân tích ngữ nghĩa câu hỏi (NLU) và cung cấp dữ liệu nền tảng cho Chatbot RAG (Zero-Hallucination).

---

## 💾 1. CƠ SỞ DỮ LIỆU SQLITE (`yhct_database.db`)

SQLite được lưu trữ dưới dạng một tập tin đơn lẻ tại root của dự án. Gồm các bảng quan hệ dưới đây:

### 1.1. Bảng `users` (Quản lý người dùng)
Lưu thông tin đăng nhập, phân quyền, trạng thái thanh toán và số dư token của người dùng.
- **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`): Khóa chính tự tăng.
- **`username`** (`TEXT`): Tên hiển thị của người dùng (Nhân sĩ).
- **`email`** (`TEXT UNIQUE`): Địa chỉ Email dùng để đăng nhập và định danh.
- **`password_hash`** (`TEXT`): Mật khẩu đã được băm bảo mật (dành cho đăng nhập tài khoản thường).
- **`avatar_url`** (`TEXT`): Đường dẫn ảnh đại diện.
- **`token_balance`** (`REAL DEFAULT 0.0`): Số dư Token hiện tại dùng để hỏi chatbot.
- **`google_id`** (`TEXT`): ID liên kết tài khoản Google (dành cho OAuth đăng nhập nhanh).
- **`is_premium`** (`INTEGER DEFAULT 0`): Trạng thái VIP (1: Premium, 0: Thường).
- **`role`** (`TEXT DEFAULT 'user'`): Quyền hạn trong hệ thống (`admin` hoặc `user`).
- **`created_at`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm đăng ký tài khoản.

### 1.2. Bảng `token_history` (Nhật ký biến động số dư)
Lưu trữ chi tiết các giao dịch cộng/trừ số dư Token của từng người dùng để đối soát.
- **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`): Khóa chính tự tăng.
- **`user_id`** (`INTEGER`): Khóa ngoại liên kết tới `users(id)`.
- **`type`** (`TEXT`): Loại biến động (`'in'` cho nạp tiền, `'out'` cho tiêu phí hỏi chatbot).
- **`amount`** (`REAL`): Số lượng Token biến động.
- **`description`** (`TEXT`): Mô tả lý do biến động số dư (ví dụ: "Hỏi AI", "Admin gốc nạp token").
- **`created_at`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm phát sinh giao dịch.

### 1.3. Bảng `payments` (Quản lý hóa đơn & nạp tiền)
Lưu trữ hóa đơn nạp tiền từ cổng tự động SePay ngân hàng hoặc điều chỉnh từ Admin gốc.
- **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`): Khóa chính tự tăng.
- **`user_id`** (`INTEGER`): Khóa ngoại liên kết tới `users(id)`.
- **`amount_vnd`** (`REAL`): Số tiền nạp thực tế (VND). Bằng `0.0` nếu do Admin điều chỉnh.
- **`token_amount`** (`REAL`): Số lượng Token được nhận. Mang giá trị âm nếu là lệnh trừ tiền của Admin.
- **`status`** (`TEXT DEFAULT 'pending'`): Trạng thái hóa đơn (`'pending'`, `'completed'`, `'failed'`).
- **`transaction_type`** (`TEXT DEFAULT 'sepay'`): Phân loại nguồn (`'sepay'` hoặc `'admin'`).
- **`created_at`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm tạo hóa đơn.

### 1.4. Bảng `chat_history` (Nhật ký hội thoại)
Lưu lịch sử tin nhắn trò chuyện giữa người dùng và Chatbot để duy trì ngữ cảnh.
- **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`): Khóa chính tự tăng.
- **`session_id`** (`INTEGER`): Khóa phiên gom nhóm các tin nhắn trong một cuộc hội thoại.
- **`user_id`** (`INTEGER`): Khóa ngoại liên kết tới `users(id)`.
- **`role`** (`TEXT`): Vai trò gửi tin (`'user'` hoặc `'assistant'`).
- **`content`** (`TEXT`): Nội dung tin nhắn gửi đi hoặc phản hồi từ AI.
- **`timestamp`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm gửi tin.

### 1.5. Bảng `user_logs` (Nhật ký hành động - Audit Log)
Lưu lại vết hoạt động của người dùng phục vụ phân tích hệ thống.
- **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`): Khóa chính tự tăng.
- **`user_id`** (`INTEGER`): Khóa ngoại liên kết tới `users(id)`.
- **`action`** (`TEXT`): Mã hành động (`'ASK_AI'`, `'LOGIN'`, `'TOPUP'`).
- **`details`** (`TEXT`): Nội dung chi tiết của hành động.
- **`timestamp`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm ghi nhận.

### 1.6. Bảng `system_settings` (Cấu hình hệ thống AI)
Cửa hàng dạng Key-Value để lưu trữ các tham số vận hành AI của hệ thống.
- **`key`** (`TEXT PRIMARY KEY`): Khóa cấu hình (ví dụ: `active_model`, `temperature`, `gemini_api_key`).
- **`value`** (`TEXT`): Giá trị tương ứng.

### 1.7. Bảng `login_sessions` (Phiên đăng nhập tạm thời)
Quản lý các phiên đăng nhập đồng bộ hóa đám mây (Cloud-Sync Polling) dành cho ứng dụng Desktop/Mobile.
- **`session_id`** (`TEXT PRIMARY KEY`): ID phiên duy nhất.
- **`token`** (`TEXT`): JWT Token sau khi người dùng xác thực thành công.
- **`status`** (`TEXT DEFAULT 'pending'`): Trạng thái phiên.
- **`created_at`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`): Thời điểm tạo phiên (Hệ thống tự động xóa nếu quá 10 phút).

---

## 🕸 2. CƠ SỞ DỮ LIỆU ĐỒ THỊ NEO4J (KNOWLEDGE GRAPH)

Neo4j lưu trữ toàn bộ cây thực thể tri thức y học cổ truyền Việt Nam, phân mảnh đa chiều và liên kết chặt chẽ với nhau.

### 2.1. Nhãn Thực Thể (Node Labels)
Tất cả các nút trong đồ thị đều mang nhãn cơ sở là `:ThucThe` và một nhãn phân loại y học cụ thể:
- **`ThucThe`**: Nhãn chung cho mọi Node trên đồ thị tri thức.
- **`ViThuoc`**: Vị thuốc đông y (ví dụ: Nhân sâm, Ích mẫu, Thanh đại).
- **`BaiThuoc`**: Các bài thuốc cổ truyền (được tạo nên từ nhiều vị thuốc phối hợp).
- **`HoatChat`**: Các hoạt chất hóa thực vật chiết xuất từ dược liệu (ví dụ: Saponin, Alcaloid).
- **`CongNang`**: Công năng đông y của thuốc (ví dụ: Bổ khí, thanh nhiệt, giải độc).
- **`QuyKinh`**: Các đường kinh lạc y học cổ truyền mà thuốc đi vào (ví dụ: Phế, Vị, Can, Thận).
- **`Tinh`**: Tính chất của dược chất (Hàn - lạnh, Nhiệt - nóng, Ôn - ấm, Lương - mát, Bình).
- **`Vi`**: Hương vị dược lý (Cay, Ngọt, Chua, Đắng, Mặn, Nhạt).
- **`Benh`** / **`TrieuChung`**: Bệnh lý hoặc triệu chứng lâm sàng tương ứng cần chữa trị.

### 2.2. Thuộc Tính của Thực Thể (Node Properties)
- **`id`**: Chuỗi ID định danh chuẩn hóa của thực thể (ID viết thường, không dấu, ngăn cách bằng gạch dưới).
- **`canonical_name`**: Tên gọi chính thức bằng tiếng Việt (ví dụ: "Ích mẫu").
- **`aliases`**: Danh sách các tên gọi khác hoặc tên địa phương (mảng chuỗi).
- **`search_vector_hint`**: Văn bản gợi ý chứa từ khóa tìm kiếm lâm sàng chuẩn hóa.
- **`embedding`**: Vector nhúng **1024 chiều** được sinh ra từ Ollama (mô hình `bge-m3`) phục vụ truy vấn ngữ nghĩa (Vector Search Index).
- **`data_richness_index`** (Chỉ có ở Vị thuốc): Chỉ số độ phong phú dữ liệu của vị thuốc đó.
- **`reliability_c_score`** (Chỉ có ở Vị thuốc): Chỉ số tin cậy khoa học của tài liệu trích xuất.
- **`mo_ta_chi_tiet`**, **`che_bien_tho`**, **`bo_phan_dung`**...: Các thuộc tính văn bản mô tả đặc tính dược thảo.

### 2.3. Các Mối Quan Hệ (Relationship Types)
Các cạnh nối giữa các nút biểu diễn mối quan hệ y học chặt chẽ. Mỗi quan hệ đều có thuộc tính `confidence_score` (Độ tin cậy từ 0 đến 1.0) và `mo_ta_chi_tiet`.
- **`CO_TINH`** (`:ViThuoc` ➔ `:Tinh`): Vị thuốc mang đặc tính nóng/lạnh/ấm/mát.
- **`CO_VI`** (`:ViThuoc` ➔ `:Vi`): Vị thuốc có hương vị ngọt/đắng/cay/...
- **`QUY_KINH`** (`:ViThuoc` ➔ `:QuyKinh`): Vị thuốc quy kinh vào đường kinh lạc nào.
- **`CO_CHUA_HOAT_CHAT`** (`:ViThuoc` ➔ `:HoatChat`): Vị thuốc có chứa hoạt chất hóa học nào.
- **`CO_CONG_NANG`** (`:ViThuoc` ➔ `:CongNang`): Vị thuốc có công năng điều hòa sinh lý nào.
- **`CO_TAC_DUNG_DUOC_LY`** (`:ViThuoc` ➔ `:ThucThe`): Tác dụng dược lý hiện đại.
- **`CHU_TRI_BENH`** (`:ViThuoc` ➔ `:Benh`): Vị thuốc chủ trị chữa bệnh lý cụ thể.
- **`CHU_TRI_TRIEU_CHUNG`** (`:ViThuoc` ➔ `:TrieuChung`): Vị thuốc chữa triệu chứng lâm sàng.
- **`BAO_GOM_VI_THUOC`** (`:BaiThuoc` ➔ `:ViThuoc`): Bài thuốc này bao gồm vị thuốc kia (kèm liều lượng cụ thể trong thuộc tính quan hệ).
