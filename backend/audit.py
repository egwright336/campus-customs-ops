"""Append-only audit trail: output/audit_trail.json.

The file is one JSON array. Every agent-loop step (what went into the model, what came back, each tool call and
its result, every delegation, every guard that blocked something, and token usage per run) is appended as one
entry. Existing entries are never removed, so the file accumulates across runs.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_LOCK = threading.Lock()
MAX_TEXT = 4000


def _clip(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT else value[:MAX_TEXT] + f"... [{len(value) - MAX_TEXT} more chars]"
    return value


def append(entry: dict) -> None:
    """Append one entry (thread-safe). Creates the file as [] the first time; never truncates it."""
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), **{k: _clip(v) for k, v in entry.items()}}
    with _LOCK:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
        except json.JSONDecodeError:  # never lose history: keep the damaged file and start a fresh array
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json"))
            data = []
        data.append(entry)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, default=str))
        tmp.replace(AUDIT_PATH)
