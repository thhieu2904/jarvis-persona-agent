# JARVIS Persona Agent 🤖

<p align="center">
  <b>Trợ lý AI cá nhân mang phong cách J.A.R.V.I.S — Bộ não thứ hai của sinh viên</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React" />
  <img src="https://img.shields.io/badge/LangGraph-0.3-orange" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase" alt="Supabase" />
</p>

---

## 📖 Giới thiệu

**JARVIS Persona Agent** là một trợ lý AI cá nhân được xây dựng cho sinh viên — đặc biệt là sinh viên Đại học Trà Vinh (TVU). Dự án lấy cảm hứng từ J.A.R.V.I.S (Iron Man), nơi AI không chỉ trả lời câu hỏi mà còn **chủ động hiểu và hỗ trợ cuộc sống học tập hàng ngày** của bạn.

### ✨ JARVIS có thể làm gì?

- 📅 **Tra cứu thời khóa biểu, điểm số** trực tiếp từ portal nhà trường (TVU), tự động cache và luôn mới nhất
- ✅ **Quản lý task, nhắc việc** — tạo, sửa, hoàn thành, xóa task qua hội thoại tự nhiên
- 📝 **Ghi chú nhanh** — lưu, tìm kiếm, ghim ghi chú bằng giọng nói hoặc text
- 📆 **Quản lý lịch hẹn** — tạo sự kiện, xem lịch sắp tới
- 🌤️ **Thời tiết real-time** — tra cứu thời tiết bằng địa điểm hoặc tọa độ GPS
- 🌐 **Tìm kiếm Internet** — sử dụng Tavily AI Search Engine, đọc nội dung trang web
- 🎨 **Tạo hình ảnh AI** — sinh ảnh từ mô tả văn bản bằng Gemini Image
- 🏠 **Điều khiển nhà thông minh** — bật/tắt ổ cắm Tuya/SmartLife qua mạng LAN cục bộ
- ⏰ **Báo cáo sáng/tối tự động** — gửi tóm tắt lịch học, task, thời tiết về Zalo
- 🤖 **Lên lịch AI tự động** — đặt lịch để JARVIS tự thực hiện bất kỳ hành động nào theo chu kỳ Cron
- 📱 **Thông báo Zalo** — nhận báo cáo kèm sticker cảm xúc thông minh

---

## 🗂️ Mục lục

- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Tech Stack](#-tech-stack)
- [Tính năng chi tiết](#-tính-năng-chi-tiết)
- [Cơ sở dữ liệu](#-cơ-sở-dữ-liệu)
- [Cài đặt & Chạy](#-cài-đặt--chạy)
- [Biến môi trường](#-biến-môi-trường)
- [API Endpoints](#-api-endpoints)
- [Agent Tools](#-agent-tools)
- [Frontend](#-frontend)
- [IoT & Nhà thông minh](#-iot--nhà-thông-minh)
- [Thông báo Zalo](#-thông-báo-zalo)
- [Background Scheduler](#-background-scheduler)
- [Lộ trình phát triển](#-lộ-trình-phát-triển)

---

## 🏛️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JARVIS PERSONA AGENT                         │
│                                                                     │
│  ┌──────────────┐      ┌──────────────────────────────────────┐    │
│  │   Frontend   │ SSE  │              Backend (FastAPI)        │    │
│  │  React + TS  │◄────►│                                      │    │
│  │  Vite + Zustand    │      ┌─────────────────────────┐      │    │
│  └──────────────┘      │      │     LangGraph Agent     │      │    │
│                         │      │  (ReAct Loop + Tools)   │      │    │
│                         │      └────────────┬────────────┘      │    │
│                         │                   │                    │    │
│                         │      ┌────────────▼────────────┐      │    │
│                         │      │        Tool Layer        │      │    │
│                         │      │  Academic | Tasks | Notes│      │    │
│                         │      │  Calendar | Weather | IoT│      │    │
│                         │      │  Web Search | Image Gen  │      │    │
│                         │      └────────────┬────────────┘      │    │
│                         │                   │                    │    │
│                         │      ┌────────────▼────────────┐      │    │
│                         │      │       Supabase DB        │      │    │
│                         │      │  (PostgreSQL + pgvector) │      │    │
│                         │      └─────────────────────────┘      │    │
│                         │                                        │    │
│                         │      ┌─────────────────────────┐      │    │
│                         │      │   Background Scheduler   │      │    │
│                         │      │   (APScheduler + Cron)   │      │    │
│                         │      └─────────────────────────┘      │    │
│                         └──────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │  Gemini AI  │  │  Tavily API │  │ OpenWeather │  │ Zalo Bot │  │
│  │  (LLM/Img)  │  │  (Search)   │  │   (Weather) │  │  (Push)  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Luồng xử lý một tin nhắn

```
User gửi tin nhắn
       │
       ▼
  FastAPI nhận request (/api/agent/chat)
       │
       ▼
  MemoryManager: Load session + lịch sử hội thoại
       │
       ▼
  LangGraph Agent (ReAct Loop):
    ┌──────────────────────┐
    │  Agent Node (LLM)    │ ◄── System Prompt (thời gian VN, sở thích user)
    │  Quyết định: Trả lời │     Lịch sử hội thoại (sliding window)
    │  hoặc gọi tool?      │     Conversation Summary
    └──────┬───────────────┘
           │
     Cần tool?
     ┌─────┴──────┐
     │            │
     ▼            ▼
  Tool Node    Trả lời ngay
  (thực thi)  (stream về client)
     │
     ▼
  Kết quả tool → quay lại Agent Node
       │
       ▼
  Phản hồi cuối cùng (stream SSE về frontend)
       │
       ▼
  Lưu DB + Generate session title + Maybe summarize
```

---

## 📁 Cấu trúc thư mục

```
jarvis-persona-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point, app factory
│   │   ├── config.py                  # Pydantic Settings (đọc từ .env)
│   │   ├── core/                      # Shared infrastructure
│   │   │   ├── database.py            # Supabase client (anon + admin)
│   │   │   ├── dependencies.py        # FastAPI DI (get_db, get_current_user_id)
│   │   │   ├── exceptions.py          # Custom exception classes
│   │   │   ├── llm_provider.py        # LLM factory (Gemini/OpenAI/Groq)
│   │   │   ├── security.py            # Fernet encrypt, JWT, bcrypt
│   │   │   ├── zalo.py                # Zalo Bot push notification
│   │   │   ├── zalo_formatter.py      # Emotion → Sticker mapping
│   │   │   └── stickers.json          # Zalo sticker ID database
│   │   ├── features/                  # Feature-based modules
│   │   │   ├── auth/                  # Đăng ký, đăng nhập, profile
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   └── schemas.py
│   │   │   ├── academic/              # Tích hợp portal nhà trường
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py         # Cache-first, sync từ school API
│   │   │   │   ├── school_client.py   # HTTP client cho TVU API
│   │   │   │   ├── schemas.py         # TimetableSlot, GradeEntry, ...
│   │   │   │   └── tools.py           # LangChain tools cho agent
│   │   │   ├── agent/                 # LangGraph ReAct engine
│   │   │   │   ├── graph.py           # Build StateGraph, tool node
│   │   │   │   ├── memory.py          # 3-tier memory system
│   │   │   │   ├── prompts.py         # System prompt + JARVIS persona
│   │   │   │   ├── router.py          # Chat API, sessions, SSE stream
│   │   │   │   └── tools/
│   │   │   │       ├── web_search.py  # Tavily search + scrape
│   │   │   │       ├── image_gen.py   # Gemini image generation
│   │   │   │       ├── weather.py     # OpenWeather AI Assistant
│   │   │   │       └── scheduler_tools.py  # AI Cronjob creator
│   │   │   ├── tasks/                 # Task & reminder management
│   │   │   ├── notes/                 # Quick notes
│   │   │   ├── calendar/              # Calendar events
│   │   │   ├── iot/                   # Smart home (Tuya LAN)
│   │   │   │   ├── router.py
│   │   │   │   ├── tuya.py            # TinyTuya + Auto-Heal IP
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── README_Tuya_Setup.md
│   │   │   └── knowledge/             # RAG pipeline (Phase 3)
│   │   └── background/
│   │       └── scheduler.py           # APScheduler (morning/evening/dynamic)
│   ├── migrations/
│   │   ├── 001_full_setup.sql         # Schema đầy đủ (Phase 1 + 2)
│   │   ├── phase2_iot.sql             # IoT devices + scheduled_prompts
│   │   └── phase2_notes_calendar.sql  # Quick notes + Calendar events
│   ├── tests/
│   │   ├── test_image_upload.py
│   │   └── test_scheduler.py
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
│
└── frontend/
    ├── src/
    │   ├── App.tsx                    # React Router setup
    │   ├── main.tsx                   # Entry point
    │   ├── pages/
    │   │   ├── Chat/                  # Trang chat chính
    │   │   │   ├── ChatPage.tsx       # Message list, input, SSE stream
    │   │   │   └── components/
    │   │   │       ├── Sidebar.tsx    # Danh sách sessions
    │   │   │       ├── FeaturePanel.tsx  # Panel widget bên phải
    │   │   │       ├── WeatherWidget.tsx
    │   │   │       ├── CalendarWidget.tsx
    │   │   │       ├── TasksWidget.tsx
    │   │   │       ├── NotesListWidget.tsx
    │   │   │       └── RoutineWidget.tsx  # Báo cáo sáng/tối
    │   │   ├── Login/                 # Trang đăng nhập
    │   │   ├── Register/              # Trang đăng ký
    │   │   └── Settings/              # Cài đặt
    │   │       ├── ProfileSettingsPage.tsx   # Profile + tài khoản trường
    │   │       ├── SchedulerSettingsPage.tsx # Thời tiết + lịch trình
    │   │       ├── SettingsLayout.tsx
    │   │       └── components/
    │   │           └── IoTManagementTab.tsx  # Quản lý thiết bị nhà thông minh
    │   ├── services/
    │   │   ├── api.ts                 # Axios instance + interceptors
    │   │   ├── auth.service.ts
    │   │   ├── chat.service.ts
    │   │   ├── iot.service.ts
    │   │   ├── notes.service.ts
    │   │   └── tasks.service.ts
    │   ├── stores/
    │   │   ├── authStore.ts           # Zustand auth state
    │   │   └── chatStore.ts           # Zustand chat state + SSE logic
    │   ├── types/
    │   │   ├── auth.ts
    │   │   └── chat.ts
    │   └── assets/styles/
    │       ├── global.css
    │       ├── variables.css
    │       └── animations.css
    ├── package.json
    └── vite.config.ts
```

---

## 🛠️ Tech Stack

### Backend
| Thành phần | Công nghệ | Phiên bản |
|---|---|---|
| Web Framework | FastAPI | 0.115.x |
| ASGI Server | Uvicorn | 0.34.x |
| AI Agent | LangGraph (ReAct) | 0.3.x |
| LLM | LangChain (Gemini/OpenAI/Groq) | 0.3.x |
| Database | Supabase (PostgreSQL) | 2.x |
| Vector DB | pgvector (trong Supabase) | - |
| Encryption | Cryptography (Fernet) | 44.x |
| Auth | JWT (python-jose) + bcrypt | 3.3.x |
| IoT | TinyTuya (Tuya LAN) | ≥1.17.6 |
| Scheduler | APScheduler | - |
| Web Search | Tavily | - |
| Weather | OpenWeather AI Assistant | - |
| Image Gen | Google Gemini Image | - |
| Notifications | Zalo Bot API | - |
| HTTP Client | httpx | 0.28.x |

### Frontend
| Thành phần | Công nghệ | Phiên bản |
|---|---|---|
| Framework | React | 19.x |
| Language | TypeScript | 5.8.x |
| Build Tool | Vite | 6.x |
| State Management | Zustand | 5.x |
| HTTP Client | Axios | 1.x |
| Markdown Render | react-markdown + remark-gfm | 10.x |
| Icons | lucide-react | 0.575.x |
| Routing | react-router-dom | 7.x |

---

## ✨ Tính năng chi tiết

### 🔐 Xác thực (Auth)
- Đăng ký tài khoản với email, họ tên, MSSV
- Đăng nhập trả về JWT token (24 giờ)
- Cập nhật profile (họ tên, avatar)
- Cấu hình Agent: độ chi tiết câu trả lời (Đầy đủ / Ngắn gọn)
- Tích hợp tài khoản đào tạo TVU (MSSV + mật khẩu) với mã hóa Fernet

### 📚 Học vụ (Academic)
- Kết nối trực tiếp đến API cổng thông tin đào tạo TVU (`ttsv.tvu.edu.vn`)
- Lấy thời khóa biểu theo tuần / học kỳ
- Lấy bảng điểm đầy đủ theo từng học kỳ (hệ 10 + hệ 4)
- Cache dữ liệu 24 giờ (TTL có thể cấu hình)
- Tự động detect học kỳ hiện tại từ server nhà trường
- Xử lý lỗi thông minh: phân biệt thông tin đăng nhập sai vs API trường lỗi

### 🤖 AI Agent (LangGraph ReAct)
- **Kiến trúc ReAct**: LLM → Quyết định → Tool → Kết quả → LLM → ...
- **3-tier Memory System**:
  - *Short-term*: Sliding window 7 cặp tin nhắn gần nhất
  - *Summary Memory*: Nén lịch sử cũ thành tóm tắt bằng LLM khi > 10 tin nhắn
  - *Long-term*: Preferences người dùng inject vào System Prompt
- **Streaming**: Server-Sent Events (SSE) — phản hồi token-by-token
- **Multimodal**: Hỗ trợ gửi ảnh kèm câu hỏi (phân tích hình ảnh)
- **Thinking Mode**: Hiển thị "quá trình suy nghĩ" của Gemini nếu model hỗ trợ
- Tự động generate tiêu đề cho mỗi cuộc hội thoại
- Dừng stream giữa chừng (Stop Generation)

### ✅ Task & Nhắc nhở
- Tạo task với tiêu đề, mô tả, deadline, mức ưu tiên, danh mục
- Liệt kê, lọc, sắp xếp task
- Đánh dấu hoàn thành / xóa task
- Agent tự động nhắc task sắp đến hạn trong hội thoại

### 📝 Ghi chú nhanh
- Lưu ghi chú tức thì (tự động trích xuất tags bằng AI)
- Tìm kiếm full-text nhanh (PostgreSQL GIN index)
- Ghim ghi chú quan trọng
- Lưu trữ (archive) ghi chú cũ
- Cập nhật nội dung, tags

### 📆 Lịch hẹn
- Tạo sự kiện với tiêu đề, mô tả, thời gian bắt đầu/kết thúc, địa điểm
- Xem sự kiện sắp tới
- Cập nhật và xóa sự kiện
- Widget lịch tháng trực quan trên frontend

### 🌤️ Thời tiết
- Tra cứu thời tiết real-time bằng OpenWeather AI Assistant API
- Hỗ trợ truy vấn bằng tên thành phố hoặc tọa độ GPS
- Cache kết quả (mặc định 30 phút, người dùng có thể chỉnh 15/30/60/120 phút)
- Widget thời tiết trên frontend (dùng GPS của trình duyệt)
- Cấu hình vị trí mặc định trong Settings

### 🌐 Tìm kiếm Web
- Tìm kiếm thông tin real-time bằng Tavily AI Search Engine
- Phân tích độ mới của dữ liệu (so sánh ngày kết quả với ngày hiện tại)
- Đọc toàn bộ nội dung trang web qua URL
- Miễn phí 1,000 requests/tháng

### 🎨 Tạo hình ảnh AI
- Sinh ảnh từ mô tả văn bản (Tiếng Việt hoặc Tiếng Anh)
- Sử dụng Gemini Pro Image model
- Tự động upload lên Supabase Storage và trả về URL công khai
- Hiển thị ảnh trực tiếp trong chat (Markdown image rendering)
### 📚 Tài liệu & RAG (Phase 3)
- Upload PDF/PPTX lên Supabase S3 (`knowledge-base` bucket private)
- Background pipeline: TextSplitter (1000/200) → Gemini Embeddings (`text-embedding-004`, 768 dims) → pgvector
- **Dual-mode ingestion**:
  - *Luồng 1 (Temp)*: `/extract-text` giải nén văn bản vào RAM, gửi inline trong chat (không tốn vector DB)
  - *Luồng 2 (Persistent)*: `/upload` xử lý nền, chunk + embed, lưu vào `material_chunks`
  - *Luồng 3 (Promote)*: Agent tool `save_temp_document_to_knowledge_base` chuyển tài liệu từ `/temp/` lên domain thật
- Agent tự động có 6 knowledge tools: search, save memory, semantic search, save, find, delete
- `display_message`: lịch sử chat hiển thị clean (không dump raw document content)
### 🏠 Nhà thông minh (IoT)
- Điều khiển ổ cắm thông minh Tuya/SmartLife qua mạng LAN cục bộ
- Bật / Tắt / Kiểm tra trạng thái thiết bị
- Hỗ trợ ổ đơn (Single) và ổ đa năng (Multi — nhiều cổng DPS)
- **Auto-Heal IP**: Tự động quét LAN tìm IP mới nếu thiết bị đổi IP (DHCP)
- Quản lý thiết bị trên giao diện web (thêm, sửa, xóa, test kết nối)
- Auto-discovery: Quét UDP Broadcast để tìm thiết bị Tuya trên mạng

### ⏰ Lịch trình tự động
- **Báo cáo sáng**: Tóm tắt lịch học, task, thời tiết gửi vào giờ cấu hình
- **Tổng kết tối**: Review task hôm nay, xem lịch ngày mai
- Tùy chỉnh prompt cho mỗi loại báo cáo qua giao diện web
- **Dynamic AI Cronjobs**: Đặt lịch để Agent tự thực hiện bất kỳ hành động nào (Cron Expression UTC+7)
- Sync cronjobs mỗi 5 phút từ database
- Kết quả báo cáo được lưu vào chat history (hiển thị trên web)

### 📱 Thông báo Zalo
- Gửi báo cáo tự động qua Zalo Bot
- **Emotion-based Sticker**: LLM phân tích cảm xúc nội dung → chọn sticker Zalo phù hợp trước khi gửi text
- Giới hạn 2000 ký tự/tin nhắn (tự động cắt ngắn)
- Fallback về text thuần nếu LLM gặp lỗi

---

## 🗄️ Cơ sở dữ liệu

Sử dụng **Supabase** (PostgreSQL managed) với các bảng:

```sql
-- Người dùng
users                  -- id, full_name, student_id, email, password_hash,
                       -- preferences (JSONB), agent_config (JSONB)

-- Bảo mật
user_credentials       -- school_username_enc, school_password_enc (Fernet-encrypted)

-- Học vụ
academic_sync_cache    -- raw_data (JSONB), last_synced_at, data_type, semester

-- Task
tasks_reminders        -- title, due_date, priority, status, category, embedding (vector)

-- Ghi chú
quick_notes            -- content, tags (TEXT[]), is_pinned, embedding (vector)
                       -- Full-text search index: GIN on to_tsvector(content)

-- Lịch hẹn
calendar_events        -- title, start_time, end_time, location, event_type

-- Hội thoại
conversation_sessions  -- title, summary, message_count
chat_messages          -- role, content, tool_calls (JSONB)

-- Tài liệu học (Phase 3)
study_materials        -- file_name, file_url, subject, chunk_count
material_chunks        -- content, embedding vector(3072)  ← pgvector

-- Nhà thông minh
iot_devices            -- name, ip_address, device_id, local_key, dps_mapping (JSONB)

-- AI Cronjobs
scheduled_prompts      -- name, cron_expr, prompt, is_active
```

**Extensions PostgreSQL được sử dụng:**
- `vector` — lưu trữ và tìm kiếm vector embedding (pgvector — đã dùng cho RAG Phase 3)
- `pgcrypto` — tạo UUID
- `unaccent` — tìm kiếm không dấu tiếng Việt

---

## 🚀 Cài đặt & Chạy

### Yêu cầu hệ thống
- Python 3.11+
- Node.js 18+ (cho frontend)
- Tài khoản Supabase (free tier đủ dùng)
- API Key: Gemini AI (bắt buộc), Tavily (tùy chọn), OpenWeather (tùy chọn)

### 1. Clone & Chuẩn bị

```bash
git clone https://github.com/thhieu2904/jarvis-persona-agent.git
cd jarvis-persona-agent
```

### 2. Thiết lập Supabase

1. Tạo project tại [supabase.com](https://supabase.com)
2. Mở **SQL Editor** trong Supabase Dashboard
3. Chạy lần lượt các migration scripts:
   ```sql
   -- Chạy file này trước
   backend/migrations/001_full_setup.sql

   -- Sau đó chạy file này
   backend/migrations/phase2_iot.sql
   ```
4. Lấy `SUPABASE_URL`, `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_KEY` (service_role) từ **Settings → API**
5. Tạo Storage bucket tên `chat-uploads` và `generated-images` (Public)

### 3. Cài đặt Backend

```bash
cd backend

# Tạo virtual environment (khuyến nghị)
python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate         # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Tạo file .env từ template
cp .env.example .env
```

Chỉnh sửa file `.env` (xem phần [Biến môi trường](#-biến-môi-trường) bên dưới).

```bash
# Chạy backend
uvicorn app.main:app --reload --port 8000
```

Truy cập Swagger UI: http://localhost:8000/docs

### 4. Cài đặt Frontend

```bash
cd frontend

# Cài đặt dependencies
npm install

# Chạy development server
npm run dev
```

Truy cập: http://localhost:5173

### 5. Docker (Tùy chọn)

```bash
cd backend
docker build -t jarvis-backend .
docker run -p 8000:8000 --env-file .env jarvis-backend
```

---

## ⚙️ Biến môi trường

Tạo file `backend/.env` từ `backend/.env.example`:

```env
# ── App ──────────────────────────────────────────────────
APP_NAME=aic-persona-agent
APP_VERSION=0.1.0
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ── Supabase ─────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# ── Security ─────────────────────────────────────────────
# Tạo Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_SECRET_KEY=your-fernet-key-here

# Tạo JWT secret: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440   # 24 giờ

# ── LLM (Provider-Agnostic) ─────────────────────────────
# Chọn 1 trong 3: gemini | openai | groq
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=your-gemini-api-key
LLM_TEMPERATURE=0.7

# ── Image Generation ─────────────────────────────────────
IMAGE_MODEL=gemini-3-pro-image-preview
IMAGE_MODEL_ENABLED=true

# ── Embedding (Phase 3 RAG) ──────────────────────────────
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSIONS=3072

# ── School API (TVU) ─────────────────────────────────────
SCHOOL_API_BASE_URL=https://ttsv.tvu.edu.vn/public/api
SCHOOL_CACHE_TTL_HOURS=24   # Cache 24 giờ
SCHOOL_API_TIMEOUT=30       # Timeout 30 giây

# ── Tavily (Web Search) — tùy chọn ──────────────────────
TAVILY_API_KEY=tvly-xxxxxxxxxxxx   # Free: 1000 req/tháng

# ── OpenWeather — tùy chọn ──────────────────────────────
OPENWEATHER_API_KEY=your-openweather-key

# ── Zalo Bot — tùy chọn ──────────────────────────────────
ZALO_BOT_TOKEN=your-bot-token
ZALO_CHAT_ID=your-personal-chat-id

# ── Agent Tuning ─────────────────────────────────────────
AGENT_RECURSION_LIMIT=25   # Số bước tối đa trong 1 lần chat
AGENT_MEMORY_WINDOW_SIZE=7 # Số cặp tin nhắn giữ lại
AGENT_SUMMARY_THRESHOLD=10 # Ngưỡng trigger tóm tắt
```

### Cách lấy API Keys

| Service | Cách lấy |
|---|---|
| **Gemini AI** | [aistudio.google.com](https://aistudio.google.com) → Get API key (miễn phí) |
| **Supabase** | [supabase.com](https://supabase.com) → Tạo project → Settings → API |
| **Tavily** | [tavily.com](https://tavily.com) → Sign up (free 1000 req/tháng) |
| **OpenWeather** | [openweathermap.org](https://openweathermap.org/api) → Free tier |
| **Zalo Bot** | [bot.zaloplatforms.com](https://bot.zaloplatforms.com) → Tạo bot |

---

## 📡 API Endpoints

### Auth (`/api/auth`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/register` | Đăng ký tài khoản mới |
| `POST` | `/login` | Đăng nhập, nhận JWT token |
| `GET` | `/profile` | Lấy thông tin profile (cần auth) |
| `PUT` | `/profile` | Cập nhật profile (cần auth) |

### Agent (`/api/agent`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/chat` | Gửi tin nhắn, nhận phản hồi SSE stream |
| `POST` | `/upload_image` | Upload ảnh lên Supabase Storage |
| `GET` | `/sessions` | Danh sách các phiên hội thoại |
| `GET` | `/sessions/{id}/messages` | Lịch sử tin nhắn của một phiên |
| `DELETE` | `/sessions/{id}` | Xóa phiên hội thoại |
| `GET` | `/weather` | Lấy dữ liệu thời tiết (lat/lon hoặc default) |
| `GET` | `/routine_schedule` | Lấy cấu hình báo cáo sáng/tối |
| `PUT` | `/routine_schedule` | Cập nhật giờ báo cáo sáng/tối |
| `GET` | `/available_tools` | Danh sách tool dùng trong routine prompt |

### Academic (`/api/academic`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/credentials` | Lưu thông tin đăng nhập trường |
| `POST` | `/reconnect` | Cập nhật thông tin đăng nhập |
| `GET` | `/timetable` | Lấy thời khóa biểu |
| `GET` | `/grades` | Lấy bảng điểm |
| `GET` | `/semesters` | Danh sách học kỳ |

### Tasks (`/api/tasks`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Danh sách tasks |
| `POST` | `/` | Tạo task mới |
| `PUT` | `/{id}` | Cập nhật task |
| `DELETE` | `/{id}` | Xóa task |

### Notes (`/api/notes`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Danh sách ghi chú |
| `POST` | `/` | Tạo ghi chú mới |
| `PUT` | `/{id}` | Cập nhật ghi chú |
| `DELETE` | `/{id}` | Archive ghi chú |
| `GET` | `/search` | Tìm kiếm full-text |

### Calendar (`/api/calendar`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/events` | Danh sách sự kiện |
| `POST` | `/events` | Tạo sự kiện mới |
| `PUT` | `/events/{id}` | Cập nhật sự kiện |
| `DELETE` | `/events/{id}` | Xóa sự kiện |

### Knowledge (`/api/knowledge`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/upload` | Upload file lên RAG (background processing + embeddings) |
| `POST` | `/extract-text` | Extract text tạm thời vào RAM — không lưu DB |
| `POST` | `/promote` | Promote tài liệu tạm từ temp/ lên persistent RAG |
| `GET` | `/` | Danh sách tài liệu đã upload |
| `DELETE` | `/{material_id}` | Xóa tài liệu khỏi S3 + DB (cascade chunks) |

### IoT (`/api`)
| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/iot/devices` | Danh sách thiết bị IoT |
| `POST` | `/iot/devices` | Thêm thiết bị mới |
| `PUT` | `/iot/devices/{id}` | Cập nhật thiết bị |
| `DELETE` | `/iot/devices/{id}` | Xóa thiết bị |
| `POST` | `/iot/scan` | Quét tự động thiết bị Tuya trên LAN |
| `POST` | `/iot/ping` | Test kết nối và lấy DPS ports của thiết bị |

### System
| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |

> **Xác thực**: Tất cả endpoint (trừ `/register`, `/login`, `/health`, `/docs`) yêu cầu header `Authorization: Bearer <jwt_token>`

---

## 🔧 Agent Tools

JARVIS có **25 tools** tích hợp sẵn, được phân nhóm như sau:

### 📚 Học tập (Academic)
| Tool | Mô tả |
|---|---|
| `get_semesters()` | Lấy danh sách học kỳ từ trường |
| `get_timetable(semester?)` | Lấy thời khóa biểu theo tuần/học kỳ |
| `get_grades(semester?)` | Lấy bảng điểm đầy đủ |

### ✅ Task & Nhắc nhở
| Tool | Mô tả |
|---|---|
| `create_task(title, due_date?, priority?, ...)` | Tạo task mới |
| `list_tasks(status?, priority?)` | Xem danh sách task |
| `update_task(task_id, ...)` | Sửa task |
| `complete_task(task_id)` | Đánh dấu hoàn thành |
| `delete_task(task_id)` | Xóa task |

### 📝 Ghi chú
| Tool | Mô tả |
|---|---|
| `save_quick_note(content, tags?)` | Lưu ghi chú nhanh |
| `search_notes(query)` | Tìm kiếm ghi chú |
| `list_notes()` | Xem tất cả ghi chú |
| `update_note(note_id, ...)` | Sửa ghi chú |
| `delete_note(note_id)` | Archive ghi chú |

### 📆 Lịch hẹn
| Tool | Mô tả |
|---|---|
| `create_event(title, start_time, ...)` | Tạo sự kiện |
| `get_events(days_ahead?)` | Xem sự kiện sắp tới |
| `update_event(event_id, ...)` | Sửa sự kiện |
| `delete_event(event_id)` | Xóa sự kiện |

### 🌐 Tiện ích
| Tool | Mô tả |
|---|---|
| `search_web(query)` | Tìm kiếm internet real-time (Tavily) |
| `scrape_website(url)` | Đọc nội dung trang web |
| `get_weather(location)` | Tra cứu thời tiết theo địa điểm |
| `generate_image(prompt)` | Tạo hình ảnh từ văn bản (Gemini Image) |

### 🏠 Nhà thông minh
| Tool | Mô tả |
|---|---|
| `list_smart_home_devices()` | Khám phá tất cả thiết bị IoT của user |
| `toggle_smart_plug(device_id, action, dps_index?)` | Bật/Tắt/Kiểm tra ổ cắm |

### ⏰ Lên lịch tự động
| Tool | Mô tả |
|---|---|
| `schedule_automation(task_name, cron_expr, prompt)` | Đặt lịch AI tự động theo Cron |

### 📖 Tài liệu & Kiến thức (RAG — Phase 3)
| Tool | Mô tả |
|---|---|
| `search_memories(query)` | Tìm kiếm bộ nhớ dài hạn đã lưu |
| `save_memory(content)` | Lưu thông tin quan trọng vào bộ nhớ dài hạn |
| `search_study_materials(query)` | Semantic search tài liệu học qua pgvector |
| `save_temp_document_to_knowledge_base(storage_path, ...)` | Promote tài liệu tạm vào RAG persistent |
| `find_study_materials(query)` | Tìm tài liệu theo tên file (ILIKE) |
| `delete_study_material(material_id)` | Xóa tài liệu khỏi RAG (S3 + DB cascade) |

---

## 🖥️ Frontend

### Các trang chính

| Trang | Route | Mô tả |
|---|---|---|
| **Chat** | `/` | Giao diện chat chính với JARVIS |
| **Đăng nhập** | `/login` | Form đăng nhập |
| **Đăng ký** | `/register` | Form đăng ký tài khoản |
| **Hồ sơ** | `/settings/profile` | Thông tin cá nhân + tài khoản trường |
| **IoT** | `/settings/iot` | Quản lý thiết bị nhà thông minh |
| **Lịch trình** | `/settings/scheduler` | Cấu hình thời tiết + lịch tự động |

### Tính năng giao diện Chat

- **Sidebar trái**: Danh sách phiên hội thoại (có tiêu đề tự sinh)
- **Vùng chat chính**: Render Markdown (bảng, code, ảnh)
- **Quá trình suy nghĩ (Thinking)**: Có thể xem reasoning của Gemini
- **Tool results**: Xem dữ liệu trả về từ các tools (thu gọn được)
- **Image Upload**: Đính kèm tối đa 5 ảnh / tin nhắn
- **Document Attach**: Đính kèm PDF/PPTX vào chat — AI đọc nội dung inline (Dual-mode: temp context + promote to RAG)
- **Voice Input**: Nhận diện giọng nói tiếng Việt (Web Speech API)
- **Stop Generation**: Dừng stream giữa chừng
- **FeaturePanel phải**: Widget thời tiết, lịch, task, ghi chú, routine

### State Management (Zustand)

- `authStore`: User, JWT token, preferences, agent_config
- `chatStore`: Messages, sessions, SSE streaming state, error

---

## 🏠 IoT & Nhà thông minh

### Thiết bị hỗ trợ
Tất cả thiết bị thương hiệu **Tuya / SmartLife** (ổ cắm đơn, ổ đa năng, công tắc thông minh) hoạt động trên cùng mạng WiFi với backend.

### Cách setup thiết bị

**Bước 1**: Lấy `Device ID` và `Local Key` bằng TinyTuya Wizard:
```bash
pip install tinytuya
python -m tinytuya wizard
# Điền Access ID, Secret, Device ID từ Tuya IoT Platform
# Kết quả: file devices.json chứa id và key của tất cả thiết bị
```

**Bước 2**: Thêm thiết bị vào JARVIS:
- Vào **Settings → Quản lý Smart Home**
- Nhấn **📡 Quét Radar Tự Động** (auto-discovery qua UDP)
- Hoặc điền thủ công: Tên, IP, Device ID, Local Key
- Nhấn **Test Kết Nối** → Hệ thống tự detect DPS ports

**Bước 3**: Điều khiển qua chat:
```
Bạn: "Bật đèn học lên"
JARVIS: → list_smart_home_devices() → toggle_smart_plug(device_id="xxx", action="on", dps_index="2")
        → "✅ Đã bật đèn học!"
```

### Auto-Heal IP
Khi thiết bị đổi IP (DHCP), hệ thống tự động:
1. Phát hiện timeout kết nối
2. Phát UDP Broadcast quét toàn mạng LAN
3. Tìm thiết bị theo Device ID
4. Cập nhật IP mới vào database
5. Thực thi lại lệnh với IP mới

> 📖 Xem thêm tại [`backend/app/features/iot/README_Tuya_Setup.md`](backend/app/features/iot/README_Tuya_Setup.md)

---

## 📱 Thông báo Zalo

JARVIS có thể gửi thông báo về Zalo của bạn với **sticker cảm xúc thông minh**:

### Cách hoạt động
1. JARVIS tạo xong nội dung báo cáo (text)
2. LLM phân tích cảm xúc nội dung → trả về enum `EmotionType`
3. Map emotion → Sticker ID từ `stickers.json`
4. Gửi sticker trước, sau đó gửi text
5. Fallback về text thuần nếu LLM gặp lỗi

### Setup Zalo Bot
1. Tạo bot tại [bot.zaloplatforms.com](https://bot.zaloplatforms.com)
2. Lấy `Bot Token`
3. Chat với bot để lấy `Chat ID` của bạn
4. Điền vào `.env`: `ZALO_BOT_TOKEN` và `ZALO_CHAT_ID`

---

## ⏰ Background Scheduler

### Báo cáo định kỳ
Cấu hình trong **Settings → Lịch trình** hoặc qua chat:
```
Bạn: "Đặt báo cáo sáng lúc 6:30"
JARVIS: → update_routine_schedule() → "Đã đặt báo cáo sáng lúc 06:30 ✅"
```

**Prompt mẫu báo cáo sáng:**
> Kiểm tra lịch học hôm nay → Rà soát task đến hạn → Xem sự kiện lịch → Lấy thời tiết → Viết báo cáo ngắn gọn

### Dynamic AI Cronjobs
Tạo lịch tự động qua chat:
```
Bạn: "Mỗi tối 9h, nhắc tôi tắt đèn"
JARVIS: → schedule_automation("Tắt đèn 9h tối", "0 21 * * *", "Tắt đèn học đi")
```

- Lưu vào bảng `scheduled_prompts` trong Supabase
- APScheduler sync lại từ DB mỗi 5 phút
- Kết quả chạy được lưu vào chat history

---

## 📦 Phát triển

### Thêm tính năng mới (Feature-based Architecture)

```bash
# Tạo thư mục feature mới
mkdir backend/app/features/my_feature
touch backend/app/features/my_feature/__init__.py
touch backend/app/features/my_feature/router.py
touch backend/app/features/my_feature/service.py
touch backend/app/features/my_feature/tools.py

# Đăng ký router trong main.py
from app.features.my_feature.router import router as my_router
app.include_router(my_router, prefix="/api/my_feature", tags=["My Feature"])
```

### Thêm LLM Provider mới

Chỉ cần chỉnh `LLM_PROVIDER` và `LLM_MODEL` trong `.env` — không cần sửa code:
```env
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxx

# Groq (llama3, mixtral...)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-70b-versatile
LLM_API_KEY=gsk_xxx
```

### Chạy Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🗺️ Lộ trình phát triển

| Phase | Tính năng | Trạng thái |
|---|---|---|
| **Phase 1** | Auth, Academic (TVU), LangGraph Agent, Tasks | ✅ Hoàn thành |
| **Phase 2** | Notes, Calendar, IoT Tuya, Zalo Bot, Scheduler | ✅ Hoàn thành |
| **Phase 2.5** | Frontend React, Image Upload, Voice Input, Thinking Mode | ✅ Hoàn thành |
| **Phase 3** | RAG Pipeline — Dual-mode ingestion (temp context + persistent pgvector), Knowledge tools, File đính kèm trong chat | ✅ Hoàn thành |
| **Phase 4** | Mobile App (React Native), offline support | 💡 Ý tưởng |
| **Phase 5** | Multi-user mode, family/team sharing | 💡 Ý tưởng |

---

## 🤝 Đóng góp

Dự án được xây dựng với tất cả tâm huyết. Mọi đóng góp đều được chào đón:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/ten-tinh-nang`)
3. Commit changes (`git commit -m 'feat: thêm tính năng X'`)
4. Push branch (`git push origin feature/ten-tinh-nang`)
5. Tạo Pull Request

---

## 📄 License

MIT License — Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

<p align="center">
  Được xây dựng với ❤️ bởi <a href="https://github.com/thhieu2904">thhieu2904</a>
</p>
