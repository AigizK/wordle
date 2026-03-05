from __future__ import annotations

from datetime import date, datetime, time, timezone

from app.config import Settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_today(settings: Settings, now: datetime | None = None) -> date:
    current = now or utc_now()
    return current.astimezone(settings.fixed_timezone).date()


def day_start_utc(settings: Settings, day: date) -> datetime:
    local_start = datetime.combine(day, time.min, tzinfo=settings.fixed_timezone)
    return local_start.astimezone(timezone.utc)


def day_key(day: date) -> str:
    return day.isoformat()


def day_index(settings: Settings, day: date) -> int:
    return (day - settings.start_date).days
