# NGUYÊN LÝ HOẠT ĐỘNG: THANH TOÁN TỰ ĐỘNG QUA MÃ QR & CỘNG TOKEN

Hệ thống thanh toán tự động (Auto-Topup) không dựa vào việc "Mã QR tự biết ai chuyển", mà dựa vào một chuỗi thông tin liên kết chặt chẽ thông qua **Nội dung chuyển khoản (Transfer Content)** và **Webhook Ngân hàng**.

Dưới đây là nguyên lý hoạt động chi tiết từng bước:

## 1. Bí quyết cốt lõi: "Mã QR Động" và "Cú pháp chuyển khoản"

Mã QR mã hóa 3 thông tin quan trọng nhất mà ứng dụng ngân hàng cần:
1. **Số tài khoản nhận** (Của hệ thống).
2. **Số tiền cần chuyển** (Ví dụ: 20.000đ).
3. **Nội dung chuyển khoản** (Ví dụ: `NAP 123456`).

Bí quyết nằm ở **Nội dung chuyển khoản**. Mỗi khi một User bấm "Nạp tiền", Backend sẽ tạo ra một **Mã đơn hàng duy nhất** (ví dụ: `123456`) và lưu vào Database cùng với ID của User đó và Số tiền yêu cầu. Khi quét QR, nội dung này tự động được điền vào app ngân hàng của người dùng.

---

## 2. Luồng thực thi (User Flow & System Flow)

### Bước 1: Khởi tạo giao dịch (Frontend -> Backend)
- Người dùng nhập số tiền 20.000đ và bấm **Xác nhận nạp**.
- Frontend gọi API `/payment/create?amount_k=20`.
- Backend nhận yêu cầu:
  - Lấy `user_id` từ Token người dùng.
  - Tạo một Transaction mới trong Database: `[ID: 123456, UserID: 99, Amount: 20000, Status: Pending]`.
  - Sinh ra Cú pháp chuyển khoản: `NAP 123456`.
  - Trả về cho Frontend: URL ảnh VietQR chứa cấu hình sẵn Số tiền và Nội dung `NAP 123456`.

### Bước 2: Chờ thanh toán (Polling)
- Frontend hiển thị mã QR.
- Trong lúc này, Frontend liên tục gọi API `/payment/status/123456` (mỗi 5-6 giây) để hỏi Backend xem đơn hàng đã được thanh toán chưa.

### Bước 3: Người dùng quét mã và chuyển tiền
- Người dùng dùng App Ngân hàng quét QR. App tự điền sẵn số tiền `20.000` và nội dung `NAP 123456`. Người dùng nhập mã PIN và chuyển thành công.

### Bước 4: Ngân hàng báo tin (Webhook - SePay)
- Tiền vào tài khoản hệ thống.
- Ngân hàng gửi tin báo biến động số dư.
- Dịch vụ trung gian (như SePay/Casso) đọc tin nhắn biến động và ngay lập tức gửi một **Webhook (HTTP POST)** về Backend của bạn.
- Payload Webhook có dạng (như định nghĩa trong `schemas.py`):
  ```json
  {
    "transferAmount": 20000,
    "content": "NGUYEN VAN A chuyen tien NAP 123456",
    "transferType": "in"
  }
  ```

### Bước 5: Backend xử lý và Cộng Token
Khi Backend nhận được Webhook, nó sẽ thực hiện các logic sau:
1. **Trích xuất mã:** Quét chuỗi `content` để tìm Regex khớp với cú pháp hệ thống (Tìm chữ `NAP 123456`).
2. **Đối chiếu Database:** Tìm trong CSDL xem có giao dịch nào mang ID `123456` đang ở trạng thái `Pending` không.
3. **Kiểm tra số tiền:** Kiểm tra xem `transferAmount` (20.000) từ Webhook có khớp (hoặc lớn hơn/bằng) số tiền của Transaction trong CSDL không (Chống người dùng tự sửa số tiền khi chuyển khoản).
4. **Cộng Token:** Nếu hợp lệ, hệ thống lấy `UserID` được gắn với giao dịch `123456`.
   - Quy đổi 20.000đ = 200.000 Token.
   - Cộng thẳng vào số dư Token của User.
5. **Hoàn tất:** Cập nhật trạng thái giao dịch `123456` thành `Completed`.

### Bước 6: Frontend nhận kết quả
- Ở chu kỳ hỏi thăm (polling) tiếp theo, API `/payment/status/123456` sẽ trả về `status: "completed"`.
- Frontend lập tức tắt giao diện quét QR, hiện thông báo thành công và gọi hàm `refreshUser()` để cập nhật lại số dư Token hiển thị trên màn hình.

---

## 3. Tóm tắt ưu điểm của kiến trúc này

- **Không cần nhập tay:** Người dùng không cần tự gõ số tài khoản, số tiền hay nội dung. Tránh sai sót.
- **Tính chính danh:** Một mã QR sinh ra gắn chặt với `1 User + 1 Số tiền cụ thể`. Nội dung chuyển khoản là chiếc chìa khóa duy nhất kết nối tiền của ngân hàng với tài khoản hệ thống.
- **Bảo mật:** Dù người dùng có dùng tool để sửa số tiền trên app ngân hàng (ví dụ sửa từ 20k thành 1k), Webhook trả về Backend vẫn là số tiền thực tế (1k). Hệ thống sẽ phát hiện số tiền không khớp với đơn hàng và sẽ KHÔNG cộng Token.

## 4. Các dịch vụ cần thiết để triển khai
1. **VietQR API:** (như vietqr.io) dùng để tạo ảnh QR.
2. **Dịch vụ lắng nghe số dư:** SePay, Casso, PayOS... dùng để lấy biến động số dư tự động thay vì phải tự viết bot cắm vào app ngân hàng.