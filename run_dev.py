#!/usr/bin/env python3
"""Development runner - starts FastAPI only (no PyWebView)."""

import os
import sys

os.environ["WHPALLET_DEV"] = "true"
sys.path.insert(0, os.path.dirname(__file__))

from backend.main import start_server

if __name__ == "__main__":
    print("WH Pallet Printer API running at http://127.0.0.1:8766")
    print("API docs:            http://127.0.0.1:8766/api/docs")
    start_server()
