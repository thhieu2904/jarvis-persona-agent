-- =====================================================
-- Phase 2 Migration: Quick Notes + Calendar Events
-- Run in Supabase SQL Editor
-- =====================================================

-- Prerequisite: pgvector extension (should already exist from schema.md)
CREATE EXTENSION IF NOT EXISTS vector;


-- =====================================================
-- 1. Quick Notes
-- =====================================================
CREATE TABLE IF NOT EXISTS quick_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Nội dung
    content TEXT NOT NULL,
    note_type TEXT DEFAULT 'note',     -- note | idea | link | snippet
    tags TEXT[],                        -- Auto-tagged bởi LLM
    url TEXT,                           -- Bookmark link
    related_subject TEXT,               -- Liên kết môn học
    
    -- Semantic search (Phase 2.5: filled by background job)
    embedding vector(768),             -- NULL lúc INSERT, bg job fill sau
    
    -- Quản lý
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notes_user 
    ON quick_notes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_tags 
    ON quick_notes USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_notes_search 
    ON quick_notes USING gin(to_tsvector('simple', content));

-- Trigger
CREATE TRIGGER trg_notes_updated
    BEFORE UPDATE ON quick_notes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- 2. Calendar Events
-- =====================================================
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Cái gì + Khi nào
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT DEFAULT 'personal',  -- personal | club | study_group | birthday | other
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    is_all_day BOOLEAN DEFAULT FALSE,
    
    -- Chi tiết
    location TEXT,
    
    -- Semantic search (Phase 2.5: filled by background job)
    embedding vector(768),              -- NULL lúc INSERT, bg job fill sau
    
    -- Quản lý
    source TEXT DEFAULT 'user',          -- user | agent
    reminder_minutes INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_user_time 
    ON calendar_events(user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_events_type 
    ON calendar_events(user_id, event_type);

-- Trigger
CREATE TRIGGER trg_events_updated
    BEFORE UPDATE ON calendar_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- 3. Add embedding column to tasks_reminders
-- =====================================================
ALTER TABLE tasks_reminders 
    ADD COLUMN IF NOT EXISTS embedding vector(768);
