from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _today_answer(app_setup):
    idx = (app_setup["today"] - app_setup["settings"].start_date).days
    return app_setup["tasks"][idx]["word"]


def test_cookie_created_and_progress_restored(client, app_setup):
    answer = _today_answer(app_setup)

    r = client.get("/api/state")
    assert r.status_code == 200
    assert "wordle_sid=" in r.headers.get("set-cookie", "")

    wrong_guess = "other" if answer != "other" else "alpha"
    r_guess = client.post("/api/guess", json={"guess": wrong_guess})
    assert r_guess.status_code == 200
    assert r_guess.json()["game_state"]["status"] == "in_progress"

    r2 = client.get("/api/state")
    payload = r2.json()
    assert payload["game_state"]["current_row"] == 1
    assert payload["game_state"]["guesses"][0]["guess_word"] == wrong_guess


def test_win_place_and_replay_block(app_setup):
    app = app_setup["app"]
    answer = _today_answer(app_setup)

    with TestClient(app) as c1:
        c1.get("/api/state")
        first = c1.post("/api/guess", json={"guess": answer})
        assert first.status_code == 200
        first_payload = first.json()
        assert first_payload["game_state"]["status"] == "won"
        assert first_payload["game_state"]["place"] == 1

        replay = c1.post("/api/guess", json={"guess": answer})
        assert replay.status_code == 409

    with TestClient(app) as c2:
        c2.get("/api/state")
        second = c2.post("/api/guess", json={"guess": answer})
        assert second.status_code == 200
        second_payload = second.json()
        assert second_payload["game_state"]["status"] == "won"
        assert second_payload["game_state"]["place"] == 2

        lb = c2.get("/api/leaderboard/today?limit=10")
        assert lb.status_code == 200
        items = lb.json()["items"]
        assert len(items) == 2
        assert items[0]["place"] == 1
        assert items[1]["place"] == 2


def test_share_endpoint_and_payload(client, app_setup):
    answer = _today_answer(app_setup)
    client.get("/api/state")

    win = client.post("/api/guess", json={"guess": answer})
    assert win.status_code == 200

    share = client.post("/api/share")
    assert share.status_code == 200
    url = share.json()["url"]
    token = url.rstrip("/").split("/")[-1]

    share_payload = client.get(f"/api/share/{token}")
    assert share_payload.status_code == 200
    data = share_payload.json()
    assert data["word"] == "иртәгә әйтәм"
    assert data["description"] == "иртәгә әйтәм"
    assert data["status"] == "won"
    assert len(data["guesses"]) == 1


def test_lost_state_hides_answer_until_next_day(client, app_setup):
    answer = _today_answer(app_setup)
    wrong_guess = "other" if answer != "other" else "alpha"

    client.get("/api/state")
    for _ in range(6):
        res = client.post("/api/guess", json={"guess": wrong_guess})
        assert res.status_code == 200

    state = client.get("/api/state")
    assert state.status_code == 200
    payload = state.json()["game_state"]
    assert payload["status"] == "lost"
    assert payload["answer"] is None


def test_history_returns_last_10_days_with_word_and_description(client):
    r = client.get("/api/state")
    assert r.status_code == 200

    history = r.json()["history_last_10_days"]
    assert len(history) == 10
    for item in history:
        assert item["word"]
        assert item["description"]
        assert item["day"]


def test_index_has_pwa_metadata(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html
    assert '<meta name="theme-color" content="#0f1117">' in html
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in html
    assert '<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon-180.png">' in html


def test_manifest_route_returns_valid_manifest(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    payload = json.loads(r.text)
    assert payload["name"] == "ҺҮҘЛЕ — Wordle башҡортса"
    assert payload["display"] == "standalone"
    assert payload["start_url"] == "/"
    assert any(icon.get("purpose") == "maskable" for icon in payload["icons"])


def test_service_worker_route_has_no_cache_header(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert "no-cache" in r.headers.get("cache-control", "")
    assert "CACHE_NAME" in r.text
