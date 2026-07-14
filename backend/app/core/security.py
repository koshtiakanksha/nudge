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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

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

# Process-local cache of user ids we've already confirmed/created a row
# for, so we're not running an INSERT ... ON CONFLICT on every single
# authenticated request. Safe to lose on restart -- worst case we just
# redo one no-op insert.
_ensured_user_ids: set[uuid.UUID] = set()


async def _ensure_user_row(db: AsyncSession, user_id: uuid.UUID, email: str | None) -> None:
    """
    Guarantees a `users` row exists for this id before the request
    proceeds. Almost every endpoint in this codebase inserts rows that
    foreign-key onto users.id (plaid_items, transactions, budgets, ...)
    without checking the user row exists first -- only a couple of
    endpoints defensively created it themselves. That meant any first
    action other than visiting Settings (which happened to create it)
    would 500 with a ForeignKeyViolationError. Fixing it once here, in
    the dependency every authenticated route already goes through,
    instead of patching each endpoint individually.
    """
    if user_id in _ensured_user_ids:
        return
    stmt = (
        pg_insert(User)
        .values(id=user_id, email=email or f"{user_id}@local.test")
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(stmt)
    await db.commit()
    _ensured_user_ids.add(user_id)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    # Mock mode: no Supabase JWT secret configured -> single dev user,
    # no token required. Lets the whole app run locally without Supabase.
    if not settings.supabase_jwt_secret:
        await _ensure_user_row(db, DEV_USER_ID, "dev@local.test")
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

    user_id = uuid.UUID(sub)
    await _ensure_user_row(db, user_id, payload.get("email"))
    return CurrentUser(id=user_id, email=payload.get("email"))
