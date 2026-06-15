"""Local FastAPI web UI for AutoMap."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.ui_models import PROJECT_TITLE, repo_root
from app.ui_routes import router


def create_app() -> FastAPI:
    """Create the local-only AutoMap FastAPI app."""
    app = FastAPI(
        title=PROJECT_TITLE,
        description="Local AutoMap review UI. Dry-run publishing only.",
        version="1.1",
    )
    app.include_router(router)
    static_dir = repo_root() / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app


app = create_app()


def run_ui(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local UI server bound to localhost by default."""
    import uvicorn

    uvicorn.run("app.web_ui:app", host=host, port=port, reload=False)
