VinFast Smart Sales Agent 

1. Các thành phần cốt lõi (Components)
Hệ thống của chúng ta sẽ bao gồm 4 "cơ quan" chính:
 Giao tiếp (UI & Input): Nơi tiếp nhận tin nhắn của khách hàng.
 Bộ não & Trí nhớ (LLM + Context): * LLM: Đóng vai trò là luồng suy nghĩ trung tâm (Quyết định xem nên trả lời luôn hay phải dùng công cụ).
Memory: Ghi nhớ lịch sử chat để khách không phải nhắc lại thông tin (Ví dụ: Câu trước hỏi giá VF 5, câu sau bảo "tính trả góp con đó").
Tay chân (Tools): Các công cụ Agent được phép cầm nắm:
Công cụ Tra cứu: Đọc thông số, giá xe (Database/PDF).
Công cụ Máy tính: Tính toán tỷ lệ trả trước, lãi suất.
Công cụ Đặt lịch: Ghi nhận thông tin lái thử (Tên, SĐT).
Hệ thống Khiên (Guardrails): 3 lớp bảo vệ bao bọc xung quanh "Bộ não" và "Tay chân".
2. Kịch bản vận hành thực tế (Workflow)
Hãy hình dung luồng chạy của hệ thống khi một khách hàng nhắn tin: "Tính cho tôi khoản trả trước 30% của chiếc VF 8. Nếu được thì đặt lịch cho tôi lái thử, tôi là Hoàng, 0987654321."
Giai đoạn 1: Lọc cửa sổ đầu vào
Lớp 1 (Input Guard): Quét câu hỏi. Xác nhận không có câu lệnh xúi giục tẩu tán dữ liệu (Prompt Injection) hay hỏi ngoài lề (Off-topic). Câu hỏi hợp lệ $\rightarrow$ Cho phép đi vào "Bộ não".
Giai đoạn 2: Vòng lặp Suy luận & Hành động (ReAct)
Thought 1: Khách muốn tính 30% của VF 8. Mình chưa nhớ giá VF 8.
Action 1: Gọi công cụ Tra cứu với từ khóa "VF 8".
Lớp 2 (Tool Guard): Công cụ nhả kết quả giá VF 8. Hệ thống tự động gọt bỏ các thẻ ẩn, link lạ (Sanitize) trước khi trả lại cho Bộ não.
Thought 2: Đã có giá là 1.090.000.000 VNĐ. Giờ cần tính 30%.
Action 2: Gọi công cụ Máy tính với biểu thức 1090000000 * 0.3.
Lớp 2 (Tool Guard): Quét biểu thức toán học, đảm bảo không có mã độc thực thi ngầm. Kết quả trả về: 327.000.000 VNĐ.
Thought 3: Khách muốn đặt lịch lái thử.
Action 3: Gọi công cụ Đặt lịch (Truyền vào Tên: Hoàng, SĐT: 0987654321, Xe: VF 8).
Giai đoạn 3: Kiểm duyệt cửa sổ đầu ra
Lớp 3 (Output Guard): Công cụ Đặt lịch được đánh dấu là "Rủi ro cao" (High-risk). Thay vì âm thầm chốt lịch, hệ thống chặn lại và buộc "Bộ não" phải xuất ra một câu hỏi xác nhận.
Giai đoạn 4: Trả lời khách hàng
Agent xuất Output: "Dạ, chiếc VF 8 có giá 1.090.000.000 VNĐ. Khoản trả trước 30% của anh là 327.000.000 VNĐ. Hệ thống đang chuẩn bị đặt lịch lái thử cho anh Hoàng (0987654321). Anh vui lòng xác nhận ĐỒNG Ý để em chốt lịch nhé!"


Usecase 1: Tư vấn so sánh xe dựa trên nhu cầu (Car Comparison & Consultation)

Mô tả: Khách hàng chưa biết nên chọn dòng xe nào và cần chatbot phân tích, so sánh các lựa chọn để ra quyết định.
Ví dụ câu hỏi của khách: "Tôi đã có gia đình 4 người, chủ yếu đi làm trong phố, đang phân vân giữa VF 5 và VF 6. Hãy so sánh giúp tôi và tính xem chênh lệch giá lăn bánh là bao nhiêu?"
Luồng vận hành dự kiến:
Lớp 1 (Input Guard): Quét câu hỏi xem có vi phạm tiêu chuẩn hay không.
Vòng lặp ReAct:
Thought 1 & Action 1: LLM nhận thấy cần dữ liệu của 2 xe. Gọi Công cụ Tra cứu để kéo dữ liệu về thông số kích thước, tính năng an toàn gia đình và giá niêm yết của VF 5, VF 6. Lớp 2 (Tool Guard) sẽ lọc các kết quả trả về.
Thought 2 & Action 2: Cần tính chênh lệch giá. Gọi Công cụ Máy tính để trừ giá hoặc tính toán chi phí lăn bánh dự kiến giữa 2 xe.
Agent xuất Output: Chatbot tổng hợp ưu điểm của VF 5 (nhỏ gọn, rẻ hơn) và VF 6 (rộng rãi cho 4 người), đưa ra mức giá chênh lệch, và gợi ý khách hàng cung cấp thông tin để đặt lịch xem cả 2 xe thực tế.
tạo sẵn lịch hẹn mang xe qua xưởng. Anh vui lòng phản hồi ĐỒNG Ý để em chốt lịch cho anh nhé!"

Tools: search review danh gia ve chiec xe ma khac hang muon hoi

—----------------------------------------------------------------------------------------------------------------------
Bảng phân công chi tiết để dựng thành phẩm Web UI/UX:
Thành viên 1: Chuyên trách Giao tiếp (Frontend Web & UI/UX)
Mục tiêu: Xây dựng phần Giao tiếp (UI & Input) nơi tiếp nhận tin nhắn của khách hàng và hiển thị câu trả lời.
Nhiệm vụ cụ thể:
Thiết kế giao diện (UI/UX) cho một Web Chatbot chuyên nghiệp (có khung chat, nút gửi, hiển thị người gửi/bot).
Hiển thị các định dạng tin nhắn đa dạng (văn bản thường, bảng so sánh thông số VF 5 và VF 6 cho Usecase 1, định dạng in đậm các con số quan trọng như chênh lệch giá, tổng tiền).
Tích hợp API để nối luồng gửi tin nhắn từ Frontend xuống hệ thống Agent (Backend) và nhận phản hồi ngược lại.
Xử lý UI cho phần xác nhận (Ví dụ: Nút "ĐỒNG Ý" nổi bật để khách hàng chốt lịch xem xe/lái thử).
Thành viên 2: Chuyên trách Bộ não & Trí nhớ (LLM Core & Prompt Engineering)
Mục tiêu: Xây dựng luồng suy nghĩ trung tâm (LLM + Context) và kỹ thuật Prompt.
Nhiệm vụ cụ thể:
Prompting Usecase 1: Viết prompt hướng dẫn LLM cách phân tích nhu cầu (gia đình 4 người, đi trong phố), so sánh ưu nhược điểm giữa VF 5 và VF 6.
Xây dựng vòng lặp ReAct: Lập trình để LLM biết tự sinh ra các bước Thought (Suy nghĩ) và Action (Hành động) khi khách hỏi (ví dụ: "Mình chưa nhớ giá VF 5, cần gọi công cụ tra cứu").
Quản lý Memory (Trí nhớ): Lưu trữ ngữ cảnh hội thoại để khách không phải nhắc lại thông tin (ví dụ: Câu trước hỏi so sánh VF 5 và VF 6, câu sau bảo "tính giá lăn bánh con rẻ hơn").
Thành viên 3: Chuyên trách Tay chân (Backend API & Tools)
Mục tiêu: Phát triển các Công cụ (Tools) để Agent "cầm nắm" và thao tác thực tế.
Nhiệm vụ cụ thể:
Xây dựng Công cụ Tra cứu: Lập trình hàm truy xuất dữ liệu từ Database hoặc file PDF chứa thông số kỹ thuật (kích thước, tính năng an toàn) và giá niêm yết của VF 5, VF 6, VF 8.
Xây dựng Công cụ Máy tính: Viết hàm tính toán toán học để tính tỷ lệ trả trước (ví dụ 30%), chênh lệch giá giữa các dòng xe, hoặc tính chi phí lăn bánh.
Xây dựng Công cụ Đặt lịch: Viết API tiếp nhận thông tin người dùng (Tên, SĐT, Dòng xe) để ghi nhận vào hệ thống CRM/Database đặt lịch xem xe hoặc lái thử.
Thành viên 4: Chuyên trách Hệ thống Khiên (Guardrails & Security)
Mục tiêu: Xây dựng 3 lớp bảo vệ bao bọc xung quanh "Bộ não" và "Tay chân" để đảm bảo an toàn, chính xác.
Nhiệm vụ cụ thể:
Lớp 1 (Input Guard): Viết bộ lọc ngay cửa sổ đầu vào. Quét câu hỏi của khách để chặn các lệnh tẩu tán dữ liệu (Prompt Injection) hoặc các câu hỏi nằm ngoài lề (Off-topic), chỉ cho phép câu hỏi hợp lệ đi vào Bộ não.
Lớp 2 (Tool Guard): Tạo bộ lọc dữ liệu trung gian. Gọt bỏ các thẻ ẩn, link lạ từ nguồn tra cứu trả về (Sanitize); đồng thời quét các biểu thức toán học trước khi đưa vào công cụ Máy tính để chặn mã độc thực thi ngầm.
Lớp 3 (Output Guard): Cấu hình cơ chế chặn các hành động "Rủi ro cao" (High-risk) như gọi hàm Đặt lịch. Thay vì để hệ thống âm thầm lưu database, lớp khiên này phải buộc LLM xuất ra câu hỏi xác nhận lại với người dùng (như "Anh vui lòng xác nhận ĐỒNG Ý...").
Tổng kết luồng phối hợp của 4 bạn (Workflow Integration): Khi khách hàng nhập tin nhắn vào web (do Thành viên 1 làm) → Tin nhắn qua cửa kiểm duyệt Thành viên 4 (Lớp 1) → Đẩy vào Bộ não của Thành viên 2 suy luận → Gọi các công cụ do Thành viên 3 làm → Kết quả công cụ đi qua khiên Lớp 2 (của Thành viên 4) → LLM tổng hợp lại đưa ra quyết định đặt lịch → Bị khiên Lớp 3 (của Thành viên 4) chặn lại đòi xác nhận → LLM nhả câu trả lời cuối cùng ra UI Web (của Thành viên 1).


Chung nang: 1-3 user, giu duoc lich su cua tung user, 
Log: luu lai lich su ma agent tra loi, agent su dung tool nao khi nguoi dung hoi
tech: rag, vector search du lei xe tu db
