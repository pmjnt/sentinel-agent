# Chat-First Agent Pulse UI Design

## Mục tiêu

Thay dashboard vintage hiện tại bằng một giao diện chat tập trung, mềm và dễ
đọc. Sentinel vẫn phải khác chatbot thông thường nhờ `Agent Pulse`: một dòng
process nhỏ gắn với từng câu trả lời, cho biết Agent đã dùng tool và kiểm tra
deterministic nào.

UI dùng bảng màu lấy cảm hứng từ Binance: graphite tối, vàng làm accent, xanh
và đỏ chỉ dành cho trạng thái. Không dùng logo Binance, không sao chép màn hình
trading và không dùng icon Sentinel.

## Phạm vi

Thiết kế này bao gồm:

- chat UI responsive;
- Agent Pulse thu/phóng được;
- structured portfolio/policy/profile/market evidence trong lượt chat;
- model selector nhỏ và có thể đổi model thật;
- backend model allowlist;
- SSE activity và response hiện có;
- trạng thái loading, completed và failed.

Không bao gồm sidebar lịch sử, database, authentication, trade, transfer,
withdrawal, approval hoặc hidden chain-of-thought.

## Visual system

- Page background: graphite, không dùng đen tuyệt đối.
- Surface: nhiều lớp tối gần nhau thay cho border cứng.
- Accent: vàng dịu; không dùng vàng cho body text dài.
- Success/failure: xanh và đỏ chỉ dùng cho status.
- Typography: system sans-serif cho hội thoại, monospace cho metadata/process.
- Spacing: lưới 8px; gutter desktop 28px, mobile 15px.
- Radius: 16–20px cho shell/composer, 7–12px cho control phụ.
- Shadow: nhẹ, không glow mạnh.

Wordmark chỉ là chữ `SENTINEL` kèm một đường vàng ngắn. Không có logo hoặc
biểu tượng hình học.

## Layout

```text
+----------------------------------------------------+
| SENTINEL                         Current model  v   |
+----------------------------------------------------+
|                                                    |
|                              User message bubble   |
|                                                    |
| Sentinel   Assistant response                      |
|            [small Agent Pulse · 4 steps · done v]  |
|                                                    |
|                              Next user message     |
|                                                    |
+----------------------------------------------------+
| Ask Sentinel anything...                       ↑   |
+----------------------------------------------------+
```

Header, conversation và composer dùng chung một content grid tối đa 680px.
Desktop dùng cột speaker cố định 72px. Mobile chuyển speaker label lên trên,
không giữ cột rỗng.

Composer nằm cuối khung chat và có thể sticky trong viewport. Không có các
portfolio/report panel luôn mở bên cạnh chat.

## Agent Pulse

Agent Pulse là activity log, không phải reasoning nội bộ.

Trạng thái đóng mặc định chỉ cao khoảng 26px:

```text
▥  ●  4 steps completed  v
```

Khi đang chạy, text thay đổi theo event mới nhất, ví dụ `Checking market…`.
Khi mở, panel rộng tối đa 340px và hiển thị activity allowlist theo thứ tự:

```text
✓ Read portfolio       Binance Demo
✓ Check market         BTCUSDT
✓ Evaluate policy      Python
✓ Run Risk Engine      Python
```

Panel có thể kèm evidence summary ngắn từ structured response. Nó không hiển
thị raw tool arguments, raw result, prompt, API key hay chain-of-thought.

Mỗi lượt assistant có Pulse riêng. Activity của lượt mới không cập nhật nhầm
Pulse của lượt cũ.

## Structured response trong chat

Câu trả lời tự nhiên vẫn là nội dung chính. Dữ kiện authoritative được render
từ JSON, không parse từ prose của LLM.

Khi người dùng mở evidence, UI có thể hiển thị theo thứ tự:

1. portfolio total và allocation;
2. market observations;
3. policy/profile đã dùng;
4. violations và proposed action;
5. Risk Engine status;
6. `Execution: NOT_EXECUTED`.

Các section không có dữ liệu sẽ không chiếm chỗ. General chat không tạo evidence
panel trống.

## Model selector

Model control là một pill nhỏ ở góc phải header. Nó dùng CSS chevron với flex
alignment, không dùng ký tự Unicode `⌄` để tránh lệch baseline.

Khi bấm, một popover nhỏ hiển thị các route backend cho phép. Danh sách không
được nhập tùy ý và không fetch trực tiếp từ provider.

Backend cung cấp:

```text
GET /api/models
```

Response chỉ chứa route được enable, label và default route. Nó không tiết lộ
API key hoặc giá trị secret. Provider không có key hợp lệ sẽ không xuất hiện.

Mỗi request gửi lựa chọn đã xác định:

```json
{
  "session_id": "browser-session-id",
  "message": "Analyze my portfolio.",
  "provider": "gemini",
  "model": "configured-model-id"
}
```

Backend validate cặp `provider/model` bằng allowlist trước khi tạo Agent. Route
không hợp lệ trả lỗi validation an toàn và không gọi LLM.

Allowlist được cấu hình ở backend; UI không tự quyết định model nào hợp lệ hay
miễn phí. Gemini free-tier-compatible routes được đặt trước trong catalog theo
cấu hình dự án, nhưng UI không cam kết quota hoặc giá vì chúng có thể thay đổi.

## Giữ hội thoại khi đổi model

Đổi model áp dụng từ message kế tiếp và không tạo session chat mới.

```text
one browser session_id
        |
        +-- shared conversation session
        +-- shared PortfolioPolicy store
        +-- shared InvestorProfile store
        |
        +-- message A → Gemini Agent
        +-- message B → OpenAI Agent
```

Các Agent route dùng chung `ConversationSessionStore`. Policy và profile tiếp
tục được quản lý bởi deterministic application state, không phụ thuộc model.
Model mới nhận recent filtered conversation cùng current validated policy và
profile như bình thường.

## Backend boundaries

Một model routing component sẽ:

- trả safe catalog cho API;
- validate route;
- tạo/cache Agent loop theo route;
- inject cùng conversation session store vào mọi route.

`SentinelApplication` vẫn chịu trách nhiệm commit policy/profile và render
structured response. Binance gateway, domain models, PortfolioPolicy logic và
RiskEngine không thay đổi theo model.

Final `completed` event bổ sung route thực tế đã dùng để UI và audit biết response
đến từ model nào.

## Streaming flow

```text
UI submits message + selected route
  → backend validates allowlist and configured key
  → Agent starts
  → semantic tool events update this turn's Agent Pulse
  → Python validates tool data and Risk Engine result
  → model prose passes output safety validation
  → text_delta renders assistant response
  → completed maps structured evidence and final route
```

Model text vẫn được buffer đến khi safety validation thành công. Activity có thể
stream ngay; điều này tránh phát một financial claim chưa được kiểm tra.

## Error handling

- Market/portfolio error: Pulse đánh dấu đúng step `FAILED`; answer hiển thị lý
  do đã sanitize, không tạo recommendation.
- Invalid model route: hiển thị lỗi ngay dưới model pill/composer; không bắt đầu
  Agent run.
- Provider failure: giữ message người dùng, tạo assistant error row có nút retry.
- Stream interruption: Pulse chuyển `Interrupted`; retry tạo một lượt mới.
- Unexpected backend error: UI nhận generic message; secret và raw provider body
  không đi qua SSE.

## Accessibility và responsive

- Model pill và Agent Pulse là button thật, hỗ trợ Enter/Space.
- Popover và expanded process có `aria-expanded`, `aria-controls` và focus state.
- Activity status không chỉ dựa vào màu; luôn có text/icon trạng thái.
- `aria-live="polite"` dùng cho process, không đọc lại toàn bộ timeline mỗi event.
- `prefers-reduced-motion` tắt pulse animation và transition không cần thiết.
- Mobile dùng full-width chat shell, process detail không vượt viewport.

## Testing

- Unit test model catalog và route validation.
- Test provider thiếu key không xuất hiện trong catalog.
- Test đổi model vẫn dùng cùng conversation/policy/profile session.
- API test `/api/models` và chat request có route.
- UI test model popover, normalized request và invalid-route state.
- UI test activity của từng turn không bị trộn.
- UI test Pulse expand/collapse và safe structured evidence mapping.
- Regression test không render raw tool payload, secrets hoặc hidden reasoning.
- Responsive/manual visual check cho desktop và mobile.

## Acceptance criteria

1. Màn hình chính nhìn như một chat product, không như dashboard.
2. Model control không chiếm một hàng form riêng.
3. User có thể đổi giữa route được backend cho phép.
4. Đổi model không làm mất recent conversation, policy hoặc profile.
5. Agent Pulse mặc định là một dòng nhỏ và mở đúng activity của từng response.
6. UI chỉ render activity/evidence an toàn, không render chain-of-thought.
7. Portfolio analysis vẫn fail-closed và không có execution capability.
