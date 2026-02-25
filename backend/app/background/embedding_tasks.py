"""
Background tasks for processing embeddings.
Moved here for better architecture and dashboard tracking.
"""

import logging
from app.core.database import get_supabase_client
from app.features.knowledge.embedding import embed_text

logger = logging.getLogger(__name__)


def process_note_embedding(note_id: str, content: str):
    """Generate embedding vector for a note and update DB status.
    Designed to run as a FastAPI BackgroundTask.
    Tracks status: pending -> success / failed.
    """
    db = get_supabase_client()
    try:
        # Mark as generating (in case it takes time)
        db.table("quick_notes").update({
            "embedding_status": "processing"
        }).eq("id", note_id).execute()

        # Generate vector
        vector = embed_text(content)

        # Update vector and status
        db.table("quick_notes").update({
            "embedding": vector,
            "embedding_status": "success"
        }).eq("id", note_id).execute()

        logger.info(f"✅ Background Task: Embedded note {note_id} ({len(vector)} dims)")

    except Exception as e:
        logger.error(f"❌ Background Task: Failed to embed note {note_id}: {e}")
        # Mark as failed so dashboard can show it and allow retry
        db.table("quick_notes").update({
            "embedding_status": "failed"
        }).eq("id", note_id).execute()
