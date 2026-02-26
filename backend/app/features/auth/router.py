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


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Gia hạn JWT token. Gọi khi token sắp hết hạn.
    
    Requires: valid Bearer token in Authorization header.
    Returns: new access_token with fresh expiry.
    """
    from uuid import UUID
    from app.core.security import create_access_token

    # Verify user still exists
    result = db.table("users").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")

    new_token = create_access_token(UUID(user_id))
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "user": UserResponse(**result.data),
    }
