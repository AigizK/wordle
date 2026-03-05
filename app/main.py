from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings, load_settings
from app.db import create_schema, make_engine, make_session_factory
from app.routes.api import router as api_router
from app.routes.web import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or load_settings()

    app = FastAPI(title=active_settings.app_name, debug=active_settings.debug)

    engine = make_engine(active_settings.database_url)
    session_factory = make_session_factory(engine)
    create_schema(engine)

    base_dir = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))

    app.state.settings = active_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.templates = templates

    static_dir = base_dir / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    app.include_router(api_router)
    app.include_router(web_router)

    return app


app = create_app()
