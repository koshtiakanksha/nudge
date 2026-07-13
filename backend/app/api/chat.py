import calendar
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
    result = claude_service.chat(payload.message, context, history_dicts)

    db.add(ChatMessage(user_id=current.id, role="user", content=payload.message))
    db.add(
        ChatMessage(
            user_id=current.id, role="assistant", content=result["reply"], chart_data=result.get("chart_data")
        )
    )
    await db.commit()

    return ChatResponse(reply=result["reply"], chart_data=result.get("chart_data"))


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
