from fastapi import APIRouter

from app.api import anomalies, budgets, chat, dashboard, deals, forecast, plaid, price_watches, statements, transactions, users

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(plaid.router)
api_router.include_router(statements.router)
api_router.include_router(transactions.router)
api_router.include_router(budgets.router)
api_router.include_router(forecast.router)
api_router.include_router(dashboard.router)
api_router.include_router(anomalies.router)
api_router.include_router(price_watches.router)
api_router.include_router(deals.router)
api_router.include_router(chat.router)
