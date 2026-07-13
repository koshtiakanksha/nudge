from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.misc import DealOut
from app.api.decision_context import build_decision_context
from app.services.affordability_service import deal_affordability_label
from app.services.deals_service import deals_service

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("", response_model=list[DealOut])
async def get_deals(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.id == current.id))
    user = user_result.scalar_one_or_none()

    lat = float(user.location_lat) if user and user.location_lat else None
    lng = float(user.location_lng) if user and user.location_lng else None

    deals = await deals_service.get_deals(lat, lng)
    ctx = await build_decision_context(db, current.id)
    safe_today = ctx["safe"]["safe_to_spend_today"]
    for deal in deals:
        price = deal.get("price")
        if price is None and deal.get("cost"):
            cost = str(deal["cost"]).lower()
            price = 0 if "free" in cost else None
        deal["affordability_label"] = deal_affordability_label(price, safe_today)
    return deals
