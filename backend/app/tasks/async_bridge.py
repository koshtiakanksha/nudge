"""Celery tasks run in a sync worker process; the rest of the app is async
SQLAlchemy. This helper runs an async coroutine to completion inside a task,
creating a fresh event loop each time (safe for Celery's prefork workers)."""
import asyncio
from typing import Any, Awaitable, Callable


def run_async(coro_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro_func(*args, **kwargs))
    finally:
        loop.close()
