"""
Seeds the database with a dev user (matching the DEV_USER_ID used when
Supabase auth is unconfigured) plus a mock linked bank item and 90 days of
mock transactions, so the app has real-looking data on first run.

Run with: python scripts/seed_dev_data.py
"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.security import DEV_USER_ID, encrypt_token  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.plaid_item import PlaidItem  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.claude_service import claude_service  # noqa: E402
from app.services.plaid_service import plaid_service  # noqa: E402


async def main():
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(User).where(User.id == DEV_USER_ID))).scalar_one_or_none()
        if existing:
            print("Dev user already exists, skipping seed. Delete the row to re-seed.")
            return

        user = User(
            id=DEV_USER_ID,
            email="dev@local.test",
            monthly_income=6000,
            spend_ceiling=4200,
            buffer_pct=0.10,
            location_lat=47.6062,
            location_lng=-122.3321,
            cards=[{"name": "Chase Sapphire Preferred", "cashback_rules": {"dining": 3, "travel": 2}}],
            onboarding_complete=True,
        )
        db.add(user)
        await db.commit()

        exchange = plaid_service.exchange_public_token("mock-public-token")
        accounts = plaid_service.get_accounts(exchange["access_token"])
        item = PlaidItem(
            user_id=DEV_USER_ID,
            item_id=exchange["item_id"],
            access_token_encrypted=encrypt_token(exchange["access_token"]),
            institution_name="Mock Chase Bank",
            accounts=accounts,
        )
        db.add(item)
        await db.flush()

        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        raw_txns = plaid_service.get_transactions(exchange["access_token"], start_date, end_date)

        for t in raw_txns:
            nudge_category = claude_service.categorize_transaction(t["merchant_name"], t.get("category"))
            db.add(
                Transaction(
                    user_id=DEV_USER_ID,
                    plaid_transaction_id=t["plaid_transaction_id"],
                    amount=t["amount"],
                    date=t["date"],
                    merchant_name=t["merchant_name"],
                    category=t.get("category"),
                    nudge_category=nudge_category,
                    account_id=t.get("account_id"),
                )
            )

        await db.commit()
        print(f"Seeded dev user with {len(raw_txns)} mock transactions over 90 days.")


if __name__ == "__main__":
    asyncio.run(main())
