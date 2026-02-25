-- =====================================================
-- FULL Database Setup: Initial Schema + Phase 2
-- Run in Supabase SQL Editor or via psycopg2
-- =====================================================

-- ═════════════════════════════════════════════════════
-- INITIAL SCHEMA (from schema.md)
-- ═════════════════════════════════════════════════════

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Users & Security
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    student_id TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    agent_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    school_username_enc TEXT NOT NULL,  -- Fernet-encrypted, base64 string
    school_password_enc TEXT NOT NULL,  -- Fernet-encrypted, base64 string
    school_token TEXT,
    token_expires_at TIMESTAMPTZ,
    encryption_key_hint TEXT,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Academic Cache
CREATE TABLE IF NOT EXISTS academic_sync_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    data_type TEXT NOT NULL,
    semester TEXT,
    raw_data JSONB NOT NULL,
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    sync_status TEXT DEFAULT 'success',
    sync_error TEXT,
    UNIQUE(user_id, data_type, semester),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_academic_cache_lookup
    ON academic_sync_cache(user_id, data_type, semester);
CREATE INDEX IF NOT EXISTS idx_academic_cache_sync
    ON academic_sync_cache(last_synced_at);

-- 4. Tasks & Reminders
CREATE TABLE IF NOT EXISTS tasks_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ,
    remind_at TIMESTAMPTZ,
    recurrence TEXT DEFAULT 'none',
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    category TEXT,
    related_subject TEXT,
    source TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status
    ON tasks_reminders(user_id, status, due_date);

-- 5. Knowledge (RAG) - Phase 3 ready
CREATE TABLE IF NOT EXISTS study_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_url TEXT,
    file_size_bytes BIGINT,
    subject TEXT,
    semester TEXT,
    tags TEXT[],
    description TEXT,
    processing_status TEXT DEFAULT 'pending',
    chunk_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS material_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID REFERENCES study_materials(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    page_number INT,
    section_title TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_material
    ON material_chunks(material_id);

-- 6. Conversations
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    summary TEXT,
    summary_updated_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    message_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_call_id TEXT,
    token_count INT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON chat_messages(session_id, created_at);

-- 7. Auto-update trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to initial tables
CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_credentials_updated
    BEFORE UPDATE ON user_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_academic_updated
    BEFORE UPDATE ON academic_sync_cache FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_tasks_updated
    BEFORE UPDATE ON tasks_reminders FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_materials_updated
    BEFORE UPDATE ON study_materials FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_sessions_updated
    BEFORE UPDATE ON conversation_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ═════════════════════════════════════════════════════
-- PHASE 2: Quick Notes + Calendar Events
-- ═════════════════════════════════════════════════════

-- 8. Quick Notes
CREATE TABLE IF NOT EXISTS quick_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    note_type TEXT DEFAULT 'note',
    tags TEXT[],
    url TEXT,
    related_subject TEXT,
    embedding vector(768),
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_user
    ON quick_notes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_tags
    ON quick_notes USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_notes_search
    ON quick_notes USING gin(to_tsvector('simple', content));

CREATE TRIGGER trg_notes_updated
    BEFORE UPDATE ON quick_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 9. Calendar Events
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT DEFAULT 'personal',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    is_all_day BOOLEAN DEFAULT FALSE,
    location TEXT,
    embedding vector(768),
    source TEXT DEFAULT 'user',
    reminder_minutes INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_time
    ON calendar_events(user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_events_type
    ON calendar_events(user_id, event_type);

CREATE TRIGGER trg_events_updated
    BEFORE UPDATE ON calendar_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 10. Add embedding column to tasks_reminders
ALTER TABLE tasks_reminders
    ADD COLUMN IF NOT EXISTS embedding vector(768);
