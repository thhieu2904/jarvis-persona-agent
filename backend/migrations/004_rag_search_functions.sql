-- =====================================================
-- Migration 004: pgvector search functions for RAG
-- Run in Supabase SQL Editor
-- =====================================================

-- 1. Search notes by embedding (cosine similarity)
CREATE OR REPLACE FUNCTION search_notes_by_embedding(
    query_embedding vector(768),
    match_user_id UUID,
    match_count INT DEFAULT 5,
    filter_tags TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    note_type TEXT,
    tags TEXT[],
    is_pinned BOOLEAN,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        qn.id,
        qn.content,
        qn.note_type,
        qn.tags,
        qn.is_pinned,
        qn.created_at,
        1 - (qn.embedding <=> query_embedding) AS similarity
    FROM quick_notes qn
    WHERE qn.user_id = match_user_id
      AND qn.is_archived = FALSE
      AND qn.embedding IS NOT NULL
      AND (filter_tags IS NULL OR qn.tags && filter_tags)
    ORDER BY qn.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2. Search material chunks by embedding (cosine similarity)
CREATE OR REPLACE FUNCTION search_materials_by_embedding(
    query_embedding vector(768),
    match_user_id UUID,
    match_count INT DEFAULT 5,
    filter_subject TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    chunk_index INT,
    page_number INT,
    section_title TEXT,
    material_id UUID,
    file_name TEXT,
    subject TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        mc.id AS chunk_id,
        mc.content,
        mc.chunk_index,
        mc.page_number,
        mc.section_title,
        sm.id AS material_id,
        sm.file_name,
        sm.subject,
        1 - (mc.embedding <=> query_embedding) AS similarity
    FROM material_chunks mc
    JOIN study_materials sm ON mc.material_id = sm.id
    WHERE sm.user_id = match_user_id
      AND mc.embedding IS NOT NULL
      AND (filter_subject IS NULL OR sm.subject = filter_subject)
    ORDER BY mc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
