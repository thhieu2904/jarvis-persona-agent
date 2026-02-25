"""
Knowledge feature: Service layer for vector-based knowledge retrieval.
Handles semantic search across notes (memories) and study materials.
"""

import logging
from supabase import Client

from app.features.knowledge.embedding import embed_text

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Vector search operations using pgvector."""

    def __init__(self, db: Client):
        self.db = db

    def search_notes_by_vector(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Semantic search across quick_notes using cosine similarity.

        Args:
            user_id: Owner of the notes.
            query: Natural language search query.
            top_k: Number of results to return.
            tags: Optional tag filter.

        Returns:
            List of matching notes sorted by relevance.
        """
        # Generate query vector
        query_vector = embed_text(query)

        # Use Supabase RPC for pgvector cosine similarity search
        # We need a DB function for this — use raw SQL via rpc
        result = self.db.rpc(
            "search_notes_by_embedding",
            {
                "query_embedding": query_vector,
                "match_user_id": user_id,
                "match_count": top_k,
                "filter_tags": tags,
            },
        ).execute()

        return result.data if result.data else []

    def search_materials_by_vector(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        subject: str | None = None,
    ) -> list[dict]:
        """Semantic search across study material chunks.

        Args:
            user_id: Owner of the materials.
            query: Natural language search query.
            top_k: Number of results to return.
            subject: Optional subject filter.

        Returns:
            List of matching chunks with material metadata.
        """
        query_vector = embed_text(query)

        result = self.db.rpc(
            "search_materials_by_embedding",
            {
                "query_embedding": query_vector,
                "match_user_id": user_id,
                "match_count": top_k,
                "filter_subject": subject,
            },
        ).execute()

        return result.data if result.data else []
