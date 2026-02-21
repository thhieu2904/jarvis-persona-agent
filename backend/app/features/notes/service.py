"""
Notes feature: Service layer for quick notes management.
"""

from supabase import Client


class NotesService:
    """CRUD operations for quick notes with keyword search."""

    def __init__(self, db: Client):
        self.db = db

    def create_note(
        self,
        user_id: str,
        content: str,
        note_type: str = "note",
        tags: list[str] | None = None,
        url: str | None = None,
        related_subject: str | None = None,
    ) -> dict:
        """Create a new quick note (embedding = NULL, filled by bg job later)."""
        insert_data = {
            "user_id": user_id,
            "content": content,
            "note_type": note_type,
            "tags": tags or [],
            "url": url,
            "related_subject": related_subject,
        }
        result = self.db.table("quick_notes").insert(insert_data).execute()
        return result.data[0]

    def list_notes(
        self,
        user_id: str,
        include_archived: bool = False,
        pinned_only: bool = False,
    ) -> list[dict]:
        """List notes for a user, ordered by newest first."""
        query = (
            self.db.table("quick_notes")
            .select("*")
            .eq("user_id", user_id)
        )

        if not include_archived:
            query = query.eq("is_archived", False)

        if pinned_only:
            query = query.eq("is_pinned", True)

        result = query.order("created_at", desc=True).execute()
        return result.data

    def search_notes(self, user_id: str, query: str, tags: list[str] | None = None) -> list[dict]:
        """Search notes by keyword (ILIKE) and/or tags.
        
        Phase 2: Simple keyword search.
        Phase 2.5: Will add cosine similarity on embedding column.
        """
        db_query = (
            self.db.table("quick_notes")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_archived", False)
            .ilike("content", f"%{query}%")
        )

        if tags:
            # PostgreSQL array contains operator
            db_query = db_query.contains("tags", tags)

        result = db_query.order("created_at", desc=True).limit(10).execute()
        return result.data

    def update_note(self, user_id: str, note_id: str, update_data: dict) -> dict | None:
        """Update an existing note."""
        # Filter out None values
        clean_data = {k: v for k, v in update_data.items() if v is not None}
        if not clean_data:
            return None

        result = (
            self.db.table("quick_notes")
            .update(clean_data)
            .eq("id", note_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_note(self, user_id: str, note_id: str) -> None:
        """Soft delete: archive the note instead of hard delete."""
        self.db.table("quick_notes").update(
            {"is_archived": True}
        ).eq("id", note_id).eq("user_id", user_id).execute()
