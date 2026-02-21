"""
AIC Persona Agent - FastAPI Application Entry Point.

Feature-based modular architecture:
  Each feature in app/features/ has its own router, service, and tools.
  Adding a new feature = adding a new folder, no existing code changes needed.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

# ── Feature Routers ──────────────────────────────────────
from app.features.auth.router import router as auth_router
from app.features.academic.router import router as academic_router
from app.features.agent.router import router as agent_router
from app.features.tasks.router import router as tasks_router

# Phase 3: Uncomment when knowledge feature is ready
# from app.features.knowledge.router import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup & shutdown."""
    settings = get_settings()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"🤖 LLM Provider: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")
    print(f"🔗 Supabase: {settings.SUPABASE_URL[:40]}...")
    yield
    print("👋 Shutting down...")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Agent cá nhân - Bộ não thứ hai",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Feature Routers ─────────────────────────
    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(academic_router, prefix="/api/academic", tags=["Academic"])
    app.include_router(agent_router, prefix="/api/agent", tags=["Agent"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
    # Phase 3:
    # app.include_router(knowledge_router, prefix="/api/knowledge", tags=["Knowledge"])

    # ── Health Check ─────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()
