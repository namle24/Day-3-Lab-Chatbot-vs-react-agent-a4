# Sơ đồ Luồng (Flowchart) & Insights Nhóm - Lab 3: Chatbot vs ReAct Agent

Tài liệu này trình bày sơ đồ tư duy hệ thống (Visual logic diagram) của Trợ lý Bán hàng Thông minh VinFast và các bài học kinh nghiệm thu được từ quá trình triển khai thực tế.

---

## 📊 1. Sơ đồ Luồng Hoạt động Hệ thống (Flowchart)

Dưới đây là sơ đồ chi tiết biểu diễn luồng đi của một yêu cầu từ khi khách hàng nhập tin nhắn trên Web UI cho đến khi nhận được phản hồi, bao gồm cả 3 lớp bảo vệ (Guardrails) và vòng lặp suy luận ReAct.

```text
       [ Khách hàng gửi tin nhắn trên Web UI ]
                         │
                         ▼
             ┌───────────────────────┐
             │   Lớp 1: INPUT GUARD  │
             └───────────┬───────────┘
                         │
        Vi phạm          ├─────────────────► [ Trả về phản hồi từ chối ]
  (Prompt Injection)     │                         (Cảnh báo bảo mật)
                         ▼ Hợp lệ                  ▲
               ┌───────────────────┐               │
               │ Tải lịch sử từ DB │               │
               └─────────┬─────────┘               │
                         │                         │
                         ▼                         │
               ┌───────────────────┐               │
         ┌────►│ Vòng lặp ReAct    │               │
         │     └─────────┬─────────┘               │
         │               │                         │
         │               ▼                         │
         │     ┌───────────────────┐               │
         │     │ Thought: Phân tích│               │
         │     └─────────┬─────────┘               │
         │               │                         │
         │               ▼                         │
         │     /───────────────────\               │
         │    <      Quyết định?    >              │
         │     \───────────────────/               │
         │               │                         │
         │               ├─────────────────────────┤ Đủ thông tin
         │               │ Cần gọi công cụ         │ (Final Answer)
         │               ▼                         ▼
         │     ┌───────────────────┐     ┌───────────────────┐
         │     │ Lớp 2: TOOL GUARD │     │ Tổng hợp câu      │
         │     └─────────┬─────────┘     │ trả lời tiếng Việt│
         │               │               └─────────┬─────────┘
         │  Phát hiện    ├──────────────┐          │
         │  mã độc / lỗi │              │          │
         │               ▼              ▼ An toàn  │
         │       [ Chặn & Báo lỗi ]  [ Thực thi ]  │
         │               │           (Vehicle/Calc)│
         │               │              │          │
         │               ▼              ▼          │
         │     /───────────────────────────\       │
         │    <     Phân loại tác vụ?       >      │
         │     \───────────────────────────/       │
         │               │              │          │
         │   Tra cứu/Tính│              │ Đăng ký  │
         │   toán thường │              │ lái thử  │
         │               ▼              ▼          │
         │     ┌───────────────────┐ ┌─────────────┴─────┐
         │     │ Observation:      │ │ Lớp 3: OUTPUTGUARD│
         │     │ Kết quả từ Tool   │ │(Chặn chốt ngầm)   │
         └─────┴───────────────────┘ └──────┬────────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │ Yêu cầu xác │
                                     │ nhận từ khách│
                                     └──────┬──────┘
                                            │
                                            ▼
                                     /─────────────\
                                    < Khách ĐỒNG Ý? >
                                     \──────┬──────/
                                            │
                                   ĐỒNG Ý   ├──────────────┐ Từ chối / Khác
                                            ▼              ▼
                                     ┌─────────────┐ ┌─────────────┐
                                     │ Chốt lịch   │ │ Hủy chốt    │
                                     │ vào DB      │ │ Tiếp tục tư │
                                     │ (Commit)    │ │ vấn (Cancel)│
                                     └──────┬──────┘ └──────┬──────┘
                                            │               │
                                            ▼               ▼
                                     [ Hiển thị phản hồi lên Web UI ]
```
---

## 💡 2. Các Insights & Bài học Kinh nghiệm Nhóm (Group Learning Points)

### 2.1. Phân biệt Chatbot truyền thống vs ReAct Agent
*   **Chatbot truyền thống (Baseline Chatbot)**:
    *   **Cơ chế**: Nhận prompt đầu vào và cố gắng tạo ra câu trả lời trực tiếp trong một lượt sinh (Single forward pass).
    *   **Hạn chế**: Dễ gặp hiện tượng ảo tưởng (Hallucination) về thông số kỹ thuật xe hoặc thực hiện sai lệch các phép tính phức tạp (như tính 30% giá lăn bánh của dòng xe VF 8). Chatbot không có khả năng tự sửa sai khi thiếu thông tin.
*   **ReAct Agent (Thought -> Action -> Observation)**:
    *   **Cơ chế**: Chia nhỏ bài toán phức tạp thành nhiều bước suy luận trung gian.
    *   **Ưu điểm**: 
        *   Khi cần dữ liệu thông số: Biết gọi công cụ tra cứu (`vehicle_lookup`).
        *   Khi cần tính toán tài chính: Sử dụng công cụ máy tính (`calculator`) để tính toán số học chuẩn xác thay vì để LLM tự "đoán" kết quả.
        *   Khi phát hiện hành vi rủi ro cao: Hệ thống khiên bảo vệ (Guardrails) lập tức can thiệp để tương tác xác nhận với người dùng trước khi ghi xuống cơ sở dữ liệu.

### 2.2. Tầm quan trọng của Mô tả Công cụ (Tool Spec)
*   LLM "nhìn thấy" các công cụ thông qua phần chuỗi mô tả (description) trong code.
*   Nếu mô tả quá mơ hồ (ví dụ: *"Hàm tính toán"*), LLM sẽ truyền sai tham số hoặc gọi sai thời điểm. 
*   **Bài học**: Mô tả công cụ cần được thiết kế rõ ràng về **loại tham số truyền vào**, **mục đích sử dụng** và **ví dụ mẫu** để LLM đưa ra hành động chính xác nhất.

### 2.3. Vấn đề Hiệu năng (Token & Latency) trong Production
*   **Chi phí Token**: Do ReAct Agent phải gửi toàn bộ lịch sử suy luận (`Thought`, `Action`, `Observation`) ở mỗi bước quay vòng, số lượng token tiêu thụ tăng lũy tiến theo số bước suy luận (loop count). Cần tối ưu hóa System Prompt để Agent dừng đúng lúc.
*   **Độ trễ (Latency)**: Mỗi bước suy luận ReAct gọi API LLM một lần. Nếu một câu trả lời cần tới 3-4 bước gọi tool, độ trễ có thể lên tới 3 - 5 giây. Trong môi trường production, điều này đòi hỏi chúng ta phải áp dụng cơ chế truyền dữ liệu dạng luồng (Streaming) hoặc tối ưu hóa luồng suy luận song song.

### 2.4. Tính an toàn và Khiên bảo mật (Guardrails)
*   Không nên tin cậy hoàn toàn vào việc sinh tự do của LLM.
*   **Input Guard** là bộ lọc đầu tiên ngăn chặn tấn công Prompt Injection và các câu hỏi ngoài lề (off-topic) phá hoại hệ thống.
*   **Output Guard** đóng vai trò cực kỳ quan trọng đối với các tác vụ làm thay đổi trạng thái hệ thống (State-changing actions) như ghi thông tin khách hàng, đặt cọc xe. Việc chặn chốt lịch ngầm và yêu cầu khách hàng phản hồi rõ ràng chữ "ĐỒNG Ý" giúp tăng tính minh bạch và tránh rác dữ liệu DB.

### 2.5. Sự cần thiết của Cơ chế Dự phòng (Graceful Fallback)
*   Khi triển khai ứng dụng AI trong môi trường thực tế, lỗi API (hết quota, lỗi mạng, rate limit 429) là khó tránh khỏi.
*   Việc bổ sung cơ chế kiểm soát lỗi (`try-except` xung quanh luồng chạy của Agent) và chuyển hướng tự động sang hệ thống dự phòng (rule-based local fallback / Mock Provider) giúp đảm bảo ứng dụng **luôn trực tuyến và hoạt động ổn định** thay vì trả về lỗi trắng trang hoặc 500 cho người dùng.
