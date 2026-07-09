"""HTTP routes for the OpenAirTouch service API."""

from __future__ import annotations

from typing import Any

from .api_assets import index_html
from .commands import CommandRequestError, build_transaction
from .controller import RuntimeController


def register_http_routes(app, controller: RuntimeController) -> None:
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return controller.health()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return index_html()

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return controller.snapshot()

    @app.get("/api/events")
    def events() -> dict[str, Any]:
        return {"events": controller.recent_events()}

    @app.post("/api/adaptive")
    async def adaptive(body: dict[str, Any]) -> dict[str, Any]:
        try:
            config = controller.update_adaptive_config(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"adaptive": config}

    @app.post("/api/runtime")
    async def runtime_config(body: dict[str, Any]) -> dict[str, Any]:
        try:
            config = controller.update_runtime_config(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"runtime": config}

    @app.post("/api/adaptive/model")
    async def adaptive_model(body: dict[str, Any]) -> dict[str, Any]:
        try:
            learning = controller.manage_adaptive_learning(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"learning": learning}

    @app.post("/api/command")
    async def command(body: dict[str, Any]) -> dict[str, Any]:
        action = str(body.get("action", ""))
        data = body.get("data", {})
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="data must be an object")
        try:
            runtime = controller.snapshot().get("runtime") or {}
            spec = build_transaction(action, data, state=runtime.get("state") or {})
        except CommandRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return controller.enqueue(spec)
