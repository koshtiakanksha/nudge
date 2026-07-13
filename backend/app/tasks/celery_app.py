from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "nudge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.sync_tasks", "app.tasks.ai_tasks", "app.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "nightly-plaid-sync": {
            "task": "app.tasks.sync_tasks.sync_all_plaid_items",
            "schedule": crontab(hour=3, minute=0),  # 3am UTC daily
        },
        "nightly-anomaly-scan": {
            "task": "app.tasks.ai_tasks.scan_all_users_for_anomalies",
            "schedule": crontab(hour=4, minute=0),
        },
        "price-watch-refresh": {
            "task": "app.tasks.ai_tasks.refresh_all_price_watches",
            "schedule": crontab(hour="*/6", minute=0),  # every 6 hours
        },
        "weekly-pulse-email": {
            "task": "app.tasks.notification_tasks.send_weekly_pulse_emails",
            "schedule": crontab(day_of_week=1, hour=8, minute=0),  # Monday 8am UTC
        },
    },
)
