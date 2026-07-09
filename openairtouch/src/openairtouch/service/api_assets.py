"""Static asset handling for the OpenAirTouch service API."""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).with_name("assets")
WEB_DIR = Path(__file__).with_name("web")
WEB_INDEX = WEB_DIR / "index.html"
WEB_ASSETS_DIR = WEB_DIR / "ui-assets"


def validate_ui_build() -> None:
    if not WEB_INDEX.exists():
        raise RuntimeError(f"OpenAirTouch UI build is missing: {WEB_INDEX}")


def index_html() -> str:
    return WEB_INDEX.read_text(encoding="utf-8")


def mount_static_assets(app) -> None:
    try:
        from fastapi.staticfiles import StaticFiles
    except ModuleNotFoundError:  # pragma: no cover - guarded by create_app
        return

    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    if WEB_ASSETS_DIR.exists():
        app.mount("/ui-assets", StaticFiles(directory=WEB_ASSETS_DIR), name="ui-assets")
    if WEB_DIR.exists():
        app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")
