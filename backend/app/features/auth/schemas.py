"""
Auth feature: Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


# ── Requests ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    student_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    student_id: str | None = None
    avatar_url: str | None = None
    preferences: dict | None = None
    agent_config: dict | None = None


# ── Responses ────────────────────────────────────────────
class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    student_id: str | None = None
    avatar_url: str | None = None
    preferences: dict = {}
    agent_config: dict = {}
    created_at: datetime | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
