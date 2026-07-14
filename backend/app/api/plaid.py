import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user, encrypt_token, decrypt_token
from app.db.session import get_db
from app.models.plaid_item import PlaidItem
from app.models.transaction import Transaction
from app.schemas.plaid import ExchangePublicTokenRequest, LinkTokenResponse, PlaidItemOut, SyncResponse
from app.services.claude_service import claude_service
from app.services.plaid_service import plaid_service

router = APIRouter(prefix="/plaid", tags=["plaid"])


@router.post("/link-token", response_model=LinkTokenResponse)
async def create_link_token(current: CurrentUser = Depends(get_current_user)):
    result = plaid_service.create_link_token(str(current.id))
    return result


@router.post("/exchange-token", response_model=PlaidItemOut)
async def exchange_public_token(
    payload: ExchangePublicTokenRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exchange = plaid_service.exchange_public_token(payload.public_token)
    accounts = plaid_service.get_accounts(exchange["access_token"])

    item = PlaidItem(
        user_id=current.id,
        item_id=exchange["item_id"],
        access_token_encrypted=encrypt_token(exchange["access_token"]),
        institution_name=payload.institution_name or "Linked Bank",
        accounts=accounts,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return PlaidItemOut(
        id=str(item.id),
        institution_name=item.institution_name,
        accounts=item.accounts,
        last_synced_at=None,
    )


@router.get("/items", response_model=list[PlaidItemOut])
async def list_items(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlaidItem).where(PlaidItem.user_id == current.id))
    items = result.scalars().all()
    return [
        PlaidItemOut(
            id=str(i.id),
            institution_name=i.institution_name,
            accounts=i.accounts,
            last_synced_at=i.last_synced_at.isoformat() if i.last_synced_at else None,
        )
        for i in items
    ]


@router.post("/sync/{item_id}", response_model=SyncResponse)
async def sync_item(
    item_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlaidItem).where(PlaidItem.id == item_id, PlaidItem.user_id == current.id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Plaid item not found")

    access_token = decrypt_token(item.access_token_encrypted)
    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    raw_txns = plaid_service.get_transactions(access_token, start_date, end_date)

    new_count = 0
    for t in raw_txns:
        nudge_category = claude_service.categorize_transaction(t["merchant_name"], t.get("category"))

        stmt = (
            pg_insert(Transaction)
            .values(
                user_id=current.id,
                plaid_transaction_id=t["plaid_transaction_id"],
                amount=t["amount"],
                date=t["date"],
                merchant_name=t["merchant_name"],
                category=t.get("category"),
                nudge_category=nudge_category,
                account_id=t.get("account_id"),
            )
            .on_conflict_do_nothing(index_elements=["plaid_transaction_id", "date"])
        )
        res = await db.execute(stmt)
        if res.rowcount:
            new_count += 1

    item.accounts = plaid_service.get_accounts(access_token)
    from datetime import datetime
    item.last_synced_at = datetime.utcnow()

    await db.commit()

    return SyncResponse(
        new_transactions=new_count,
        accounts_synced=len(item.accounts),
        mock_mode=plaid_service.mock_mode,
    )
