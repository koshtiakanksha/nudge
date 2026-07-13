from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2, environment=settings.environment)
    yield


app = FastAPI(
    title="Nudge API",
    description="Personal finance copilot — Plaid sync, AI budgeting, forecasting, anomaly detection, "
                "price intelligence, local deals, and conversational chat.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
        "mock_mode": {
            "plaid": not settings.plaid_configured,
            "claude": not settings.claude_configured,
            "supabase": not settings.supabase_configured,
        },
    }


@app.get("/")
async def root():
    return {"message": "Nudge API is running. See /docs for the interactive API explorer."}
