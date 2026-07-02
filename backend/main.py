import os
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine
from .migrations import run_migrations
from .routes import articles, print as print_routes

app = FastAPI(title="WH Pallet Printer API", docs_url="/api/docs")


@app.on_event("startup")
def _bootstrap_schema():
    os.makedirs(settings.data_dir, exist_ok=True)
    run_migrations(engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(print_routes.router)

DEV = os.getenv("WHPALLET_DEV", "false").lower() == "true"


def _frontend_dist_dir() -> str:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    return os.path.join(base, "frontend", "dist")


def _serve_frontend():
    dist = _frontend_dist_dir()
    if os.path.isdir(dist):
        app.mount("/", StaticFiles(directory=dist, html=True), name="static")


def start_server():
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings.api_port,
        log_level="info" if DEV else "error",
    )


def main():
    if not DEV:
        _serve_frontend()

    if DEV:
        start_server()
    else:
        import webview

        t = threading.Thread(target=start_server, daemon=True)
        t.start()
        time.sleep(1.5)

        window = webview.create_window(
            "WH Pallet Printer",
            f"http://127.0.0.1:{settings.api_port}",
            width=1100,
            height=760,
            resizable=True,
            min_size=(900, 600),
        )
        webview.start()


if __name__ == "__main__":
    main()
