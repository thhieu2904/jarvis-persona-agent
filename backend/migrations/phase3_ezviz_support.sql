-- ==============================================================================
-- Migration script for IoT Phase 3: EZVIZ Camera Support
-- Mở rộng bảng `iot_devices` để hỗ trợ đa nền tảng (Tuya + EZVIZ + ...)
-- Execute this script in your Supabase SQL Editor.
-- ==============================================================================

-- 1. Thêm cột provider để phân biệt loại thiết bị
--    Dữ liệu cũ (Tuya) tự động nhận giá trị mặc định 'tuya'
ALTER TABLE public.iot_devices
ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'tuya';

-- 2. Thêm cột config_data (JSONB) để lưu cấu hình linh hoạt theo từng provider
--    VD EZVIZ: {"username": "84387839744", "password": "...", "region": "apiisgp.ezvizlife.com"}
ALTER TABLE public.iot_devices
ADD COLUMN IF NOT EXISTS config_data JSONB DEFAULT '{}'::jsonb;

-- 3. Gỡ ràng buộc NOT NULL cho các cột đặc thù của Tuya
--    Vì EZVIZ không cần device_id/local_key (dùng config_data thay thế)
--    Lưu ý: Dữ liệu Tuya cũ vẫn giữ nguyên giá trị, KHÔNG bị mất
ALTER TABLE public.iot_devices
ALTER COLUMN device_id DROP NOT NULL;

ALTER TABLE public.iot_devices
ALTER COLUMN local_key DROP NOT NULL;

-- 4. Gỡ ràng buộc NOT NULL cho ip_address
--    EZVIZ dùng Cloud API nên không cần IP nội bộ khi tạo config
ALTER TABLE public.iot_devices
ALTER COLUMN ip_address DROP NOT NULL;

-- 5. Cập nhật CHECK constraint cho device_type để hỗ trợ thêm loại 'camera'
--    Xóa constraint cũ (nếu có) và tạo mới
ALTER TABLE public.iot_devices
DROP CONSTRAINT IF EXISTS iot_devices_device_type_check;

ALTER TABLE public.iot_devices
ADD CONSTRAINT iot_devices_device_type_check
CHECK (device_type IN ('single', 'multi', 'camera'));

-- 6. Index cho cột provider để query theo loại nhanh hơn
CREATE INDEX IF NOT EXISTS idx_iot_devices_provider
ON public.iot_devices(provider);

-- ==============================================================================
-- VERIFICATION: Kiểm tra sau migration
-- Chạy query này để xác nhận cấu trúc mới:
--   SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'iot_devices'
--   ORDER BY ordinal_position;
-- ==============================================================================
