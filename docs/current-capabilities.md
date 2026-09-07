# Tổng hợp chức năng hiện có của Sentinel

> Cập nhật theo source code ngày 08/09/2026. Tài liệu này mô tả những gì dự án
> đang làm được, không mô tả các ý tưởng tương lai như thể chúng đã hoàn thành.

## 1. Sentinel hiện tại là gì?

Sentinel là một AI Agent quản lý quy trình phân tích rủi ro portfolio crypto.
Người dùng có thể nói bằng ngôn ngữ tự nhiên, ví dụ:

```text
Mục tiêu của tôi là tăng trưởng trong 12 tháng, chấp nhận giảm 20%.
Hãy kiểm tra portfolio và đưa ra vài phương án phù hợp.
```

Sentinel có thể hiểu yêu cầu, tự chọn tool cần dùng, đọc dữ liệu Binance Demo,
gọi các phép tính Python, xem kết quả rồi quyết định bước tiếp theo.

Điểm quan trọng nhất của kiến trúc:

```text
LLM hiểu ý định và đưa ra nhận định.
Python tính toán và kiểm tra business rule.
Risk Engine bảo vệ giới hạn tài chính.
Người dùng phê duyệt rõ ràng.
Binance Demo thực thi và xác nhận.
```

Sentinel không phải chatbot chỉ nhận một câu rồi trả một đoạn văn. Nó có vòng lặp
Agent nhiều bước và quan sát được kết quả tool giữa các bước.

## 2. Bảng chức năng hiện có

| Nhóm | Trạng thái | Sentinel đang làm được |
|---|---|---|
| Chat AI | Hoạt động | Hiểu tiếng Việt/Anh, nhớ hội thoại ngắn, trả lời tự nhiên |
| Portfolio | Hoạt động | Đọc balance Binance Demo, định giá theo USDT, tính tổng và tỷ trọng |
| Market data | Hoạt động | Đọc ticker, biến động 24h, order book và ước tính slippage |
| Policy chat | Hoạt động | Tạo, xem và cập nhật policy bằng ngôn ngữ tự nhiên |
| Investor profile | Hoạt động | Lưu mục tiêu, thời hạn, mức chịu lỗ/rủi ro và preference |
| Policy analysis | Hoạt động | Phát hiện concentration và thiếu stablecoin reserve |
| Rebalance | Hoạt động | Tạo phương án điều chỉnh bằng Python, chưa tự động thực thi |
| Risk Engine | Hoạt động | BLOCKED, REQUIRES_APPROVAL hoặc SAFE_TO_PROPOSE |
| Market research | Hoạt động | Quét top Spot USDT volume và phân tích kline nhiều timeframe |
| Model switching | Hoạt động | Chọn OpenAI/Gemini từ allowlist backend qua LiteLLM |
| Web UI | Hoạt động | Giao diện chat, streaming activity, verified facts, plan approval |
| Demo proposal | Hoạt động | Tạo immutable BUY/SELL plan với hạn mức cứng |
| Demo execution | Có kiểm soát | Chỉ chạy khi bật config và người dùng bấm approve |
| Production trading | Không hỗ trợ | Runtime chỉ chấp nhận Binance Demo |
| Binance MCP | Không hoạt động | Dự án hiện dùng official `binance-cli` |
| Database bền vững | Chưa có | State mất khi process dừng |

## 3. LLM và Python chia trách nhiệm như thế nào?

### LLM là phần AI brain

LLM hiện làm các việc sau:

- hiểu câu nói tiếng Việt hoặc tiếng Anh;
- nhận ra người dùng muốn chat, xem policy, sửa policy, phân tích portfolio,
  nghiên cứu thị trường hay đề xuất giao dịch;
- tự quyết định tool an toàn nào cần gọi tiếp theo;
- đọc kết quả tool vừa trả về và tiếp tục vòng lặp;
- chọn research recipe dựa trên mục tiêu và thời hạn của người dùng;
- chọn candidate nào trong market scan cần phân tích sâu;
- so sánh dữ kiện, hình thành nhận định riêng và có thể không đồng ý với người dùng;
- giải thích kết quả bằng ngôn ngữ tự nhiên.

LLM không chỉ chuyển JSON thành câu chữ. Nó tham gia vào quá trình chọn hướng
phân tích và đưa ra đánh giá định tính. Tuy nhiên, đánh giá đó chỉ hợp lệ khi dựa
trên dữ kiện đã được tool và Python xác minh.

### Python là phần quyết định có tính thẩm quyền

Python chịu trách nhiệm:

- parse và validate dữ liệu bằng Pydantic;
- tính tổng portfolio và allocation;
- phát hiện policy violation;
- tính lượng rebalance;
- tính return, trend, volatility, drawdown và volume change;
- kiểm tra threshold, slippage, balance và symbol eligibility;
- tạo formal Risk Engine status;
- quản lý plan, approval, expiry và execution state;
- từ chối request nếu dữ liệu bắt buộc không xác minh được.

LLM không được tự tuyên bố `BLOCKED`, `REQUIRES_APPROVAL`, `SAFE_TO_PROPOSE`,
`EXECUTED` hay tự tạo số liệu portfolio/market.

## 4. Vòng lặp AI Agent hoạt động thế nào?

```text
1. Người dùng gửi message
2. Backend đưa message, policy và investor profile hiện tại cho Agent
3. LLM nhìn thấy schema của 12 controlled tools
4. LLM chọn một tool và điền tham số
5. OpenAI Agents SDK gọi Python function tương ứng
6. Python validate, gọi Binance nếu cần và trả structured result
7. SDK đưa tool result trở lại conversation của LLM
8. LLM đọc result và chọn tool kế tiếp
9. Khi đủ dữ kiện, LLM tạo phần nhận định
10. Application ghép verified facts của Python với AI interpretation
```

`parallel_tool_calls=False` ngăn các tool thay đổi state chạy đồng thời. Thứ tự
nghiệp vụ vẫn do LLM lựa chọn theo instruction; runtime ghi nhận thứ tự tool thực
tế để application xử lý và hiển thị tuần tự.

## 5. Mười hai controlled tools

Agent hiện chỉ nhìn thấy đúng 12 tool sau:

| Tool | Công dụng | Có thực thi giao dịch không? |
|---|---|---|
| `get_portfolio()` | Đọc holdings Binance Demo | Không |
| `get_market_data(symbol)` | Đọc price, 24h change, volatility, slippage | Không |
| `update_policy(changes)` | Stage thay đổi policy đã nói rõ | Không |
| `view_policy()` | Xem policy hiện tại | Không |
| `update_investor_profile(changes)` | Stage preference nhà đầu tư | Không |
| `view_investor_profile()` | Xem investor profile | Không |
| `evaluate_portfolio_risk(focus_symbols)` | Chạy tính toán, planner và Risk Engine | Không |
| `propose_trade(...)` | Tạo Binance Demo plan chờ approve | Không |
| `set_market_research_plan(...)` | Tạo research recipe có giới hạn | Không |
| `scan_top_markets()` | Quét Spot USDT theo quote volume | Không |
| `analyze_market_history(symbol)` | Tính indicator từ kline candidate | Không |
| `finalize_market_research()` | Khóa evidence để LLM so sánh | Không |

Không có `place_order()`, `execute()`, `transfer()`, `withdraw()`, generic CLI,
generic URL hay arbitrary Python tool cho LLM.

## 6. Phân tích portfolio

Với yêu cầu:

```text
Analyze my BTC exposure and tell me whether it looks risky.
```

Luồng thường là:

```text
get_portfolio
    ↓
LLM thấy BTC trong holdings
    ↓
get_market_data("BTCUSDT")
    ↓
evaluate_portfolio_risk(["BTC"])
    ↓
Python trả PortfolioAnalysis
    ↓
LLM giải thích ý nghĩa và đưa ra nhận định
```

Python tính:

```text
asset_weight = asset_usd_value / total_portfolio_usd_value
```

Portfolio analysis có thể chứa portfolio, market observations, policy
violations, rebalance plan, formal Risk Engine decision và các lý do đi kèm.

Nếu Agent đọc dữ liệu tài chính nhưng dừng trước deterministic evaluation,
runtime từ chối final answer. Nếu dữ liệu bắt buộc lỗi, Sentinel fail-closed và
không giữ lại một khuyến nghị dựa trên dữ liệu chưa đầy đủ.

## 7. Portfolio policy qua chat

Người dùng có thể nói:

```text
Giữ ít nhất 30% stablecoin.
Không asset nào vượt 40%.
Không rebalance khi volatility HIGH.
Mỗi trade tối đa 80 USDT và slippage không quá 0.1%.
```

Policy hiện có các field:

| Field | Ý nghĩa |
|---|---|
| `min_stablecoin_weight` | Tỷ trọng stablecoin tối thiểu |
| `max_asset_weight` | Tỷ trọng tối đa cho một crypto asset |
| `block_high_volatility` | Chặn rebalance khi volatility HIGH |
| `max_trade_usd_without_approval` | Ngưỡng formal approval trong Risk Engine |
| `max_trade_usd` | Hạn mức trade do người dùng đặt, chỉ được chặt hơn hard limit |
| `max_slippage_percent` | Slippage tối đa cho proposal/execution |
| `allowed_trade_symbols` | Allowlist symbol do người dùng giới hạn |

LLM chỉ lấy giá trị người dùng nói rõ. Python parse chuỗi thành kiểu dữ liệu thật
và Pydantic kiểm tra range. Giá trị mơ hồ không được tự đoán.

Policy patch được stage trong `SentinelRunContext`. Store chỉ commit patch sau
khi toàn bộ Agent run thành công, nhờ đó lỗi model giữa chừng không làm policy
bị cập nhật một nửa.

## 8. Investor profile qua chat

Investor profile giúp Sentinel nhớ mục tiêu giữa các message:

| Field | Ví dụ |
|---|---|
| `objective` | CAPITAL_PRESERVATION, BALANCED, GROWTH |
| `time_horizon_months` | 1, 12, 36 |
| `risk_tolerance` | LOW, MEDIUM, HIGH |
| `acceptable_loss_percent` | 10%, 20% |
| `liquidity_need` | LOW, MEDIUM, HIGH |
| `excluded_assets` | Không muốn BTC, SOL... |

Đây chỉ là preference, không phải balance, market fact, policy hay quyền giao
dịch. Khi profile đủ mục tiêu, thời hạn và mức chịu lỗ/rủi ro, Agent có thể đưa
ra 2–4 phương án khác nhau thay vì hỏi lại quá nhiều câu.

## 9. Adaptive Binance market research

Với yêu cầu tìm cơ hội hoặc so sánh token, LLM không bị ép vào một thuật toán
cố định duy nhất. Nó được chọn một recipe có kiểm soát:

```text
set_market_research_plan
    ↓
scan_top_markets
    ↓
analyze_market_history(candidate A)
    ↓
analyze_market_history(candidate B, C... nếu cần)
    ↓
finalize_market_research
    ↓
LLM so sánh và đưa ra lựa chọn ưu tiên
```

Giới hạn bắt buộc:

- scan 3–10 Spot USDT candidates;
- chọn 1–2 timeframe trong `15m`, `1h`, `4h`, `1d`;
- lookback 1–90 ngày;
- mỗi timeframe phải tạo 20–1.000 candles;
- tối đa 5 candidate được thử deep analysis, kể cả attempt thất bại;
- ít nhất 2 candidate thành công trước khi finalize;
- chỉ một research plan trong mỗi Agent run;
- sau finalize không được thêm hoặc thay đổi candidate.

Python loại stablecoin pair và leveraged token suffix khỏi candidate ranking,
sau đó xếp hạng theo Binance quote volume. High volume chỉ là dấu hiệu thanh
khoản, không phải bằng chứng token chắc chắn tốt.

Từ klines, Python tính return, trend, realized volatility, maximum drawdown và
thay đổi average volume giữa nửa sau và nửa đầu mẫu.

Gateway từ chối ticker cũ hơn 15 phút, candle thiếu, trùng, sai interval, không
liên tục hoặc quá cũ. Raw candles ở backend; UI chỉ nhận summary đã tính.

LLM dùng các summary này để so sánh, nêu quan điểm và nói dữ kiện nào có thể làm
nó thay đổi quan điểm. Đây là phần AI judgment thật sự của Sentinel.

## 10. Risk Engine hiện kiểm tra gì?

Trong portfolio/rebalance flow, thứ tự ưu tiên là:

1. Nếu policy chặn HIGH volatility và action liên quan đang HIGH → `BLOCKED`.
2. Nếu action vượt approval threshold → `REQUIRES_APPROVAL`.
3. Nếu không có rule nào kích hoạt → `SAFE_TO_PROPOSE`.

Blocking condition luôn thắng approval condition.

Ngoài formal Risk Engine, trade proposal/execution còn có deterministic guard:

- environment phải là Binance Demo;
- symbol phải là active Spot USDT market;
- hỗ trợ MARKET và quote-value market order;
- amount phải nằm trong hard limit 10–100 USDT;
- không vượt `max_trade_usd` hoặc `max_slippage_percent`;
- symbol phải nằm trong policy allowlist nếu policy có cấu hình;
- BUY phải đủ USDT, SELL phải đủ base asset;
- proposal không được tạo hoặc làm nặng hơn portfolio-policy violation;
- HIGH volatility có thể bị policy block;
- plan chưa hết hạn và đúng session;
- mọi order đều cần explicit approval.

## 11. Trade proposal, approval và Binance Demo execution

`propose_trade` tạo một `ExecutionPlan` immutable có PLAN-ID, session, symbol,
BUY/SELL, USDT value, estimated quantity/price, reason, expiry và trạng thái.
Tool này không gọi Binance order API.

Approval không được suy ra từ chat. Nó phải đi qua approval endpoint/action riêng;
UI hiện gọi endpoint này bằng nút xác nhận.
Các symbol phổ biến sau dùng normal order approval:

```text
BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT
```

Token khác chỉ được đề xuất nếu Binance xác nhận nó là active Spot USDT market.
Plan đó cần hai bước:

```text
Approve token exception
    ↓
Approve Demo order
```

Token exception chỉ áp dụng cho đúng plan và không tự gửi order.

Khi người dùng approve, Python đọc lại portfolio, market data, symbol info và
policy hiện tại. Nếu mọi check vẫn hợp lệ và config execution đang bật, gateway
mới gửi một MARKET order lên Binance Demo.

Sau đó Sentinel gọi `get-order`. Chỉ khi Binance xác nhận `FILLED`, plan mới có
trạng thái `EXECUTED`. Retry plan đã hoàn tất trả kết quả lưu sẵn thay vì gửi một
order mới.

Execution bị tắt mặc định:

```dotenv
SENTINEL_DEMO_EXECUTION_ENABLED=false
```

## 12. Conversation memory và state

Mỗi `session_id` có conversation history bằng SQLite in-memory của Agents SDK,
policy store, investor-profile store và execution-plan store trong RAM.

Sentinel giữ tối đa 16 user/assistant messages gần nhất khi gửi history cho
model. Tool calls và tool results cũ bị loại khỏi history để tránh dùng giá cũ
như dữ liệu hiện tại. Mỗi financial request vẫn phải đọc Binance data mới.

Toàn bộ state trên mất khi process dừng; hiện chưa có database bền vững.

## 13. Model switching qua LiteLLM

Sentinel hỗ trợ OpenAI và Gemini. Backend dùng `LLM_ALLOWED_MODELS` làm allowlist;
chỉ model có provider key tương ứng mới được trả về `GET /api/models`.

Route tương ứng:

```text
litellm/gemini/<model-id>
litellm/openai/<model-id>
```

LiteLLM đọc `GEMINI_API_KEY` cho Gemini và `OPENAI_API_KEY` cho OpenAI. Browser
chỉ gửi provider/model; API key không được gửi lên UI. Model switch giữ nguyên
`session_id`, nên conversation, policy và profile tiếp tục trong cùng process.

## 14. FastAPI, streaming và giao diện

Endpoint chính:

| Endpoint | Công dụng |
|---|---|
| `GET /api/models` | Trả model routes được backend cho phép |
| `POST /api/chat/stream` | Gửi chat và nhận SSE stream |
| `POST /api/plans/{id}/approve-symbol` | Approve token exception cho đúng plan |
| `POST /api/plans/{id}/approve` | Approve và revalidate Demo order |
| `POST /api/plans/{id}/reject` | Reject plan |

SSE gồm `activity`, `text_delta`, `completed` và `error`. Typed response có
policy, investor profile, portfolio analysis, market research, activity, AI
interpretation, execution status và execution plan.

UI hiện có giao diện chat, model picker gọn, Agent Pulse có thể thu/phóng,
streaming activity, Markdown an toàn, Verified tool facts, Demo plan card và các
nút approve/reject.

Agent Pulse không phải hidden chain-of-thought. Raw args, raw result, prompt,
secret và raw candles không đi vào timeline.

## 15. Xử lý lỗi và bảo mật

- `.env` nằm trong `.gitignore` và key không được commit.
- Binance CLI được gọi bằng argument array, không ghép shell command từ LLM.
- Credentials chỉ inject cho command cần authentication.
- Runner không đưa stdout/stderr nhạy cảm vào public error.
- Market symbol, timeframe, limits và Binance payload đều được validate.
- `ticker24hr`, depth, market-universe và kline reads retry một lần.
- Required-data failure loại bỏ AI financial claim và trả safe message.
- Model route ngoài allowlist bị API từ chối.
- LLM không có execution tool và không thể tự approve.
- Raw chain-of-thought không được hiển thị.

Chỉ bật `LITELLM_DEBUG=true` khi debug cục bộ. Log debug có thể chứa prompt và
request body, vì vậy không chia sẻ công khai.

## 16. Các file liên kết với nhau như thế nào?

```text
main.py / app/api.py
        ↓
app/bootstrap.py
        ↓
app/application.py
        ↓
app/agent/tool_loop.py
        ├── app/agent/prompts.py
        ├── app/agent/controlled_tools.py
        ├── app/agent/run_context.py
        ├── app/agent/conversation_memory.py
        └── app/agent/streaming.py
                 ↓
        app/services/*.py
                 ↓
        app/gateways.py (Protocol)
                 ↓
        app/binance/gateway.py
                 ↓
        app/binance/runner.py
                 ↓
             binance-cli
```

| File | Trách nhiệm chính |
|---|---|
| `app/agent/tool_loop.py` | Tạo Agent, chạy loop, validate điều kiện hoàn tất |
| `app/agent/controlled_tools.py` | 12 tool mà LLM được phép gọi |
| `app/agent/run_context.py` | State tin cậy trong đúng một Agent run |
| `app/application.py` | Commit state, ghép facts với AI text, tạo response |
| `app/models/` | Pydantic domain/API models |
| `app/services/` | Logic deterministic, độc lập LLM |
| `app/gateways.py` | Interface giữa application và external data |
| `app/binance/gateway.py` | Map fixed Binance CLI command sang domain model |
| `app/binance/runner.py` | Chạy CLI an toàn và parse JSON |
| `app/execution/store.py` | Quản lý immutable plan lifecycle |
| `app/api.py` | FastAPI, SSE, model và approval endpoints |
| `web/app.js` | Chat UI, stream parser, activity/evidence rendering |
| `app/config.py` | Đọc và validate `.env` |

Các file `app/agent/request_interpreter.py`, `analysis_reporter.py`,
`sentinel.py` và `app/tools/` là code legacy/educational vẫn có test. Runtime
chính hiện dùng `tool_loop.py` và `controlled_tools.py`.

## 17. Giới hạn hiện tại

Sentinel hiện chưa hỗ trợ:

- production Binance trading;
- withdraw, transfer, derivatives, futures hoặc margin;
- database bền vững;
- background monitoring hay scheduler chạy liên tục;
- Binance MCP;
- news, sentiment, on-chain hoặc social data;
- dự đoán giá bằng custom ML model;
- arbitrary algorithm, Python hoặc CLI do LLM tạo;
- approval từ câu chat;
- unrestricted autonomous trading.

## 18. Chạy dự án và prompt mẫu

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python main.py
```

Chạy UI:

```bash
uvicorn app.api:create_app --factory --reload
```

Chạy test:

```bash
python -m pytest -q
node --test tests/test_ui.js
python -m compileall -q app main.py tests
```

Prompt mẫu:

```text
Kiểm tra portfolio hiện tại và giải thích rủi ro BTC.

Giữ ít nhất 30% stablecoin, không asset nào trên 40%, sau đó phân tích lại.

Mục tiêu của tôi là tăng trưởng trong 12 tháng, chấp nhận giảm 20%.
Kiểm tra tài khoản và đưa ra 3 phương án, sau đó nói phương án bạn ưu tiên.

Quét các Spot USDT market có volume cao trên Binance và so sánh những lựa chọn
phù hợp mục tiêu tăng trưởng một tháng của tôi.

Đọc lại dữ liệu và đề xuất mua 50 USDT BTC trên Binance Demo.
```

Sau khi plan xuất hiện, approval phải đi qua endpoint/action riêng; UI cung cấp nút
để gọi endpoint đó.

## 19. Kết luận

Sentinel hiện đã chứng minh một Agent workflow hoàn chỉnh trong môi trường Demo:

```text
Hiểu ý định
→ tự chọn tool
→ quan sát dữ liệu Binance
→ tính toán bằng Python
→ đưa ra nhận định AI
→ tạo plan có kiểm soát
→ Risk Engine và user approval bảo vệ execution
→ Binance Demo xác nhận kết quả
```

Giá trị chính của dự án không nằm ở việc dùng LLM để viết lại JSON. LLM là lớp
hiểu ý định, điều phối nghiên cứu và đưa ra phán đoán; Python và Risk Engine là
lớp bảo đảm phán đoán đó không biến thành hành động tài chính thiếu kiểm soát.
