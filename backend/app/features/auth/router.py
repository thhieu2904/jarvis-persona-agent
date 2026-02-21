"""
Auth feature: API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.dependencies import get_db, get_current_user_id
from app.features.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UpdateProfileRequest,
    UserResponse,
    MessageResponse,
)
from app.features.auth.service import AuthService

router = APIRouter()


@router.post("/register", response_model=LoginResponse)
async def register(data: RegisterRequest, db: Client = Depends(get_db)):
    """Đăng ký tài khoản mới."""
    service = AuthService(db)
    try:
        result = await service.register(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: Client = Depends(get_db)):
    """Đăng nhập và nhận JWT token."""
    service = AuthService(db)
    try:
        result = await service.login(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Lấy thông tin profile."""
    service = AuthService(db)
    return await service.get_profile(user_id)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Cập nhật thông tin profile."""
    service = AuthService(db)
    return await service.update_profile(user_id, data.model_dump())
