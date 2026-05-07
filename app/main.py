"""FastAPI app factory + routing."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import __version__
from app.api.v1 import cities as cities_v1
from app.core.cities import CITIES
from app.core.config import get_settings

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(cities_v1.router, prefix=settings.api_prefix, tags=["cities"])

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "cities": CITIES,
                "weights": {
                    "temperature": settings.weight_temperature,
                    "wind": settings.weight_wind,
                    "humidity": settings.weight_humidity,
                    "cloud": settings.weight_cloud,
                },
            },
        )

    return app


app = create_app()
