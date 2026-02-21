"""
Tasks feature: Agent tools for task/reminder management.
"""

import json
from datetime import datetime
from langchain_core.tools import tool


@tool
def create_task(title: str, due_date: str | None = None, priority: str = "medium", description: str = "") -> str:
    """Tạo task mới hoặc nhắc nhở cho chủ nhân.
    
    Args:
        title: Tiêu đề task (bắt buộc)
        due_date: Hạn hoàn thành (format: YYYY-MM-DD). None = không có deadline.
        priority: Mức ưu tiên: "low", "medium", "high"
        description: Mô tả chi tiết (tùy chọn)
    
    Returns:
        Xác nhận task đã được tạo.
    """
    # TODO: Phase 2 - Save to tasks_reminders table
    return json.dumps({
        "status": "mock",
        "message": f"Đã tạo task: '{title}'",
        "task": {
            "title": title,
            "due_date": due_date,
            "priority": priority,
            "description": description,
        },
    }, ensure_ascii=False)


@tool
def list_tasks(status: str = "pending") -> str:
    """Xem danh sách các tasks và nhắc nhở.
    
    Args:
        status: Lọc theo trạng thái: "pending", "done", "all"
    
    Returns:
        Danh sách tasks bao gồm: tiêu đề, hạn, ưu tiên, trạng thái.
    """
    # TODO: Phase 2 - Query from tasks_reminders table
    return json.dumps({
        "status": "mock",
        "message": "Chưa có task nào.",
        "tasks": [],
    }, ensure_ascii=False)
