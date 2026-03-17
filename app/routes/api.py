from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.dependencies import get_current_player, get_db, get_settings
from app.models import Player
from app.config import Settings
from app.schemas import (
    GuessRequest,
    GuessResponseOut,
    ShareCreateResponse,
    ShareDataOut,
    StateOut,
)
from app.services.game_service import (
    GameError,
    apply_share_visibility,
    build_achievements,
    build_game_state,
    build_history_last_10_days,
    build_totals,
    get_finished_game_for_player,
    get_or_create_share_link,
    get_share_payload,
    get_today_context,
    leaderboard_for_day,
    submit_guess,
)
from app.services.time_service import local_today

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/state", response_model=StateOut)
def state(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    player: Player = Depends(get_current_player),
):
    day_available, daily_word, game, today_key = get_today_context(db, settings, player)

    leaderboard_top = []
    if day_available and daily_word is not None:
        leaderboard_top = leaderboard_for_day(db, daily_word.id, limit=10)

    game_state = build_game_state(db, game, daily_word)
    history = build_history_last_10_days(db, settings, player, local_today(settings))
    totals = build_totals(db, player)
    achievements = build_achievements(db, settings, player)

    return {
        "today": today_key,
        "day_available": day_available,
        "game_state": game_state,
        "leaderboard_top": leaderboard_top,
        "history_last_10_days": history,
        "totals": totals,
        "achievements": achievements,
    }


@router.post("/guess", response_model=GuessResponseOut)
def make_guess(
    payload: GuessRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    player: Player = Depends(get_current_player),
):
    try:
        result = submit_guess(db, settings, player, payload.guess)
    except GameError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    game_state = build_game_state(db, result.game, result.daily_word)
    leaderboard_top = leaderboard_for_day(db, result.daily_word.id, limit=10)
    totals = build_totals(db, player)
    achievements = build_achievements(db, settings, player)

    return {
        "guess": {
            "attempt_no": result.guess.attempt_no,
            "guess_word": result.guess.guess_word,
            "result_mask": result.guess.result_mask,
            "submitted_at": result.guess.submitted_at,
        },
        "game_state": game_state,
        "leaderboard_top": leaderboard_top,
        "totals": totals,
        "achievements": achievements,
    }


@router.get("/leaderboard/today")
def leaderboard_today(
    limit: int = 10,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    player: Player = Depends(get_current_player),
):
    day_available, daily_word, _game, today_key = get_today_context(db, settings, player)
    if not day_available or daily_word is None:
        return {"today": today_key, "items": []}

    bounded_limit = max(1, min(limit, 100))
    return {
        "today": today_key,
        "items": leaderboard_for_day(db, daily_word.id, bounded_limit),
    }


@router.post("/share", response_model=ShareCreateResponse)
def create_share_link(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    player: Player = Depends(get_current_player),
):
    day_available, daily_word, game, _today_key = get_today_context(db, settings, player)
    if not day_available or daily_word is None or game is None:
        raise HTTPException(status_code=409, detail="Сегодня нет доступной игры.")
    if game.status not in {"won", "lost"}:
        raise HTTPException(status_code=409, detail="Ссылку можно получить только после завершения игры.")

    share = get_or_create_share_link(db, settings, game)
    base = str(request.base_url).rstrip("/")
    return {"url": f"{base}/share/{share.token}"}


@router.post("/share/game/{game_id}", response_model=ShareCreateResponse)
def create_share_link_for_game(
    game_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    player: Player = Depends(get_current_player),
):
    game = get_finished_game_for_player(db, player.id, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Уйын табылманы.")
    if game.status not in {"won", "lost"}:
        raise HTTPException(status_code=409, detail="Ссылку можно получить только после завершения игры.")

    share = get_or_create_share_link(db, settings, game)
    base = str(request.base_url).rstrip("/")
    return {"url": f"{base}/share/{share.token}"}


@router.get("/share/{token}", response_model=ShareDataOut)
def share_data(
    token: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    payload = get_share_payload(db, token)
    if not payload:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return apply_share_visibility(settings, payload)
