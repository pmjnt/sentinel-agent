# Sentinel Agent Guidelines

## Vai trò của LLM

LLM chịu trách nhiệm:

- hiểu tiếng Việt hoặc tiếng Anh của người dùng;
- phân biệt cập nhật, xem policy, phân tích và yêu cầu cần làm rõ;
- giữ đúng thứ tự khi một message chứa nhiều action;
- chọn thông tin portfolio/market cần đọc;
- giải thích kết quả đã được Python xác minh.

LLM không phải nguồn sự thật cho:

- portfolio arithmetic;
- policy threshold checking;
- rebalance amount;
- volatility blocking;
- approval requirement;
- execution authorization.

## Policy parser Agent

Policy parser là một Agent riêng, không có tool tài chính. Nó nhận:

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
```

Không tồn tại action đặt lệnh hoặc chuyển tiền.

## Structured output

Structured output là dữ liệu nội bộ, không phải nội dung hiển thị trực tiếp cho người dùng.

```text
Natural-language message
        ↓
Policy parser LLM
        ↓
ParsedRequest
        ↓
Pydantic validation
        ↓
PolicyConversationService
        ↓
Natural-language confirmation
```

Nếu output không đúng schema, parser retry đúng một lần. Nếu vẫn sai, workflow trả lỗi; không tự đoán action thay thế. Lỗi provider hoặc network không được retry như lỗi schema và không được đổi thành kết quả giả.

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

Python thực hiện đúng thứ tự. Một clarification action dừng workflow để tránh thực hiện yêu cầu dựa trên policy mơ hồ.

## Conversation state

Policy được lưu theo `session_id` trong RAM. LLM luôn nhận policy hiện tại dưới dạng JSON đã validate; không phải tự nhớ policy từ hội thoại.

Việc này tránh:

- model quên một rule cũ;
- model merge sai field;
- lịch sử chat trở thành nguồn sự thật nghiệp vụ.

Restart ứng dụng sẽ xóa session trong phiên bản hiện tại.

## Hai Agent có trách nhiệm khác nhau

### Policy parser

- Không có tool.
- Chỉ hiểu requested actions.
- Trả structured output.

### Sentinel analysis Agent

- Có hai tool ứng dụng ổn định: `get_portfolio()` và `get_market_data()`.
- Chọn dữ liệu cần đọc.
- Nhận kết quả deterministic và giải thích.
- Không thay đổi policy hoặc RiskDecision.

Tách hai trách nhiệm giúp prompt ngắn, output rõ và test dễ hơn.

## Prompt review checklist

- Prompt có nói rõ source of truth không?
- Output có schema thay vì JSON tự do không?
- Có cấm threshold do model tự nghĩ ra không?
- Có cấm execution action không?
- Có chỉ dẫn hỏi lại khi mơ hồ không?
- Có yêu cầu phân biệt tool facts và interpretation không?
- Thay prompt có làm thay đổi behavior cần test không?
