# Hướng dẫn kiểm thử Sentinel

## Mục tiêu

Test phải chứng minh logic tài chính đúng mà không phụ thuộc vào OpenAI, Gemini hoặc Binance.

## Test layers

### Unit tests

Kiểm tra model và pure service:

- validation và normalization;
- portfolio total và allocation;
- policy patch semantics;
- policy violations;
- rebalance arithmetic;
- RiskEngine priority.
- research-plan bounds và candidate filtering;
- deterministic kline indicators;
- Agent không được kết luận khi research chưa finalize.

Unit test không được:

- đọc `.env` thật;
- gọi LLM;
- gọi `binance-cli` thật hoặc kết nối mạng;
- mở browser;
- phụ thuộc thời gian chờ.

Application orchestration cũng được test offline bằng fake Request Interpreter,
fake gateway và fake Reporter. Fake chỉ thay thế ranh giới I/O; policy,
allocation, planner và RiskEngine vẫn chạy code thật trong test của chúng.

### Integration tests

Khi FastAPI được thêm, integration test kiểm tra:

- API contract bằng dependency override;
- API workflow bằng fake Request Interpreter, fake gateway và fake Reporter;
- Binance CLI payload mapping bằng fixture đã loại dữ liệu nhạy cảm;
- read-only allow-list;
- error path không fallback sang mock.
- SSE research activity và typed `market_research` response;
- UI evidence không chứa raw candles hoặc secrets.

Fake chỉ mô phỏng boundary, không mô phỏng lại business logic.

### Real smoke test

Smoke test Binance là lệnh opt-in và không nằm trong pytest mặc định. Nó dùng Binance Demo credentials do người dùng cấu hình cục bộ và chỉ chạy các lệnh đọc nằm trong allow-list. Không chạy trong CI và không in khóa bí mật.

## TDD workflow

```text
1. Viết một test thể hiện behavior mong muốn.
2. Chạy và xác nhận test fail đúng lý do.
3. Viết implementation nhỏ nhất.
4. Chạy test mới.
5. Chạy toàn bộ suite liên quan.
6. Refactor khi mọi test đang xanh.
```

## Lệnh kiểm tra

Python:

```bash
.venv/bin/python -m pytest -q
```

UI JavaScript:

```bash
node --test tests/test_ui.js
```

Syntax/import compilation:

```bash
.venv/bin/python -m compileall -q app main.py tests
```

Dependency boundary:

```bash
rg -n 'from (agents|fastapi|mcp)|import (agents|fastapi|mcp)' app/models app/services
```

Lệnh cuối phải không có kết quả.

Whitespace validation:

```bash
git diff --check
```

## Test data

Sử dụng chuỗi khi tạo `Decimal`:

```python
Decimal("5500")
Decimal("0.55")
```

Không dùng:

```python
Decimal(0.55)
```

Fixture SRD chuẩn:

```text
BTC  $5,500  55%
ETH  $2,500  25%
USDT $2,000  20%
Total $10,000
```

Market fixture:

```text
BTCUSDT price $110,000
24h change -4.2%
volatility HIGH
estimated slippage 0.05%
```

Không copy credential, account ID hoặc Binance response chưa làm sạch vào fixture.

Research fixtures phải dùng timestamp cố định, ít nhất 20 candles và `Decimal`
từ string. Gateway tests chỉ fake kết quả CLI; chúng phải xác nhận batching tối
đa 100 symbol, kline limit tối đa 1.000 và không thực thi process/network thật.

Không test bằng lệnh order thật. Luồng approval/execution luôn dùng fake gateway;
pytest không được phụ thuộc vào Binance Demo balance hoặc trạng thái thị trường.
