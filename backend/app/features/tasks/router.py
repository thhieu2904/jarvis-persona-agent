"""
Tasks feature: API routes for task management.
"""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_db, get_current_user_id

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: str | None = None
    priority: str = "medium"  # low, medium, high


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None  # pending, in_progress, done
    is_pinned: bool | None = None


@router.get("/")
async def list_tasks(
    status: str = "all",
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """List all tasks for the current user."""
    query = db.table("tasks_reminders").select("*").eq("user_id", user_id)
    
    if status != "all":
        query = query.eq("status", status)

    result = query.order("is_pinned", desc=True).order("due_date", desc=False).execute()
    return {"data": result.data}


@router.post("/")
async def create_task(
    data: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Create a new task/reminder."""
    result = (
        db.table("tasks_reminders")
        .insert({
            "user_id": user_id,
            "title": data.title,
            "description": data.description,
            "due_date": data.due_date,
            "priority": data.priority,
            "status": "pending",
            "source": "manual",
        })
        .execute()
    )
    return {"data": result.data[0]}


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Update an existing task."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    result = (
        db.table("tasks_reminders")
        .update(update_data)
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )
    return {"data": result.data[0] if result.data else None}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Delete a task."""
    db.table("tasks_reminders").delete().eq("id", task_id).eq("user_id", user_id).execute()
    return {"message": "Task đã được xóa"}
