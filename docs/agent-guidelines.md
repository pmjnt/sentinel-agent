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
propose_trade(symbol, side, quote_usd, reason)
set_market_research_plan(candidate_limit, timeframes, lookback_days, priorities)
scan_top_markets()
analyze_market_history(symbol)
finalize_market_research()
```

Không thêm `place_order`, `execute`, `transfer`, `withdraw`, generic CLI hoặc URL
tool vào Agent. `propose_trade` chỉ tạo plan. Execution adapter nằm ngoài LLM,
chỉ chạy sau RiskEngine, explicit UI approval và revalidation.

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

## Vòng nghiên cứu thị trường thích ứng

```text
1. LLM chọn recipe bằng set_market_research_plan
2. scan_top_markets xếp hạng Spot USDT theo quote volume đã xác minh
3. LLM chọn ít nhất 2 candidate trong scan để analyze_market_history
4. Python tính indicator cho từng timeframe
5. finalize_market_research đóng gói evidence so sánh
6. LLM đưa ra nhận định và lựa chọn ưu tiên của riêng Sentinel
```

Recipe bị giới hạn: 3–10 candidate, 1–2 timeframe, 1–90 ngày, 20–1.000
candle/timeframe và tối đa 5 deep analyses. LLM không được phân tích symbol ngoài
scan, gọi CLI tùy ý hoặc tự tính authoritative indicator. High volume chỉ là bộ
lọc thanh khoản, không tự động có nghĩa là cơ hội tốt.

Mỗi run chỉ được set một plan. Candidate thất bại/retry vẫn tính vào cap 5.
Sau finalize, snapshot bị khóa và không được thêm candidate. Gateway yêu cầu đủ
số candle, đúng interval, liên tục và còn mới; ticker scan quá 15 phút bị từ chối.

Runtime từ chối final answer nếu Agent đã bắt đầu research nhưng chưa
`finalize_market_research`. Ít nhất hai candidate thành công mới được so sánh.
Lỗi một candidate được ghi nhận; lỗi scan bắt buộc làm request fail-closed.

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
- SSE `completed` trả policy, profile, analysis, market research, activity và
  execution state dưới dạng JSON typed.
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

Response không bắt buộc `Assessment / Rationale / Recommendation / Limitations`.
LLM chọn cấu trúc tự nhiên phù hợp, nhưng mọi nhận định tài chính phải dựa trên
analysis hoặc finalized research đã xác minh.

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
- Research có được finalize và giữ raw candles ở backend không?
- Recommendation có bị nhầm thành approval hoặc execution không?
