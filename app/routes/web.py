from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import set_player_cookie
from app.services.game_service import get_or_create_player

router = APIRouter(tags=["web"])
STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_static_path(*parts: str) -> Path:
    path = STATIC_DIR.joinpath(*parts).resolve()
    try:
        path.relative_to(STATIC_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    return path


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


@router.get("/manifest.webmanifest")
def manifest():
    return FileResponse(
        get_static_path("manifest.webmanifest"),
        media_type="application/manifest+json",
    )


@router.get("/sw.js")
def service_worker():
    return FileResponse(
        get_static_path("sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


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
