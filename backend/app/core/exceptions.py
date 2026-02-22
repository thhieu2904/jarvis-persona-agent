"""
Custom exception classes for unified error handling.
"""

from fastapi import HTTPException, status


class AppBaseError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class CredentialsNotFoundError(AppBaseError):
    """Raised when user hasn't connected their school account."""
    def __init__(self, message: str = "Chưa kết nối tài khoản trường"):
        super().__init__(
            message=message,
            detail="Vui lòng vào Cài đặt > Tài khoản trường để kết nối.",
        )


class SchoolAPIError(AppBaseError):
    """Raised when school API is down, times out, or returns invalid data."""
    def __init__(self, message: str = "Lỗi kết nối API trường"):
        super().__init__(
            message=message,
            detail="API trường có thể đang bảo trì. Dữ liệu cache cũ sẽ được sử dụng nếu có.",
        )


class ToolExecutionError(AppBaseError):
    """Raised when an agent tool fails during execution."""
    def __init__(self, tool_name: str, original_error: str):
        super().__init__(
            message=f"Tool '{tool_name}' thực thi thất bại",
            detail=original_error,
        )


class InvalidTokenError(AppBaseError):
    """Raised when JWT token is invalid or expired."""
    def __init__(self):
        super().__init__(
            message="Token không hợp lệ hoặc đã hết hạn",
            detail="Vui lòng đăng nhập lại.",
        )


# ── Utility: convert to HTTPException ────────────────────

def app_error_to_http(error: AppBaseError, status_code: int = 400) -> HTTPException:
    """Convert an AppBaseError to an HTTPException with consistent JSON body."""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error.message,
            "detail": error.detail,
            "type": type(error).__name__,
        },
    )
