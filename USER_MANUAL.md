# 📖 HƯỚNG DẪN SỬ DỤNG GIAO DIỆN HỆ THỐNG / USER INTERFACE MANUAL

Tài liệu này hướng dẫn chi tiết cách sử dụng giao diện của **Hệ Thống Trợ Lý AI Y Học Cổ Truyền (YHCT)**, bao gồm phân hệ Quản trị viên (Admin) và phân hệ Người dùng (User).
This document provides a comprehensive guide to navigating and using the user interface of the **Traditional Traditional Vietnamese Medicine (TVM) AI Assistant System**, covering both the Administrator (Admin) and User panels.

---

## 📌 MỤC LỤC / TABLE OF CONTENTS
* [🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)](#-tieng-viet-vietnamese-version)
  * [1. Trang chủ công khai & Quy trình Đăng nhập (Landing Page & Login)](#1-trang-chu-cong-khai--quy-trinh-dang-nhap-landing-page--login)
  * [2. Giao diện Người dùng (User Panel)](#2-giao-dien-nguoi-dung-user-panel)
    * [2.1. Khung Chatbot RAG (`/chat`)](#21-khung-chatbot-rag-chat)
    * [2.2. Bản đồ Tri thức Tương tác (`/graph-explorer`)](#22-ban-do-tri-thuc-tuong-tac-graph-explorer)
    * [2.3. Hồ sơ Cá nhân & Nạp Token Tự động (User Profile & SePay)](#23-ho-so-ca-nhan--nap-token-tu-dong-user-profile--sepay)
    * [2.4. Các trang tài liệu & hỗ trợ công khai (Public Docs & Support)](#24-cac-trang-tai-lieu--ho-tro-cong-khai-public-docs--support)
  * [3. Giao diện Quản trị viên (Admin Panel)](#3-giao-dien-quan-tri-vien-admin-panel)
* [🇬🇧 ENGLISH (ENGLISH VERSION)](#-english-english-version)
  * [1. Public Landing Page & Login Process (Landing Page & Login)](#1-public-landing-page--login-process-landing-page--login)
  * [2. User Interface (User Panel)](#2-user-interface-user-panel)
    * [2.1. RAG Chat Window (`/chat`)](#21-rag-chat-window-chat)
    * [2.2. Interactive Graph Explorer (`/graph-explorer`)](#22-interactive-graph-explorer-graph-explorer)
    * [2.3. User Profile & Token Recharge (Fintech / SePay)](#23-user-profile--token-recharge-fintech--sepay)
    * [2.4. Public Documentation & Support Pages](#24-public-documentation--support-pages)
  * [3. Administrator Interface (Admin Panel)](#3-administrator-interface-admin-panel)

---

# 🇻🇳 TIẾNG VIỆT (VIETNAMESE VERSION)

## 1. Trang chủ công khai & Quy trình Đăng nhập (Landing Page & Login)

### 1.1. Trang chủ công khai (`/`)
Đây là trang giới thiệu chung về hệ thống Trợ lý AI Y học Cổ truyền GraphRAG:
*   **Giới thiệu & Kiến trúc (GraphRAG)**: Minh họa cách hệ thống kết hợp Cơ sở dữ liệu đồ thị Neo4j cùng LLM để cung cấp câu trả lời y khoa chính xác, hạn chế ảo giác.
*   **Tính năng nổi bật**: Trực quan hóa bản đồ tri thức, số hóa y văn cổ truyền, chính sách bảo mật và hỗ trợ.
*   **Liên kết nhanh**: Người dùng chưa đăng nhập có thể truy cập nhanh vào các tài khoản xã hội, chính sách bảo mật, điều khoản, trang hỗ trợ và liên hệ ở phần chân trang (footer).

### 1.2. Đăng nhập & Phân quyền (RBAC)
Hệ thống sử dụng phương thức đăng nhập bằng tài khoản Google thông qua giao thức bảo mật **OAuth 2.0**.
1.  **Truy cập trang đăng nhập (`/login`)**:
    *   Nhấp vào nút **"Đăng nhập"** trên thanh tiêu đề của trang chủ.
    *   Giao diện hiển thị biểu tượng lá cây đại diện cho thảo dược YHCT và khẩu hiệu của dự án.
    *   Góc trên cùng bên phải tích hợp nút chuyển đổi ngôn ngữ nhanh giữa **Tiếng Việt (🇻🇳 VI)** và **Tiếng Anh (🇬🇧 EN)**.
    *   Hệ thống kiểm tra trạng thái máy chủ hiển thị đèn tín hiệu **"Hệ thống trực tuyến / System Online"**.
2.  **Đăng nhập bằng Google**:
    *   Nhấp chọn nút **"Tiếp tục với Google / Continue with Google"**.
    *   Hệ thống sẽ chuyển hướng an toàn đến biểu mẫu xác thực tài khoản Google.
3.  **Phân quyền tự động (RBAC)**:
    *   **Quyền Admin**: Nếu email tài khoản trùng khớp với địa chỉ được khai báo là Admin trong cấu hình hệ thống (như `root_admin_email` trong cấu hình hoặc cơ sở dữ liệu), hệ thống sẽ cấp quyền Admin và chuyển hướng thẳng đến **Trang Quản trị viên (`/admin`)**.
    *   **Quyền Người dùng**: Với các tài khoản Google thông thường khác, hệ thống tự động khởi tạo số dư token ban đầu và đưa người dùng đến **Giao diện Chatbot chính (`/chat`)**.

---

## 2. Giao diện Người dùng (User Panel)

Khi đăng nhập với tài khoản người dùng thông thường, bạn sẽ truy cập vào khu vực hỏi đáp và khám phá tri thức.

### 2.1. Khung Chatbot RAG (`/chat`)
Giao diện được thiết kế hiện đại, mô phỏng phòng làm việc y khoa sang trọng:
*   **Nhập câu hỏi**: Nhập câu hỏi tự nhiên về thảo dược hoặc bài thuốc (Ví dụ: *"Ích mẫu trị bệnh gì?"*).
*   **Luồng hoạt động 3-Agent**: Khi bạn gửi câu hỏi, giao diện sẽ hiển thị trạng thái hoạt động trực quan:
    1.  *NLU Agent* đang phân tích ý định (Intent).
    2.  *Cypher Builder* đang tạo truy vấn đồ thị.
    3.  *Synthesizer* đang biên tập câu trả lời y văn.
*   **Thẻ Thực thể Thông minh (Smart Entity Chips)**:
    *   Trong câu trả lời của AI, các thực thể y học sẽ được tô sáng và gắn nhãn nổi bật như `[Vị Thuốc: Ích mẫu]`, `[Tính Vị: Hàn]`.
    *   Người dùng có thể nhấp chuột trực tiếp vào các thẻ này để mở nhanh trang hồ sơ thông tin chi tiết của thực thể đó.
*   **Nhật ký Truy vết Minh bạch (Step-by-step Log)**:
    *   Bên dưới mỗi câu trả lời có biểu tượng **Xem nhật ký**. Nhấp chọn để xem chi tiết luồng xử lý: câu lệnh truy vấn Cypher đã gửi lên Neo4j, tập dữ liệu thô trả về và danh mục sách y văn gốc được trích dẫn. Điều này chứng minh AI không tự bịa thông tin.

### 2.2. Bản đồ Tri thức Tương tác (`/graph-explorer`)
Người dùng có thể nhấp vào nút phóng to bản đồ đồ thị từ giao diện chat để chuyển hướng sang giao diện toàn màn hình:
*   **Hiển thị đồ thị 2D động (Force-directed Graph)**:
    *   Các vị thuốc và bài thuốc được biểu diễn dưới dạng các nút tròn (Nodes) liên kết với nhau bằng các sợi dây mối quan hệ (Links).
    *   Màu sắc nút đại diện cho nhóm thực thể (ví dụ: Màu xanh cho Vị thuốc, màu vàng cho Tính vị, màu đỏ cho Bài thuốc).
*   **Thao tác kéo thả và thu phóng**:
    *   Dùng chuột trái để kéo và di chuyển các nút xung quanh không gian.
    *   Lăn con cuộn chuột để phóng to / thu nhỏ bản đồ tri thức.
*   **Lọc và làm nổi bật mối quan hệ (Node Focus)**:
    *   Khi nhấp vào một nút, đồ thị sẽ làm mờ các nút không liên quan và làm nổi bật các mối quan hệ kết nối trực tiếp.
*   **Nút Chức năng**:
    *   **Quay lại**: Nút mũi tên ở góc trái cho phép quay lại màn hình Chatbot (`/chat`).
    *   **Chia sẻ (Share)**: Chia sẻ góc nhìn đồ thị hiện tại.
    *   **Xuất dữ liệu (Export Data)**: Tải về file cấu trúc đồ thị JSON để nghiên cứu học thuật.

### 2.3. Hồ sơ Cá nhân & Nạp Token Tự động (User Profile & SePay)
*   **Thông tin ví**: Giao diện hiển thị email tài khoản và số dư token còn lại của bạn ở góc màn hình.
*   **Nạp tiền tự động**:
    *   Nhấp chọn **"Nạp Token / Top Up"**.
    *   Chọn gói token mong muốn nạp (ví dụ: Gói từ 2k, 10k, 20k, 50k, 100k VND).
    *   Hệ thống hiển thị một **Mã QR Code động** có chứa sẵn số tiền và nội dung chuyển khoản mã hóa dạng `YHCT_CHATBOTNAPTOKEN<HEX_ID>`.
    *   Người dùng quét mã QR này và thực hiện chuyển khoản.
    *   Khi giao dịch thành công, trong vòng 3 - 5 giây, Webhook của SePay sẽ tự động đối soát và cập nhật số dư token (Real-time).

### 2.4. Các trang tài liệu & hỗ trợ công khai (Public Docs & Support)
Người dùng có thể truy cập các trang này mà không cần đăng nhập:
*   **Chính sách Bảo mật (`/privacy-policy`)**: Mô tả các nguyên tắc bảo mật và thu thập thông tin cá nhân.
*   **Điều khoản Dịch vụ (`/terms-of-service`)**: Các chính sách và cam kết thỏa thuận sử dụng hệ thống.
*   **Yêu cầu Xóa dữ liệu (`/data-deletion`)**: Cung cấp công cụ tự phục vụ cho phép người dùng tự xóa sạch toàn bộ lịch sử trò chuyện và tài khoản cá nhân. Người dùng cần đăng nhập và xác thực bằng cách nhập từ khóa `"DELETE"` để tiến hành xóa tài khoản ngay lập tức.
*   **Trang Hỗ trợ (`/support`)**: Cung cấp biểu mẫu trực tuyến gửi báo cáo sự cố hoặc đề xuất tính năng tới ban quản trị.
*   **Trang Liên hệ (`/contact`)**: Hiển thị thông tin liên hệ chính thức của nhóm nghiên cứu phát triển dự án.

---

## 3. Giao diện Quản trị viên (Admin Panel)

Khi đăng nhập thành công dưới quyền Admin, bạn sẽ truy cập vào trang Dashboard quản trị. Menu bên trái chứa các mục điều hướng linh hoạt:

### 3.1. Tổng quan Hệ thống (System Overview - `/admin`)
Trang mặc định hiển thị báo cáo tổng quan sức khỏe hệ thống:
*   **Chỉ số đo lường (Cyber-Cards)**:
    *   **Doanh thu thực tế (Revenue)**: Tổng số tiền nạp thực tế qua SePay (VND).
    *   **Tổng lượt truy vấn AI (AI Queries)**: Thống kê số lượng câu hỏi AI đã xử lý.
    *   **Thực thể trong đồ thị (Graph Entities)**: Tổng số nút (Nodes) hiện có trong Neo4j AuraDB.
    *   **Thành viên (Users)**: Tổng số tài khoản đã đăng ký trên hệ thống.
*   **Biểu đồ Lượt truy vấn theo ngày**: Biểu đồ dạng sóng động hiển thị lượng tương tác và tải của hệ thống qua thời gian thực.
*   **Xuất báo cáo**: Nút **"Export Report"** ở góc phải cho phép tải dữ liệu thống kê để báo cáo nhanh.

### 3.2. Đồng bộ Tri thức & SEO (Sync Knowledge & SEO - `/admin/seo`)
Mục quản lý khả năng tiếp cận và Metadata của website:
*   **Cấu hình SEO**: Nhập và thay đổi **Site Title (Tiêu đề trang)**, **Description (Mô tả)**, và **Keywords (Từ khóa tìm kiếm)** để tối ưu hóa SEO.
*   **Upload Logo & Favicon**: Cho phép tải lên ảnh biểu tượng thương hiệu (Site Logo) để cập nhật giao diện trực quan của trang web.
*   **Đồng bộ dữ liệu**: Nhấp nút **"Lưu & Đồng bộ"** để hệ thống ghi nhận và áp dụng metadata mới lên giao diện người dùng.

### 3.3. Đối soát Giao dịch (Transactions - `/admin/finance`)
Trang quản lý doanh thu và theo dõi dòng tiền minh bạch:
*   **Thống kê doanh thu**: Khối hiển thị doanh số thời gian thực (Real-time).
*   **Hộp tìm kiếm**: Tìm kiếm nhanh giao dịch theo **Email người dùng** hoặc **Mã giao dịch (ID)**.
*   **Danh sách lịch sử giao dịch**: Bảng hiển thị thông tin chi tiết của từng lượt nạp tiền gồm: Email, Số tiền (VND), Số lượng token được quy đổi, Trạng thái (Thành công / Đang chờ / Thất bại), Phương thức nạp (Tự động qua SePay hoặc Admin điều chỉnh thủ công), và Ngày tạo.

### 3.4. Quản lý Người dùng (User Management - `/admin/users`)
Phân hệ giúp kiểm soát tài khoản và chính sách ví token:
*   **Bảng thành viên**: Danh sách tất cả tài khoản gồm tên, email, vai trò (admin/user), số dư token hiện tại, định danh VIP (Premium), và ngày đăng ký.
*   **Cập nhật vai trò (Change Role)**:
    *   Nhập Email của tài khoản cần đổi.
    *   Chọn vai trò mong muốn (`Admin` hoặc `User`).
    *   Bấm chọn **"Cập nhật vai trò"** (hệ thống sẽ yêu cầu xác nhận trước khi thực thi).
*   **Điều chỉnh ví Token (Adjust Tokens)**:
    *   Nhập Email tài khoản cần can thiệp.
    *   Nhập số lượng token cần cộng (hoặc trừ - nhập dấu trừ `-` phía trước).
    *   Bấm chọn **"Cập nhật Token"** để thực hiện bơm/rút token trực tiếp.

### 3.5. Cấu hình AI & Hệ Thống (AI Settings - `/admin/settings`)
Trang cấu hình cốt lõi hoạt động của chatbot RAG:
*   **Cài đặt Mô hình (Model Settings)**:
    *   Chọn mô hình LLM hoạt động (Gemini hoặc OpenAI).
    *   Điều chỉnh **Temperature (Độ sáng tạo)** (khuyến nghị `0.0` - `0.3` để tránh ảo giác y khoa).
    *   Nhập **System Prompt** (Prompt Ngự Y chỉ đạo hành vi và tôn chỉ trả lời của AI).
*   **Quản lý Khóa API (API Keys)**:
    *   Xem/sửa/xóa **API Key chính (Gemini API Key hoặc OpenAI API Key)**.
    *   Quản lý danh sách **Khóa dự phòng (Fallback Keys)**: Admin có thể thêm hoặc xóa nhiều khóa phụ để luân chuyển tự động khi khóa chính bị nghẽn (Gemini/OpenAI Fallback Keys).
    *   Cấu hình cổng kết nối **Ollama (Qwen API URL)** chạy local.
*   **Chính sách Phí Token (Fintech Cost Rules)**:
    *   **Tỷ giá quy đổi**: Số lượng token nhận được trên mỗi 1.000 VNĐ nạp vào.
    *   **Giá mỗi câu hỏi**: Số token bị trừ trên mỗi lượt chat hỏi đáp RAG.
*   **Root Admin Email**: Cấu hình địa chỉ email quản trị viên tối cao của hệ thống.

---
---

# 🇬🇧 ENGLISH (ENGLISH VERSION)

## 1. Public Landing Page & Login Process (Landing Page & Login)

### 1.1. Public Landing Page (`/`)
The welcome page that introduces the Traditional Vietnamese Medicine AI Assistant system using GraphRAG:
*   **Core Concepts & Architecture (GraphRAG)**: Visualizes how the system couples Neo4j database with LLMs to deliver verified medical answers and eliminate hallucination.
*   **Highlighted Features**: Covers interactive knowledge graph, TVM literature digitisation, privacy, and support.
*   **Quick Links**: Unauthenticated users can quickly access social profiles, privacy policy, terms of service, support, and contact details from the footer.

### 1.2. Login Process & Role-Based Access Control (RBAC)
The system utilizes Google Sign-In via the secure **OAuth 2.0** protocol.
1.  **Access the Login Page (`/login`)**:
    *   Click the **"Login"** button in the header of the landing page.
    *   The login view displays a clean leaf logo representing traditional herbs along with the project's sub-heading.
    *   A language switcher is available in the top-right corner, letting you toggle between **Vietnamese (🇻🇳 VI)** and **English (🇬🇧 EN)**.
    *   The system status light displays **"System Online / Hệ thống trực tuyến"**.
2.  **Sign in with Google**:
    *   Click the **"Continue with Google"** button.
    *   You will be securely redirected to the Google Account authentication page.
3.  **Role-Based Access Control (RBAC)**:
    *   **Admin Access**: If your Google email is registered as an administrator (via the `root_admin_email` variable or database roles), you will be routed straight to the **Admin Dashboard (`/admin`)**.
    *   **User Access**: For regular Google accounts, the system automatically initializes a startup token balance and redirects you to the **Main Chatbot Interface (`/chat`)**.

---

## 2. User Interface (User Panel)

Logging in with a standard account opens the user panel, giving you access to chat queries and knowledge visualization.

### 2.1. RAG Chat Window (`/chat`)
Designed as a premium, virtual medical dashboard:
*   **Submit Questions**: Type natural language queries regarding herbs or remedies (e.g., *"What is Motherwort used for?"*).
*   **3-Agent Workflow Status**: As you submit a message, visual indicators show the stage of the multi-agent system:
    1.  *NLU Agent* parsing intents and entities.
    2.  *Cypher Builder* generating graph queries.
    3.  *Synthesizer* generating the literature-aligned answer.
*   **Smart Entity Chips**:
    *   AI responses feature highlighted labels like `[Herb: Motherwort]`, `[Property: Cold]`.
    *   Users can click on these chips to quickly jump to the corresponding entity's detailed bio page.
*   **Step-by-step Audit Logs**:
    *   A **"Show Log"** icon is available below each response. Click it to view the raw Cypher query sent to Neo4j, the raw database output, and the source literature bibliography.

### 2.2. Interactive Graph Explorer (`/graph-explorer`)
Users can open a full-screen interactive view of the graph network:
*   **2D Dynamic Force-Directed Graph**:
    *   Herbs and remedies are rendered as nodes connected by relationship lines.
    *   Node colors represent different categories (e.g., green for Herbs, yellow for Properties, red for Remedies).
*   **Drag, Pan, and Zoom**:
    *   Left-click and drag nodes to adjust the graph layout.
    *   Use the mouse scroll wheel to zoom in or out of the network canvas.
*   **Relationship Highlighting (Focus Mode)**:
    *   Clicking a node dims the rest of the graph, highlighting only its direct connections.
*   **Functional Buttons**:
    *   **Back**: The left arrow button navigates back to the main chat interface (`/chat`).
    *   **Share**: Share the current graph perspective.
    *   **Export Data**: Click **"Export Data"** in the header to download the graph's JSON dataset for academic research.

### 2.3. User Profile & Token Recharge (Fintech / SePay)
*   **Wallet Balance**: View your email and current token balance at the top edge of the panel.
*   **Automatic Token Purchase**:
    *   Click **"Top Up / Nạp Token"**.
    *   Select your preferred token package (e.g., 2k, 10k, 20k, 50k, 100k VND).
    *   The app displays a **dynamic payment QR Code** containing the pre-configured bank transfer amount and encoded memo following the pattern `YHCT_CHATBOTNAPTOKEN<HEX_ID>`.
    *   Scan the QR code with your mobile banking application and approve the transaction.
    *   Once completed, the SePay Webhook updates your token balance in real-time (usually taking 3-5 seconds).

### 2.4. Public Documentation & Support Pages
Accessible to all visitors without logging in:
*   **Privacy Policy (`/privacy-policy`)**: Outlines data collection, storage, and privacy protocols.
*   **Terms of Service (`/terms-of-service`)**: Rules and agreements when utilizing the chatbot services.
*   **Data Deletion (`/data-deletion`)**: Provides a self-service tool enabling users to delete their entire chat history and personal account permanently by confirming with the word `"DELETE"`.
*   **Support (`/support`)**: Support request submission form.
*   **Contact (`/contact`)**: Complete developer team contact details.

---

## 3. Administrator Interface (Admin Panel)

Upon logging in with administrator privileges, you will gain access to the Admin Dashboard. The sidebar on the left provides easy navigation:

### 3.1. System Overview (`/admin`)
The default screen displaying the health and analytics of the system:
*   **Key Metrics (Cyber-Cards)**:
    *   **Revenue**: Total amount of money recharged via SePay (VND).
    *   **AI Queries**: Total number of AI questions processed.
    *   **Graph Entities**: Total node count currently stored in Neo4j AuraDB.
    *   **Users**: Number of registered accounts in the system.
*   **Daily Query Chart**: An interactive wave chart showing the system load and interaction rates in real-time.
*   **Export Data**: The **"Export Report"** button in the top right downloads statistical data for quick reporting.

### 3.2. Sync Knowledge & SEO (`/admin/seo`)
Management tool for website metadata and search presence:
*   **SEO Parameters**: Enter or modify **Site Title**, **Description**, and **Keywords** to optimize search engine performance.
*   **Logo & Favicon Upload**: Upload your customized Site Logo to update the branding across the system.
*   **Sync Settings**: Click the **"Save & Sync"** button to apply metadata updates globally to the site.

### 3.3. Transaction Management (Finance - `/admin/finance`)
Tools for transparent revenue tracking:
*   **Real-time Revenue Summary**: Displays actual earnings dynamically.
*   **Search Engine**: Easily filter logs by **User Email** or **Transaction ID**.
*   **Payment History Table**: Lists payment logs with: Email, Amount (VND), Tokens Granted, Status (Completed / Pending / Failed), Transaction Type (Automatic SePay or Admin Adjustment), and Creation Date.

### 3.4. User Management (`/admin/users`)
Allows monitoring user accounts and adjusting token wallets:
*   **User Directory**: Lists user profiles with email, role (admin/user), current token balance, VIP status (Premium), and registration date.
*   **Change Role**:
    *   Enter the user's email address.
    *   Select the target role (`Admin` or `User`).
    *   Click **"Change Role"** (a confirmation popup will appear to prevent accidental changes).
*   **Adjust Token Balances**:
    *   Enter the target user's email address.
    *   Specify the token amount to add (or subtract using a negative `-` sign).
    *   Click **"Update Tokens"** to immediately modify the user's wallet.

### 3.5. AI & System Settings (`/admin/settings`)
Configures the core AI execution parameters:
*   **Model Settings**:
    *   Set the active LLM engine (Gemini or OpenAI).
    *   Adjust **Temperature** (recommended: `0.0` - `0.3` to ensure medical precision and prevent hallucination).
    *   Input the **System Prompt** (governs chatbot tone and instruction guidelines).
*   **API Key Management**:
    *   View/edit/delete the **Primary Gemini API Key** or **OpenAI API Key**.
    *   Manage **Fallback Keys**: Add secondary API keys to enable automatic key rotation if the primary key gets rate-limited (Gemini/OpenAI Fallback Keys).
    *   Configure the local **Ollama connection endpoint (Qwen API URL)**.
*   **Fintech & Cost Rules**:
    *   **Tokens per 1000 VND**: Set how many tokens a user receives per 1,000 VND deposited.
    *   **Cost per Query**: Define the token cost deducted for each RAG chatbot query.
*   **Root Admin Email**: Configures the main administrator email for safety backups.
