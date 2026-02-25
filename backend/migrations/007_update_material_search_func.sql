-- 007_update_material_search_func.sql

-- Drop function with old signature if exists to avoid conflicts
DROP FUNCTION IF EXISTS search_materials_by_embedding(vector(768), UUID, INT, TEXT);

-- Create new function with domain filter
CREATE OR REPLACE FUNCTION search_materials_by_embedding(
    query_embedding vector(768),
    match_user_id UUID,
    match_count INT DEFAULT 5,
    filter_domain TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    chunk_index INT,
    page_number INT,
    section_title TEXT,
    material_id UUID,
    file_name TEXT,
    domain TEXT,
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
        sm.domain,
        1 - (mc.embedding <=> query_embedding) AS similarity
    FROM material_chunks mc
    JOIN study_materials sm ON mc.material_id = sm.id
    WHERE sm.user_id = match_user_id
      AND mc.embedding IS NOT NULL
      AND (filter_domain IS NULL OR sm.domain = filter_domain)
    ORDER BY mc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
