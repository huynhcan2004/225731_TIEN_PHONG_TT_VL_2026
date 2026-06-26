"""
Module: app/routers/base.py
Chức năng: Chứa các endpoint cơ bản về hệ thống.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.config import settings
from app.models.base_db import db
import json
from pydantic import BaseModel

router = APIRouter(tags=["Hệ thống"])

DEFAULT_DOCS = {
    "privacy-policy": """# Chính sách quyền riêng tư
*Cập nhật lần cuối: Ngày 16 tháng 06 năm 2026*

Hệ thống Tri thức Y học Cổ truyền **YHCT Diamond** cam kết bảo vệ quyền riêng tư và thông tin cá nhân của bạn. Chính sách này giải thích cách chúng tôi thu thập, sử dụng và chia sẻ thông tin khi bạn sử dụng ứng dụng và các dịch vụ liên quan của chúng tôi.

### 1. Thông tin chúng tôi thu thập
Chúng tôi chỉ thu thập các thông tin cần thiết để cung cấp và cải thiện dịch vụ hỏi đáp y học cổ truyền:
* **Thông tin định danh cá nhân:** Địa chỉ email, tên hiển thị, và ảnh đại diện được cung cấp thông qua xác thực tài khoản Google (Google Sign-In).
* **Lịch sử hội thoại & Truy vấn:** Nội dung các câu hỏi hỏi đáp và các từ khóa bạn nhập vào hệ thống để truy xuất tri thức nhằm cải thiện độ chính xác của chatbot AI và hiển thị lại lịch sử cuộc trò chuyện của bạn.
* **Dữ liệu giao dịch:** Nhật ký nạp tiền, số dư token và trạng thái thanh toán (chúng tôi không lưu thông tin thẻ ngân hàng hoặc thông tin tài khoản ngân hàng trực tiếp của bạn).

### 2. Mục đích sử dụng thông tin
* Cung cấp quyền truy cập và xác thực người dùng an toàn thông qua Google.
* Hiển thị, gom nhóm và lưu trữ lịch sử hội thoại cá nhân của bạn.
* Vận hành và tối ưu hóa hệ thống truy vấn đồ thị tri thức (GraphRAG) để trả lời chính xác câu hỏi của bạn.
* Quản lý số dư ví token và đối soát các giao dịch nạp tiền.
* Nghiên cứu khoa học, cải tiến thuật toán trích xuất tri thức và giảm thiểu ảo giác của mô hình ngôn ngữ lớn (LLM).

### 3. Cookies và Lưu trữ cục bộ
Chúng tôi sử dụng **LocalStorage** để lưu trữ khóa mã hóa phiên làm việc của bạn (JWT access token). Chúng tôi không sử dụng bất kỳ cookie theo dõi quảng cáo nào của bên thứ ba. LocalStorage giúp bạn duy trì trạng thái đăng nhập mà không cần nhập lại thông tin trong mỗi phiên làm việc.

### 4. Chia sẻ thông tin với bên thứ ba
> **Cam kết quan trọng:** Chúng tôi **KHÔNG** bán, chia sẻ hoặc cho thuê dữ liệu cá nhân hay lịch sử hỏi đáp của bạn cho bất kỳ bên thứ ba nào vì mục đích tiếp thị hoặc thương mại.
>
> Dữ liệu của bạn được xử lý nội bộ thông qua các API bảo mật của chúng tôi kết nối tới các dịch vụ Cloud đáng tin cậy (như Google Vertex AI để sinh câu trả lời) theo các thỏa thuận bảo mật nghiêm ngặt. Dữ liệu gửi đi cho mô hình LLM là ẩn danh và không chứa thông tin định danh cá nhân của bạn.

### 5. Quyền của người dùng & Cách xóa dữ liệu
Bạn có toàn quyền đối với dữ liệu cá nhân của mình, bao gồm:
* Xem và đọc lại toàn bộ lịch sử hỏi đáp của bạn trong ứng dụng.
* Chủ động xóa từng cuộc hội thoại cụ thể trực tiếp tại thanh Menu Chat.
* **Yêu cầu xóa tài khoản vĩnh viễn:** Bạn có thể tự thực hiện xóa tài khoản và toàn bộ dữ liệu đi kèm (lịch sử chat, giao dịch, nhật ký) ngay lập tức tại trang [Yêu cầu xóa dữ liệu](/data-deletion) mà không cần sự can thiệp của quản trị viên.
* Gửi yêu cầu xóa dữ liệu hoặc yêu cầu hỗ trợ qua email hỗ trợ của chúng tôi.

***

### Bảo mật thông tin của bạn
Chúng tôi áp dụng các biện pháp bảo mật mã hóa và quản lý truy cập nghiêm ngặt để bảo vệ dữ liệu trên cơ sở dữ liệu SQLite và Đồ thị Neo4j. Mọi kết nối truyền tải dữ liệu giữa trình duyệt của bạn và máy chủ đều được mã hóa bằng giao thức HTTPS/TLS bảo mật.""",

    "terms-of-service": """# Điều khoản sử dụng
*Cập nhật lần cuối: Ngày 16 tháng 06 năm 2026*

Chào mừng bạn đến với **YHCT Diamond**. Bằng việc truy cập hoặc sử dụng ứng dụng của chúng tôi, bạn đồng ý tuân thủ và chịu sự ràng buộc bởi các Điều khoản sử dụng này. Vui lòng đọc kỹ trước khi sử dụng dịch vụ.

> ### Tuyên bố miễn trừ trách nhiệm y văn & AI
> * **Không thay thế tư vấn y khoa:** Các câu trả lời từ chatbot AI của YHCT Diamond được tổng hợp từ dữ liệu y văn cổ truyền (ví dụ: cuốn "Những cây thuốc và vị thuốc Việt Nam") và công nghệ GraphRAG. Các thông tin này **CHỈ MANG TÍNH CHẤT THAM KHẢO**.
> * **Không sử dụng để tự điều trị:** Tuyệt đối không tự ý áp dụng các bài thuốc hay vị thuốc mà không có sự chỉ định, thăm khám trực tiếp từ bác sĩ hoặc thầy thuốc y học cổ truyền có chứng chỉ hành nghề.
> * **Trách nhiệm người dùng:** Người dùng tự chịu hoàn toàn trách nhiệm đối với việc sử dụng hoặc áp dụng các thông tin do hệ thống cung cấp. Ban phát triển không chịu bất kỳ trách nhiệm pháp lý nào đối với tổn hại sức khỏe phát sinh do tự ý áp dụng thông tin từ chatbot.

### 1. Điều kiện sử dụng và Đăng ký tài khoản
Để sử dụng đầy đủ các tính năng của ứng dụng (hỏi đáp AI, bản đồ tri thức), bạn cần đăng nhập thông qua tài khoản Google được ủy quyền. Bạn có trách nhiệm bảo mật phiên đăng nhập của mình và chịu trách nhiệm về tất cả các hoạt động xảy ra dưới tài khoản của bạn.

### 2. Chính sách hoạt động của AI (GraphRAG)
Hệ thống của chúng tôi áp dụng cơ chế **"Ngự Y Kim Cương"** kết hợp Đồ thị tri thức (Neo4j) để loại bỏ tối đa hiện tượng ảo giác (hallucination) thường gặp ở các LLM thông thường. Tuy nhiên:
* Mặc dù đã hạn chế ảo giác bằng cách đối chiếu thông tin đồ thị, thông tin y văn dịch từ chữ Nôm/chữ Hán hoặc các ghi chép cổ có thể có các điểm dị biệt hoặc không còn phù hợp hoàn toàn với y học hiện đại.
* Hệ thống luôn hiển thị các liên kết nguồn gốc thực thể trong đồ thị tri thức (Ví dụ: tên sách, chương, trang vị thuốc) ở phần cuối câu trả lời để người dùng có thể tự đối chiếu và kiểm chứng.

### 3. Hành vi bị cấm
Khi sử dụng YHCT Diamond, bạn đồng ý không:
* Sử dụng bất kỳ công cụ quét tự động (scraping), bot hoặc script nào để thu thập dữ liệu đồ thị tri thức từ hệ thống của chúng tôi.
* Cố tình tấn công phá hoại, tiêm nhiễm mã độc (Cypher injection, SQL injection) hoặc làm gián đoạn dịch vụ máy chủ.
* Sử dụng chatbot để tạo ra hoặc phát tán các nội dung bạo lực, khiêu dâm, chống phá nhà nước hoặc vi phạm pháp luật.
* Giả mạo các giao dịch nạp tiền hoặc tìm cách can thiệp vào số dư ví token một cách trái phép.

### 4. Giới hạn trách nhiệm pháp lý
Hệ thống được cung cấp trên cơ sở "nguyên trạng" (as-is) và "sẵn có". Ban phát triển không đưa ra bất kỳ bảo đảm nào, dù rõ ràng hay ngụ ý, về tính chính xác tuyệt đối của mọi câu trả lời AI trong mọi tình huống lâm sàng thực tế. Chúng tôi từ chối chịu trách nhiệm đối với mọi thiệt hại trực tiếp hoặc gián tiếp liên quan đến sức khỏe, kinh tế, hoặc pháp lý phát sinh từ việc sử dụng sai lệch thông tin của ứng dụng.

### 5. Thay đổi điều khoản và Chấm dứt dịch vụ
Chúng tôi có quyền cập nhật hoặc điều chỉnh Điều khoản sử dụng này bất cứ lúc nào mà không cần thông báo trước. Việc bạn tiếp tục sử dụng ứng dụng sau khi các thay đổi được đăng tải đồng nghĩa với việc chấp thuận các điều khoản mới. Chúng tôi cũng có quyền tạm ngừng hoặc khóa tài khoản vĩnh viễn đối với bất kỳ người dùng nào vi phạm nghiêm trọng các quy định tại điều khoản này.""",

    "data-deletion": """# Yêu cầu xóa dữ liệu
*Chính sách & Công cụ tự phục vụ xóa tài khoản*

### Quy trình và Cam kết xóa dữ liệu
Theo quy định của Google và Apple về bảo vệ quyền riêng tư của người dùng, YHCT Diamond cho phép bạn xóa hoàn toàn tài khoản của mình. Khi bạn gửi yêu cầu xóa:
* **Thông tin cá nhân:** Tên, email, ảnh đại diện lấy từ Google OAuth sẽ bị xóa vĩnh viễn khỏi Database.
* **Lịch sử chatbot:** Toàn bộ các tin nhắn, cuộc hội thoại hỏi đáp y khoa sẽ bị xóa sạch (xóa vật lý khỏi SQLite).
* **Số dư & Giao dịch:** Ví token, lịch sử biến động số dư và các giao dịch nạp tiền sẽ bị hủy bỏ hoàn toàn.
* **Thời gian xử lý:** Tự động xóa ngay lập tức nếu thực hiện qua công cụ dưới đây, hoặc tối đa 30 ngày nếu gửi yêu cầu thủ công qua Email.""",

    "support": """[
      {"question": "Hệ thống YHCT Diamond là gì?", "answer": "YHCT Diamond là một nền tảng Trí tuệ Nhân tạo hỗ trợ nghiên cứu và tra cứu Y học Cổ truyền Việt Nam. Hệ thống kết hợp Đồ thị tri thức (Knowledge Graph) được số hóa từ các y văn kinh điển và kỹ thuật GraphRAG (Retrieval-Augmented Generation) nhằm đem lại khả năng trả lời câu hỏi chính xác nhất."},
      {"question": "Làm thế nào hệ thống loại bỏ hiện tượng 'ảo giác' (hallucination)?", "answer": "Hệ thống sử dụng bộ não phân tích ngôn ngữ (NLU Engine) chuyển câu hỏi tự nhiên của bạn thành truy vấn đồ thị Cypher. Hệ thống sẽ rút trích tri thức thực tế từ cơ sở dữ liệu Neo4j đã được xác thực (Gold Linked Data) và chỉ cung cấp dữ liệu thật này cho mô hình ngôn ngữ Gemini để tổng hợp câu trả lời. LLM được lập trình theo quy tắc nghiêm ngặt: không tự ý bịa đặt hoặc suy diễn ra ngoài ngữ cảnh y văn thực tế."},
      {"question": "Nguồn dữ liệu của YHCT Diamond lấy từ đâu?", "answer": "Dữ liệu cốt lõi của hệ thống được trích xuất tự động bằng OCR nâng cao (Google Document AI) từ các bộ y văn chính thống của Việt Nam, tiêu biểu là cuốn sách kinh điển 'Những cây thuốc và vị thuốc Việt Nam' của GS. Đỗ Tất Lợi, sau đó được cấu trúc hóa thành các nút thực thể (Vị thuốc, Hoạt chất, Bộ phận dùng, Dược lý, Bài thuốc) và các mối quan hệ liên kết trên Neo4j."},
      {"question": "Tôi có thể tự ý bốc thuốc và uống theo hướng dẫn của Chatbot không?", "answer": "Không! Mọi câu trả lời của chatbot chỉ nhằm phục vụ mục đích nghiên cứu học thuật, tìm hiểu thông tin và tra cứu y văn cổ. Tuyệt đối không tự ý áp dụng các bài thuốc nếu không có sự chỉ định và giám sát trực tiếp từ các bác sĩ chuyên khoa hoặc các lương y có giấy phép hành nghề y học cổ truyền."},
      {"question": "Ví Token dùng để làm gì và nạp tiền như thế nào?", "answer": "Mỗi câu hỏi hỏi đáp RAG chuyên sâu hoặc thao tác phân tích bản đồ tri thức sẽ tiêu tốn một lượng token nhất định của tài khoản để chi trả cho tài nguyên máy chủ và API. Bạn có thể nạp thêm token thông qua cổng đối soát tự động SePay bằng cách chuyển khoản ngân hàng quét mã QR động tại trang quản lý Tài chính của bạn."}
    ]""",

    "contact": """{
      "description": "Hệ thống **YHCT Diamond Knowledge Graph** được phát triển bởi nhóm nghiên cứu trí tuệ nhân tạo, tập trung vào việc áp dụng công nghệ đồ thị tri thức và xử lý ngôn ngữ tự nhiên để bảo tồn và khai thác giá trị của y học cổ truyền nước nhà.",
      "email": "support@yhct-diamond.vn",
      "unit": "Trường Đại học Công nghệ thông tin - ĐHQG TP.HCM",
      "office": "Khu phố 6, P. Linh Trung, TP. Thủ Đức, TP. Hồ Chí Minh, Việt Nam",
      "github": "https://github.com/huynhcan2004/225731_TIEN_PHONG_TT_VL_2026",
      "copyright": "Các tài liệu y văn được sử dụng làm cơ sở tri thức (Knowledge Graph) đều thuộc về tác giả gốc và nhà xuất bản gốc. Hệ thống chỉ thực hiện lập chỉ mục thực thể phục vụ mục đích tìm kiếm khoa học phi lợi nhuận."
    }""",

    "sidebar": """[
      {"path": "/privacy-policy", "label": "Chính sách bảo mật", "icon": "Shield", "description": "Quyền riêng tư & Thu thập dữ liệu"},
      {"path": "/terms-of-service", "label": "Điều khoản sử dụng", "icon": "FileText", "description": "Quy định sử dụng & Chính sách AI"},
      {"path": "/data-deletion", "label": "Yêu cầu xóa dữ liệu", "icon": "Trash2", "description": "Xóa tài khoản & Dữ liệu cá nhân"},
      {"path": "/support", "label": "Hỗ trợ & FAQ", "icon": "HelpCircle", "description": "Câu hỏi thường gặp & Trợ giúp"},
      {"path": "/contact", "label": "Liên hệ", "icon": "Mail", "description": "Thông tin liên hệ nhà phát triển"}
    ]"""
}

@router.get("/", summary="Lời chào hệ thống")
async def root():
    return {
        "message": f"Chào mừng đến với {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "status": "online"
    }

@router.get("/health", summary="Kiểm tra sức khỏe hệ thống")
async def health_check():
    """
    Kiểm tra trạng thái kết nối của API và Cơ sở dữ liệu.
    """
    db_status = True if db and db.graph else False
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": db_status,
        "environment": "development"
    }

@router.get("/docs/{page_id}", summary="Lấy nội dung trang tài liệu công khai")
async def get_doc(page_id: str):
    if page_id not in DEFAULT_DOCS:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang tài liệu")
    
    val = db.get_setting("doc_" + page_id, "")
    if not val:
        val = DEFAULT_DOCS[page_id]
        
    if page_id in ["support", "contact", "sidebar"]:
        try:
            return {"page_id": page_id, "content": json.loads(val)}
        except Exception:
            return {"page_id": page_id, "content": json.loads(DEFAULT_DOCS[page_id])}
            
    return {"page_id": page_id, "content": val}

@router.get("/settings/public", summary="Lấy cấu hình SEO & Logo công khai")
async def get_public_settings():
    return {
        "site_title": db.get_setting("site_title", "Chatbot YHCT Diamond"),
        "site_description": db.get_setting("site_description", "Hệ thống tra cứu vị thuốc và bài thuốc Y học cổ truyền dựa trên Đồ thị tri thức"),
        "site_keywords": db.get_setting("site_keywords", "YHCT, chatbot, AI, đồ thị tri thức, đông y"),
        "site_logo": db.get_setting("site_logo", "")
    }

class SupportMessageRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str

@router.post("/support/submit", summary="Gửi yêu cầu hỗ trợ và liên hệ")
async def submit_support_message(payload: SupportMessageRequest):
    """
    Tiếp nhận yêu cầu hỗ trợ hoặc liên hệ từ người dùng:
    1. Lưu thông tin vào CSDL SQLite.
    2. Gửi email thông báo về Gmail của Admin (nếu cấu hình SMTP).
    """
    if not payload.name.strip() or not payload.email.strip() or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Vui lòng điền đầy đủ các thông tin bắt buộc!")
    
    # 1. Lưu vào CSDL
    try:
        msg_id = db.save_support_message(
            name=payload.name.strip(),
            email=payload.email.strip(),
            subject=payload.subject.strip() or "Yêu cầu hỗ trợ/liên hệ",
            message=payload.message.strip()
        )
    except Exception as e:
        print(f"[ERROR] Không thể lưu tin nhắn hỗ trợ vào CSDL: {e}")
        msg_id = None

    # 2. Gửi email cho Admin
    email_sent = False
    from app.config import settings
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or db.get_setting("root_admin_email", "")
    
    if not admin_email:
        # Thử lấy email admin đầu tiên từ users làm fallback
        conn = db._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            if row:
                admin_email = row['email']
        except Exception:
            pass
        finally:
            conn.close()

    # Lấy thông số SMTP
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USERNAME
    smtp_pass = settings.SMTP_PASSWORD

    if smtp_user and smtp_pass:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        target_email = admin_email or smtp_user
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = target_email
            msg['Subject'] = f"[YHCT Diamond] {payload.subject or 'Liên hệ mới'}"
            
            body_text = f"""
Có một yêu cầu hỗ trợ/liên hệ mới từ hệ thống YHCT Diamond:

- Họ tên người gửi: {payload.name}
- Email liên hệ: {payload.email}
- Chủ đề: {payload.subject or 'Không có chủ đề'}
- Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Nội dung chi tiết:
----------------------------------------
{payload.message}
----------------------------------------

---
Tin nhắn này được gửi tự động từ máy chủ API YHCT Diamond.
"""
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            # Kết nối gửi mail
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [target_email], msg.as_string())
            server.quit()
            email_sent = True
            print(f"[SMTP] Đã gửi mail thành công tới {target_email}")
        except Exception as e:
            print(f"[SMTP ERROR] Lỗi gửi email: {str(e)}")
    else:
        print("[SMTP] SMTP_USERNAME hoặc SMTP_PASSWORD chưa được cấu hình. Chỉ lưu tin nhắn vào CSDL.")

    return {
        "status": "success",
        "message": "Đã tiếp nhận yêu cầu của huynh thành công!",
        "message_id": msg_id,
        "email_sent": email_sent
    }