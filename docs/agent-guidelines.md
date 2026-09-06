# Sentinel Agent Guidelines

## LLM được làm gì?

- Hiểu tiếng Việt hoặc tiếng Anh.
- Phân biệt chat thường, xem/đổi policy và yêu cầu phân tích.
- Tự chọn tool đọc portfolio/market phù hợp.
- Sau khi nhận kết quả tool, quyết định bước an toàn tiếp theo.
- Đưa ra nhận định định tính và lời khuyên thận trọng từ facts đã xác minh.

LLM không được tự tạo portfolio, market data, threshold, phép tính, formal risk
status hoặc execution state.

## Tool allowlist

Agent chỉ được thấy:

```text
get_portfolio()
get_market_data(symbol)
update_policy(changes)
view_policy()
update_investor_profile(changes)
view_investor_profile()
evaluate_portfolio_risk(focus_symbols)
```

Không thêm `place_order`, `trade`, `transfer`, `withdraw`, generic CLI hoặc URL
tool vào Agent. Nếu sau này có execution, một workflow riêng phải kiểm tra plan,
RiskEngine và explicit user approval trước khi gọi execution adapter.

## Vòng lặp bắt buộc cho phân tích

```text
1. get_portfolio
2. đọc holdings do tool trả về
3. get_market_data cho symbol liên quan
4. evaluate_portfolio_risk
5. giải thích PortfolioAnalysis do Python trả về
```

Nếu evaluation trả `MISSING_OBSERVATIONS`, Agent phải gọi tool được yêu cầu rồi
evaluation lại; không được đoán. Nếu tool trả `ERROR`, Agent phải nói dữ liệu
không xác minh được và không khuyến nghị hành động.

Một analysis tối đa 20 market observations. Vượt giới hạn sẽ fail-closed. Nếu
Agent đọc dữ liệu hoặc nhận yêu cầu tài chính nhưng dừng trước
`evaluate_portfolio_risk`, runtime từ chối final text.

OpenAI Agents SDK thực hiện loop: gửi prompt và tool schemas cho model, chạy tool
mà model chọn, trả result vào conversation, rồi gọi model lại. Vì vậy LLM thật
sự quan sát dữ liệu giữa các bước; nó không chỉ biến JSON thành văn bản.

## Policy qua chat

`update_policy` nhận danh sách `PolicyToolChange`: field là enum và value là
text đơn giản (`"0.30"`, `"true"`, `"false"`, `"null"`). Python parse text
thành `PolicyChange` typed rồi Pydantic validate:

- Field không được gọi: giữ nguyên.
- Value `null`: xóa optional rule.
- Giá trị ngoài range hoặc trùng field: từ chối.
- Mơ hồ: Agent hỏi một câu làm rõ, không tự tạo số.

Patch chỉ được stage trong `SentinelRunContext`. Store chỉ commit sau khi
`Runner.run` thành công; vì thế lỗi model giữa chừng không cập nhật session.
Policy được giữ theo `session_id` trong RAM và mất khi process restart.

## Investor profile qua chat

Profile chỉ lưu preference người dùng nói rõ: mục tiêu, thời hạn, mức chịu rủi
ro, mức lỗ chấp nhận, nhu cầu thanh khoản và asset loại trừ. LLM dùng hai tool
profile để stage/view; Python parse và Pydantic validate. Profile không phải
portfolio observation, policy, approval hay quyền thực thi. Với phân bổ cụ thể,
Agent phải biết tối thiểu mục tiêu, thời hạn và risk tolerance/acceptable loss.

## Activity và structured response

- Chỉ map semantic tool event nằm trong allowlist sang timeline.
- Không gửi raw tool args/result, prompt, chain-of-thought hoặc secret.
- Text của model được buffer đến khi safety validation thành công.
- SSE `completed` trả policy, profile, analysis, activity và
  `execution_status=NOT_EXECUTED` dưới dạng JSON typed.
- Agent Pulse chỉ hiển thị các activity trên; đây không phải chain-of-thought.

## Chọn model an toàn

- `LLM_ALLOWED_MODELS` là allowlist do backend quản lý, không phải kết quả fetch
  tự do từ provider.
- `GET /api/models` chỉ trả provider/model đã bật và không bao giờ trả API key.
- `POST /api/chat/stream` phải gửi provider/model; backend validate lại trước
  khi tạo hoặc tái sử dụng Agent tương ứng.
- Đổi model vẫn dùng cùng `session_id`, nên conversation, policy và investor
  profile không bị reset.

Ví dụ “đổi giới hạn thành 40% rồi phân tích” phải gọi `update_policy` trước các
tool phân tích. “Phân tích trước rồi đổi thành 40%” dùng policy snapshot cũ cho
analysis đầu tiên và giữ nguyên thứ tự event khi render.

## Phân biệt facts và AI interpretation

Python render trước:

- portfolio và market facts;
- violations và proposal;
- `BLOCKED`, `REQUIRES_APPROVAL` hoặc `SAFE_TO_PROPOSE`;
- `Execution: NOT_EXECUTED`.

LLM chỉ viết phần có nhãn `AI interpretation`. Output định tính không được tự
tuyên bố formal status hoặc đã thực thi. Những từ reserved đó bị validator chặn.

## Model và độ ổn định

- Mọi Agent dùng `build_agent_model_settings()`.
- `parallel_tool_calls=False` để bảo toàn thứ tự stateful tools.
- Không gửi reasoning option riêng của provider. GPT-5.4 Mini mặc định là
  `none`; bỏ parameter dư tránh LiteLLM tự bridge sang một request path khác.
- Runtime tool loop trả text bình thường, không dùng union `ParsedRequest` phức
  tạp làm structured output. Mỗi tool vẫn có schema nhỏ, rõ và được validate.

## Checklist khi sửa prompt/tool

- Source of truth có luôn là tool result hoặc validated model không?
- Tool mới có mở rộng quyền tài chính hay shell không?
- Arithmetic và business rule có nằm trong deterministic Python không?
- Error có fail-closed và không rò secret không?
- Policy update có chỉ commit sau lượt chạy thành công không?
- Behavior mới có unit/integration test không gọi mạng không?
