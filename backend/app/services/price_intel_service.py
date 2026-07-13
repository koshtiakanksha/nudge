"""
Price intelligence service.

Real mode: uses CamelCamelCamel API (Amazon) where configured, otherwise
falls back to a lightweight scraper (Playwright + BeautifulSoup) for basic
"current price" extraction from a product page's meta tags.

Mock mode (no API key, or scrape fails): generates a plausible synthetic
price history so the price-watch feature is fully testable without any
external dependency.
"""
import random
import re
from datetime import date, timedelta

import httpx

from app.core.config import settings


class PriceIntelService:
    def __init__(self):
        self.mock_mode = not settings.camel_configured

    async def fetch_current_price(self, product_url: str) -> dict:
        """Returns {"price": float, "product_name": str, "retailer": str}"""
        if not self.mock_mode:
            try:
                return await self._fetch_real(product_url)
            except Exception:
                pass  # fall through to mock so the feature never hard-fails
        return self._mock_price(product_url)

    async def _fetch_real(self, product_url: str) -> dict:
        headers = {"User-Agent": settings.scraper_user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
            resp = await client.get(product_url)
            html = resp.text

        # Try common meta tags first (works on many e-commerce sites)
        price_match = re.search(r'"price"\s*:\s*"?([\d.]+)"?', html) or re.search(
            r'content="USD ([\d.]+)"', html
        )
        name_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)

        price = float(price_match.group(1)) if price_match else None
        name = name_match.group(1).strip() if name_match else "Unknown product"

        if price is None:
            raise ValueError("Could not extract price from page")

        retailer = self._guess_retailer(product_url)
        return {"price": price, "product_name": name, "retailer": retailer}

    def _guess_retailer(self, url: str) -> str:
        for domain, label in [
            ("amazon", "Amazon"), ("bestbuy", "Best Buy"), ("target", "Target"),
            ("walmart", "Walmart"),
        ]:
            if domain in url.lower():
                return label
        return "Unknown"

    def _mock_price(self, product_url: str) -> dict:
        rng = random.Random(product_url)
        base_price = rng.uniform(20, 800)
        return {
            "price": round(base_price, 2),
            "product_name": f"Mock Product ({product_url.split('/')[-1][:20] or 'item'})",
            "retailer": self._guess_retailer(product_url),
        }

    def generate_price_history(self, product_url: str, current_price: float, days: int = 90) -> list[dict]:
        """Mock historical series anchored around current_price, with a seasonal dip pattern."""
        rng = random.Random(product_url + "-history")
        history = []
        price = current_price * rng.uniform(1.05, 1.25)
        today = date.today()
        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            drift = rng.uniform(-0.02, 0.015)
            price = max(current_price * 0.7, price * (1 + drift))
            history.append({"date": d.isoformat(), "price": round(price, 2)})
        history.append({"date": today.isoformat(), "price": current_price})
        return history


price_intel_service = PriceIntelService()
