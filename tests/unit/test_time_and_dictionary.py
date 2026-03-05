from datetime import date

import pytest

from app.config import Settings
from app.services.time_service import day_index
from app.services.word_data import load_dictionary


def test_day_index_from_start_date():
    settings = Settings(
        app_name="test",
        debug=False,
        database_url="sqlite:///tmp.db",
        tasks_path=__import__("pathlib").Path("/tmp/tasks.json"),
        dictionary_path=__import__("pathlib").Path("/tmp/dict.txt"),
        start_date=date(2026, 3, 5),
        utc_offset_hours=5,
        cookie_name="sid",
        cookie_max_age=10,
        share_token_bytes=8,
    )
    assert day_index(settings, date(2026, 3, 5)) == 0
    assert day_index(settings, date(2026, 3, 6)) == 1


def test_dictionary_rejects_non_5_char_words(tmp_path):
    dict_path = tmp_path / "dict.txt"
    dict_path.write_text("alpha\nxx\n", encoding="utf-8")
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text("[]", encoding="utf-8")

    settings = Settings(
        app_name="test",
        debug=False,
        database_url="sqlite:///tmp.db",
        tasks_path=tasks_path,
        dictionary_path=dict_path,
        start_date=date(2026, 3, 5),
        utc_offset_hours=5,
        cookie_name="sid",
        cookie_max_age=10,
        share_token_bytes=8,
    )

    with pytest.raises(ValueError):
        load_dictionary(settings)
