"""
Application configuration using Pydantic Settings.
All config is loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "aic-persona-agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"  # comma-separated

    # ── Supabase ─────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon/public key
    SUPABASE_SERVICE_KEY: str = ""  # service_role key (for admin ops)

    # ── Security ─────────────────────────────────────────
    ENCRYPTION_SECRET_KEY: str  # Fernet key for encrypting school credentials
    JWT_SECRET_KEY: str  # JWT signing key
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440  # 24 hours

    # ── LLM (Provider-Agnostic) ──────────────────────────
    LLM_PROVIDER: str = "gemini"  # gemini | openai | groq
    LLM_MODEL: str = "gemini-3-flash-preview"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 1.0  # Gemini 3 docs: keep at 1.0, lower causes looping

    # ── Image Model (future: avatar, image generation) ───
    IMAGE_MODEL: str = "gemini-3-pro-image-preview"  # Nano Banana Pro
    IMAGE_MODEL_ENABLED: bool = True

    # ── Embedding ────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = 768

    # ── School API ───────────────────────────────────────
    SCHOOL_API_BASE_URL: str = "https://ttsv.tvu.edu.vn/public/api"
    SCHOOL_CACHE_TTL_HOURS: int = 24  # Cache expiry
    SCHOOL_API_TIMEOUT: int = 30  # HTTP timeout in seconds

    # ── Tavily (AI Search Engine) ────────────────────────
    TAVILY_API_KEY: str = ""  # Free tier: 1000 req/month

    # ── OpenWeather (Weather API) ────────────────────────
    OPENWEATHER_API_KEY: str = ""

    # ── Zalo Bot (Push Notifications) ────────────────────
    ZALO_BOT_TOKEN: str = ""  # Token from Zalo Bot Creator
    ZALO_CHAT_ID: str = ""    # Your personal Zalo chat ID

    # ── Agent ────────────────────────────────────────────
    AGENT_RECURSION_LIMIT: int = 25  # Max graph steps (agent+tool nodes per turn)
    AGENT_MEMORY_WINDOW_SIZE: int = 7
    AGENT_SUMMARY_THRESHOLD: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (singleton)."""
    return Settings()
