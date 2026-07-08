"""ASGI app factory for the AirTouch runtime service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from .commands import CommandRequestError, build_transaction
from .controller import RuntimeController

ASSETS_DIR = Path(__file__).with_name("assets")
WEB_DIR = Path(__file__).with_name("web")
WEB_INDEX = WEB_DIR / "index.html"
WEB_ASSETS_DIR = WEB_DIR / "ui-assets"
WEBSOCKET_PING_INTERVAL = 15.0
WEBSOCKET_COALESCE_DELAY = 0.1

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:  # pragma: no cover - import guard
    FastAPI = HTTPException = WebSocket = WebSocketDisconnect = HTMLResponse = StaticFiles = None  # type: ignore[assignment]


def create_app(controller: RuntimeController):
    if FastAPI is None:  # pragma: no cover - import guard
        raise RuntimeError("FastAPI is required for the service API. Install dependencies from requirements.txt")
    if not WEB_INDEX.exists():
        raise RuntimeError(f"OpenAirTouch UI build is missing: {WEB_INDEX}")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        controller.start()
        try:
            yield
        finally:
            controller.stop()

    app = FastAPI(title="OpenAirTouch", version="0.8.6", lifespan=lifespan)
    if StaticFiles is not None and ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    if StaticFiles is not None and WEB_ASSETS_DIR.exists():
        app.mount("/ui-assets", StaticFiles(directory=WEB_ASSETS_DIR), name="ui-assets")
    if StaticFiles is not None and WEB_DIR.exists():
        app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return controller.health()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return WEB_INDEX.read_text(encoding="utf-8")

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

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        recent = controller.recent_events()
        cursor = len(recent)
        version = controller.change_version()
        await websocket.send_json({
            "type": "hello",
            "version": version,
            "health": controller.health(),
            "state": controller.snapshot(),
            "events": recent,
        })
        try:
            while True:
                next_version = await asyncio.to_thread(controller.wait_for_change, version, WEBSOCKET_PING_INTERVAL)
                if next_version == version:
                    await websocket.send_json({"type": "ping", "version": version})
                    continue

                await asyncio.sleep(WEBSOCKET_COALESCE_DELAY)
                version = max(next_version, controller.change_version())
                recent = controller.recent_events()
                if cursor > len(recent):
                    cursor = 0
                new_events = recent[cursor:]
                cursor = len(recent)
                if new_events:
                    await websocket.send_json({"type": "events", "version": version, "events": new_events})
                await websocket.send_json({
                    "type": "state",
                    "version": version,
                    "health": controller.health(),
                    "state": controller.snapshot(),
                    "events": recent,
                })
        except WebSocketDisconnect:
            return

    return app
