# Thiết kế giao diện vintage cho Sentinel

## Mục tiêu

Tạo một giao diện web tĩnh, đơn giản và đậm phong cách vintage để minh họa trải nghiệm phân tích portfolio của Sentinel. UI cho phép chọn OpenAI/Gemini từ danh sách model cố định, nhập yêu cầu, quan sát từng bước Agent giả lập, xem tool input/output và đọc báo cáo tách biệt facts với AI interpretation.

Giao diện không gọi OpenAI, Gemini hoặc backend. FastAPI, model fetching, streaming thật, authentication và Binance vẫn ngoài phạm vi.

## Công nghệ và cấu trúc

Chỉ dùng HTML, CSS và JavaScript thuần:

```text
web/
├── index.html
├── styles.css
└── app.js
```

Không thêm npm, React, bundler hoặc CSS framework. Có thể chạy bằng:

```bash
python -m http.server 8000 -d web
```

## Phong cách thị giác

Giao diện mang cảm giác bàn phân tích tài chính cũ:

- Nền giấy ngà với texture nhẹ tạo bằng CSS, không dùng ảnh tải ngoài.
- Mực xanh đen, đỏ con dấu và vàng đồng làm accent.
- Serif cho tiêu đề/báo cáo, monospace cho log và dữ liệu.
- Viền kép, đường kẻ mảnh, góc vuông, nhãn viết hoa và dấu thời gian.
- Không gradient bóng bẩy, glassmorphism, neon hoặc bo góc lớn.
- Chuyển động vừa đủ: con trỏ log nhấp nháy và dòng trạng thái xuất hiện tuần tự.
- Tôn trọng `prefers-reduced-motion`.

UI responsive: desktop dùng hai cột control/report; màn hình hẹp xếp thành một cột. Contrast, focus state, label và semantic HTML phải rõ.

## Bố cục

### Masthead

Hiển thị `SENTINEL`, phụ đề `CRYPTO RISK DESK · EST. 2026`, trạng thái `LOCAL MOCK TERMINAL`, và ghi chú dữ liệu hiện tại là mock.

### Analysis request

- Provider select: OpenAI hoặc Gemini.
- Model select phụ thuộc provider, dùng danh sách cố định trong JavaScript.
- Textarea chứa sẵn prompt mẫu phân tích BTC exposure.
- Nút `RUN RISK ANALYSIS`.
- Không hiển thị hoặc thu thập API key.

Danh sách ban đầu:

```text
OpenAI: gpt-5.6-luna, gpt-5.4-mini
Gemini: gemini-3.8-flash, gemini-3.1-pro-preview
```

### Agent activity log

Khi người dùng chạy phân tích, UI reset trạng thái cũ, khóa nút và lần lượt hiển thị:

1. Request received.
2. Portfolio data required.
3. Calling `get_portfolio()`.
4. Portfolio tool returned data.
5. BTC market context required.
6. Calling `get_market_data("BTCUSDT")`.
7. Market tool returned data.
8. Analyzing concentration risk.
9. Report ready.

Mỗi bước có trạng thái pending, active hoặc complete. Tiến trình chỉ là mô phỏng bằng timer; nhãn `SIMULATED AGENT RUN` luôn hiển thị để không gây hiểu nhầm đây là sự kiện backend thật.

### Tool evidence

Hai khối tool result mở sẵn khi tool tương ứng hoàn thành:

```text
get_portfolio()
BTC $6,000 · ETH $2,500 · USDT $1,500 · TOTAL $10,000

get_market_data("BTCUSDT")
PRICE $110,000 · 24H -4.2% · VOLATILITY HIGH
```

Dữ liệu này khớp với mock Python hiện tại. Tool input/output được trình bày như bằng chứng, không trộn với nhận định AI.

### Sentinel report

Báo cáo xuất hiện sau bước cuối và gồm hai phần:

- `FACTS FROM TOOLS`: BTC chiếm 60%, thay đổi 24h -4.2%, volatility HIGH.
- `AI INTERPRETATION`: concentration risk cao và kết hợp với volatility cao khiến exposure hiện có vẻ rủi ro.

Báo cáo ghi rõ dữ liệu market là mock và không phải lời khuyên tài chính. Không tuyên bố thực hiện giao dịch.

## Hành vi JavaScript

- Provider change cập nhật model select và tự chọn model đầu tiên.
- Submit rỗng hiển thị validation cạnh textarea và không bắt đầu tiến trình.
- Submit hợp lệ chạy state machine giả lập, ngăn double-submit và cập nhật `aria-live`.
- Chạy lại sẽ hủy timer cũ, reset log/evidence/report rồi chạy tiến trình mới.
- Model/provider được chọn hiển thị trong run metadata nhưng không thay đổi nội dung mock report.

Logic danh sách model và tạo các bước tiến trình được viết thành hàm nhỏ có thể kiểm tra độc lập bằng Node built-in test runner, không thêm dependency frontend.

## Kiểm thử và xác thực

- Unit test đổi provider trả đúng model list.
- Unit test activity steps có đúng thứ tự tool calls.
- Unit test prompt rỗng bị từ chối.
- Chạy `node --test` cho logic JavaScript.
- Chạy Python tests hiện tại để bảo đảm Agent backend không bị ảnh hưởng.
- Chạy `compileall` cho Python.
- Mở UI qua local HTTP server và kiểm tra desktop/mobile, progress, tool evidence, report, keyboard focus và reduced motion.

## Kết nối backend sau này

Khi FastAPI/streaming được thêm:

```text
Hiện tại: timer giả lập -> render activity event
Sau này:  SSE/WebSocket event -> render cùng activity event
```

Hàm render và bố cục giữ nguyên. Chỉ lớp tạo event mock trong `app.js` được thay bằng client gọi backend. Provider/model select sẽ tiếp tục gửi lựa chọn, còn API keys luôn nằm ở backend.

