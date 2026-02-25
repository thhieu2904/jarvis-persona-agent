-- =====================================================
-- Migration 005: RAG Adjustments (Vector 768 & Status)
-- Run in Supabase SQL Editor
-- =====================================================

-- 1. Thêm cột trạng thái tiến độ nhúng vector (embedding) cho quick_notes
ALTER TABLE quick_notes
    ADD COLUMN IF NOT EXISTS embedding_status TEXT DEFAULT 'pending';

-- 2. Đổi chuẩn kích thước Vector về 768 (chuẩn của gemini-embedding-001)
-- LƯU Ý: Do cột này trước đây là 3072, cần type cast
ALTER TABLE quick_notes 
    ALTER COLUMN embedding TYPE vector(768);

ALTER TABLE calendar_events 
    ALTER COLUMN embedding TYPE vector(768);

ALTER TABLE tasks_reminders 
    ALTER COLUMN embedding TYPE vector(768);

-- Bảng study_materials và material_chunks (nếu đã tạo từ 001) cũng cần đổi
ALTER TABLE material_chunks 
    ALTER COLUMN embedding TYPE vector(768);
