# Individual Report: Lab 3 - VinFast Smart Sales Agent

- **Student Name**: Ngô Đắc Lãm
- **Student ID**: 2A202600655
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Vai trò chính trong nhóm: **Merge code & tích hợp API giữa Frontend và Backend (Integration Engineer)**

### 1.1 Giải quyết Merge Conflict

Sau khi các thành viên phát triển song song trên các nhánh khác nhau (`feature/backend-api`, `feature/frontend-ui`, `feature/llm-agent`), tôi chịu trách nhiệm **merge code toàn bộ** và giải quyết các xung đột (conflict) trong quá trình hợp nhất.

- **Modules liên quan đến merge conflict**:
  - `src/services/chat_service.py` — Conflict giữa phiên bản logging đơn giản của HEAD và phiên bản telemetry có cấu trúc (`AGENT_ERROR_FALLBACK`). Đã gộp cả hai để giữ nguyên tính năng của cả hai nhánh.
  - `src/api/main.py` — Conflict giữa cấu hình CORS và cơ chế xử lý lỗi toàn cục (`global_exception_handler`).
  - `src/api/static/app.js` — Conflict giữa phiên bản giao diện chat cũ và phiên bản nâng cấp mới của Frontend.
  - `src/rag/chunking.py` — Conflict giữa logic chia chunk theo cấu trúc `vehicles` của một thành viên và logic chia chunk theo `detailed_products` (dữ liệu sản phẩm web-scraped) của thành viên khác.

- **Code Highlights**:
  - Trong `chat_service.py`, đã hợp nhất block conflict để **giữ đồng thời** cả hai cách log lỗi:
    ```python
    logger.info(f"Error running agent, falling back: {e}")
    logger.log_event("AGENT_ERROR_FALLBACK", {
        "user_id": user_id, "error": str(e), "message": message
    })
    ```

### 1.2 Tích hợp API — Kết nối Frontend Static với Backend FastAPI

Toàn bộ frontend của dự án nằm trong `src/api/static/` (HTML + CSS + JS thuần) và cần gọi vào Backend API. Tôi chịu trách nhiệm xây dựng lớp tích hợp này.

- **Modules được triển khai / chỉnh sửa**:
  - `src/api/main.py` — Thêm 3 adapter endpoints mới:
    - `GET /api/users` — Trả về danh sách 3 user giả lập cho sidebar Frontend.
    - `GET /api/chat/{user_id}/history` — Ánh xạ lịch sử tin nhắn từ DB sang định dạng `{sender, text}` mà Frontend yêu cầu.
    - `POST /api/chat` — Nhận tin nhắn từ Frontend, gọi `handle_chat()` của Agent, tính `latency_ms`, bổ sung thông tin `model` và `provider`, trả về response đầy đủ.
  - `src/api/main.py` — Cấu hình FastAPI **serve static files** tại `/static` và **phục vụ `index.html`** tại route gốc `/` để Frontend hoạt động trực tiếp qua server API.
  - `src/api/static/app.js` — Viết lại toàn bộ logic kết nối: gọi đúng endpoint adapter, xử lý `pending_action` (hiển thị card xác nhận đặt lịch lái thử), hiển thị bảng Markdown động, render nhật ký tool calls (`ReAct Tool Log Panel`).

- **Documentation**: Frontend gửi `POST /api/chat` → `main.py` router nhận, gọi `handle_chat()` trong `chat_service.py` → `chat_service` gọi `ReActAgent` → Agent dùng `ToolExecutor` để gọi các tools (RAG lookup, so sánh xe, tính tiền...) → Kết quả trả về theo chuỗi ngược lại ra Frontend.

---

## II. Debugging Case Study (10 Points)

### Lỗi 1: `422 Unprocessable Content` khi Frontend gửi chat

- **Mô tả lỗi**: Sau khi tích hợp endpoint `/api/chat`, mọi lần gửi tin nhắn từ giao diện đều trả về `422 Unprocessable Content` — FastAPI từ chối parse request.
- **Nguồn log**: Terminal server in ra `INFO: 127.0.0.1:55923 - "POST /api/chat HTTP/1.1" 422`.
- **Chẩn đoán**: Pydantic schema `ChatRequest` định nghĩa 3 trường bắt buộc (`user_id`, `message`, `confirm_action_id`). Frontend chỉ gửi 2 trường (`user_id`, `message`). Dù `confirm_action_id` được khai báo là `Optional`, cách dùng `Field(default=None, examples=[None])` không đủ để Pydantic bỏ qua khi key hoàn toàn vắng mặt.
- **Giải pháp**:
  1. Sửa schema `src/api/schemas.py`: đổi `confirm_action_id: Optional[str] = Field(...)` thành `confirm_action_id: Optional[str] = None`.
  2. Sửa `app.js`: thêm `confirm_action_id: null` vào JSON payload gửi đi để luôn đảm bảo đủ các trường.

### Lỗi 2: `SyntaxError` khi khởi động server — Merge conflict chưa giải quyết

- **Mô tả lỗi**: Server crash ngay khi khởi động với thông báo `SyntaxError: invalid decimal literal` tại dòng 132 của `chat_service.py`.
- **Nguồn log**: Traceback Python trỏ đến ký tự `>` trong dòng `>>>>>>> 578728fb...` — đây là marker kết thúc của Git conflict.
- **Chẩn đoán**: Git merge bị interrupted, các marker conflict (`<<<<<<<`, `=======`, `>>>>>>>`) chưa được xóa khỏi file Python. Python không thể parse các ký tự này như code hợp lệ.
- **Giải pháp**: Đọc kỹ cả hai phiên bản trong block conflict, hợp nhất logic của cả hai (giữ `logger.info` đơn giản + `logger.log_event` có cấu trúc), xóa toàn bộ marker, commit lại.

### Lỗi 3: `0.0.0.0` không mở được trong trình duyệt Windows

- **Mô tả lỗi**: Sau khi server khởi động thành công, truy cập `http://0.0.0.0:8000` trên Windows thì báo "Hmm… can't reach this page".
- **Chẩn đoán**: `0.0.0.0` là địa chỉ lắng nghe trên tất cả interface nhưng không phải địa chỉ có thể truy cập từ trình duyệt trên Windows. Windows không định tuyến gói tin đến `0.0.0.0`.
- **Giải pháp**: Dùng `http://localhost:8000` hoặc `http://127.0.0.1:8000` để truy cập.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: Khối `Thought` trong ReAct Agent cho phép hệ thống "suy nghĩ" trung gian trước khi hành động — điều mà một Chatbot thông thường không có. Ví dụ: khi khách hỏi *"So sánh VF5 và VF6, tính thêm trả trước 30% VF6 giúp tôi"*, Chatbot trả lời thiếu hoặc bịa số, còn Agent tự chia thành 2 bước: gọi `compare_vehicles` rồi gọi `calculate`, hai bước riêng biệt, kết quả chính xác.

2. **Reliability**: Agent thực tế chậm hơn và đắt hơn Chatbot đơn giản ở các câu hỏi ngắn, trực tiếp như *"VF5 màu mấy?"*. Trong trường hợp này, LLM tốn thêm token để suy nghĩ và gọi tool không cần thiết, trong khi Chatbot có thể trả lời ngay từ system prompt.

3. **Observation**: Bước Observation trong vòng lặp ReAct đóng vai trò "kiểm thực" — kết quả trả về từ tool (dù đúng hay lỗi) được đưa trở lại LLM để điều chỉnh bước tiếp theo. Đây là điều tôi thấy rõ nhất khi debug: khi tool trả về `{"ok": false, "error": "..."}`, Agent thường tự điều chỉnh lại argument và thử lại, thay vì crash.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Tách riêng Frontend thành một dịch vụ độc lập (React/Vite app) thay vì serve static qua FastAPI, kết nối qua CORS chuẩn production. Điều này giúp Frontend và Backend scale độc lập.
- **Safety**: Thêm lớp Guardrails kiểm tra đầu vào trước khi Agent xử lý — đặc biệt với các tool có side-effect như `schedule_test_drive` (tạo record trong DB). Cần bắt buộc xác nhận từ người dùng trước khi ghi vào hệ thống.
- **Performance**: Cache kết quả của `lookup_vehicle` và `compare_vehicles` (TTL ~5 phút) để giảm độ trễ và tiết kiệm chi phí gọi RAG lặp lại cho cùng một câu hỏi.

---

> [!NOTE]
> Báo cáo này mô tả đóng góp thực tế của Ngô Đắc Lãm trong vai trò Integration Engineer — merge code và kết nối API cho dự án VinFast Smart Sales Agent (Bàn A4, Lab 3).
