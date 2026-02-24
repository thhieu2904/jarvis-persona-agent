-- ==============================================================================
-- Migration script for IoT Phase 2.3
-- Adds `iot_devices` table and sets up proper indexes for fast ILIKE searches.
-- Execute this script in your Supabase SQL Editor.
-- ==============================================================================

-- Bật extension unaccent để hỗ trợ tìm kiếm không dấu
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS public.iot_devices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    mac_address TEXT,
    is_active BOOLEAN DEFAULT true,
    device_id TEXT NOT NULL,
    local_key TEXT NOT NULL,
    version NUMERIC DEFAULT 3.3,
    device_type TEXT DEFAULT 'single' CHECK (device_type IN ('single', 'multi')),
    dps_mapping JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Index cho phép tìm kiếm thiết bị của auth user nhanh hơn
CREATE INDEX IF NOT EXISTS idx_iot_devices_user_id ON public.iot_devices(user_id);

-- GIN Index (tùy chọn) trên cột dps_mapping giúp query object JSONB cực nhanh nếu cần so sánh cấu trúc mạnh hơn
CREATE INDEX IF NOT EXISTS idx_iot_devices_dps_mapping ON public.iot_devices USING gin (dps_mapping);

-- Hàm trigger để tự động update cột updated_at
CREATE OR REPLACE FUNCTION update_iot_devices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_iot_devices_updated_at
BEFORE UPDATE ON public.iot_devices
FOR EACH ROW
EXECUTE FUNCTION update_iot_devices_updated_at();

-- RLS (Row Level Security) - chỉ User thao tác mới đọc được thiết bị
ALTER TABLE public.iot_devices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own IoT devices"
ON public.iot_devices
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ==============================================================================
-- Table: scheduled_prompts
-- Dùng cho cơ chế AI Scheduler. Agent sẽ lưu câu lệnh vào đây kèm mã cron.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.scheduled_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    cron_expr TEXT NOT NULL,
    prompt TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

ALTER TABLE public.scheduled_prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own scheduled prompts"
ON public.scheduled_prompts
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
