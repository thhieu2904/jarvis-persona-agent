"""
Auth feature: Business logic for user registration, login, and profile management.
"""

from uuid import UUID
from supabase import Client

from app.core.security import hash_password, verify_password, create_access_token
from app.features.auth.schemas import RegisterRequest, LoginRequest, UserResponse


class AuthService:
    """Handles user authentication and profile management."""

    def __init__(self, db: Client):
        self.db = db

    async def register(self, data: RegisterRequest) -> dict:
        """Register a new user.
        
        Returns:
            dict with access_token and user data.
        
        Raises:
            ValueError: If email already exists.
        """
        # Check if email already exists
        existing = (
            self.db.table("users")
            .select("id")
            .eq("email", data.email)
            .execute()
        )
        if existing.data:
            raise ValueError("Email đã được sử dụng")

        # Create user
        user_data = {
            "full_name": data.full_name,
            "email": data.email,
            "password_hash": hash_password(data.password),
            "student_id": data.student_id,
            "preferences": {},
            "agent_config": {},
        }

        result = self.db.table("users").insert(user_data).execute()
        user = result.data[0]

        # Generate JWT
        token = create_access_token(UUID(user["id"]))

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse(**user),
        }

    async def login(self, data: LoginRequest) -> dict:
        """Authenticate user and return JWT token.
        
        Raises:
            ValueError: If credentials are invalid.
        """
        result = (
            self.db.table("users")
            .select("*")
            .eq("email", data.email)
            .execute()
        )

        if not result.data:
            raise ValueError("Email hoặc mật khẩu không đúng")

        user = result.data[0]

        if not verify_password(data.password, user["password_hash"]):
            raise ValueError("Email hoặc mật khẩu không đúng")

        token = create_access_token(UUID(user["id"]))

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse(**user),
        }

    async def get_profile(self, user_id: str) -> UserResponse:
        """Get user profile by ID."""
        result = (
            self.db.table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return UserResponse(**result.data)

    async def update_profile(self, user_id: str, data: dict) -> UserResponse:
        """Update user profile fields."""
        # Filter out None values
        update_data = {k: v for k, v in data.items() if v is not None}
        
        if not update_data:
            return await self.get_profile(user_id)

        result = (
            self.db.table("users")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )
        return UserResponse(**result.data[0])
