# Flexible portfolio advice

## Mục tiêu

Sentinel phải hành xử như một cố vấn hội thoại thay vì một biểu mẫu hỏi đáp. Khi
đã có đủ dữ kiện cốt lõi, Agent đưa ra một số phương án phù hợp và để người dùng
chọn, thay vì tiếp tục hỏi các thông tin tùy chọn.

## Thiết kế

Python xác định trạng thái hồ sơ tư vấn:

- Cần có mục tiêu đầu tư.
- Cần có thời hạn đầu tư.
- Cần có ít nhất một trong hai: mức lỗ chấp nhận hoặc risk tolerance.

Trạng thái `READY` hoặc `INCOMPLETE` được đưa vào input mỗi lượt chạy. Khi `READY`,
LLM được quyền chọn 2–4 phương án phù hợp với tình huống, nêu trade-off và phương
án nó nghiêng về. Các trường phụ như liquidity need không được dùng làm lý do để
hỏi lặp lại.

Khi `INCOMPLETE`, LLM chỉ hỏi nếu thông tin thiếu thực sự làm thay đổi lời khuyên;
nếu vẫn có thể giúp, nó nêu giả định và đưa lựa chọn không mang tính thực thi.

## Ranh giới an toàn

LLM chỉ tạo nhận định và phương án tư vấn. Portfolio, market data, phép tính,
policy validation, Risk Engine, trade proposal và approval vẫn đi qua Python và
Binance Demo. Một phương án tư vấn không phải lệnh giao dịch.

## Kiểm thử

- Hồ sơ đủ ba nhóm dữ kiện trả `READY` dù không có risk tolerance riêng.
- Hồ sơ thiếu dữ kiện cốt lõi trả `INCOMPLETE`.
- Input gửi LLM chứa trạng thái rõ ràng.
- Instruction yêu cầu đưa lựa chọn khi `READY` và không hỏi trường tùy chọn.
- Chạy lại hội thoại tư vấn thực tế qua streaming API.
