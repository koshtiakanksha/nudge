"""
Security helpers:
1. Fernet symmetric encryption for Plaid access tokens at rest.
2. Supabase JWT verification for authenticating API requests.

In mock mode (no TOKEN_ENCRYPTION_KEY / SUPABASE_JWT_SECRET set), both
fall back to safe no-op/dev behavior so local dev doesn't require Supabase.
"""
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Token encryption (Plaid access tokens)
# ---------------------------------------------------------------------------
def _get_fernet() -> Fernet | None:
    if not settings.token_encryption_key:
        return None
    return Fernet(settings.token_encryption_key.encode())


def encrypt_token(raw: str) -> str:
    fernet = _get_fernet()
    if fernet is None:
        # Dev fallback: store as a clearly-marked plaintext value. Never do
        # this in production -- set TOKEN_ENCRYPTION_KEY.
        return f"plaintext::{raw}"
    return fernet.encrypt(raw.encode()).decode()


def decrypt_token(stored: str) -> str:
    if stored.startswith("plaintext::"):
        return stored[len("plaintext::"):]
    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY not set but an encrypted token was found.")
    return fernet.decrypt(stored.encode()).decode()


# ---------------------------------------------------------------------------
# Auth: verify Supabase-issued JWT, extract user id
# ---------------------------------------------------------------------------
class CurrentUser:
    def __init__(self, id: uuid.UUID, email: str | None):
        self.id = id
        self.email = email


DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> CurrentUser:
    # Mock mode: no Supabase JWT secret configured -> single dev user,
    # no token required. Lets the whole app run locally without Supabase.
    if not settings.supabase_jwt_secret:
        return CurrentUser(id=DEV_USER_ID, email="dev@local.test")

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    return CurrentUser(id=uuid.UUID(sub), email=payload.get("email"))
