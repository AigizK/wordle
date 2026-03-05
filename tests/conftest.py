from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _make_words() -> list[str]:
    return [
        "alpha",
        "bravo",
        "cabin",
        "delta",
        "eagle",
        "flame",
        "globe",
        "honey",
        "ivory",
        "joker",
        "karma",
        "lemur",
        "mango",
        "noble",
        "ocean",
        "piano",
        "quart",
        "raven",
        "solar",
        "tiger",
        "ultra",
        "vivid",
        "whale",
        "xenon",
        "yacht",
        "zebra",
        "adore",
        "bloom",
        "crane",
        "daisy",
    ]


@pytest.fixture()
def app_setup(tmp_path: Path):
    words = _make_words()
    tasks = [{"word": w, "description": f"desc {w}"} for w in words]

    tasks_path = tmp_path / "tasks.json"
    dictionary_path = tmp_path / "dictionary.txt"
    db_path = tmp_path / "wordle.db"

    tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    dictionary_path.write_text("\n".join(words + ["other"]) + "\n", encoding="utf-8")

    tz = timezone(timedelta(hours=5))
    today_local = datetime.now(timezone.utc).astimezone(tz).date()
    start_date = today_local - timedelta(days=12)

    settings = Settings(
        app_name="test",
        debug=False,
        database_url=f"sqlite:///{db_path}",
        tasks_path=tasks_path,
        dictionary_path=dictionary_path,
        start_date=start_date,
        utc_offset_hours=5,
        cookie_name="wordle_sid",
        cookie_max_age=3600,
        share_token_bytes=8,
    )

    app = create_app(settings)

    return {
        "app": app,
        "settings": settings,
        "tasks": tasks,
        "today": today_local,
    }


@pytest.fixture()
def client(app_setup):
    with TestClient(app_setup["app"]) as c:
        yield c
