"""Shared settings for the MCP server and the FastAPI backend.

Both pieces read and write the WORKING copy of the shop database. The original
data/campus_customs.db is never modified, so the shop can be reset at any time
with `python reset_db.py`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ORIGINAL_DB = DATA_DIR / "campus_customs.db"        # pristine starting state (read-only)
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "campus_customs_new.db"))  # working copy the agents update

# API: PORTKEY_API_KEY from a .env in this folder, then the parent folders (course convention).
for _env in (ROOT / ".env", ROOT.parent / ".env", ROOT.parent.parent / ".env"):
    load_dotenv(_env)
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# Shop rule: every agent uses ONLY this model. Deliberately not configurable.
MODEL_NAME = "gpt-6-luna"


def portkey_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Put it in a .env file in this folder or a parent folder.")
    return key
