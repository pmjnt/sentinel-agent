# Thiết kế chuyển đổi LLM provider bằng LiteLLM

## Mục tiêu

Cho phép Sentinel chọn OpenAI hoặc Gemini và tự cấu hình model cụ thể qua `.env`, trong khi vẫn dùng OpenAI Agents SDK để quản lý Agent và tool-calling loop. Thay đổi này chỉ tác động đến cấu hình LLM; portfolio/market tools vẫn dùng dữ liệu mock và Binance vẫn ngoài phạm vi.

## Cấu hình

Ứng dụng đọc bốn biến môi trường:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=
```

`LLM_PROVIDER` chỉ nhận `openai` hoặc `gemini`. `LLM_MODEL` bắt buộc và chứa model ID của provider, không bao gồm prefix LiteLLM. Chỉ API key của provider đang hoạt động là bắt buộc.

Ví dụ Gemini:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.8-flash
OPENAI_API_KEY=
GEMINI_API_KEY=your_gemini_key_here
```

## Model routing

`Settings` tạo model ID mà OpenAI Agents SDK 0.22.0 hiểu:

```text
openai + gpt-5.6-luna
    -> litellm/openai/gpt-5.6-luna

gemini + gemini-3.8-flash
    -> litellm/gemini/gemini-3.8-flash
```

Agents SDK nhận chuỗi bắt đầu bằng `litellm/`, chuyển phần còn lại cho `LitellmProvider`, và LiteLLM đọc API key tương ứng từ environment. Không có logic tự động đoán provider từ API key.

## Thành phần thay đổi

### `requirements.txt`

Thay dependency `openai-agents` bằng optional dependency `openai-agents[litellm]` để cài đúng integration được SDK hỗ trợ.

### `app/config.py`

- Thêm enum `LLMProvider` gồm `OPENAI` và `GEMINI`.
- `Settings` chứa provider, model và các key tùy chọn.
- Thuộc tính `agents_model` tạo model ID có prefix `litellm/`.
- `load_settings()` chuẩn hóa provider về chữ thường, trim model/key, và báo lỗi rõ khi provider, model hoặc active key không hợp lệ.

### `app/agent.py`

`create_sentinel_agent(settings)` truyền `settings.agents_model` vào thuộc tính `model` của Agent. Sentinel instructions và hai tool giữ nguyên. OpenAI tracing được tắt cho MVP để chạy Gemini không cần một OpenAI key thứ hai chỉ dành cho tracing.

### `main.py`

Load settings một lần và truyền cùng object vào Agent factory.

### `.env.example` và `README.md`

Hiển thị cấu hình mặc định OpenAI, ví dụ chuyển sang Gemini, cách đổi model, quy tắc chỉ khai báo model ID không có provider prefix, và lỗi thường gặp.

## Luồng hoạt động

```text
.env
  |
  v
Settings: provider + model + active key
  |
  v
OpenAI Agents SDK
  |
  v
LiteLLM
  +----> OpenAI API
  |
  +----> Gemini API
  |
  v
Sentinel uses portfolio/market tools
```

LiteLLM chỉ định tuyến request tới LLM provider. OpenAI Agents SDK vẫn quản lý Agent, instructions, tool selection và agent loop.

## Xử lý lỗi

- `LLM_PROVIDER` không phải `openai`/`gemini`: dừng khi khởi động với danh sách giá trị hợp lệ.
- `LLM_MODEL` trống: dừng với hướng dẫn khai báo model.
- Thiếu key của provider đang chọn: dừng với tên chính xác của biến cần cấu hình.
- Model không tồn tại hoặc key không có quyền: provider trả lỗi ở request đầu tiên; console giữ thông báo an toàn hiện tại và không in secret.

## Kiểm thử

Unit tests không gọi mạng hoặc API thật. Chúng kiểm tra:

- Cấu hình OpenAI tạo đúng model ID LiteLLM.
- Cấu hình Gemini tạo đúng model ID LiteLLM.
- Provider không hợp lệ bị từ chối.
- Model trống bị từ chối.
- Thiếu active API key bị từ chối nhưng key của provider không hoạt động không bắt buộc.
- Agent nhận đúng model ID và giữ hai tools.

Xác thực cuối gồm `pytest`, `compileall`, `pip check` và chạy console với input kết thúc mà không gửi LLM request.

## Ngoài phạm vi

- Không thêm provider ngoài OpenAI và Gemini.
- Không thêm fallback hoặc load balancing giữa providers.
- Không chạy LiteLLM Proxy Server.
- Không thêm tracking chi phí, retry routing hoặc database.
- Không thay portfolio/market mock tools.
- Không kết nối Binance hoặc thực hiện trading.

