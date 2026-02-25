-- =====================================================
-- Migration 003: Add is_pinned to tasks_reminders
-- Run in Supabase SQL Editor
-- =====================================================

-- Thêm cột is_pinned vào bảng tasks_reminders
ALTER TABLE tasks_reminders
    ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;

-- Index hỗ trợ sort pinned items lên đầu
CREATE INDEX IF NOT EXISTS idx_tasks_pinned
    ON tasks_reminders(user_id, is_pinned DESC, due_date ASC);
