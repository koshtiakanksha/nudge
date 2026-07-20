from fastapi import APIRouter

from app.api import affordability, anomalies, budget_actions, budgets, chat, dashboard, forecast, plaid, scenarios, statements, transactions, users

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(plaid.router)
api_router.include_router(statements.router)
api_router.include_router(affordability.router)
api_router.include_router(budget_actions.router)
api_router.include_router(transactions.router)
api_router.include_router(budgets.router)
api_router.include_router(forecast.router)
api_router.include_router(dashboard.router)
api_router.include_router(anomalies.router)
api_router.include_router(chat.router)
api_router.include_router(scenarios.router)
# price_watches and deals routers intentionally not registered -- cut from
# product scope per the refocus roadmap (see ROADMAP.md). Code kept in
# app/api/price_watches.py and app/api/deals.py, just not exposed.
