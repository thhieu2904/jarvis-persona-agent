"""
Calendar feature: API routes for event management.
"""

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_db, get_current_user_id
from app.features.calendar.schemas import EventCreate, EventUpdate
from app.features.calendar.service import CalendarService

router = APIRouter()


@router.get("/")
async def list_events(
    date: str | None = None,
    event_type: str | None = None,
    days_ahead: int = 7,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """List events within a date range."""
    service = CalendarService(db)
    events = service.get_events(user_id, date, event_type, days_ahead)
    return {"data": events}


@router.post("/")
async def create_event(
    data: EventCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Create a new calendar event."""
    service = CalendarService(db)
    event = service.create_event(
        user_id=user_id,
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        description=data.description,
        event_type=data.event_type,
        is_all_day=data.is_all_day,
        location=data.location,
        source="manual",
        reminder_minutes=data.reminder_minutes,
    )
    return {"data": event}


@router.put("/{event_id}")
async def update_event(
    event_id: str,
    data: EventUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Update an existing event."""
    service = CalendarService(db)
    event = service.update_event(user_id, event_id, data.model_dump())
    return {"data": event}


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Delete an event."""
    service = CalendarService(db)
    service.delete_event(user_id, event_id)
    return {"message": "Sự kiện đã được xóa"}
