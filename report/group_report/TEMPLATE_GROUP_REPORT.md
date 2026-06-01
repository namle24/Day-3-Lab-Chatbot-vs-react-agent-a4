# Group Report: Lab 3 - VinFast Smart Sales Agent

- **Team Name**: [bàn A4]
- **Team Members**: [Phạm Thanh Hằng - 2A202600593, Ngô Đắc Lãm - 2A202600655, Phan Quốc Anh - 2A202600890, Lê Hoài Nam - 2A202600657]
- **Deployment Date**: [2026-06-01]

---

## 1. Executive Summary

*Tóm tắt ngắn gọn về mục tiêu của VinFast Smart Sales Agent và tỉ lệ thành công (Success Rate) so với chatbot cơ bản (chatbot baseline).*

- **Success Rate**: [e.g., 90% trên 30 ca kiểm thử chuẩn]
- **Key Outcome**: [e.g., "Agent thông minh vượt trội chatbot baseline 45% ở các câu hỏi phức tạp cần so sánh thông số kỹ thuật xe VinFast, tra cứu nhận xét và tính toán chi phí trả trước nhờ khả năng gọi chuỗi công cụ (multi-step tool calls) chính xác."]

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
*Sơ đồ hoặc mô tả chu kỳ Thought-Action-Observation của VinFast Agent.*
*VD: Luồng hoạt động khi nhận câu hỏi phức tạp (So sánh VF5/VF6 + tính trả trước) -> Suy nghĩ (Thought) -> Gọi tool so sánh -> Nhận kết quả (Observation) -> Suy nghĩ -> Gọi tool tính toán -> Nhận kết quả -> Phản hồi cuối cùng.*

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `lookup_vehicle` | `{"query": "string", "top_k": int}` | Tra cứu thông số, giá niêm yết, giá lăn bánh từ Knowledge Base. |
| `compare_vehicles` | `{"model_a": "string", "model_b": "string"}` | So sánh nhanh thông số và điểm nổi bật giữa hai dòng xe VinFast. |
| `calculate` | `{"mode": "expression/down_payment/difference", ...}` | Tính biểu thức toán học, số tiền trả trước (%), hoặc chênh lệch giá lăn bánh. |
| `schedule_test_drive` | `{"customer_name": "str", "phone": "str", "car_model": "str"}` | Tạo yêu cầu đăng ký lịch lái thử xe của khách (ở trạng thái pending). |
| `search_reviews` | `{"query": "string", "car_model": "string optional"}` | Tìm kiếm đánh giá khen/chê, cảm nhận người dùng về từng dòng xe. |

### 2.3 LLM Providers Used
- **Primary**: [e.g., GPT-4o hoặc Gemini 1.5 Flash]
- **Secondary (Backup)**: [e.g., Phi-3-mini chạy local / Gemini 1.5 Flash]

---

## 3. Telemetry & Performance Dashboard

*Phân tích các chỉ số vận hành được hệ thống telemetry/logger ghi nhận.*

- **Average Latency (P50)**: [e.g., 1800ms]
- **Max Latency (P99)**: [e.g., 5200ms khi chạy ReAct loop qua nhiều bước]
- **Average Tokens per Task**: [e.g., 450 tokens]
- **Total Cost of Test Suite**: [e.g., $0.08]

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Phân tích chi tiết nguyên nhân gây lỗi của Agent.*

### Case Study: [e.g., Hallucinated Argument trong đăng ký lái thử]
- **Input**: "Đặt cho tôi lịch lái thử xe VF6 nhé. Tôi tên Hải, số điện thoại là 0912345678."
- **Observation**: Agent gọi sai tool `schedule_test_drive` do nhầm lẫn tên xe hoặc truyền thiếu tham số hoặc gọi sai format JSON khi ReAct loop trích xuất thông tin.
- **Root Cause**: Phần định nghĩa mô tả tham số (docstring) của tool hoặc hệ thống prompt hướng dẫn trích xuất thông tin chưa đủ mạnh mẽ và thiếu ví dụ `Few-Shot` trực quan cho các tên xe đặc thù của VinFast.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 (Cơ bản) vs Prompt v2 (Thêm Hướng dẫn ReAct + System Guardrails)
- **Diff**: Bổ sung hướng dẫn *"Hãy suy nghĩ kỹ định dạng JSON của tham số tool trước khi xuất Action và luôn kiểm tra đầy đủ thông tin Tên + Số điện thoại trước khi lưu lịch hẹn"*.
- **Result**: Giảm thiểu lỗi gọi sai tham số của tool xuống [e.g., 35%].

### Experiment 2 (So Sánh): Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Tra cứu giá VF5 | Đúng (nhờ System Prompt cứng) | Đúng (nhờ gọi `lookup_vehicle`) | Hòa |
| So sánh xe VF5 & VF6 + tính trả trước 30% | Chỉ so sánh chay bằng text có sẵn, không tính được phần trăm trả trước hoặc tính sai | So sánh đầy đủ thông số chính xác + gọi `calculate` tính số tiền trả trước hoàn hảo | **Agent** |

---

## 6. Production Readiness Review

*Các điểm cần lưu ý trước khi đưa hệ thống tư vấn xe VinFast vào vận hành thực tế.*

- **Security & Validation**: Đảm bảo lọc đầu vào (input sanitization), kiểm tra định dạng số điện thoại hợp lệ tại tool `schedule_test_drive` trước khi đưa vào Database.
- **Guardrails**: Giới hạn số bước lặp ReAct (`max_steps=5`) để tránh hiện tượng Agent suy nghĩ vô hạn hoặc lặp vòng vô tận gây hao phí chi phí token LLM.
- **Scaling**: Nâng cấp luồng tư vấn và chốt lịch bằng sơ đồ trạng thái (LangGraph) để xử lý hội thoại mượt mà khi khách hàng thay đổi ý định đột ngột.

---

> [!NOTE]
> Hãy hoàn thiện báo cáo này, đổi tên file thành `GROUP_REPORT_A4.md` và lưu vào thư mục này để nộp bài.
