"""
Notes feature: Schemas for request/response models.
"""

from pydantic import BaseModel
from datetime import datetime


class NoteCreate(BaseModel):
    """Request to create a new quick note."""
    content: str
    note_type: str = "note"  # note | idea | link | snippet
    tags: list[str] = []
    url: str | None = None
    related_subject: str | None = None


class NoteUpdate(BaseModel):
    """Request to update an existing note."""
    content: str | None = None
    note_type: str | None = None
    tags: list[str] | None = None
    url: str | None = None
    related_subject: str | None = None
    is_pinned: bool | None = None
    is_archived: bool | None = None


class NoteResponse(BaseModel):
    """Response model for a quick note."""
    id: str
    content: str
    note_type: str
    tags: list[str] = []
    url: str | None = None
    related_subject: str | None = None
    is_pinned: bool = False
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
