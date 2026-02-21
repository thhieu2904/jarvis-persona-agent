# Jarvis Persona Agent 🤖

**Trợ lý ảo AI cá nhân mang phong cách J.A.R.V.I.S dành cho sinh viên.**  
Tích hợp tự động trích xuất dữ liệu từ portal trường, tìm kiếm web và các tính năng thông minh.

## Quick Start

```bash
# 1. Clone & setup
cd backend
cp .env.example .env
# Edit .env with your actual keys

# 2. Install deps
pip install -r requirements.txt

# 3. Run
uvicorn app.main:app --reload --port 8000
```

Open Swagger: http://localhost:8000/docs

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Pydantic Settings (.env)
│   ├── core/                # Shared infrastructure
│   │   ├── security.py      # Fernet encryption, JWT, bcrypt
│   │   ├── database.py      # Supabase client
│   │   ├── llm_provider.py  # Provider-agnostic LLM factory
│   │   └── dependencies.py  # FastAPI DI
│   └── features/            # Feature-based modules
│       ├── auth/            # User registration & login
│       ├── academic/        # School API + data cache
│       ├── agent/           # LangGraph ReAct engine
│       ├── tasks/           # Task/reminder management
│       └── knowledge/       # RAG layer (Phase 3)
├── .env.example
├── requirements.txt
└── Dockerfile
```

## Features

| Feature   | Status     | Description                           |
| --------- | ---------- | ------------------------------------- |
| Auth      | ✅ Phase 1 | Register, login, JWT, profile         |
| Academic  | ✅ Phase 1 | School API client, cache, credentials |
| Agent     | ✅ Phase 1 | LangGraph ReAct, 3-tier memory        |
| Tasks     | ✅ Phase 1 | CRUD tasks/reminders                  |
| Knowledge | 📋 Phase 3 | RAG pipeline with pgvector            |
| Frontend  | 📋 Phase 4 | React chat UI + dashboard             |
