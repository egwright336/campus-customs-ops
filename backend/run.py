"""Run the agent team from the command line.

    python -m backend.run --ticket 101            # one ticket
    python -m backend.run --all --reset           # reset the working DB (shop rule), then every open ticket

Every step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3

from backend.team import DB_PATH, CampusCustomsTeam
from config import ORIGINAL_DB


def open_ticket_ids() -> list[int]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    return [r[0] for r in con.execute("SELECT id FROM tickets WHERE status != 'resolved' ORDER BY created_at")]


async def main(ticket: int | None, run_all: bool, reset: bool) -> None:
    if reset:
        shutil.copyfile(ORIGINAL_DB, DB_PATH)
        DB_PATH.chmod(0o644)
        print(f"Reset {DB_PATH.name} from {ORIGINAL_DB.name}")
    team = CampusCustomsTeam()
    ids = open_ticket_ids() if run_all else [ticket]
    for tid in ids:
        result = await team.work_ticket(tid)
        print(json.dumps(result["decision"], indent=1))
        print(f"  agent runs: {result['agent_runs']}, tokens: {result['tokens_used']:,}, "
              f"delegations: {[(d['from_agent'], d['to_agent'], d['outcome']) for d in result['delegations']]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    if not a.all and a.ticket is None:
        ap.error("give --ticket N or --all")
    asyncio.run(main(a.ticket, a.all, a.reset))
