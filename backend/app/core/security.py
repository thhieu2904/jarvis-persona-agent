"""
Security utilities: Fernet encryption for school credentials, JWT handling, password hashing.
"""

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.config import get_settings

# ── Password Hashing ────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── Fernet Encryption (for school credentials) ──────────
def _get_fernet() -> Fernet:
    """Get Fernet instance from config secret key."""
    settings = get_settings()
    return Fernet(settings.ENCRYPTION_SECRET_KEY.encode())


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value using Fernet symmetric encryption.
    
    Used to encrypt MSSV and password before storing in DB.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode())


def decrypt_value(ciphertext: bytes) -> str:
    """Decrypt a Fernet-encrypted value back to string.
    
    Raises:
        InvalidToken: If the secret key is wrong or data is corrupted.
    """
    f = _get_fernet()
    return f.decrypt(ciphertext).decode()


def is_valid_encryption_key() -> bool:
    """Test if the current encryption key can decrypt data."""
    try:
        test_data = encrypt_value("test")
        decrypt_value(test_data)
        return True
    except Exception:
        return False


# ── JWT Token ────────────────────────────────────────────
def create_access_token(user_id: UUID, extra_data: dict | None = None) -> str:
    """Create a JWT access token for app authentication."""
    settings = get_settings()
    
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    if extra_data:
        payload.update(extra_data)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None if invalid."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
