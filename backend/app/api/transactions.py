import csv
import io
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionListResponse, TransactionOut, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _resolve_date_range(range_preset: str | None, start_date: date | None, end_date: date | None) -> tuple[date | None, date | None]:
    """Explicit start_date/end_date win if given; otherwise a named preset
    resolves to a range anchored on today. Returns (None, None) for 'all'
    or when nothing was specified."""
    if start_date or end_date:
        return start_date, end_date

    today = date.today()
    if range_preset == "this_month":
        return today.replace(day=1), today
    if range_preset == "last_3_months":
        return today - timedelta(days=90), today
    if range_preset == "ytd":
        return today.replace(month=1, day=1), today
    if range_preset == "last_year":
        return today - timedelta(days=365), today
    return None, None


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    range_preset: str | None = Query(None, description="this_month | last_3_months | ytd | last_year"),
    start_date: date | None = None,
    end_date: date | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_start, resolved_end = _resolve_date_range(range_preset, start_date, end_date)

    base_query = select(Transaction).where(Transaction.user_id == current.id)
    count_query = select(func.count()).select_from(Transaction).where(Transaction.user_id == current.id)

    if category:
        base_query = base_query.where(Transaction.nudge_category == category)
        count_query = count_query.where(Transaction.nudge_category == category)
    if resolved_start:
        base_query = base_query.where(Transaction.date >= resolved_start)
        count_query = count_query.where(Transaction.date >= resolved_start)
    if resolved_end:
        base_query = base_query.where(Transaction.date <= resolved_end)
        count_query = count_query.where(Transaction.date <= resolved_end)

    total = (await db.execute(count_query)).scalar_one()

    result = await db.execute(
        base_query.order_by(Transaction.date.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()

    return TransactionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/export")
async def export_transactions(
    category: str | None = None,
    range_preset: str | None = Query(None, description="this_month | last_3_months | ytd | last_year"),
    start_date: date | None = None,
    end_date: date | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV export of everything list_transactions would return, unpaginated
    -- for cross-checking forecast/anomaly output against the raw data."""
    resolved_start, resolved_end = _resolve_date_range(range_preset, start_date, end_date)

    query = select(Transaction).where(Transaction.user_id == current.id)
    if category:
        query = query.where(Transaction.nudge_category == category)
    if resolved_start:
        query = query.where(Transaction.date >= resolved_start)
    if resolved_end:
        query = query.where(Transaction.date <= resolved_end)

    result = await db.execute(query.order_by(Transaction.date.desc()))
    txns = result.scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "merchant_name", "category", "amount", "is_recurring", "is_ignored"])
    for t in txns:
        writer.writerow([
            t.date.isoformat(), t.merchant_name or "", t.nudge_category or "",
            float(t.amount), t.is_recurring, t.is_ignored,
        ])
    buffer.seek(0)

    filename = f"nudge-transactions-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
