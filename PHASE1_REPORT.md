# Phase 1 Completion Report — Jarvis Persona Agent

> **Ngày:** 21/02/2026  
> **Trạng thái:** Phase 1 Agent Core ✅ HOÀN THÀNH  
> **Model:** Gemini 3 Flash Preview + Nano Banana Pro (Image)

---

## 1. Tổng quan kiến trúc

```
User message
  → build_system_prompt() inject datetime + persona
    → Gemini 3 Flash (LLM, temp 1.0)
      → LangGraph ReAct agent chọn tool(s)
        → Academic tools (School API thật)
        → Web search (DuckDuckGo via ddgs)
        → Image gen (Nano Banana Pro)
      → Vietnamese response
```

---

## 2. Config hiện tại

### `.env` (backend/)

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-flash-preview          # Gemini 3 — Pro-level, Flash speed
LLM_API_KEY=AIzaSyDUnhLfuNQJ3W18Iim-CKYaXs1TKWy199U
LLM_TEMPERATURE=1.0                       # Gemini 3 docs: keep 1.0, lower causes looping

IMAGE_MODEL=gemini-3-pro-image-preview    # Nano Banana Pro (4K, text rendering)
IMAGE_MODEL_ENABLED=true

AGENT_RECURSION_LIMIT=10                  # Bumped from 5: multi-tool chains
```

### `app/config.py` — Pydantic Settings

Tất cả config load từ `.env`. Key settings:

- `LLM_MODEL`: default `gemini-3-flash-preview`
- `LLM_TEMPERATURE`: default `1.0` (per Gemini 3 recommendation)
- `IMAGE_MODEL`: default `gemini-3-pro-image-preview`
- `AGENT_RECURSION_LIMIT`: `10`

### Models có sẵn trên API key

| Model                        | Loại       | Trạng thái             |
| ---------------------------- | ---------- | ---------------------- |
| `gemini-3-flash-preview`     | Agent LLM  | ✅ Đang dùng           |
| `gemini-3-pro-image-preview` | Image gen  | ✅ Đang dùng           |
| `gemini-2.5-pro`             | Text/Agent | ✅ Available, dự phòng |
| `gemini-2.5-flash`           | Text       | ✅ Available, nhẹ hơn  |
| `gemini-2.5-flash-image`     | Image gen  | ✅ Available           |
| `gemini-2.0-flash`           | Text       | ✅ Available, cũ       |

> **Lưu ý:** `gemini-3.1-pro-preview` có trong docs nhưng CHƯA available trên API key này.

---

## 3. Cấu trúc thư mục đã triển khai

```
backend/
├── app/
│   ├── config.py                          # Pydantic Settings, load .env
│   ├── main.py                            # FastAPI app (scaffold)
│   ├── core/
│   │   ├── database.py                    # Supabase client (placeholder)
│   │   ├── security.py                    # Fernet encrypt/decrypt + JWT
│   │   ├── llm_provider.py               # LLM factory (Gemini/OpenAI/Groq)
│   │   └── dependencies.py               # FastAPI DI
│   └── features/
│       ├── academic/
│       │   ├── school_client.py           # ⭐ SchoolAPIClient — REAL auth + data
│       │   ├── tools.py                   # ⭐ 3 tools: get_semesters, get_timetable, get_grades
│       │   ├── service.py                 # Data sync service (needs DB)
│       │   └── schemas.py                 # Pydantic models
│       ├── agent/
│       │   ├── graph.py                   # LangGraph ReAct state machine
│       │   ├── prompts.py                 # ⭐ System prompt + build_system_prompt()
│       │   ├── memory.py                  # 3-tier memory (needs DB)
│       │   ├── router.py                  # POST /agent/chat (scaffold)
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── web_search.py          # ⭐ search_web + scrape_website (DuckDuckGo)
│       │       └── image_gen.py           # ⭐ generate_image (Nano Banana Pro)
│       ├── auth/                          # Auth feature (scaffold, needs DB)
│       ├── tasks/                         # Task tools (scaffold, needs DB)
│       └── knowledge/                     # Knowledge feature (scaffold)
├── test_verify.py                         # ⭐ E2E test script (5 scenarios)
├── test_school_api.py                     # School API unit test
├── .env                                   # Environment config
└── requirements.txt                       # Python deps
```

---

## 4. Chi tiết từng component đã hoàn thành

### 4.1 School API Client (`academic/school_client.py`)

Authentication flow (đã verified bằng live testing):

```
1. Build JSON: {"username": MSSV, "password": pass, "uri": "https://ttsv.tvu.edu.vn/#/"}
2. Base64-encode → code param
3. GET /api/pn-signin?code=[base64] — KHÔNG follow redirects
4. Server trả 302, Location header chứa CurrUser=[base64_json]
5. Decode CurrUser → extract access_token (JWE, ~1359 chars)
6. Mọi data API: POST với Authorization: Bearer <access_token>
```

Data endpoints (tất cả POST, không phải GET):

- `POST /public/api/sch/w-locdshockytkbuser` → Danh sách học kỳ
- `POST /public/api/sch/w-locdstkbtuanusertheohocky` → TKB
- `POST /public/api/srm/w-locdsdiemsinhvien` → Bảng điểm

> **⚠️ Hardcoded credentials:** Tools hiện dùng MSSV/password hardcoded (`110122221`/`290406`) trong `tools.py` line 28. Production cần lấy từ Supabase DB (encrypted).

### 4.2 Academic Tools (`academic/tools.py`)

3 LangChain `@tool` functions, async, kết nối **real data**:

| Tool                          | API endpoint                  | Output format                               |
| ----------------------------- | ----------------------------- | ------------------------------------------- |
| `get_semesters()`             | `w-locdshockytkbuser`         | HK hiện tại + danh sách 6 HK gần nhất       |
| `get_timetable(semester_id?)` | `w-locdstkbtuanusertheohocky` | TKB 3 tuần: thứ, tiết, môn, phòng, GV       |
| `get_grades()`                | `w-locdsdiemsinhvien`         | 3 HK gần nhất: GPA, điểm từng môn, xếp loại |

### 4.3 Web Search Tools (`agent/tools/web_search.py`)

Package: `ddgs` (NOT `duckduckgo-search` — package cũ đã deprecated, trả empty results).

| Tool                  | Chức năng                                                |
| --------------------- | -------------------------------------------------------- |
| `search_web(query)`   | Tìm kiếm DuckDuckGo, trả 5 kết quả (title + body + link) |
| `scrape_website(url)` | Đọc nội dung từ URL (qua DuckDuckGo site: search)        |

### 4.4 Image Generation Tool (`agent/tools/image_gen.py`)

- Dùng `google-genai` SDK (native, KHÔNG qua LangChain)
- Model: `gemini-3-pro-image-preview` (Nano Banana Pro)
- Flow: prompt → Gemini API → save ảnh `.jpg`/`.png` → trả path
- Agent tự biết search thông tin trước khi tạo ảnh (VD: search màu TVU trước khi vẽ mascot)

### 4.5 System Prompt (`agent/prompts.py`)

```python
def build_system_prompt(user_name="bạn", user_preferences="") -> str:
    """Inject datetime.now() + persona vào system prompt."""
```

Key features:

- **Auto-inject datetime** với thứ tiếng Việt: `"16:49 ngày 21/02/2026 (Thứ Sáu)"`
- **7 quy tắc** bao gồm:
  - Bắt buộc dùng tool cho data học tập
  - Thời gian chính xác (dùng datetime inject, KHÔNG đoán)
  - **Trung thực về độ mới dữ liệu**: nếu search trả data ngày khác → phải nói rõ
- Persona: "Aic", trợ lý AI của sinh viên TVU
- Liệt kê 6 tools available

### 4.6 LangGraph Agent (`agent/graph.py`)

```python
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", execute_tools)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")
app = graph.compile(recursion_limit=10)
```

- ReAct pattern: Think → Act → Observe → Repeat
- `recursion_limit=10`: đủ cho multi-tool chains (đã test 3-tool chain)

---

## 5. E2E Test Results (5/5 pass)

Test script: `test_verify.py`  
Model: `gemini-3-flash-preview` | Temperature: `1.0`  
Tools: `get_semesters`, `get_timetable`, `get_grades`, `search_web`, `scrape_website`, `generate_image`

| #   | Query                      | Tools Called                           | Kết quả                                    |
| --- | -------------------------- | -------------------------------------- | ------------------------------------------ |
| 1   | "GPA tích lũy?"            | `get_grades`                           | ✅ 8.23/3.33 + nhận xét "xếp loại Giỏi"    |
| 2   | "Giá vàng SJC hôm nay?"    | `search_web`                           | ✅ Trả giá cụ thể + ngày đúng (21/02/2026) |
| 3   | "Bạn là ai?"               | Không dùng tool                        | ✅ Tự giới thiệu "Aic" + features          |
| 4   | "Vẽ mascot TVU"            | `search_web` → `generate_image`        | ✅ Search TVU colors → tạo ảnh 3D          |
| 5   | "Điểm HK + tin tuyển sinh" | `get_grades` + `search_web` (parallel) | ✅ 2 tools gọi song song                   |

### Capabilities đã verified:

- ✅ Tool selection chính xác (chọn đúng tool theo query)
- ✅ Multi-tool chaining (gọi tool liên tiếp)
- ✅ Parallel tool calling (gọi 2+ tools cùng lúc)
- ✅ No-tool response (trả lời trực tiếp khi không cần tool)
- ✅ Vietnamese response (emoji, ngữ cảm phù hợp)
- ✅ Datetime awareness (biết ngày hiện tại)
- ✅ Data freshness transparency (nói rõ khi data không phải hôm nay)
- ✅ Image generation (Nano Banana Pro, save to disk)

---

## 6. Dependencies đã cài

```
langchain-google-genai    # LangChain ↔ Gemini integration
langgraph                 # ReAct agent loop
langchain-core            # @tool decorator, messages
google-genai              # Native Gemini SDK (image gen)
ddgs                      # DuckDuckGo search (thay thế duckduckgo-search deprecated)
httpx                     # Async HTTP client (school API)
pydantic-settings         # Config from .env
python-dotenv             # Load .env file
fastapi                   # Web framework
uvicorn                   # ASGI server
```

---

## 7. Các vấn đề đã giải quyết

| Vấn đề                                           | Nguyên nhân                                       | Giải pháp                                                             |
| ------------------------------------------------ | ------------------------------------------------- | --------------------------------------------------------------------- |
| School API auth thất bại                         | API dùng GET + Base64 + redirect, không phải POST | Rewrite `SchoolAPIClient` theo đúng flow                              |
| Model `gemini-2.5-flash-preview-05-20` not found | Tên model sai, chưa available                     | Dùng `gemini-3-flash-preview` (stable, available)                     |
| `duckduckgo-search` trả empty `[]`               | Package deprecated, renamed to `ddgs`             | `pip install ddgs`, đổi import                                        |
| Agent nói sai ngày (23/5/2024)                   | LLM không biết current date                       | Inject `datetime.now()` vào system prompt                             |
| Agent nói "hôm nay" khi data là hôm qua          | Không so sánh date search results vs current      | Thêm rule "trung thực về độ mới dữ liệu" trong prompt                 |
| Output tiếng Việt bị lỗi encoding trên Windows   | PowerShell redirect `>` dùng cp1252               | UTF-8 wrapper + `chcp 65001`. Không ảnh hưởng production (JSON UTF-8) |

---

## 8. Những gì CHƯA làm (Phase 2+)

### Cần Supabase DB:

- [ ] Setup Supabase + migrations (tables: users, user_credentials, conversations, messages)
- [ ] Auth feature (register/login, JWT)
- [ ] Credential management (encrypt/decrypt MSSV/password từ DB thay vì hardcode)
- [ ] Memory persistence (conversation history → DB)
- [ ] Task tools (create_task, list_tasks → DB)

### Cần FastAPI endpoints:

- [ ] `POST /agent/chat` endpoint hoạt động thật (hiện scaffold)
- [ ] Test qua Swagger UI `/docs`
- [ ] WebSocket cho streaming responses

### Frontend:

- [ ] Chat UI
- [ ] Auth pages (login/register)

---

## 9. Hướng dẫn chạy test

```bash
cd backend
pip install -r requirements.txt
python test_verify.py
```

Output ghi vào console (có thể redirect: `python test_verify.py > output.txt 2>&1`).

> **Lưu ý Windows:** Cần `chcp 65001` trước khi chạy nếu muốn xem tiếng Việt đúng trong terminal.

---

## 10. Gemini 3 — Lưu ý quan trọng

Từ docs `SourceThamKhao/MD_Gemini/huongdan-gemini-3.md.txt`:

1. **Temperature = 1.0**: Giảm temperature gây looping/degraded performance
2. **Thought Signatures**: Gemini 3 trả `thoughtSignature` trong response. SDK LangChain tự handle — KHÔNG cần xử lý manual
3. **Thinking Level**: Default `high`. Có thể set `low` cho queries đơn giản (giảm latency)
4. **Nano Banana Pro** (`gemini-3-pro-image-preview`): Hỗ trợ 4K, text rendering, conversational editing qua thought signatures
5. **Parallel function calling**: Gemini 3 tự gọi nhiều tools cùng lúc nếu query yêu cầu (đã verified ở test 5)
