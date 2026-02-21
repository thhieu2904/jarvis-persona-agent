"""
Calendar feature: Schemas for request/response models.
"""

from pydantic import BaseModel
from datetime import datetime


class EventCreate(BaseModel):
    """Request to create a new calendar event."""
    title: str
    description: str | None = None
    event_type: str = "personal"  # personal | club | study_group | birthday | other
    start_time: str  # ISO format: YYYY-MM-DDTHH:MM
    end_time: str | None = None
    is_all_day: bool = False
    location: str | None = None
    reminder_minutes: int | None = None


class EventUpdate(BaseModel):
    """Request to update an existing event."""
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_all_day: bool | None = None
    location: str | None = None
    reminder_minutes: int | None = None


class EventResponse(BaseModel):
    """Response model for a calendar event."""
    id: str
    title: str
    description: str | None = None
    event_type: str
    start_time: datetime
    end_time: datetime | None = None
    is_all_day: bool = False
    location: str | None = None
    source: str = "user"
    reminder_minutes: int | None = None
    created_at: datetime
    updated_at: datetime
