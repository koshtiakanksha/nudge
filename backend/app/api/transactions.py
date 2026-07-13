import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionListResponse, TransactionOut, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Transaction).where(Transaction.user_id == current.id)
    count_query = select(func.count()).select_from(Transaction).where(Transaction.user_id == current.id)

    if category:
        base_query = base_query.where(Transaction.nudge_category == category)
        count_query = count_query.where(Transaction.nudge_category == category)

    total = (await db.execute(count_query)).scalar_one()

    result = await db.execute(
        base_query.order_by(Transaction.date.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    return TransactionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current.id)
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)

    await db.commit()
    await db.refresh(txn)
    return txn
