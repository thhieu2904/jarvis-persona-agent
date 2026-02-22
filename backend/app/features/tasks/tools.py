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
            "id": t["id"],
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


@tool
def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Cập nhật thông tin task đã tồn tại.
    Dùng khi chủ nhân muốn sửa tiêu đề, mô tả, deadline, ưu tiên hoặc trạng thái.
    Trước khi gọi, hãy dùng list_tasks() để lấy task_id cần sửa.

    Args:
        task_id: ID của task cần cập nhật (lấy từ list_tasks)
        title: Tiêu đề mới (None = giữ nguyên)
        description: Mô tả mới (None = giữ nguyên)
        due_date: Deadline mới, YYYY-MM-DD (None = giữ nguyên)
        priority: Ưu tiên mới: "low", "medium", "high" (None = giữ nguyên)
        status: Trạng thái mới: "pending", "done" (None = giữ nguyên)

    Returns:
        Xác nhận đã cập nhật task.
    """
    db = get_db()
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if due_date is not None:
        update_data["due_date"] = due_date
    if priority is not None:
        update_data["priority"] = priority
    if status is not None:
        update_data["status"] = status

    if not update_data:
        return json.dumps({
            "status": "error",
            "message": "Không có thông tin nào để cập nhật.",
        }, ensure_ascii=False)

    result = (
        db.table("tasks_reminders")
        .update(update_data)
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy task với ID '{task_id}'.",
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "message": f"Đã cập nhật task '{result.data[0]['title']}'.",
        "updated_fields": list(update_data.keys()),
    }, ensure_ascii=False)


@tool
def complete_task(
    task_id: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Đánh dấu task đã hoàn thành.
    Dùng khi chủ nhân nói "xong rồi", "done", "hoàn thành task X".
    Trước khi gọi, dùng list_tasks() để xác định đúng task_id.

    Args:
        task_id: ID của task cần đánh dấu hoàn thành

    Returns:
        Xác nhận task đã được hoàn thành.
    """
    db = get_db()
    result = (
        db.table("tasks_reminders")
        .update({"status": "done"})
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy task với ID '{task_id}'.",
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "message": f"✅ Task '{result.data[0]['title']}' đã hoàn thành!",
    }, ensure_ascii=False)


@tool
def delete_task(
    task_id: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xóa task khỏi danh sách.
    Chỉ xóa khi chủ nhân yêu cầu rõ ràng. Hỏi xác nhận trước khi xóa.
    Trước khi gọi, dùng list_tasks() để xác định đúng task_id.

    Args:
        task_id: ID của task cần xóa

    Returns:
        Xác nhận task đã bị xóa.
    """
    db = get_db()
    # Get task info before deleting
    info = (
        db.table("tasks_reminders")
        .select("title")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not info.data:
        return json.dumps({
            "status": "error",
            "message": f"Không tìm thấy task với ID '{task_id}'.",
        }, ensure_ascii=False)

    title = info.data[0]["title"]

    db.table("tasks_reminders").delete().eq("id", task_id).eq("user_id", user_id).execute()

    return json.dumps({
        "status": "success",
        "message": f"Đã xóa task '{title}'.",
    }, ensure_ascii=False)


# Export all tools for the agent graph
tasks_tools = [create_task, list_tasks, update_task, complete_task, delete_task]
