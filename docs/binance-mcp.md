# Binance MCP: kết nối an toàn và đọc schema thật

## Mục đích của bước này

Sentinel kết nối trực tiếp tới Binance Agentic MCP Server tại:

```text
https://agent.binance.com/mcp/agentic
```

Lệnh discovery hiện tại chỉ thực hiện:

```text
OAuth → initialize MCP session → list_tools() → in schema đã chuẩn hóa
```

Nó **không gọi bất kỳ Binance tool nào**, không đọc portfolio, không đọc market
data và không giao dịch. Đây là bước bắt buộc để code adapter theo đúng tên tool và
schema thật thay vì phỏng đoán.

## Chạy discovery

Binance dùng OAuth Client ID Metadata Document (CIMD), không hỗ trợ dynamic client
registration cho client tùy ý. Trước tiên cần host một JSON document trên URL HTTPS
công khai có path, ví dụ `https://sentinel.example/oauth/client-metadata.json`:

```json
{
  "client_id": "https://sentinel.example/oauth/client-metadata.json",
  "client_name": "Sentinel",
  "redirect_uris": ["http://127.0.0.1:8766/callback"],
  "token_endpoint_auth_method": "none",
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "application_type": "native"
}
```

`client_id` phải chính là URL đang host document. Sau đó cấu hình `.env`:

```dotenv
BINANCE_MCP_CLIENT_METADATA_URL=https://sentinel.example/oauth/client-metadata.json
```

Không đặt secret trong document này; đây là metadata công khai của OAuth client.

Sau khi cấu hình, chạy:

```bash
python -m app.mcp.discover
```

Trình duyệt sẽ mở trang xác thực Binance. Chỉ cấp các quyền đọc cần thiết, chẳng
hạn Market Data và Account nếu giao diện quyền có hiển thị chúng. Không cấp Trade,
Transfer hoặc quyền ghi khác.

Sau khi xác nhận, Binance chuyển trình duyệt về callback cục bộ:

```text
http://127.0.0.1:8766/callback
```

Terminal sẽ in catalog JSON gồm các trường an toàn để review:

```text
name, title, description, input_schema, output_schema,
read_only_hint, destructive_hint
```

## Token được giữ ở đâu?

Token OAuth và thông tin đăng ký client chỉ nằm trong bộ nhớ của process Python.
Khi process kết thúc, dữ liệu đó biến mất. Sentinel không ghi token vào `.env`, file,
log hay database.

Vì storage chưa persistent, lần chạy discovery sau có thể yêu cầu đăng nhập lại.
Đây là chủ ý an toàn cho bước khảo sát schema.

Nếu biến `BINANCE_MCP_CLIENT_METADATA_URL` bị thiếu hoặc không phải HTTPS document,
Sentinel dừng ngay trước khi mở socket hay gửi OAuth request.

## Các nguyên tắc bảo vệ

- `list_tools()` chỉ đọc mô tả capability; nó không chạy capability đó.
- Annotation `readOnlyHint` của server chỉ là metadata để review, không phải bằng
  chứng cho phép tự động gọi tool.
- Raw Binance MCP tools không được đưa trực tiếp cho LLM.
- Adapter production sau này chỉ ánh xạ capability đã duyệt vào hai application
  tool ổn định: `get_portfolio()` và `get_market_data(symbol)`.
- Nếu Binance lỗi hoặc thiếu dữ liệu, workflow phải dừng an toàn; không thay thế âm
  thầm bằng mock data.
- Phase hiện tại không có execution, approval giả hay giao dịch thật.

## Sau khi có catalog

Ta review tên tool, input/output schema và quyền của các capability đọc. Chỉ sau đó
mới viết Binance adapter. Dữ liệu Binance sẽ được chuyển sang Pydantic domain model,
rồi deterministic Python mới tính tỷ trọng, phát hiện vi phạm, lập proposal và chạy
RiskEngine.

```text
Binance MCP payload
        ↓ adapter + validation
Portfolio / MarketData
        ↓ deterministic services
Violation → RebalancePlan → RiskDecision
        ↓
LLM giải thích kết quả cho người dùng
```
