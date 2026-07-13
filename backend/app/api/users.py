import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserProfileOut, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


async def _get_or_create_user(db: AsyncSession, current: CurrentUser) -> User:
    result = await db.execute(select(User).where(User.id == current.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=current.id, email=current.email or f"{current.id}@local.test")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("/me", response_model=UserProfileOut)
async def get_me(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await _get_or_create_user(db, current)
    return user


@router.patch("/me", response_model=UserProfileOut)
async def update_me(
    payload: UserProfileUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_create_user(db, current)

    data = payload.model_dump(exclude_unset=True)
    if "cards" in data and data["cards"] is not None:
        data["cards"] = [c if isinstance(c, dict) else c.model_dump() for c in data["cards"]]

    for field, value in data.items():
        setattr(user, field, value)

    if user.monthly_income is not None and user.spend_ceiling is not None:
        user.onboarding_complete = True

    await db.commit()
    await db.refresh(user)
    return user
