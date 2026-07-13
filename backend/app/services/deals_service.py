"""
Local deals aggregator. Pulls from configured providers and falls back to a
development sample feed with the same shape expected from live integrations.
"""
import random
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import httpx

from app.core.config import settings

SAMPLE_DEALS_POOL = [
    ("Happy Hour", "50% off appetizers, 4-6pm daily", "Dining", "The Green Table", "120 Market St"),
    ("Free Yoga in the Park", "Community yoga session, bring your own mat", "Health", "Civic Park", "1 Civic Center Plaza"),
    ("BOGO Movie Tickets", "Buy one get one free on Tuesdays", "Entertainment", "Riverview Cinema", "44 Main St"),
    ("Farmers Market Discount", "10% off seasonal produce this weekend", "Groceries", "Downtown Farmers Market", "2 Ferry Building"),
    ("Gym Day Pass Promo", "Free trial day at a local fitness studio", "Health", "Northside Fitness", "88 Pine St"),
    ("Live Music Night", "No cover charge for local bands", "Entertainment", "Harbor Hall", "9 Embarcadero"),
    ("Coffee Shop Loyalty Special", "Buy 5 drinks, get 1 free this week", "Dining", "Corner Coffee", "300 Oak St"),
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
                    "result_type": "place",
                    "location": b.get("location", {}).get("address1"),
                    "address": ", ".join(filter(None, b.get("location", {}).get("display_address", []))) or None,
                    "distance_miles": round(b.get("distance", 0) / 1609.34, 1),
                    "source": "Yelp",
                    "provider": "Yelp",
                    "image_url": b.get("image_url"),
                    "rating": b.get("rating"),
                    "url": b.get("url"),
                    "external_url": b.get("url"),
                    "website_url": b.get("url"),
                    "expires_at": None,
                    "last_updated": datetime.utcnow().isoformat(),
                    "is_sample": False,
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
                    "result_type": "event",
                    "location": None,
                    "distance_miles": None,
                    "source": "Eventbrite",
                    "provider": "Eventbrite",
                    "url": e.get("url"),
                    "external_url": e.get("url"),
                    "ticket_url": e.get("url"),
                    "expires_at": e.get("end", {}).get("local"),
                    "starts_at": e.get("start", {}).get("local"),
                    "ends_at": e.get("end", {}).get("local"),
                    "last_updated": datetime.utcnow().isoformat(),
                    "is_sample": False,
                }
                for e in data.get("events", [])
            ]
        except Exception:
            return []

    def _mock_deals(self, lat: float | None, lng: float | None) -> list[dict]:
        rng = random.Random(f"{lat}-{lng}-{datetime.utcnow().date()}")
        chosen = rng.sample(SAMPLE_DEALS_POOL, k=min(5, len(SAMPLE_DEALS_POOL)))
        deals = []
        for title, desc, category, place, address in chosen:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(place + ' ' + address)}"
            website_url = f"https://www.google.com/search?q={quote_plus(place)}"
            deals.append(
                {
                    "title": title,
                    "description": desc,
                    "category": category,
                    "result_type": "event" if "Music" in title or "Yoga" in title else "place",
                    "location": place,
                    "address": address if lat else None,
                    "distance_miles": round(rng.uniform(0.2, 4.5), 1) if lat else None,
                    "source": "Sample data",
                    "provider": "Development sample",
                    "image_url": None,
                    "cost": "Free" if "Free" in title or "No cover" in desc else None,
                    "rating": round(rng.uniform(4.1, 4.8), 1),
                    "url": website_url,
                    "external_url": website_url,
                    "website_url": website_url,
                    "ticket_url": website_url if "Tickets" in title or "Music" in title else None,
                    "expires_at": (datetime.utcnow() + timedelta(days=rng.randint(1, 7))).isoformat(),
                    "starts_at": (datetime.utcnow() + timedelta(days=rng.randint(1, 7))).isoformat(),
                    "ends_at": None,
                    "latitude": lat,
                    "longitude": lng,
                    "directions_url": maps_url,
                    "last_updated": datetime.utcnow().isoformat(),
                    "is_sample": True,
                }
            )
        return deals


deals_service = DealsService()
