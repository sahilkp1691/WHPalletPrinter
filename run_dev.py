#!/usr/bin/env python3
"""Development runner - starts FastAPI only (no PyWebView)."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")


def _in_project_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _ensure_venv_python() -> None:
    if _in_project_venv():
        return
    if os.path.isfile(VENV_PY) and os.path.realpath(sys.executable) != os.path.realpath(VENV_PY):
        os.execv(VENV_PY, [VENV_PY, *sys.argv])


_ensure_venv_python()

os.environ["WHPALLET_DEV"] = "true"
sys.path.insert(0, ROOT)

from backend.main import start_server

if __name__ == "__main__":
    print("WH Pallet Printer API running at http://127.0.0.1:8766")
    print("API docs:            http://127.0.0.1:8766/api/docs")
    start_server()
