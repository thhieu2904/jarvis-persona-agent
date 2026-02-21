"""
Notes feature: API routes for quick note management.
"""

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_db, get_current_user_id
from app.features.notes.schemas import NoteCreate, NoteUpdate
from app.features.notes.service import NotesService

router = APIRouter()


@router.get("/")
async def list_notes(
    include_archived: bool = False,
    pinned_only: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """List all quick notes for the current user."""
    service = NotesService(db)
    notes = service.list_notes(user_id, include_archived, pinned_only)
    return {"data": notes}


@router.post("/")
async def create_note(
    data: NoteCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Create a new quick note."""
    service = NotesService(db)
    note = service.create_note(
        user_id=user_id,
        content=data.content,
        note_type=data.note_type,
        tags=data.tags,
        url=data.url,
        related_subject=data.related_subject,
    )
    return {"data": note}


@router.post("/search")
async def search_notes(
    query: str,
    tags: list[str] | None = None,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Search notes by keyword and/or tags."""
    service = NotesService(db)
    notes = service.search_notes(user_id, query, tags)
    return {"data": notes}


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    data: NoteUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Update an existing note."""
    service = NotesService(db)
    note = service.update_note(user_id, note_id, data.model_dump())
    return {"data": note}


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Archive (soft delete) a note."""
    service = NotesService(db)
    service.delete_note(user_id, note_id)
    return {"message": "Ghi chú đã được lưu trữ"}
