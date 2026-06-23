# Epic 7 - Concerns & Feedback

Qua thảo luận và đối chiếu giữa `AGENTS.md`, các ADRs và `DETAIL_DESIGN.md` mới được cập nhật, chúng ta đã thống nhất các điểm sau:

## 1. Đồng bộ Quy tắc Kiến trúc
- Kiến trúc Python cho Orchestrator/LLM runtime và Go cho các domain service (theo ADR-003) đã được chấp nhận.
- Đã cập nhật Rule 12 trong `AGENTS.md` để đồng nhất với thực tế.
- Đã đánh dấu `ADR-001` là `superseded` bởi `ADR-003` và cập nhật lại Consequences trong `ADR-002` (thay "Go structs" thành "gRPC schemas / API request parameters").

## 2. Các vấn đề kỹ thuật cần giải quyết (Blockers)

### A. Thiếu định nghĩa gRPC cho Finance Service
- **Hiện trạng**: Go Finance module đã có đầy đủ logic (trong `src/backend/internal/modules/finance/service`), nhưng chưa được expose qua gRPC trong `src/proto/cortex.proto` để Python Orchestrator có thể gọi.
- **Giải pháp**: 
  - Khai báo `FinanceService` trong `src/proto/cortex.proto`.
  - Triển khai Go gRPC Server tương ứng cho module Finance.

### B. Thiếu định nghĩa gRPC cho System Services (Audit & Policy)
- **Hiện trạng**: Go system services (`audit` và `policy`) đã được viết bằng Go nhưng chỉ chạy nội bộ trong Go backend, chưa được cấu hình làm gRPC service.
- **Giải pháp**:
  - Khai báo gRPC service cho `AuditService` và `PolicyService` trong `src/proto/cortex.proto`.
  - Triển khai Go gRPC server cho hai dịch vụ này để Python Orchestrator gửi event audit và đánh giá policy.

## 3. Kế hoạch tiếp theo
1. Cập nhật `src/proto/cortex.proto` với các interface cho `FinanceService`, `AuditService`, và `PolicyService`.
2. Tạo mã nguồn gRPC (codegen) cho cả Go và Python.
3. Triển khai gRPC server phía Go backend để phục vụ các yêu cầu từ Python Orchestrator.
