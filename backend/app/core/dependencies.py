"""
FastAPI dependency injection functions.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.database import get_supabase_client
from app.core.security import decode_access_token

# Bearer token scheme for Swagger UI
bearer_scheme = HTTPBearer()


def get_db() -> Client:
    """Dependency: get Supabase client."""
    return get_supabase_client()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Dependency: extract and validate user_id from JWT token.
    
    Returns:
        str: The user's UUID as string.
    
    Raises:
        HTTPException 401: If token is invalid or expired.
    """
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa thông tin người dùng",
        )
    
    return user_id
