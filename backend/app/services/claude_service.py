"""
Anthropic Claude integration service. Powers:
- Transaction categorization into lifestyle buckets
- AI-generated monthly budgets with natural-language reasoning
- Conversational financial chat (with transaction context)
- Anomaly explanations
- Price-watch buy/wait verdicts

When ANTHROPIC_API_KEY is unset, falls back to deterministic rule-based
mock logic so every feature still produces sensible output locally.
"""
import json

from app.core.config import settings
from app.services.budget_engine import (
    compute_budget_allocation,
    diff_allocations,
    validate_allocation,
)

BUDGET_PROMPT_VERSION = "budget-explain-v1"

NUDGE_CATEGORIES = [
    "Groceries",
    "Dining",
    "Transportation",
    "Entertainment",
    "Health & Fitness",
    "Shopping",
    "Travel",
    "Utilities & Bills",
    "Subscriptions",
    "Other",
]

_CATEGORY_KEYWORDS = {
    "Groceries": ["whole foods", "trader joe", "safeway", "kroger", "grocery"],
    "Dining": ["starbucks", "chipotle", "restaurant", "cafe", "coffee", "doordash", "grubhub"],
    "Transportation": ["uber", "lyft", "shell", "gas station", "chevron", "transit"],
    "Entertainment": ["netflix", "spotify", "amc", "theatres", "hulu", "disney+"],
    "Health & Fitness": ["cvs", "pharmacy", "gym", "equinox", "fitness", "clinic"],
    "Shopping": ["amazon", "target", "walmart", "best buy"],
    "Travel": ["delta", "united", "airlines", "marriott", "hotel", "airbnb"],
    "Utilities & Bills": ["con edison", "verizon", "at&t", "comcast", "electric", "water bill"],
    "Subscriptions": ["spotify", "netflix", "subscription", "membership"],
}


class ClaudeService:
    def __init__(self):
        self.mock_mode = not settings.claude_configured
        if not self.mock_mode:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=settings.anthropic_api_key)
            self.model = settings.claude_model

    # -----------------------------------------------------------------
    def categorize_transaction(self, merchant_name: str, plaid_category: str | None) -> str:
        if self.mock_mode:
            name = (merchant_name or "").lower()
            for nudge_cat, keywords in _CATEGORY_KEYWORDS.items():
                if any(k in name for k in keywords):
                    return nudge_cat
            return "Other"

        prompt = (
            f"Classify this transaction into exactly one category from this list: "
            f"{', '.join(NUDGE_CATEGORIES)}.\n"
            f"Merchant: {merchant_name}\nPlaid category: {plaid_category}\n"
            f"Respond with ONLY the category name, nothing else."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        return text if text in NUDGE_CATEGORIES else "Other"

    # -----------------------------------------------------------------
    def generate_budget(
        self,
        monthly_income: float,
        spend_ceiling: float | None,
        buffer_pct: float,
        spending_by_category: dict[str, float],
        non_negotiables: list[str],
        previous_allocations: dict[str, dict] | None = None,
    ) -> dict:
        """
        Returns {"allocations": {...}, "buffer_reserved": float,
        "reasoning": str, "engine_version": str, "prompt_version": str,
        "changes_from_previous": list[dict]}.

        The dollar amounts in "allocations" come entirely from
        app.services.budget_engine -- a deterministic function, no LLM
        involved. Claude's only role is writing the "reasoning" prose
        that explains a result it did not compute and cannot alter. This
        replaced an earlier version where Claude generated the numbers
        directly, which an evaluation harness found was only ~57%
        consistent across repeated identical requests -- unacceptable
        for a number someone might act on financially.
        """
        ceiling = spend_ceiling or (monthly_income * (1 - buffer_pct))
        buffer_reserved = round(monthly_income * buffer_pct, 2)
        spendable = round(ceiling - buffer_reserved, 2) if ceiling else round(monthly_income - buffer_reserved, 2)

        engine_result = compute_budget_allocation(spendable, buffer_reserved, spending_by_category, non_negotiables)
        is_valid, issues = validate_allocation(engine_result.allocations, spendable, non_negotiables)
        if not is_valid:
            # A hard failure here means the deterministic engine itself
            # produced something structurally wrong (e.g. over budget).
            # That's a bug to fix in budget_engine.py, not something a
            # retry against Claude papers over -- surfacing it loudly is
            # the point of having validation at all.
            raise ValueError(f"Budget engine produced an invalid allocation: {issues}")

        reasoning = self._explain_allocation(
            engine_result, monthly_income, buffer_pct, non_negotiables,
        )

        return {
            "allocations": engine_result.allocations,
            "buffer_reserved": buffer_reserved,
            "reasoning": reasoning,
            "engine_version": engine_result.engine_version,
            "prompt_version": BUDGET_PROMPT_VERSION,
            "changes_from_previous": diff_allocations(previous_allocations, engine_result.allocations),
            "validation_warnings": [i for i in issues if i.startswith("WARNING")],
        }

    def _explain_allocation(self, engine_result, monthly_income, buffer_pct, non_negotiables) -> str:
        """Prose-only explanation of an already-computed allocation. Never
        asked to produce or alter any number."""
        if self.mock_mode:
            return self._mock_explain(engine_result, non_negotiables)

        prompt = f"""The following monthly budget allocation has ALREADY been computed by a deterministic rules engine. Do not change, recompute, or restate any number differently than given -- your only job is a 2-3 sentence plain-English explanation of the logic, referencing the real figures below.

Monthly income: ${monthly_income:.2f}
Buffer reserved: ${engine_result.buffer_reserved:.2f} ({buffer_pct*100:.0f}% of income)
Spendable amount: ${engine_result.spendable:.2f}
Non-negotiable categories (funded first, from historical spend): {non_negotiables or 'none'}
Computed allocation: {json.dumps(engine_result.allocations)}

Respond with ONLY the explanation sentence(s). No JSON, no markdown, no restating the allocation as a list."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _mock_explain(self, engine_result, non_negotiables) -> str:
        non_neg_text = ", ".join(non_negotiables) if non_negotiables else "none set"
        note = ""
        if engine_result.non_negotiables_constrained:
            note = " Your non-negotiable categories alone exceed your spendable amount this month, so they were scaled down proportionally to fit -- worth reviewing your spend ceiling or income."
        return (
            f"Allocated ${engine_result.spendable:.2f} across your categories, after reserving "
            f"${engine_result.buffer_reserved:.2f} as a safety buffer. Non-negotiable categories "
            f"({non_neg_text}) were funded first from their historical spend, and the remainder "
            f"was split proportionally across the rest based on your recent spending pattern.{note}"
        )

    # -----------------------------------------------------------------
    def chat(self, user_message: str, context: dict, history: list[dict]) -> dict:
        """Conversational financial assistant grounded in the user's real data."""
        if self.mock_mode:
            return self._mock_chat(user_message, context)

        system = (
            "You are Nudge, a friendly personal finance assistant. Answer questions about the "
            "user's spending using ONLY the context data provided below. Be concise (2-4 sentences) "
            "and concrete with numbers. If asked for a chart, describe what it would show.\n\n"
            f"User financial context:\n{json.dumps(context, default=str)}"
        )
        messages = [{"role": h["role"], "content": h["content"]} for h in history[-10:]]
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system,
            messages=messages,
        )
        return {"reply": response.content[0].text.strip(), "chart_data": None}

    def _mock_chat(self, user_message: str, context: dict) -> dict:
        msg = user_message.lower()
        top_categories = context.get("top_categories", [])
        if "dining" in msg or "restaurant" in msg or "food" in msg:
            dining = next((c for c in top_categories if c.get("category") == "Dining"), None)
            amount = dining["amount"] if dining else 0
            return {
                "reply": f"You've spent ${amount:.2f} on dining this month. That's based on your linked "
                         f"transactions so far — want me to suggest where to cut back?",
                "chart_data": None,
            }
        if "save" in msg or "saving" in msg:
            buffer = context.get("buffer_status", 0)
            return {
                "reply": f"Your savings buffer is at {buffer*100:.0f}% of target. Keep non-essential "
                         f"spending under your category limits to stay on track.",
                "chart_data": None,
            }
        mtd = context.get("month_to_date_spend", 0)
        return {
            "reply": f"So far this month you've spent ${mtd:.2f}. Ask me about a specific category like "
                     f"dining, groceries, or your savings buffer for more detail.",
            "chart_data": None,
        }

    # -----------------------------------------------------------------
    def explain_anomaly(self, merchant_name: str, amount: float, typical_amount: float) -> str:
        if self.mock_mode:
            multiple = abs(amount) / max(abs(typical_amount), 1)
            return (
                f"This ${abs(amount):.2f} charge at {merchant_name} is about {multiple:.1f}x your "
                f"typical spend there. Worth a quick check if this was expected."
            )
        prompt = (
            f"A transaction of ${abs(amount):.2f} at '{merchant_name}' was flagged as unusual "
            f"(typical spend there is ${abs(typical_amount):.2f}). "
            f"Write ONE short, friendly sentence (max 25 words) explaining why this might be worth reviewing."
        )
        response = self.client.messages.create(
            model=self.model, max_tokens=60, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    # -----------------------------------------------------------------
    def price_verdict(self, product_name: str, current_price: float, price_history: list[dict]) -> dict:
        """Returns {"verdict": "buy_now"|"wait"|"overpriced", "confidence": float, "reasoning": str}"""
        prices = [p["price"] for p in price_history] if price_history else [current_price]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)

        if self.mock_mode:
            if current_price <= min_price * 1.02:
                return {"verdict": "buy_now", "confidence": 85.0,
                        "reasoning": f"${current_price:.2f} is at or near the lowest recorded price."}
            if current_price > avg_price * 1.1:
                return {"verdict": "overpriced", "confidence": 75.0,
                        "reasoning": f"${current_price:.2f} is well above the average of ${avg_price:.2f}."}
            return {"verdict": "wait", "confidence": 60.0,
                    "reasoning": f"${current_price:.2f} is near average (${avg_price:.2f}); price may drop further."}

        prompt = f"""Analyze whether to buy now or wait for this product.
Product: {product_name}
Current price: ${current_price:.2f}
Price history: {json.dumps(price_history)}
Average historical price: ${avg_price:.2f}
Lowest historical price: ${min_price:.2f}

Return ONLY valid JSON: {{"verdict": "buy_now"|"wait"|"overpriced", "confidence": <0-100 number>, "reasoning": "<1 sentence>"}}
"""
        response = self.client.messages.create(
            model=self.model, max_tokens=200, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"verdict": "wait", "confidence": 50.0, "reasoning": "Unable to parse AI response."}


claude_service = ClaudeService()
