#!/usr/bin/env python3
"""Build assets/icon.ico from frontend/public/bga-logo.png."""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "public", "bga-logo.png")
DEST = os.path.join(ROOT, "assets", "icon.ico")
SIZES = [16, 32, 48, 64, 128, 256]


def main() -> None:
    if not os.path.isfile(SRC):
        print(f"error: logo not found at {SRC}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    img = Image.open(SRC).convert("RGBA")
    img.save(DEST, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {DEST}")


if __name__ == "__main__":
    main()
