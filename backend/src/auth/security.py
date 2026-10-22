"""Password hashing, JWT session tokens, and reversible encryption for
per-user Binance credentials (bcrypt is one-way, can't be used for those)."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
from cryptography.fernet import Fernet

from ..config import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(days=7)
COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: UUID) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_TTL}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None


def encrypt_secret(plaintext: str) -> str:
    return Fernet(settings.field_encryption_key.encode()).encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    return Fernet(settings.field_encryption_key.encode()).decrypt(token.encode()).decode()
