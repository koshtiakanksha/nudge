from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.decision_context import build_decision_context
from app.core.config import settings
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.affordability import AffordabilityCheck
from app.models.price_watch import PriceWatch
from app.schemas.affordability import AffordabilityCheckOut, AffordabilityCheckRequest, AppModeOut, TodayOut
from app.services.affordability_service import affordability_verdict

router = APIRouter(tags=["affordability"])


@router.get("/today", response_model=TodayOut)
async def today(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ctx = await build_decision_context(db, current.id)
    safe = ctx["safe"]
    return TodayOut(
        safe_to_spend_today=safe["safe_to_spend_today"],
        safe_to_spend_message=safe["message"],
        can_calculate=safe["can_calculate"],
        has_linked_data=ctx["has_linked_data"],
        month_to_date_spending=ctx["month_to_date_spending"],
        month_end_forecast=ctx["month_end_forecast"],
        spending_ceiling=ctx["spending_ceiling"],
        upcoming_bills_total=ctx["upcoming_bills_total"],
        budget_health=ctx["budget_health"],
        top_risk_category=ctx["top_risk_category"],
        recommended_action=ctx["recommended_action"],
        remaining_safe_money=safe["remaining_safe_money"],
    )


@router.post("/affordability/check", response_model=AffordabilityCheckOut)
async def check_affordability(
    payload: AffordabilityCheckRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await build_decision_context(db, current.id)
    alloc = ctx["allocations"].get(payload.category, {})
    product_deal_good = None
    if payload.product_url:
        watch = (
            await db.execute(
                select(PriceWatch).where(PriceWatch.user_id == current.id, PriceWatch.product_url == payload.product_url)
            )
        ).scalar_one_or_none()
        if watch and watch.target_price and watch.current_price:
            product_deal_good = float(watch.current_price) <= float(watch.target_price)

    result = affordability_verdict(
        price=payload.price,
        category=payload.category,
        need_or_want=payload.need_or_want,
        safe_to_spend_today=ctx["safe"]["safe_to_spend_today"],
        remaining_safe_money=ctx["safe"]["remaining_safe_money"],
        category_budget=float(alloc.get("allocated", 0) or 0),
        category_spent=ctx["category_spend"].get(payload.category, 0),
        month_end_projection=ctx["month_end_forecast"],
        spending_ceiling=ctx["spending_ceiling"],
        upcoming_bills=ctx["upcoming_bills_total"],
        product_deal_good=product_deal_good,
    )
    check = AffordabilityCheck(
        user_id=current.id,
        item_name=payload.item_name,
        price=payload.price,
        category=payload.category,
        need_or_want=payload.need_or_want,
        purchase_date=payload.purchase_date,
        product_url=payload.product_url,
        notes=payload.notes,
        **result,
    )
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return _to_out(check)


@router.get("/affordability/history", response_model=list[AffordabilityCheckOut])
async def affordability_history(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AffordabilityCheck).where(AffordabilityCheck.user_id == current.id).order_by(AffordabilityCheck.created_at.desc()).limit(25)
    )
    return [_to_out(row) for row in result.scalars().all()]


@router.get("/app-mode", response_model=AppModeOut)
async def app_mode():
    badges = []
    if not settings.supabase_configured:
        badges.append("Demo Mode")
    if settings.plaid_configured:
        badges.append("Plaid Sandbox" if settings.plaid_env == "sandbox" else "Live Mode")
    else:
        badges.append("Missing API Keys")
    if not settings.claude_configured:
        badges.append("Missing AI Key")
    return AppModeOut(
        mode="Live Mode" if settings.supabase_configured and settings.plaid_env == "production" else "Demo Mode",
        badges=badges,
        message="Demo data shown. Connect live APIs to see real results." if "Demo Mode" in badges else None,
    )


def _to_out(check: AffordabilityCheck) -> AffordabilityCheckOut:
    return AffordabilityCheckOut(
        id=check.id,
        item_name=check.item_name,
        price=float(check.price),
        category=check.category,
        need_or_want=check.need_or_want,
        purchase_date=check.purchase_date,
        product_url=check.product_url,
        notes=check.notes,
        verdict=check.verdict,
        explanation=check.explanation,
        safe_to_spend_before=float(check.safe_to_spend_before),
        safe_to_spend_after=float(check.safe_to_spend_after),
        remaining_before=float(check.remaining_before),
        remaining_after=float(check.remaining_after),
        category_impact=check.category_impact,
        forecast_impact=check.forecast_impact,
        upcoming_bill_risk=check.upcoming_bill_risk,
        suggested_actions=check.suggested_actions,
        created_at=check.created_at,
    )
