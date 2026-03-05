from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Player
from app.services.game_service import get_or_create_player


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def set_player_cookie(response: Response, settings: Settings, sid: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=settings.cookie_max_age,
    )


def get_current_player(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Player:
    cookie_sid = request.cookies.get(settings.cookie_name)
    player, new_sid = get_or_create_player(db, cookie_sid)
    if new_sid:
        set_player_cookie(response, settings, new_sid)
    return player
