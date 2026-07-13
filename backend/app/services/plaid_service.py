"""
Plaid integration service.

When PLAID_CLIENT_ID/PLAID_SECRET are not set, every method returns
realistic mock data so the rest of the app (sync, categorization,
budgeting, forecasting) can be developed and demoed without a Plaid
account at all. Swap in real sandbox/production credentials in .env
and these same call sites start hitting the real Plaid API.
"""
import random
import uuid
from datetime import date, timedelta
from typing import Any

from app.core.config import settings

MOCK_MERCHANTS = [
    ("Starbucks", "Food and Drink", -6.75),
    ("Whole Foods Market", "Groceries", -84.32),
    ("Shell Gas Station", "Transportation", -42.10),
    ("Netflix", "Entertainment", -15.49),
    ("Amazon", "Shopping", -67.88),
    ("Chipotle", "Food and Drink", -13.20),
    ("Uber", "Transportation", -22.50),
    ("Trader Joe's", "Groceries", -56.40),
    ("Spotify", "Entertainment", -10.99),
    ("AMC Theatres", "Entertainment", -28.00),
    ("CVS Pharmacy", "Health", -19.75),
    ("Equinox Gym", "Health", -185.00),
    ("Delta Air Lines", "Travel", -412.00),
    ("Con Edison", "Utilities", -134.20),
    ("Verizon Wireless", "Utilities", -95.00),
]


class PlaidService:
    def __init__(self):
        self.mock_mode = not settings.plaid_configured
        if not self.mock_mode:
            import plaid
            from plaid.api import plaid_api

            host_map = {
                "sandbox": plaid.Environment.Sandbox,
                "production": plaid.Environment.Production,
            }
            configuration = plaid.Configuration(
                host=host_map.get(settings.plaid_env, plaid.Environment.Sandbox),
                api_key={
                    "clientId": settings.plaid_client_id,
                    "secret": settings.plaid_secret,
                },
            )
            self.client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

    # -----------------------------------------------------------------
    def create_link_token(self, user_id: str) -> dict[str, Any]:
        if self.mock_mode:
            return {"link_token": f"mock-link-token-{user_id}", "mock_mode": True}

        from plaid.model.country_code import CountryCode
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.products import Products

        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
            client_name="Nudge",
            products=[Products(p) for p in settings.plaid_products.split(",")],
            country_codes=[CountryCode(c) for c in settings.plaid_country_codes.split(",")],
            language="en",
        )
        response = self.client.link_token_create(request)
        return {"link_token": response.link_token, "mock_mode": False}

    # -----------------------------------------------------------------
    def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        if self.mock_mode:
            return {
                "access_token": f"mock-access-token-{uuid.uuid4().hex[:12]}",
                "item_id": f"mock-item-{uuid.uuid4().hex[:12]}",
            }

        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = self.client.item_public_token_exchange(request)
        return {"access_token": response.access_token, "item_id": response.item_id}

    # -----------------------------------------------------------------
    def get_accounts(self, access_token: str) -> list[dict]:
        if self.mock_mode:
            return [
                {
                    "account_id": f"mock-acc-checking-{access_token[-6:]}",
                    "name": "Plaid Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "mask": "0000",
                    "balance": round(random.uniform(800, 4500), 2),
                },
                {
                    "account_id": f"mock-acc-savings-{access_token[-6:]}",
                    "name": "Plaid Savings",
                    "type": "depository",
                    "subtype": "savings",
                    "mask": "1111",
                    "balance": round(random.uniform(2000, 15000), 2),
                },
            ]

        from plaid.model.accounts_get_request import AccountsGetRequest

        request = AccountsGetRequest(access_token=access_token)
        response = self.client.accounts_get(request)
        return [
            {
                "account_id": a.account_id,
                "name": a.name,
                "type": str(a.type),
                "subtype": str(a.subtype),
                "mask": a.mask,
                "balance": a.balances.current,
            }
            for a in response.accounts
        ]

    # -----------------------------------------------------------------
    def get_transactions(
        self, access_token: str, start_date: date, end_date: date
    ) -> list[dict]:
        """Fetch transactions for a date range. In mock mode, generates
        plausible daily spending so dashboards/forecasts have real signal."""
        if self.mock_mode:
            return self._generate_mock_transactions(access_token, start_date, end_date)

        from plaid.model.transactions_get_request import TransactionsGetRequest
        from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

        all_txns: list[dict] = []
        offset = 0
        while True:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500, offset=offset),
            )
            response = self.client.transactions_get(request)
            for t in response.transactions:
                all_txns.append(
                    {
                        "plaid_transaction_id": t.transaction_id,
                        "account_id": t.account_id,
                        "amount": -float(t.amount),  # Plaid: positive = outflow; we store outflow as negative
                        "date": t.date,
                        "merchant_name": t.merchant_name or t.name,
                        "category": t.category[0] if t.category else None,
                    }
                )
            if len(all_txns) >= response.total_transactions:
                break
            offset += 500
        return all_txns

    def _generate_mock_transactions(
        self, access_token: str, start_date: date, end_date: date
    ) -> list[dict]:
        rng = random.Random(access_token)  # deterministic per linked item
        txns = []
        current = start_date
        while current <= end_date:
            # 0-4 transactions per day
            for _ in range(rng.randint(0, 4)):
                merchant, category, base_amount = rng.choice(MOCK_MERCHANTS)
                amount = round(base_amount * rng.uniform(0.7, 1.3), 2)
                txns.append(
                    {
                        "plaid_transaction_id": f"mock-{access_token[-6:]}-{current.isoformat()}-{uuid.uuid4().hex[:8]}",
                        "account_id": f"mock-acc-checking-{access_token[-6:]}",
                        "amount": amount,
                        "date": current,
                        "merchant_name": merchant,
                        "category": category,
                    }
                )
            current += timedelta(days=1)
        return txns


plaid_service = PlaidService()
