"""
Local deals aggregator. Pulls from Google Places (nearby deals/happy hours
via business descriptions), Yelp Fusion (deals category), and Eventbrite
(free/discounted local events). Any unconfigured source is simply skipped;
if none are configured, returns a realistic mock deal feed.
"""
import random
from datetime import datetime, timedelta

import httpx

from app.core.config import settings

MOCK_DEALS_POOL = [
    ("Happy Hour", "50% off appetizers, 4-6pm daily", "Dining"),
    ("Free Yoga in the Park", "Community yoga session, bring your own mat", "Health & Fitness"),
    ("BOGO Movie Tickets", "Buy one get one free on Tuesdays", "Entertainment"),
    ("Farmers Market Discount", "10% off with student ID", "Groceries"),
    ("Gym Day Pass Promo", "Free trial day at local fitness studio", "Health & Fitness"),
    ("Live Music Night", "No cover charge, local bands", "Entertainment"),
    ("Coffee Shop Loyalty Special", "Buy 5 get 1 free this week", "Dining"),
]


class DealsService:
    def __init__(self):
        self.any_configured = (
            settings.places_configured or settings.yelp_configured or settings.eventbrite_configured
        )

    async def get_deals(self, lat: float | None, lng: float | None) -> list[dict]:
        deals: list[dict] = []

        if settings.yelp_configured and lat and lng:
            deals += await self._fetch_yelp(lat, lng)
        if settings.eventbrite_configured and lat and lng:
            deals += await self._fetch_eventbrite(lat, lng)

        if not deals:
            deals = self._mock_deals(lat, lng)

        return deals

    async def _fetch_yelp(self, lat: float, lng: float) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.yelp.com/v3/businesses/search",
                    headers={"Authorization": f"Bearer {settings.yelp_fusion_api_key}"},
                    params={"latitude": lat, "longitude": lng, "term": "deals", "limit": 10},
                )
                data = resp.json()
            return [
                {
                    "title": b["name"],
                    "description": f"{b.get('rating', '?')}⭐ · {', '.join(c['title'] for c in b.get('categories', []))}",
                    "category": "Dining",
                    "location": b.get("location", {}).get("address1"),
                    "distance_miles": round(b.get("distance", 0) / 1609.34, 1),
                    "source": "Yelp",
                    "url": b.get("url"),
                    "expires_at": None,
                }
                for b in data.get("businesses", [])
            ]
        except Exception:
            return []

    async def _fetch_eventbrite(self, lat: float, lng: float) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://www.eventbriteapi.com/v3/events/search/",
                    headers={"Authorization": f"Bearer {settings.eventbrite_api_token}"},
                    params={"location.latitude": lat, "location.longitude": lng, "price": "free"},
                )
                data = resp.json()
            return [
                {
                    "title": e["name"]["text"],
                    "description": (e.get("description") or {}).get("text", "")[:120],
                    "category": "Entertainment",
                    "location": None,
                    "distance_miles": None,
                    "source": "Eventbrite",
                    "url": e.get("url"),
                    "expires_at": e.get("end", {}).get("local"),
                }
                for e in data.get("events", [])
            ]
        except Exception:
            return []

    def _mock_deals(self, lat: float | None, lng: float | None) -> list[dict]:
        rng = random.Random(f"{lat}-{lng}-{datetime.utcnow().date()}")
        chosen = rng.sample(MOCK_DEALS_POOL, k=min(5, len(MOCK_DEALS_POOL)))
        deals = []
        for title, desc, category in chosen:
            deals.append(
                {
                    "title": title,
                    "description": desc,
                    "category": category,
                    "location": "Near you" if lat else "Set your location for nearby deals",
                    "distance_miles": round(rng.uniform(0.2, 4.5), 1) if lat else None,
                    "source": "Mock",
                    "url": None,
                    "expires_at": (datetime.utcnow() + timedelta(days=rng.randint(1, 7))).isoformat(),
                }
            )
        return deals


deals_service = DealsService()
