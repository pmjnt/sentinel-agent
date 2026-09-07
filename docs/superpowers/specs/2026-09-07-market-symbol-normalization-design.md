# Chuẩn hóa symbol cho market tool

## Mục tiêu

Khi người dùng bổ sung đủ Investor Profile cho một yêu cầu tư vấn đang dang dở,
Sentinel phải tiếp tục đọc portfolio và đưa ra lời khuyên. Một cách gọi market tool
không nhất quán từ LLM không được làm hỏng toàn bộ workflow.

## Nguyên nhân hiện tại

`get_market_data` yêu cầu pair như `BTCUSDT`, nhưng LLM đôi khi gửi asset như
`USDC`. Gateway chuyển nguyên giá trị này cho Binance nên Binance từ chối request.

## Thiết kế đã chọn

Chuẩn hóa input tại controlled-tool boundary trước khi gọi gateway:

- `BTC` thành `BTCUSDT`.
- `USDC` thành `USDCUSDT`.
- Pair đã kết thúc bằng `USDT` được giữ nguyên.
- `USDT` và `USDTUSDT` trả về `NOT_REQUIRED`, không gọi Binance và không tạo
  `data_error`.

Gateway vẫn chỉ nhận symbol đã chuẩn hóa. Kết quả market thật vẫn phải đến từ
Binance Demo; hệ thống không tạo dữ liệu giả.

## Luồng xử lý

1. LLM gọi `update_investor_profile`.
2. LLM tiếp tục gọi `get_portfolio` dựa trên yêu cầu tư vấn trước đó.
3. Nếu LLM gọi `get_market_data` bằng asset, Python chuẩn hóa thành pair USDT.
4. Binance Demo trả dữ liệu market thật.
5. LLM gọi `evaluate_portfolio_risk` và tạo lời khuyên dựa trên kết quả đã xác thực.

## Xử lý lỗi

- Asset hoặc pair không hợp lệ vẫn trả lỗi an toàn.
- Lỗi Binance thật vẫn làm workflow fail-closed.
- Chỉ self-pair USDT được xem là không cần thiết thay vì là lỗi dữ liệu.

## Kiểm thử

- Test `USDC` được chuyển thành `USDCUSDT` trước khi gọi gateway.
- Giữ test `USDTUSDT` không gọi gateway và không tạo lỗi.
- Test các pair hợp lệ như `BTCUSDT` vẫn giữ nguyên.
- Chạy toàn bộ Python tests, UI tests và một lượt end-to-end qua streaming API.
