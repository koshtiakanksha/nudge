import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.ml.anomaly_detection import detect_anomalies
from app.models.anomaly import Anomaly
from app.models.transaction import Transaction
from app.schemas.misc import AnomalyFeedback, AnomalyOut
from app.services.claude_service import claude_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.post("/scan", response_model=list[AnomalyOut])
async def scan_for_anomalies(
    current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Run anomaly detection over the last 90 days and persist new findings."""
    cutoff = date.today() - timedelta(days=90)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current.id, Transaction.date >= cutoff, Transaction.amount < 0
        )
    )
    txns = result.scalars().all()

    txn_dicts = [
        {"id": t.id, "amount": float(t.amount), "date": t.date, "merchant_name": t.merchant_name or "Unknown"}
        for t in txns
    ]
    txn_date_by_id = {t.id: t.date for t in txns}
    flagged = detect_anomalies(txn_dicts)

    existing_result = await db.execute(select(Anomaly.transaction_id).where(Anomaly.user_id == current.id))
    existing_ids = {row[0] for row in existing_result.all()}

    created = []
    for f in flagged:
        if f["id"] in existing_ids:
            continue
        ai_context = claude_service.explain_anomaly(f["merchant_name"], f["amount"], f["typical_amount"])
        anomaly = Anomaly(
            user_id=current.id,
            transaction_id=f["id"],
            anomaly_score=f["anomaly_score"],
            merchant_name=f["merchant_name"],
            amount=f["amount"],
            ai_context=ai_context,
        )
        db.add(anomaly)
        created.append(anomaly)

    await db.commit()
    for a in created:
        await db.refresh(a)

    return [_to_out(a, txn_date_by_id.get(a.transaction_id)) for a in created]


@router.get("", response_model=list[AnomalyOut])
async def list_anomalies(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Anomaly, Transaction.date)
        .join(Transaction, Transaction.id == Anomaly.transaction_id, isouter=True)
        .where(Anomaly.user_id == current.id)
        .order_by(Anomaly.created_at.desc())
    )
    return [_to_out(a, txn_date) for a, txn_date in result.all()]


@router.post("/{anomaly_id}/feedback", response_model=AnomalyOut)
async def submit_feedback(
    anomaly_id: uuid.UUID,
    payload: AnomalyFeedback,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Anomaly).where(Anomaly.id == anomaly_id, Anomaly.user_id == current.id)
    )
    anomaly = result.scalar_one_or_none()
    if anomaly is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.user_marked_intentional = payload.intentional
    anomaly.notified = True
    await db.commit()
    await db.refresh(anomaly)
    txn_result = await db.execute(select(Transaction.date).where(Transaction.id == anomaly.transaction_id))
    txn_date = txn_result.scalar_one_or_none()
    return _to_out(anomaly, txn_date)


def _to_out(a: Anomaly, transaction_date=None) -> AnomalyOut:
    return AnomalyOut(
        id=a.id,
        transaction_id=a.transaction_id,
        transaction_date=transaction_date.isoformat() if transaction_date else None,
        merchant_name=a.merchant_name,
        amount=float(a.amount),
        anomaly_score=float(a.anomaly_score),
        ai_context=a.ai_context,
        user_marked_intentional=a.user_marked_intentional,
        created_at=a.created_at.isoformat(),
    )
