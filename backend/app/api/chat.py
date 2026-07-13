import calendar
import re
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.chat_message import ChatMessage
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.misc import ChatHistoryItem, ChatRequest, ChatResponse
from app.api.decision_context import build_decision_context
from app.services.affordability_service import affordability_verdict
from app.services.claude_service import claude_service

router = APIRouter(prefix="/chat", tags=["chat"])


async def _build_context(db: AsyncSession, user_id) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id, Transaction.date >= month_start, Transaction.amount < 0
        )
    )
    txns = result.scalars().all()

    category_totals: dict[str, float] = {}
    for t in txns:
        cat = t.nudge_category or "Other"
        category_totals[cat] = category_totals.get(cat, 0) + abs(float(t.amount))
    top_categories = sorted(
        [{"category": k, "amount": round(v, 2)} for k, v in category_totals.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    mtd_spend = sum(abs(float(t.amount)) for t in txns)
    buffer_target = float(user.monthly_income) * float(user.buffer_pct) if user and user.monthly_income else 1
    buffer_status = max(0.0, 1 - (mtd_spend / buffer_target)) if buffer_target else 1.0

    return {
        "month_to_date_spend": round(mtd_spend, 2),
        "top_categories": top_categories,
        "buffer_status": round(buffer_status, 2),
        "spend_ceiling": float(user.spend_ceiling) if user and user.spend_ceiling else None,
    }


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history_result = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == current.id).order_by(ChatMessage.created_at.desc()).limit(10)
    )
    history = list(reversed(history_result.scalars().all()))
    history_dicts = [{"role": h.role, "content": h.content} for h in history]

    context = await _build_context(db, current.id)
    decision = await _decision_reply(db, current.id, payload.message)
    result = decision or claude_service.chat(payload.message, context, history_dicts)

    db.add(ChatMessage(user_id=current.id, role="user", content=payload.message))
    db.add(
        ChatMessage(
            user_id=current.id, role="assistant", content=result["reply"], chart_data=result.get("chart_data")
        )
    )
    await db.commit()

    return ChatResponse(reply=result["reply"], chart_data=result.get("chart_data"), actions=result.get("actions", []))


@router.get("/history", response_model=list[ChatHistoryItem])
async def get_chat_history(
    current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == current.id).order_by(ChatMessage.created_at.asc())
    )
    return [
        ChatHistoryItem(role=m.role, content=m.content, chart_data=m.chart_data, created_at=m.created_at.isoformat())
        for m in result.scalars().all()
    ]


async def _decision_reply(db: AsyncSession, user_id, message: str) -> dict | None:
    msg = message.lower()
    ctx = await build_decision_context(db, user_id)
    if "safe" in msg and "spend" in msg:
        return {
            "reply": ctx["safe"]["message"],
            "chart_data": None,
            "actions": [{"label": "View budget", "href": "/budget"}, {"label": "Check affordability", "href": "/afford"}],
        }
    price_match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", msg)
    afford_words = any(phrase in msg for phrase in ["can i afford", "should i buy", "buy this", "go out", "go out tonight"])
    if price_match and afford_words:
        price = float(price_match.group(1))
        category = "Dining" if "dinner" in msg or "go out" in msg else "Shopping"
        result = affordability_verdict(
            price=price,
            category=category,
            need_or_want="want",
            safe_to_spend_today=ctx["safe"]["safe_to_spend_today"],
            remaining_safe_money=ctx["safe"]["remaining_safe_money"],
            category_budget=float(ctx["allocations"].get(category, {}).get("allocated", 0) or 0),
            category_spent=ctx["category_spend"].get(category, 0),
            month_end_projection=ctx["month_end_forecast"],
            spending_ceiling=ctx["spending_ceiling"],
            upcoming_bills=ctx["upcoming_bills_total"],
        )
        return {
            "reply": f"{result['verdict']}: {result['explanation']} Your safe-to-spend would move from ${result['safe_to_spend_before']:.0f} to ${result['safe_to_spend_after']:.0f}.",
            "chart_data": None,
            "actions": [{"label": "Check affordability", "href": "/afford"}, {"label": "Rebalance budget", "href": "/budget"}, {"label": "View forecast", "href": "/"}],
        }
    if "over budget" in msg or "what can i cut" in msg:
        risk = ctx["top_risk_category"] or "flexible spending"
        return {
            "reply": f"Your top budget risk is {risk}. {ctx['recommended_action']}",
            "chart_data": None,
            "actions": [{"label": "Rebalance budget", "href": "/budget"}, {"label": "Find deals", "href": "/deals"}],
        }
    if "dinner deals" in msg or "deals under" in msg:
        return {
            "reply": f"You have ${ctx['safe']['safe_to_spend_today']:.0f} safe to spend today. I’d start with deals under that amount.",
            "chart_data": None,
            "actions": [{"label": "Find deals", "href": "/deals"}],
        }
    return None
