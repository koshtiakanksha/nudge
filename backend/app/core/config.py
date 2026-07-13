"""
Central application configuration.

Every external integration has a corresponding `*_configured` property.
When a key is missing, the relevant service module falls back to a mock
implementation so the app is fully runnable out of the box.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-change-me"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:3000"

    # Supabase / DB
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nudge"
    sync_database_url: str = "postgresql://postgres:postgres@localhost:5432/nudge"
    supabase_jwt_secret: str = ""

    # Encryption
    token_encryption_key: str = ""

    # Plaid
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"
    plaid_products: str = "transactions"
    plaid_country_codes: str = "US"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Price intel
    camelcamelcamel_api_key: str = ""
    scraper_user_agent: str = "Mozilla/5.0 (NudgeBot/1.0)"

    # Deals
    google_places_api_key: str = ""
    yelp_fusion_api_key: str = ""
    flipp_api_key: str = ""
    eventbrite_api_token: str = ""

    # Inflation
    bls_api_key: str = ""

    # Investments
    alpha_vantage_api_key: str = ""

    # Email
    sendgrid_api_key: str = ""
    email_from: str = "nudge@example.com"

    # Web push
    vapid_public_key: str = ""
    vapid_private_key: str = ""

    # Monitoring
    sentry_dsn: str = ""

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # --- mock-mode flags ---
    @property
    def plaid_configured(self) -> bool:
        return bool(self.plaid_client_id and self.plaid_secret)

    @property
    def claude_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def places_configured(self) -> bool:
        return bool(self.google_places_api_key)

    @property
    def yelp_configured(self) -> bool:
        return bool(self.yelp_fusion_api_key)

    @property
    def eventbrite_configured(self) -> bool:
        return bool(self.eventbrite_api_token)

    @property
    def flipp_configured(self) -> bool:
        return bool(self.flipp_api_key)

    @property
    def camel_configured(self) -> bool:
        return bool(self.camelcamelcamel_api_key)

    @property
    def sendgrid_configured(self) -> bool:
        return bool(self.sendgrid_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
