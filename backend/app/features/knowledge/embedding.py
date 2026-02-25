"""
Knowledge feature: Embedding utility functions.
Wraps the LLM provider's embedding model for use across the app.
"""

import logging
from app.core.llm_provider import create_embeddings

logger = logging.getLogger(__name__)

# Singleton embedding model (lazy init)
_embeddings_model = None


def get_embeddings_model():
    """Get or create the shared embeddings model instance."""
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = create_embeddings()
    return _embeddings_model


def embed_text(text: str) -> list[float]:
    """Generate embedding vector for a single text string.

    Args:
        text: The text to embed.

    Returns:
        A list of floats (3072 dimensions for Gemini).
    """
    from app.config import get_settings
    settings = get_settings()
    model = get_embeddings_model()
    vector = model.embed_query(text)
    # Truncate to the desired dimensionality (e.g. 768)
    return vector[:settings.EMBEDDING_DIMENSIONS]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts (batch).

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    from app.config import get_settings
    settings = get_settings()
    model = get_embeddings_model()
    vectors = model.embed_documents(texts)
    dim = settings.EMBEDDING_DIMENSIONS
    return [v[:dim] for v in vectors]
