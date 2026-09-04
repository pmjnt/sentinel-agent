# Thiết kế Sentinel Phase 1

## Mục tiêu

Xây dựng một ứng dụng console Python tối giản để minh họa cách một AI Agent tự chọn tool, nhận dữ liệu có cấu trúc và phân tích rủi ro danh mục crypto. Phase 1 chỉ dùng dữ liệu mock, không kết nối Binance, không giao dịch và không có API web, frontend hay database.

## Kiến trúc

Sentinel gồm bốn phần có trách nhiệm rõ ràng:

1. Pydantic models mô tả dữ liệu portfolio và market data.
2. Các hàm Python thuần trả dữ liệu mock.
3. Các `FunctionTool` bọc hàm thuần để OpenAI Agents SDK cung cấp chúng cho LLM.
4. Một `Agent` cùng `Runner` thực hiện vòng lặp nhận yêu cầu, chọn tool và tạo câu trả lời.

Hàm thuần và tool dùng hai tên biến khác nhau. Ví dụ, `get_portfolio` là hàm có thể unit test trực tiếp; `get_portfolio_tool` là object đăng ký với Agent nhưng có tên tool mà LLM nhìn thấy là `get_portfolio`.

## Thành phần

### Models

- `PortfolioAsset`: symbol, số lượng mock và giá trị USD.
- `Portfolio`: danh sách tài sản và tổng giá trị USD.
- `MarketData`: symbol, trạng thái hỗ trợ, giá, phần trăm thay đổi 24 giờ, volatility và thông báo lỗi tùy chọn.
- Volatility dùng enum đơn giản để tránh giá trị không nhất quán.

### Portfolio tool

`get_portfolio()` trả portfolio cố định:

- BTC: 6.000 USD
- ETH: 2.500 USD
- USDT: 1.500 USD
- Tổng: 10.000 USD

`get_portfolio_tool` bọc hàm trên bằng `function_tool`. Docstring giải thích khi nào LLM nên gọi tool.

### Market tool

`get_market_data(symbol)` chuẩn hóa symbol sang chữ hoa và trả dữ liệu cố định cho BTCUSDT và ETHUSDT. Symbol không hỗ trợ trả `MarketData` có `supported=False` và thông báo lỗi rõ ràng; hàm không crash.

`get_market_data_tool` bọc hàm trên và cung cấp tên, mô tả, input schema cho LLM.

### Sentinel Agent

Agent có tên `Sentinel`. Instructions yêu cầu Agent:

- Không tự tạo portfolio hoặc market data.
- Gọi portfolio tool khi cần thông tin sở hữu.
- Gọi market tool khi cần giá hoặc biến động mock hiện tại.
- Giải thích concentration risk.
- Tách dữ liệu thực tế từ tool khỏi nhận định của AI.
- Không thực hiện hoặc tuyên bố đã thực hiện giao dịch.
- Trả lời ngắn gọn, dễ hiểu.

MVP không tự cấu hình model; `Agent` dùng model mặc định của Agents SDK để tránh thêm cấu hình chưa cần thiết. `OPENAI_API_KEY` là cấu hình bắt buộc duy nhất.

### Console application

`python main.py` tải `.env`, kiểm tra API key và mở vòng lặp:

```text
Sentinel >
```

Mỗi input không rỗng được gửi tới `Runner.run`. Kết quả cuối được in ra console. `exit` kết thúc chương trình. README cung cấp câu hỏi mẫu: `Analyze my BTC exposure and tell me whether it currently looks risky.`

## Luồng Agent

```text
User
  |
  v
Sentinel Agent / LLM
  |
  | chooses tools
  |
  +----> get_portfolio()
  |
  +----> get_market_data()
  |
  v
LLM analyzes tool results
  |
  v
Final response
```

Với yêu cầu phân tích BTC exposure, LLM được kỳ vọng tự gọi `get_portfolio()`, sau đó gọi `get_market_data("BTCUSDT")`, rồi kết hợp hai kết quả. Việc lựa chọn tool do LLM thực hiện dựa trên Agent instructions, mô tả tool và schema tham số; code không hard-code thứ tự hai lời gọi này.

## Xử lý lỗi

- Thiếu `OPENAI_API_KEY`: dừng trước khi gọi API và in hướng dẫn cấu hình dễ hiểu.
- Symbol không hỗ trợ: trả structured result có lỗi thay vì raise exception.
- Input console rỗng: bỏ qua và tiếp tục vòng lặp.
- Lỗi khi chạy Agent: hiển thị thông báo ngắn, không làm lộ secret, rồi cho phép người dùng tiếp tục hoặc thoát.

## Kiểm thử và xác thực

Unit tests không gọi OpenAI API. Chúng gọi trực tiếp các hàm Python thuần để kiểm tra:

- Tổng và phân bổ của portfolio mock.
- Dữ liệu BTCUSDT.
- Kết quả có cấu trúc cho symbol không hỗ trợ.

Xác thực cuối gồm chạy toàn bộ `pytest` và compile tất cả file Python bằng `python -m compileall`.

## Phạm vi thay thế khi tích hợp Binance MCP

Phase sau sẽ thay hoặc loại bỏ phần dữ liệu mock trong `app/tools/portfolio.py` và `app/tools/market.py`. Agent instructions, model dữ liệu, vòng lặp console và cách LLM chọn tool có thể được giữ lại hoặc điều chỉnh nhỏ. Phase 1 không triển khai MCP client, Binance authentication hoặc trading.
