"""ASGI app factory for the OpenAirTouch runtime service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from .api_assets import mount_static_assets, validate_ui_build
from .controller import RuntimeController

try:
    from fastapi import FastAPI
except ModuleNotFoundError:  # pragma: no cover - import guard
    FastAPI = None  # type: ignore[assignment]


def create_app(controller: RuntimeController):
    if FastAPI is None:  # pragma: no cover - import guard
        raise RuntimeError("FastAPI is required for the service API. Install dependencies from requirements.txt")
    validate_ui_build()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        controller.start()
        try:
            yield
        finally:
            controller.stop()

    app = FastAPI(title="OpenAirTouch", version="0.8.8", lifespan=lifespan)
    mount_static_assets(app)

    from .api_http import register_http_routes
    from .api_websocket import register_websocket_route

    register_http_routes(app, controller)
    register_websocket_route(app, controller)

    return app
