from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.user import User
from app.tasks.async_bridge import run_async
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notification_tasks.send_weekly_pulse_emails")
def send_weekly_pulse_emails():
    return run_async(_send_weekly_pulse_emails)


async def _send_weekly_pulse_emails():
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        sent = 0

        for user in users:
            month_start = date.today().replace(day=1)
            txns = (
                await db.execute(
                    select(Transaction).where(
                        Transaction.user_id == user.id,
                        Transaction.date >= month_start,
                        Transaction.amount < 0,
                    )
                )
            ).scalars().all()
            mtd_spend = sum(abs(float(t.amount)) for t in txns)

            subject = "Your weekly Nudge pulse"
            body = (
                f"Hi! You've spent ${mtd_spend:.2f} so far this month. "
                f"Log in to Nudge to see your full breakdown and forecast."
            )
            _dispatch_email(user.email, subject, body)
            sent += 1

        return {"emails_sent": sent}


def _dispatch_email(to_email: str, subject: str, body: str) -> None:
    if not settings.sendgrid_configured:
        print(f"[MOCK EMAIL] to={to_email} subject={subject!r} body={body!r}")
        return

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(from_email=settings.email_from, to_emails=to_email, subject=subject, plain_text_content=body)
    sg = SendGridAPIClient(settings.sendgrid_api_key)
    sg.send(message)
