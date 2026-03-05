from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    debug: bool
    database_url: str
    tasks_path: Path
    dictionary_path: Path
    start_date: date
    utc_offset_hours: int
    cookie_name: str
    cookie_max_age: int
    share_token_bytes: int

    @property
    def fixed_timezone(self) -> timezone:
        return timezone(timedelta(hours=self.utc_offset_hours))


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent

    app_name = os.getenv("APP_NAME", "Wordle Bashkir")
    debug = _as_bool(os.getenv("DEBUG"), default=False)
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{root / 'wordle.db'}")
    tasks_path = Path(os.getenv("TASKS_PATH", str(root / "data" / "tasks.json")))
    dictionary_path = Path(
        os.getenv("DICTIONARY_PATH", str(root / "data" / "dictionary.txt"))
    )
    start_date_raw = os.getenv("START_DATE", "2026-03-05")
    start_date = date.fromisoformat(start_date_raw)
    utc_offset_hours = int(os.getenv("UTC_OFFSET_HOURS", "5"))
    cookie_name = os.getenv("COOKIE_NAME", "wordle_sid")
    cookie_max_age = int(os.getenv("COOKIE_MAX_AGE", str(365 * 24 * 60 * 60)))
    share_token_bytes = int(os.getenv("SHARE_TOKEN_BYTES", "12"))

    return Settings(
        app_name=app_name,
        debug=debug,
        database_url=database_url,
        tasks_path=tasks_path,
        dictionary_path=dictionary_path,
        start_date=start_date,
        utc_offset_hours=utc_offset_hours,
        cookie_name=cookie_name,
        cookie_max_age=cookie_max_age,
        share_token_bytes=share_token_bytes,
    )
