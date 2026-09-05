# Kiến trúc Sentinel

## Ranh giới trách nhiệm

```text
LLM / Agent
├── hiểu yêu cầu tiếng Việt hoặc tiếng Anh
├── chọn tool an toàn cần gọi tiếp theo
└── đưa ra nhận định định tính từ kết quả đã xác minh

Python
├── validate policy và dữ liệu
├── tính allocation, violation và proposal
├── chạy RiskEngine
└── render facts, formal status và execution state

BinanceCliGateway
├── chỉ chạy command đọc trong allowlist
├── validate JSON Binance Demo
└── chuyển transport data thành domain model
```

LLM được phân tích và đưa lời khuyên, nhưng không phải nguồn sự thật cho phép
tính, threshold, `RiskStatus`, quyền thực thi hay dữ liệu tài chính.

## Dependency direction

```text
app.models ← app.services ← app.gateways ← app.binance
                 ↑                 ↑
            controlled_tools ← tool_loop ← application ← main.py
```

- `app.models`: Pydantic domain data.
- `app.services`: business rules deterministic, không import Agents SDK.
- `app.gateways`: port do ứng dụng sở hữu.
- `app.binance`: adapter read-only cho Binance Skills Hub CLI.
- `app.agent.controlled_tools`: năm capability duy nhất LLM nhìn thấy.
- `app.agent.tool_loop`: tạo Agent, context một lượt chạy và gọi SDK Runner.
- `app.application`: commit policy sau thành công và render kết quả authoritative.
- `web`: UI tĩnh, không nhận secret.

## Tool loop đang dùng trong console

```text
User message + current validated policy
  ↓
Sentinel Agent / LLM
  ↓ chọn tool dựa trên request và tool description
get_portfolio
  ↓ BinanceCliGateway → validated Portfolio
LLM nhận Portfolio và chọn bước tiếp
  ↓
get_market_data("BTCUSDT")
  ↓ BinanceCliGateway → validated MarketData
LLM nhận MarketData và gọi bước kiểm tra bắt buộc
  ↓
evaluate_portfolio_risk
  ↓
find_policy_violations → build_rebalance_plan → RiskEngine
  ↓
PortfolioAnalysis đã validate
  ↓
LLM viết nhận định định tính
  ↓
Python render facts/status trước, rồi mới nối AI interpretation
```

Khi người dùng đổi policy, `update_policy` chỉ cập nhật `working_policy` trong
`SentinelRunContext`. `SentinelApplication` commit các patch theo đúng thứ tự sau
khi toàn bộ lượt Agent kết thúc thành công. Store kiểm tra expected policy để
không ghi đè một concurrent run mới hơn. Lỗi provider không làm policy dở dang
lọt vào session.

Nếu thiếu observation, `evaluate_portfolio_risk` trả danh sách tool còn thiếu;
LLM phải đọc dữ liệu rồi thử lại. Nếu Binance lỗi, hệ thống ghi data error và
fail-closed, không thay bằng dữ liệu giả.

Một request tối đa 20 market observations và có 28 Agent turns. Runtime từ chối
kết luận tài chính nếu Agent dừng sau tool đọc nhưng trước deterministic
evaluation.

## Quy tắc deterministic

Volatility dùng độ lớn biến động 24 giờ:

```text
< 2%       LOW
2%..<4%    MEDIUM
>= 4%      HIGH
```

Slippage được ước lượng từ bid depth cho reference sale 1,000 USDT; đây chỉ là
observation phân tích. Formal risk priority là `BLOCKED`, sau đó
`REQUIRES_APPROVAL`, rồi `SAFE_TO_PROPOSE`.

## Security boundary

Agent chỉ có năm tool:

```text
get_portfolio
get_market_data
update_policy
view_policy
evaluate_portfolio_risk
```

Không có order, trade, transfer, withdrawal hoặc generic CLI tool.
`BinanceCliRunner` dùng argument array, không mở shell. Credentials chỉ đi qua
child environment của account command, không nằm trong prompt hay run context.
`parallel_tool_calls=False` giữ thứ tự policy/observation rõ ràng.

## Legacy và khả năng thay adapter

`request_interpreter.py`, `analysis_reporter.py`,
`policy_conversation_service.py`, `sentinel.py` và `app/tools/` là luồng cũ/
giáo dục, không còn được `main.py` khởi tạo. Chúng được giữ tạm để so sánh và có
thể xóa sau khi tài liệu học tập không còn cần chúng.

Tool handler phụ thuộc vào `PortfolioMarketGateway`, không phụ thuộc trực tiếp
vào CLI. Khi có MCP được Binance hỗ trợ, chỉ cần thêm adapter implement gateway;
tool names, domain models và deterministic services không phải đổi.
