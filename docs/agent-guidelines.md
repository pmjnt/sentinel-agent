# Sentinel Agent Guidelines

## Vai trò của LLM

LLM chịu trách nhiệm:

- hiểu tiếng Việt hoặc tiếng Anh của người dùng;
- phân biệt cập nhật, xem policy, phân tích, general chat và yêu cầu cần làm rõ;
- giữ đúng thứ tự khi một message chứa nhiều action;
- chọn thông tin portfolio/market cần đọc;
- thêm interpretation định tính cho kết quả Python đã xác minh.

LLM không phải nguồn sự thật cho:

- portfolio arithmetic;
- policy threshold checking;
- rebalance amount;
- volatility blocking;
- approval requirement;
- execution authorization.

## Request Interpreter Agent

Request Interpreter là một Agent riêng, không có tool tài chính. Nó nhận:

```text
Current validated portfolio policy
+
User message
```

và trả `ParsedRequest` theo Pydantic schema.

Các action được phép:

```text
UPDATE_POLICY
VIEW_POLICY
ANALYZE_PORTFOLIO
NEEDS_CLARIFICATION
GENERAL_CHAT
```

Không tồn tại action đặt lệnh hoặc chuyển tiền.

`GENERAL_CHAT` dùng cho lời chào, câu hỏi về khả năng hoặc trò chuyện thông
thường và phải là action duy nhất. Interpreter nhận policy hiện tại làm context,
nhưng service chỉ chuyển `response` đã validate thành message trả về. Nhánh này
không sửa policy, không yêu cầu analysis, không gọi gateway và không kết nối
Binance. LLM không được bịa dữ liệu tài chính, đề xuất giao dịch hay
tuyên bố đã thực thi trong response này.

## Structured output

Structured output là dữ liệu nội bộ, không phải nội dung hiển thị trực tiếp cho người dùng.

```text
Natural-language message
        ↓
Request Interpreter LLM
        ↓
ParsedRequest
        ↓
Pydantic validation
        ↓
PolicyConversationService
        ↓
Natural-language confirmation
```

Nếu output không đúng schema, Interpreter retry đúng một lần. Nếu vẫn sai, workflow trả lỗi; không tự đoán action thay thế. Lỗi provider hoặc network không được retry như lỗi schema và không được đổi thành kết quả giả.

## Patch semantics

- Field không xuất hiện: giữ giá trị hiện tại.
- Field xuất hiện với `null`: xóa optional rule.
- Field sai range: Pydantic từ chối.
- Python merge patch; LLM không sửa session trực tiếp.

Ví dụ:

```text
User: Đổi giới hạn mỗi asset thành 45%.
LLM:  UPDATE_POLICY {max_asset_weight: 0.45}
Python: giữ nguyên các field khác
Chat: Đã cập nhật policy: tỷ trọng tối đa ... là 45%.
```

## Multiple actions

Message:

```text
Đặt giới hạn mỗi asset là 40%, sau đó phân tích portfolio.
```

Actions:

```text
1. UPDATE_POLICY
2. ANALYZE_PORTFOLIO
```

Python thực hiện đúng thứ tự. Nếu cần clarification, Interpreter chỉ trả một
`NEEDS_CLARIFICATION`; service dừng toàn bộ message trước khi thay đổi state.

## Conversation state

Policy được lưu theo `session_id` trong RAM. LLM luôn nhận policy hiện tại dưới dạng JSON đã validate; không phải tự nhớ policy từ hội thoại.

Việc này tránh:

- model quên một rule cũ;
- model merge sai field;
- lịch sử chat trở thành nguồn sự thật nghiệp vụ.

Restart ứng dụng sẽ xóa session trong phiên bản hiện tại.

Mỗi analysis action giữ một policy snapshot riêng. Vì vậy “phân tích rồi đổi
policy” phân tích bằng policy cũ, còn “đổi rồi phân tích” dùng policy mới; nhiều
analysis action không bị gộp thành một.

## Hai Agent có trách nhiệm khác nhau

### Request Interpreter

- Không có tool.
- Chỉ hiểu requested actions.
- Trả structured output.

### Analysis Reporter

- Không có tool.
- Nhận `PortfolioAnalysis` đã được Python xác minh.
- Chỉ thêm interpretation định tính; Python tự render facts và formal status.
- Không được lặp lại formal RiskStatus hoặc tuyên bố execution state.
- Không thay đổi policy hoặc RiskDecision.

Giữa hai Agent, `SentinelApplication` và `PortfolioAnalysisService` bắt buộc chạy
gateway, policy checks, planner và RiskEngine. Vì vậy LLM không thể bỏ qua một
bước kiểm tra an toàn. Agent hai-tool trong `app/agent/sentinel.py` chỉ còn là ví
dụ giáo dục về autonomous tool calling, không phải runtime policy chính.

## Prompt review checklist

- Prompt có nói rõ source of truth không?
- Output có schema thay vì JSON tự do không?
- Có cấm threshold do model tự nghĩ ra không?
- Có cấm execution action không?
- Có chỉ dẫn hỏi lại khi mơ hồ không?
- Có yêu cầu phân biệt tool facts và interpretation không?
- Thay prompt có làm thay đổi behavior cần test không?
