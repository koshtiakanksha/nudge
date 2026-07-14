from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.security import decrypt_token
from app.db.session import AsyncSessionLocal
from app.models.plaid_item import PlaidItem
from app.models.transaction import Transaction
from app.services.claude_service import claude_service
from app.services.plaid_service import plaid_service
from app.tasks.async_bridge import run_async
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.sync_tasks.sync_all_plaid_items")
def sync_all_plaid_items():
    return run_async(_sync_all_plaid_items)


async def _sync_all_plaid_items():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PlaidItem))
        items = result.scalars().all()

        total_new = 0
        for item in items:
            total_new += await _sync_one_item(db, item)

        return {"items_synced": len(items), "new_transactions": total_new}


async def _sync_one_item(db, item: PlaidItem) -> int:
    access_token = decrypt_token(item.access_token_encrypted)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)  # nightly sync only needs a short lookback

    raw_txns = plaid_service.get_transactions(access_token, start_date, end_date)

    new_count = 0
    for t in raw_txns:
        nudge_category = claude_service.categorize_transaction(t["merchant_name"], t.get("category"))
        stmt = (
            pg_insert(Transaction)
            .values(
                user_id=item.user_id,
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

    from datetime import datetime
    item.last_synced_at = datetime.utcnow()
    await db.commit()
    return new_count
