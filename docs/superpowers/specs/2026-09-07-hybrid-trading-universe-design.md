# Hybrid trading universe

## Mục tiêu

Sentinel được phép giao dịch một nhóm token phổ biến theo luồng approval thông
thường. Token ngoài nhóm vẫn có thể được giao dịch khi người dùng phê duyệt ngoại
lệ rõ ràng, nhưng approval không được vượt qua các điều kiện an toàn tuyệt đối.

## Ba tầng kiểm soát

### Default universe

Một danh sách cấu hình chứa các Spot USDT pair phổ biến. Danh sách này không do
LLM tự quyết định. Giao dịch vẫn phải qua Risk Engine và approval hiện tại.

### Symbol override

Một pair ngoài default universe có thể tạo proposal với trạng thái
`SYMBOL_OVERRIDE_REQUIRED` khi:

- Binance `exchangeInfo` xác nhận pair tồn tại, thuộc Spot và đang `TRADING`;
- market data, order-book depth và liquidity được xác minh;
- các rule tuyệt đối và portfolio policy đều cho phép.

Approval ngoại lệ được gắn với một plan bất biến gồm session, symbol, side, số
tiền và thời gian hết hạn. Nó không thêm symbol vào danh sách vĩnh viễn.

### Absolute guards

Không approval nào được bỏ qua:

- Binance không xác nhận pair đang giao dịch Spot;
- không đủ balance hoặc liquidity;
- slippage vượt giới hạn;
- giá trị lệnh vượt hard maximum;
- high volatility khi policy yêu cầu block;
- symbol bị `allowed_trade_symbols` loại trừ;
- proposal làm phát sinh hoặc làm nặng policy violation;
- withdrawal hoặc transfer.

Muốn giao dịch symbol bị policy loại trừ, người dùng phải cập nhật policy trước;
approval một plan không được ngầm sửa policy.

## Luồng

```text
LLM đề xuất symbol
→ Python đọc exchangeInfo và market data
→ Default symbol: normal approval
→ Non-default symbol: explicit symbol override approval
→ Revalidate portfolio, market, policy và plan
→ Binance Demo execution
→ Verify order status và refresh portfolio
```

## UI

Plan ngoài default universe hiển thị cảnh báo rõ ràng về symbol, lý do ngoại lệ,
số tiền và thời gian hết hạn. Người dùng phải bấm approval dành riêng cho ngoại
lệ; câu trả lời hội thoại mơ hồ không được xem là approval.

## Phạm vi đầu tiên

Chỉ Binance Demo Spot market order. Không hỗ trợ production trading, withdrawal,
transfer, margin, futures hoặc quyền tự động dài hạn trong thay đổi này.

## Kiểm thử

- Default symbol đi qua luồng approval thông thường.
- Valid non-default Spot symbol tạo yêu cầu override.
- Invalid, inactive hoặc non-Spot symbol bị chặn.
- Override không vượt qua policy, balance, liquidity, slippage hoặc hard maximum.
- Override sai session/plan hoặc hết hạn bị từ chối.
- Execution luôn revalidate và verify kết quả.
