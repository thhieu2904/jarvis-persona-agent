-- 006_add_domain_to_study_materials.sql

-- 1. Thêm cột 'domain' (bắt buộc) cho bảng study_materials để phục vụ Domain-driven RAG
ALTER TABLE study_materials
ADD COLUMN IF NOT EXISTS domain TEXT DEFAULT 'other';

-- 2. Gỡ bỏ NOT NULL của file_type (hoặc cứ để nhưng dự phòng linh hoạt)
ALTER TABLE study_materials
ALTER COLUMN file_type DROP NOT NULL;
