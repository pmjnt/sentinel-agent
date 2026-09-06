# Sentinel Development Guidelines

## 1. Ưu tiên dễ đọc

- Dùng tên mô tả nghiệp vụ: `find_policy_violations`, không dùng `process_data`.
- Một hàm làm một việc và có type hint đầy đủ.
- Ưu tiên code thẳng, tránh metaprogramming và inheritance không cần thiết.
- Chỉ viết comment để giải thích lý do hoặc ranh giới Agent; không diễn giải lại code hiển nhiên.
- Không sao chép cấu trúc controller/service/repository của Spring Boot nếu Python chưa cần.

## 2. Quy tắc module

- Model đặt trong `app/models/<domain>.py`.
- Business rule đặt trong `app/services/<responsibility>_service.py`.
- HTTP parsing và status code chỉ đặt trong `app/api`.
- Provider payload mapping chỉ đặt trong adapter như `app/binance`.
- Prompt và Agent construction chỉ đặt trong `app/agent`.
- Điều phối nhiều use case đặt ở `app/application.py`, không đặt trong prompt.
- Không đặt network call hoặc business rule trong Pydantic validator.

## 3. Dependency

Được phép:

```text
services → models + application-owned ports
agent → config + models
application → models + service protocols
binance adapter → ports + models + deterministic mapping services
api (future) → application + models
```

Không được phép:

```text
models → services/agent/binance/api
services → agents/fastapi/mcp/litellm
web → provider API hoặc Binance credential
```

Nếu xuất hiện circular import, xem lại trách nhiệm module thay vì trì hoãn import vào trong hàm.

## 4. `__init__.py`

- Giữ file rỗng theo mặc định để đánh dấu package rõ ràng.
- Chỉ re-export một API nhỏ và ổn định khi nó thực sự làm import dễ hiểu hơn.
- Không load settings, tạo Agent, kết nối MCP hoặc chạy code trong `__init__.py`.
- Không dùng wildcard import.

## 5. Kiểu dữ liệu tài chính

- Dùng `Decimal`, không dùng `float`, cho giá, amount, USD value, weight và percent.
- Tạo literal bằng chuỗi: `Decimal("0.40")`, không dùng `Decimal(0.40)`.
- Chỉ quantize ở ranh giới cần precision rõ ràng.
- Ghi rõ rounding mode khi tính lượng proposal.
- Weight nằm trong khoảng 0 đến 1; UI chịu trách nhiệm hiển thị dạng phần trăm.

## 6. Pydantic

- Dùng Pydantic cho dữ liệu đi qua boundary hoặc cần schema validation.
- Domain object hiện tại dùng `ConfigDict(frozen=True)` để tránh thay đổi ngoài ý muốn.
- Normalize symbol thành uppercase tại model boundary.
- Không dùng object thành công chứa nhiều field `None` để biểu diễn lỗi; dùng error model riêng.
- `PolicyPatch.model_fields_set` phân biệt field vắng mặt và field được đặt `null`.

## 7. Error handling

- Raise typed error khi caller có thể xử lý theo loại lỗi.
- Không `except Exception: pass`.
- Không biến lỗi network thành dữ liệu tài chính giả.
- API boundary chuyển typed error thành response rõ ràng.
- Thông báo ra người dùng không chứa token, raw credential hoặc stack trace.
- Log phải có request ID và reason code nhưng không log secret.

## 8. Async

- Domain services là synchronous vì chỉ tính toán trong bộ nhớ.
- Dùng async cho LLM, Binance CLI và HTTP/MCP I/O.
- Không biến hàm thành async chỉ để đồng nhất hình thức.
- Không gọi blocking I/O trực tiếp trong async request handler.

## 9. Agent rules

- Request Interpreter LLM hiểu intent và trả typed actions.
- Analysis Reporter LLM giải thích `PortfolioAnalysis` đã được xác minh.
- Python orchestrator bắt buộc chạy các bước data/policy/planner/risk cần thiết.
- Python là nguồn sự thật cho arithmetic và policy threshold.
- RiskEngine là nguồn sự thật cho `BLOCKED`, `REQUIRES_APPROVAL`, `SAFE_TO_PROPOSE`.
- Structured output phải được validate trước khi ảnh hưởng state.
- Nếu policy mơ hồ, hỏi lại; không tự tạo threshold.
- Tool proposal của Agent không được gọi adapter execution.
- Approval phải tham chiếu đúng immutable plan và đi qua API/use case riêng.
- Re-read portfolio/market và revalidate ngay trước order; dữ liệu lúc đề xuất
  không phải quyền thực thi.
- Hard limits của ứng dụng luôn thắng policy do chat cập nhật.
- Chỉ báo `EXECUTED` sau khi provider xác nhận trạng thái order.
- Retry approval không được tạo order thứ hai; dùng client order ID idempotent.
- Không bao giờ thêm transfer, withdrawal hoặc generic CLI tool vào Agent.

## 10. MCP rules cho adapter tương lai

- Chỉ kết nối endpoint chính thức đã cấu hình.
- Grant tối thiểu Market Data và Account scope.
- Discover schema thật trước khi viết mapping.
- Raw MCP tools không được gắn trực tiếp vào Agent; phải đi qua gateway ổn định.
- Gateway chỉ gọi tool nằm trong allow-list đã review.
- Unknown tool bị từ chối theo mặc định.
- Token nằm ở backend và không xuất hiện trong prompt hoặc browser state.

## 11. Imports và side effects

- Import rõ nguồn, ví dụ `from app.models.policy import PortfolioPolicy`.
- Không import `*`.
- Import module không được đọc `.env`, mở browser, kết nối mạng hoặc tạo background task.
- Dependency được tạo tại application composition root và truyền vào nơi sử dụng.

## 12. Review checklist

Trước khi hoàn thành một thay đổi:

- Có test RED trước implementation không?
- Financial calculation có dùng `Decimal` không?
- Business rule có vô tình nằm trong Agent/API không?
- LLM output đã được schema validate chưa?
- Failure có tạo fake result không?
- Tool write mới có nằm ngoài LLM loop và yêu cầu explicit approval không?
- Type hint và tên hàm có nói rõ ý nghĩa không?
- Có import ngược dependency direction không?
- Test, compile validation và `git diff --check` có pass không?
