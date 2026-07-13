import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.price_watch import PriceWatch
from app.schemas.misc import PriceWatchCreate, PriceWatchOut
from app.services.claude_service import claude_service
from app.services.price_intel_service import price_intel_service

router = APIRouter(prefix="/price-watches", tags=["price-watches"])


@router.post("", response_model=PriceWatchOut)
async def create_price_watch(
    payload: PriceWatchCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    price_info = await price_intel_service.fetch_current_price(payload.product_url)
    history = price_intel_service.generate_price_history(payload.product_url, price_info["price"])
    verdict_info = claude_service.price_verdict(price_info["product_name"], price_info["price"], history)

    watch = PriceWatch(
        user_id=current.id,
        product_url=payload.product_url,
        product_name=price_info["product_name"],
        retailer=price_info["retailer"],
        current_price=price_info["price"],
        target_price=payload.target_price,
        price_history=history,
        verdict=verdict_info["verdict"],
        confidence=verdict_info["confidence"],
    )
    db.add(watch)
    await db.commit()
    await db.refresh(watch)
    return _to_out(watch)


@router.get("", response_model=list[PriceWatchOut])
async def list_price_watches(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceWatch).where(PriceWatch.user_id == current.id))
    return [_to_out(w) for w in result.scalars().all()]


@router.post("/{watch_id}/refresh", response_model=PriceWatchOut)
async def refresh_price_watch(
    watch_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PriceWatch).where(PriceWatch.id == watch_id, PriceWatch.user_id == current.id))
    watch = result.scalar_one_or_none()
    if watch is None:
        raise HTTPException(status_code=404, detail="Price watch not found")

    price_info = await price_intel_service.fetch_current_price(watch.product_url)
    history = list(watch.price_history) + [{"date": str(__import__("datetime").date.today()), "price": price_info["price"]}]
    verdict_info = claude_service.price_verdict(watch.product_name or price_info["product_name"], price_info["price"], history)

    watch.current_price = price_info["price"]
    watch.price_history = history
    watch.verdict = verdict_info["verdict"]
    watch.confidence = verdict_info["confidence"]

    if watch.target_price and price_info["price"] <= watch.target_price:
        watch.alert_sent = True  # actual notification dispatch happens in the Celery task

    await db.commit()
    await db.refresh(watch)
    return _to_out(watch)


@router.delete("/{watch_id}")
async def delete_price_watch(
    watch_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PriceWatch).where(PriceWatch.id == watch_id, PriceWatch.user_id == current.id))
    watch = result.scalar_one_or_none()
    if watch is None:
        raise HTTPException(status_code=404, detail="Price watch not found")
    await db.delete(watch)
    await db.commit()
    return {"deleted": True}


def _to_out(w: PriceWatch) -> PriceWatchOut:
    return PriceWatchOut(
        id=w.id,
        product_url=w.product_url,
        product_name=w.product_name,
        retailer=w.retailer,
        current_price=float(w.current_price) if w.current_price is not None else None,
        target_price=float(w.target_price) if w.target_price is not None else None,
        price_history=w.price_history,
        verdict=w.verdict,
        confidence=float(w.confidence) if w.confidence is not None else None,
    )
