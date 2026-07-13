from datetime import date, timedelta

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.ml.anomaly_detection import detect_anomalies
from app.models.anomaly import Anomaly
from app.models.price_watch import PriceWatch
from app.models.transaction import Transaction
from app.models.user import User
from app.services.claude_service import claude_service
from app.services.price_intel_service import price_intel_service
from app.tasks.async_bridge import run_async
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.ai_tasks.scan_all_users_for_anomalies")
def scan_all_users_for_anomalies():
    return run_async(_scan_all_users_for_anomalies)


async def _scan_all_users_for_anomalies():
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        total_flagged = 0

        for user in users:
            cutoff = date.today() - timedelta(days=90)
            txns = (
                await db.execute(
                    select(Transaction).where(
                        Transaction.user_id == user.id, Transaction.date >= cutoff, Transaction.amount < 0
                    )
                )
            ).scalars().all()

            txn_dicts = [
                {"id": t.id, "amount": float(t.amount), "date": t.date, "merchant_name": t.merchant_name or "Unknown"}
                for t in txns
            ]
            flagged = detect_anomalies(txn_dicts)

            existing_ids = {
                row[0] for row in (await db.execute(select(Anomaly.transaction_id).where(Anomaly.user_id == user.id))).all()
            }

            for f in flagged:
                if f["id"] in existing_ids:
                    continue
                ai_context = claude_service.explain_anomaly(f["merchant_name"], f["amount"], f["typical_amount"])
                db.add(
                    Anomaly(
                        user_id=user.id,
                        transaction_id=f["id"],
                        anomaly_score=f["anomaly_score"],
                        merchant_name=f["merchant_name"],
                        amount=f["amount"],
                        ai_context=ai_context,
                    )
                )
                total_flagged += 1

        await db.commit()
        return {"users_scanned": len(users), "new_anomalies": total_flagged}


@celery_app.task(name="app.tasks.ai_tasks.refresh_all_price_watches")
def refresh_all_price_watches():
    return run_async(_refresh_all_price_watches)


async def _refresh_all_price_watches():
    async with AsyncSessionLocal() as db:
        watches = (await db.execute(select(PriceWatch))).scalars().all()

        for watch in watches:
            price_info = await price_intel_service.fetch_current_price(watch.product_url)
            history = list(watch.price_history) + [
                {"date": str(date.today()), "price": price_info["price"]}
            ]
            verdict_info = claude_service.price_verdict(
                watch.product_name or price_info["product_name"], price_info["price"], history
            )

            watch.current_price = price_info["price"]
            watch.price_history = history
            watch.verdict = verdict_info["verdict"]
            watch.confidence = verdict_info["confidence"]

            if watch.target_price and price_info["price"] <= watch.target_price and not watch.alert_sent:
                watch.alert_sent = True
                # Actual push/email dispatch is handled in notification_tasks via
                # a follow-up task to keep this task focused on price refresh.

        await db.commit()
        return {"watches_refreshed": len(watches)}
