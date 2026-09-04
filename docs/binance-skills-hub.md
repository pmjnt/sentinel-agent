# Binance Skills Hub cho Sentinel

## Sentinel dùng gì?

Sentinel dùng `binance-cli` chính thức từ Binance Skills Hub. Đây là integration
cho Binance Agent OS Track A và không phải Binance Agentic MCP Server.

```text
Sentinel tool → BinanceCliGateway → binance-cli → Binance Demo API
```

## Tạo môi trường Demo

1. Đăng nhập Binance Demo Trading.
2. Mở API Management trong môi trường Demo.
3. Tạo API key dành riêng cho Demo.
4. Điền key trực tiếp vào `.env` local; không gửi qua chat.

```dotenv
BINANCE_API_ENV=demo
BINANCE_CLI_PATH=binance-cli
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
```

Hai giá trị trống do người dùng tự điền. Không dùng production key cho demo.

## Quy tắc bảo mật

- `.env` nằm trong `.gitignore`.
- Không đưa key vào frontend, prompt, log hoặc exception.
- Không dùng `shell=True`.
- Không cho LLM tạo command.
- Chỉ bốn command đọc được hard-code trong gateway.
- Không sử dụng generic `binance-cli request`.
- Không có order, cancel, transfer hay withdrawal.
- Lỗi dữ liệu làm workflow dừng, không fallback mock.

## Kiểm tra public market

```bash
BINANCE_API_ENV=demo binance-cli spot ticker24hr --symbol BTCUSDT
```

Public market command không cần credentials. Account balance là private data nên
`spot get-account` cần Demo key.

## Dữ liệu trả về

Payload CLI là dữ liệu ngoài và không được tin trực tiếp. Pydantic schema kiểm tra
field và kiểu dữ liệu trước khi gateway tạo `Portfolio` hoặc `MarketData`.

Mọi kết quả được gắn `BINANCE_DEMO` để LLM và UI không thể trình bày số dư mô phỏng
như tài sản thật.
