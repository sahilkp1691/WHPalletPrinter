#!/usr/bin/env python3
"""Write seed Excel files into data/."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.services.packlist_io import create_packlist_template_xlsx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

path = os.path.join(DATA_DIR, "packlist_template.xlsx")
with open(path, "wb") as f:
    f.write(create_packlist_template_xlsx())
print(f"wrote {path}")
