"""
Tasks feature: Agent tools for task/reminder management.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
from typing import Annotated
from datetime import datetime
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db


@tool
def create_task(
    title: str,
    due_date: str | None = None,
    priority: str = "medium",
    description: str = "",
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tạo task mới hoặc nhắc nhở cho chủ nhân.
    
    Args:
        title: Tiêu đề task (bắt buộc)
        due_date: Hạn hoàn thành (format: YYYY-MM-DD). None = không có deadline.
        priority: Mức ưu tiên: "low", "medium", "high"
        description: Mô tả chi tiết (tùy chọn)
    
    Returns:
        Xác nhận task đã được tạo.
    """
    db = get_db()
    result = (
        db.table("tasks_reminders")
        .insert({
            "user_id": user_id,
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority,
            "status": "pending",
            "source": "agent",
        })
        .execute()
    )
    task = result.data[0]

    return json.dumps({
        "status": "success",
        "message": f"Đã tạo task: '{title}'",
        "task_id": task["id"],
        "due_date": due_date,
        "priority": priority,
    }, ensure_ascii=False)


@tool
def list_tasks(
    status: str = "pending",
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xem danh sách các tasks và nhắc nhở của chủ nhân.
    
    Args:
        status: Lọc theo trạng thái: "pending", "done", "all"
    
    Returns:
        Danh sách tasks bao gồm: tiêu đề, hạn, ưu tiên, trạng thái.
    """
    db = get_db()
    query = (
        db.table("tasks_reminders")
        .select("*")
        .eq("user_id", user_id)
    )

    if status != "all":
        query = query.eq("status", status)

    result = query.order("due_date", desc=False).execute()

    if not result.data:
        return json.dumps({
            "status": "success",
            "message": "Chưa có task nào." if status == "all" else f"Không có task nào ở trạng thái '{status}'.",
            "tasks": [],
        }, ensure_ascii=False)

    tasks = []
    for t in result.data:
        tasks.append({
            "title": t["title"],
            "due_date": t.get("due_date"),
            "priority": t.get("priority", "medium"),
            "status": t["status"],
            "description": t.get("description", ""),
        })

    return json.dumps({
        "status": "success",
        "message": f"Có {len(tasks)} task(s).",
        "tasks": tasks,
    }, ensure_ascii=False)


# Export all tools for the agent graph
tasks_tools = [create_task, list_tasks]
