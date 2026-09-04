# Kiến trúc Sentinel

## Mục tiêu kiến trúc

Sentinel tách ba loại trách nhiệm:

```text
LLM hiểu ngôn ngữ và điều phối việc đọc dữ liệu.
Python tính toán và áp dụng policy.
RiskEngine quyết định proposal bị chặn, cần duyệt hay an toàn để đề xuất.
```

Không thành phần nào trong phiên bản read-only có quyền thực hiện giao dịch.

## Dependency direction

```text
app.models
    ↑
app.services
    ↑
Agent / MCP adapter / FastAPI
```

- `app.models`: dữ liệu nghiệp vụ và validation cấp field.
- `app.services`: phép tính và business rule deterministic.
- `app.agent`: hiểu ngôn ngữ, chọn application tool và giải thích kết quả.
- `app.mcp`: kết nối Binance, discover tool và chuyển payload sang model nội bộ.
- `app.api`: HTTP boundary; không chứa phép tính tài chính.
- `web`: chỉ giao tiếp với FastAPI, không giữ secret.

`models` và `services` không được import `agents`, `litellm`, `fastapi` hoặc `mcp`.

## Domain core hiện đã có

### Models

- `portfolio.py`: `PortfolioAsset`, `Portfolio`.
- `market.py`: `MarketData`, `MarketDataError`, `Volatility`.
- `policy.py`: policy hoàn chỉnh, patch và violation.
- `trade.py`: action đề xuất và rebalance plan.
- `risk.py`: risk status và reason code.

### Services

- `portfolio_service.py`: tính tổng portfolio và tỷ trọng.
- `policy_service.py`: merge patch và phát hiện violation.
- `rebalance_service.py`: tạo proposal, không execute.
- `risk_service.py`: áp dụng rule theo thứ tự ưu tiên.

## Luồng deterministic

Với portfolio:

```text
BTC  $5,500
ETH  $2,500
USDT $2,000
```

`calculate_portfolio()` tự tính:

```text
BTC  55%
ETH  25%
USDT 20%
```

Với policy:

```text
USDT tối thiểu 30%
Mỗi crypto asset tối đa 40%
Chặn rebalance khi volatility HIGH
Trên $1,000 cần approval
```

Các service tạo kết quả:

```text
PolicyService
  ├── BTC vượt 40%
  └── USDT dưới 30%

RebalanceService
  └── đề xuất SELL ~$1,500 BTC

RiskService
  └── BLOCKED nếu BTC volatility HIGH
```

LLM không tham gia vào các phép tính này.

## Ranh giới dữ liệu ngoài

Ở checkpoint Binance MCP, chỉ một port được thêm:

```python
class PortfolioMarketGateway(Protocol):
    async def get_portfolio(self) -> Portfolio: ...
    async def get_market_data(self, symbol: str) -> MarketData: ...
```

Hai Agents SDK function tools ổn định gọi port này. Production implementation sử dụng Binance MCP; integration test sử dụng fake gateway. Raw Binance MCP tools không được đưa trực tiếp cho LLM.

## Trạng thái hiện tại và trạng thái đích

Hiện tại console Agent vẫn sử dụng hai tool mock cũ để giữ ứng dụng chạy được trong quá trình chuyển đổi. Đây là trạng thái tạm thời, không phải fallback production.

Trạng thái đích:

```text
Web UI
  ↓
FastAPI
  ↓
Sentinel Agent
  ├── get_portfolio() ─────┐
  └── get_market_data() ───┤
                            ↓
                     Binance MCP gateway
                            ↓
Policy Engine → Planner → RiskEngine
                            ↓
                 Structured result + explanation
```

Nếu Binance không kết nối hoặc trả lỗi, workflow dừng và báo lỗi. Không sử dụng mock data thay thế.
