from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import set_player_cookie
from app.services.game_service import get_or_create_player

router = APIRouter(tags=["web"])


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    templates = get_templates(request)
    response = templates.TemplateResponse("index.html", {"request": request})

    db = request.app.state.session_factory()
    try:
        settings = request.app.state.settings
        cookie_sid = request.cookies.get(settings.cookie_name)
        _player, new_sid = get_or_create_player(db, cookie_sid)
        if new_sid:
            set_player_cookie(response, settings, new_sid)
    finally:
        db.close()

    return response


@router.get("/share/{token}", response_class=HTMLResponse)
def share_page(request: Request, token: str):
    templates = get_templates(request)
    return templates.TemplateResponse(
        "share.html",
        {
            "request": request,
            "token": token,
        },
    )
