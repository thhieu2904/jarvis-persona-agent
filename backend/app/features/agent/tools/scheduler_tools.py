import logging
import json
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.database import get_supabase_admin_client

logger = logging.getLogger(__name__)

@tool
def schedule_automation(
    task_name: str,
    cron_expr: str,
    prompt_to_trigger: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """
    Hẹn giờ hệ thống tự động thực hiện một công việc AI trong tương lai (Tưới cây, bật bếp, gửi báo cáo).
    Sử dụng chuẩn mã Cron Expression (minute hour day month day_of_week) của UTC+7.
    Ví dụ: '0 17 * * *' (5h chiều mỗi ngày), '30 6 * * 1-5' (6h30 sáng sáng T2-T6).

    Args:
        task_name (str): Tên gợi nhớ của lịch hẹn (VD: "Bật nước nóng 6h tối").
        cron_expr (str): Chuỗi Cron biểu diễn chuẩn xác thời gian (VD: '0 18 * * *').
        prompt_to_trigger (str): Câu lệnh mớm cho AI chạy (VD: "Bật bình nóng lạnh lên").
    """
    if not user_id:
        return "Lỗi nội bộ Agent: Thiếu user_id để xác thực CSDL."
        
    try:
        supabase = get_supabase_admin_client()
        data = {
            "user_id": user_id,
            "name": task_name,
            "cron_expr": cron_expr,
            "prompt": prompt_to_trigger,
            "is_active": True
        }
        
        res = supabase.table("scheduled_prompts").insert(data).execute()
        if not res.data:
            return "Lỗi: Hệ thống Database từ chối lưu lịch hẹn giờ."
            
        return f"✅ Đã lên lịch thành công: '{task_name}' chạy với chu kỳ '{cron_expr}'. Hành động báo thức: '{prompt_to_trigger}'"
    except Exception as e:
        logger.error(f"Lỗi tạo schedule_automation: {e}")
        return f"❌ Lỗi khi thiết lập lịch: {e}"
