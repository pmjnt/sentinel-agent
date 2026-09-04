# Kiến trúc Sentinel

## Trách nhiệm

```text
LLM
├── hiểu ngôn ngữ
├── chọn get_portfolio / get_market_data
└── giải thích kết quả

BinanceCliGateway
├── chọn command đọc cố định
├── validate JSON Binance
└── chuyển thành domain model

Python services
├── tính USD value và weight
├── phát hiện policy violation
├── tạo rebalance proposal
└── chạy RiskEngine
```

LLM không được thực hiện phép tính tài chính có tính quyết định và không được
quyền tạo command Binance.

## Dependency direction

```text
app.models
    ↑
app.services
    ↑
app.gateways (application port)
    ↑
app.binance (external adapter)
    ↑
app.tools / app.agent / main.py
```

- `app.models`: Pydantic domain data.
- `app.services`: business rules deterministic.
- `app.gateways`: interface do ứng dụng sở hữu.
- `app.binance`: adapter Binance Skills Hub và schema transport.
- `app.tools`: capability nhỏ, ổn định được expose cho LLM.
- `app.agent`: prompt và Agent construction.
- `web`: UI tĩnh, không nhận secret.

`models` và `services` không import Agents SDK, LiteLLM hoặc Binance CLI.

## Data flow

```text
LLM gọi get_portfolio()
  ↓
BinanceCliGateway
  ├── spot get-account
  └── spot ticker-price
  ↓
Pydantic transport validation
  ↓
PortfolioAsset(amount, usd_value)
  ↓
calculate_portfolio()
  ↓
Portfolio(total, weights, BINANCE_DEMO)
```

```text
LLM gọi get_market_data("BTCUSDT")
  ↓
validate symbol
  ↓
BinanceCliGateway
  ├── spot ticker24hr
  └── spot depth
  ↓
MarketData(price, change, volatility, slippage, BINANCE_DEMO)
```

Volatility dùng rule deterministic dựa trên độ lớn biến động 24 giờ:

```text
< 2%       LOW
2%..<4%    MEDIUM
>= 4%      HIGH
```

Slippage được ước lượng từ bid depth cho một reference sale 1,000 USDT. Đây là
con số tham chiếu phân tích, không phải một order.

## Security boundary

`BinanceCliRunner` dùng argument array và không mở shell. Public commands không
nhận credentials. Account command nhận Binance credentials qua child environment
nhưng không log chúng. LLM provider keys không được truyền sang CLI.

Command allowlist không chứa trade, transfer, withdrawal, cancel hay generic
request. Nếu CLI lỗi, schema sai, thiếu giá hoặc thiếu depth, workflow fail-closed
và không thay bằng mock data.

## Môi trường

Mặc định là `BINANCE_API_ENV=demo`. Portfolio là số dư mô phỏng của Binance Demo,
không phải tài sản thật. `prod` chỉ dành cho giai đoạn sau với key read-only và
không thay đổi command allowlist.

## Khả năng thay adapter

Hai AI tools phụ thuộc vào `PortfolioMarketGateway`, không phụ thuộc trực tiếp
vào CLI. Sau này có thể thay bằng MCP adapter được Binance hỗ trợ mà không đổi
tên tool, Agent prompt hoặc domain services.
