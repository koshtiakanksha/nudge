import json
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.anomaly import Anomaly
from app.models.budget import Budget
from app.models.budget_recommendation import BudgetRecommendation
from app.models.category_rule import CategoryRule
from app.models.recurring_expense import RecurringExpense
from app.models.statement import StatementUpload
from app.models.transaction import Transaction
from app.schemas.statements import (
    AnomalyStatusUpdate,
    BudgetRecommendationOut,
    BulkTransactionUpdate,
    RecurringExpenseOut,
    SaveGeneratedBudgetRequest,
    SmartBudgetOut,
    SpendingSummaryOut,
    StatementAnomalyOut,
    StatementTransactionOut,
    StatementUploadOut,
    StatementUploadResponse,
    TransactionReviewUpdate,
)
from app.services.statement_analysis_service import statement_analysis_service as analyzer

router = APIRouter(tags=["statements"])


@router.post("/statements/upload", response_model=StatementUploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    bank_name: str | None = Form(None),
    statement_month: date = Form(...),
    mapping: str | None = Form(None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        file_type = analyzer["validate_upload"](file.filename or "statement", len(content)).removeprefix(".")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    statement = StatementUpload(
        user_id=current.id,
        file_name=file.filename or "statement",
        file_type=file_type,
        bank_name=bank_name,
        statement_month=statement_month.replace(day=1),
        status="uploaded",
    )
    db.add(statement)
    await db.flush()

    rules = await _category_rules(db, current.id)
    try:
        mapping_data = json.loads(mapping) if mapping else None
        parsed = analyzer["parse_statement_bytes"](statement.file_name, content, rules, mapping_data)
    except ValueError as exc:
        statement.status = "failed"
        statement.error_message = str(exc)
        await db.commit()
        await db.refresh(statement)
        return StatementUploadResponse(statement=statement, parsed_count=0, needs_mapping="mapping" in str(exc).lower(), message=str(exc))

    for item in parsed:
        db.add(
            Transaction(
                user_id=current.id,
                plaid_transaction_id=f"statement-{statement.id}-{uuid.uuid4().hex}",
                statement_id=statement.id,
                amount=item.amount,
                date=item.date,
                merchant_name=item.merchant_name,
                category=item.category,
                nudge_category=item.category,
                subcategory=None,
                transaction_type=item.transaction_type,
                raw_description=item.raw_description,
                confidence_score=item.confidence_score,
                raw_data=item.raw_data,
                currency=item.currency,
                account_id=bank_name,
            )
        )
    statement.status = "parsed"
    await db.commit()
    await db.refresh(statement)
    return StatementUploadResponse(
        statement=statement,
        parsed_count=len(parsed),
        message=f"Parsed {len(parsed)} transactions. Review them before saving.",
    )


@router.get("/statements", response_model=list[StatementUploadOut])
async def list_statements(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StatementUpload).where(StatementUpload.user_id == current.id).order_by(StatementUpload.upload_date.desc()))
    return result.scalars().all()


@router.get("/statements/{statement_id}", response_model=StatementUploadOut)
async def get_statement(statement_id: uuid.UUID, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    statement = await _get_statement(db, current.id, statement_id)
    return statement


@router.delete("/statements/{statement_id}")
async def delete_statement(statement_id: uuid.UUID, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    statement = await _get_statement(db, current.id, statement_id)
    await db.execute(delete(Anomaly).where(Anomaly.user_id == current.id, Anomaly.transaction_id.in_(select(Transaction.id).where(Transaction.statement_id == statement.id))))
    await db.execute(delete(Transaction).where(Transaction.user_id == current.id, Transaction.statement_id == statement.id))
    await db.delete(statement)
    await db.commit()
    return {"deleted": True}


@router.post("/statements/{statement_id}/parse", response_model=StatementUploadOut)
async def mark_statement_for_reupload(statement_id: uuid.UUID, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    statement = await _get_statement(db, current.id, statement_id)
    if statement.status == "failed":
        return statement
    statement.status = "parsed"
    await db.commit()
    await db.refresh(statement)
    return statement


@router.get("/statements/{statement_id}/transactions", response_model=list[StatementTransactionOut])
async def statement_transactions(statement_id: uuid.UUID, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_statement(db, current.id, statement_id)
    result = await db.execute(select(Transaction).where(Transaction.user_id == current.id, Transaction.statement_id == statement_id).order_by(Transaction.date.desc()))
    return [_txn_out(t) for t in result.scalars().all()]


@router.patch("/transactions/{transaction_id}", response_model=StatementTransactionOut)
async def patch_statement_transaction(transaction_id: uuid.UUID, payload: TransactionReviewUpdate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.user_id == current.id, Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    data = payload.model_dump(exclude_unset=True)
    apply_to_similar = data.pop("apply_to_similar", False)
    for field, value in data.items():
        setattr(txn, field, value)
    if apply_to_similar and payload.nudge_category:
        await _save_category_rule(db, current.id, txn.merchant_name or txn.raw_description, payload.nudge_category)
    await db.commit()
    await db.refresh(txn)
    return _txn_out(txn)


@router.post("/transactions/bulk-update")
async def bulk_update_transactions(payload: BulkTransactionUpdate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.user_id == current.id, Transaction.id.in_(payload.transaction_ids)))
    txns = result.scalars().all()
    for txn in txns:
        if payload.nudge_category is not None:
            txn.nudge_category = payload.nudge_category
            if payload.apply_to_similar:
                await _save_category_rule(db, current.id, txn.merchant_name or txn.raw_description, payload.nudge_category)
        if payload.is_ignored is not None:
            txn.is_ignored = payload.is_ignored
        if payload.is_recurring is not None:
            txn.is_recurring = payload.is_recurring
    await db.commit()
    return {"updated": len(txns)}


@router.post("/statements/review/save")
async def save_reviewed_transactions(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StatementUpload).where(StatementUpload.user_id == current.id, StatementUpload.status == "parsed"))
    statements = result.scalars().all()
    for statement in statements:
        statement.status = "reviewed"
    txns = await _all_statement_txns(db, current.id)
    await _persist_recurring_and_anomalies(db, current.id, txns)
    await db.commit()
    return {"reviewed_statements": len(statements)}


async def _all_statement_txns(db: AsyncSession, user_id) -> list[Transaction]:
    result = await db.execute(select(Transaction).where(Transaction.user_id == user_id, Transaction.statement_id.is_not(None)).order_by(Transaction.date.asc()))
    return result.scalars().all()


@router.get("/spending/summary", response_model=SpendingSummaryOut)
async def spending_summary(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _all_statement_txns(db, current.id)
    summary = analyzer["summarize_transactions"](txns)
    trends = analyzer["monthly_trends"](txns)
    if summary["months_of_history"] < 2:
        summary["prediction_message"] = "Not enough history yet. Upload at least 2 to 3 months of statements for better predictions."
    else:
        recent = trends[-3:]
        weights = [1, 2, 3][-len(recent):]
        weight_sum = sum(weights)
        summary["expected_next_month_spending"] = round(sum(t["spending"] * w for t, w in zip(recent, weights)) / weight_sum, 2)
        summary["expected_next_month_income"] = round(sum(t["income"] * w for t, w in zip(recent, weights)) / weight_sum, 2)
        summary["cash_left_after_predicted_expenses"] = round(summary["expected_next_month_income"] - summary["expected_next_month_spending"], 2)
    return summary


@router.get("/spending/categories")
async def spending_categories(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return analyzer["category_totals"](await _all_statement_txns(db, current.id))


@router.get("/spending/merchants")
async def spending_merchants(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return analyzer["merchant_totals"](await _all_statement_txns(db, current.id))


@router.get("/spending/trends")
async def spending_trends(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return analyzer["monthly_trends"](await _all_statement_txns(db, current.id))


@router.get("/insights")
async def insights(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return analyzer["insights"](await _all_statement_txns(db, current.id))


@router.get("/recurring-expenses", response_model=list[RecurringExpenseOut])
async def recurring_expenses(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecurringExpense).where(RecurringExpense.user_id == current.id).order_by(RecurringExpense.amount.desc()))
    persisted = result.scalars().all()
    if persisted:
        return persisted
    return analyzer["detect_recurring"](await _all_statement_txns(db, current.id))


@router.get("/statement-anomalies", response_model=list[StatementAnomalyOut])
async def statement_anomalies(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Anomaly).where(Anomaly.user_id == current.id).order_by(Anomaly.created_at.desc()))
    return [
        StatementAnomalyOut(
            id=a.id,
            transaction_id=a.transaction_id,
            anomaly_type=a.anomaly_type,
            explanation=a.explanation or a.ai_context or "This looks different from your usual pattern.",
            severity=a.severity,
            user_status=a.user_status,
            merchant_name=a.merchant_name,
            amount=float(a.amount),
        )
        for a in result.scalars().all()
    ]


@router.patch("/statement-anomalies/{anomaly_id}", response_model=StatementAnomalyOut)
async def update_statement_anomaly(anomaly_id: uuid.UUID, payload: AnomalyStatusUpdate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Anomaly).where(Anomaly.user_id == current.id, Anomaly.id == anomaly_id))
    anomaly = result.scalar_one_or_none()
    if anomaly is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anomaly.user_status = payload.user_status
    anomaly.user_marked_intentional = payload.user_status == "confirmed"
    await db.commit()
    await db.refresh(anomaly)
    return StatementAnomalyOut(id=anomaly.id, transaction_id=anomaly.transaction_id, anomaly_type=anomaly.anomaly_type, explanation=anomaly.explanation or anomaly.ai_context or "", severity=anomaly.severity, user_status=anomaly.user_status, merchant_name=anomaly.merchant_name, amount=float(anomaly.amount))


@router.post("/budget/generate-from-history", response_model=SmartBudgetOut)
async def generate_budget_from_history(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    target_month = (today.replace(day=1))
    result = analyzer["budget_recommendations"](await _all_statement_txns(db, current.id), target_month)
    await db.execute(delete(BudgetRecommendation).where(BudgetRecommendation.user_id == current.id, BudgetRecommendation.month == target_month))
    for rec in result["recommendations"]:
        db.add(BudgetRecommendation(user_id=current.id, month=target_month, category=rec["category"], recommended_amount=rec["recommended_amount"], reasoning=rec["reasoning"], confidence_score=rec["confidence_score"]))
    await db.commit()
    if result["not_enough_history"]:
        result["warnings"].append("Not enough history yet. Upload at least 2 to 3 months of statements for better predictions.")
    return result


@router.post("/budget/save")
async def save_generated_budget(payload: SaveGeneratedBudgetRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    allocations = {r.category: {"allocated": r.recommended_amount, "spent": 0, "is_non_neg": r.category in {"Rent", "Utilities", "Debt Payments"}} for r in payload.recommendations}
    budget = Budget(user_id=current.id, month=payload.month.replace(day=1), allocations=allocations, total_allocated=sum(r.recommended_amount for r in payload.recommendations), total_budget=payload.total_budget, income_estimate=payload.income_estimate, generated_by_ai=True, generated_from_statement=True, ai_reasoning="Generated from uploaded statement history.")
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return {"id": budget.id, "saved": True}


async def _get_statement(db: AsyncSession, user_id, statement_id: uuid.UUID) -> StatementUpload:
    result = await db.execute(select(StatementUpload).where(StatementUpload.id == statement_id, StatementUpload.user_id == user_id))
    statement = result.scalar_one_or_none()
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    return statement


async def _category_rules(db: AsyncSession, user_id) -> dict[str, str]:
    result = await db.execute(select(CategoryRule).where(CategoryRule.user_id == user_id))
    return {r.merchant_key: r.category for r in result.scalars().all()}


async def _save_category_rule(db: AsyncSession, user_id, merchant: str | None, category: str) -> None:
    key = analyzer["merchant_key"](merchant)
    result = await db.execute(select(CategoryRule).where(CategoryRule.user_id == user_id, CategoryRule.merchant_key == key))
    rule = result.scalar_one_or_none()
    if rule:
        rule.category = category
    else:
        db.add(CategoryRule(user_id=user_id, merchant_key=key, category=category))


def _txn_out(t: Transaction) -> StatementTransactionOut:
    return StatementTransactionOut(
        id=t.id,
        transaction_id=t.plaid_transaction_id,
        date=t.date,
        description=t.raw_description or t.merchant_name or "",
        merchant_name=t.merchant_name,
        amount=float(t.amount),
        transaction_type=t.transaction_type or ("income" if float(t.amount) > 0 else "debit"),
        category=t.nudge_category,
        subcategory=t.subcategory,
        bank_name=t.account_id,
        source_statement_id=t.statement_id,
        raw_description=t.raw_description,
        confidence_score=float(t.confidence_score) if t.confidence_score is not None else None,
        location_city=t.location_city,
        location_state=t.location_state,
        location_country=t.location_country,
        currency=t.currency or "USD",
        is_recurring=t.is_recurring,
        is_anomaly=t.is_anomaly,
        is_ignored=t.is_ignored,
    )


async def _persist_recurring_and_anomalies(db: AsyncSession, user_id, txns: list[Transaction]) -> None:
    await db.execute(delete(RecurringExpense).where(RecurringExpense.user_id == user_id))
    for item in analyzer["detect_recurring"](txns):
        db.add(RecurringExpense(user_id=user_id, **item))
        for txn in txns:
            if analyzer["merchant_key"](txn.merchant_name or txn.raw_description) == analyzer["merchant_key"](item["merchant_name"]):
                txn.is_recurring = True

    existing_result = await db.execute(select(Anomaly.transaction_id, Anomaly.anomaly_type).where(Anomaly.user_id == user_id))
    existing = set(existing_result.all())
    for item in analyzer["detect_soft_anomalies"](txns):
        if (item["transaction_id"], item["anomaly_type"]) in existing:
            continue
        db.add(Anomaly(user_id=user_id, transaction_id=item["transaction_id"], anomaly_score=0.65, merchant_name=item.get("merchant_name"), amount=item.get("amount") or 0, ai_context=item["explanation"], explanation=item["explanation"], anomaly_type=item["anomaly_type"], severity=item["severity"], user_status="pending"))
        for txn in txns:
            if txn.id == item["transaction_id"]:
                txn.is_anomaly = True
