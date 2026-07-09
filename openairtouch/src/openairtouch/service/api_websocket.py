"""WebSocket event stream for the OpenAirTouch service API."""

from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from .controller import RuntimeController

WEBSOCKET_PING_INTERVAL = 15.0
WEBSOCKET_COALESCE_DELAY = 0.1


def register_websocket_route(app, controller: RuntimeController) -> None:
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
