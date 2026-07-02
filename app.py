"""PyInstaller entry point."""
import os
import sys


def _ensure_project_root_on_path() -> None:
    if getattr(sys, "frozen", False):
        return
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


if __name__ == "__main__":
    _ensure_project_root_on_path()
    from backend.main import main

    main()
