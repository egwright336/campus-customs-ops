# Campus Customs: Multi-Agent Operations (MGT 409, HW 5)

Five AI agents (**boss, inventory, accounting, facilities, customer service**) work the shop's open tickets through
an **MCP server**. A **FastAPI** backend runs the team, and a **React** dashboard (the Night Desk) lets you watch the
agents live and sign payments. Every agent uses **gpt-6-luna through Portkey** and nothing else.

```
data/campus_customs.db       original database (read-only, never edited)
data/campus_customs_new.db   working copy (everything reads/writes this one)
mcp_server/server.py         MCP server "campus-customs-ops" (15 tools)
backend/                     FastAPI app (main.py), agent team (team.py), models.py, prompts/*.md
frontend/                    React + Vite + TypeScript dashboard
output/                      harness.md, design.md, desk_tickets.html, audit_trail.json, resolved_* …
scripts/                     builders for the output pages
```

## 1. Setup

You need Python 3.11+ and Node 20+.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your key in it: PORTKEY_API_KEY=...
cd frontend && npm install && cd ..
```

The real `.env` is not in this repo. `config.py` reads `PORTKEY_API_KEY` from `.env` in the project folder (or
its parent or grandparent). The model is fixed in `config.py` as `gpt-6-luna`.

## 2. Copy the original DB to the working copy (whenever you want a clean run)

```bash
python reset_db.py
```

This copies `data/campus_customs.db` to `data/campus_customs_new.db`, giving checking $3,400, three open tickets,
and today = 2026-08-31. The committed working copy holds the end state of our graded run (checking $20, all
tickets resolved), so **reset first**. You can also reset from the dashboard ("Reset the books") or with
`POST /api/reset`.

## 3. Start the MCP server

```bash
.venv/bin/python mcp_server/server.py          # stdio (what MCP clients such as Claude Code launch)
.venv/bin/python mcp_server/server.py --http   # or over HTTP at http://127.0.0.1:8001/mcp
```

`.mcp.json` registers it for Claude Code (`campus-customs-ops`). You don't need to start it by hand for the app:
the backend talks to the same server in-process, and the agent team launches it over stdio automatically. The
tools are listed in `mcp_server/README.md`.

## 4. Start the FastAPI backend (port 9000)

```bash
cd backend
../.venv/bin/uvicorn main:app --port 9000
```

API docs are at http://localhost:9000/docs. The routes are listed in `output/harness.md` §6.

## 5. Start the React board

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The board calls the backend at `http://localhost:9000` (override with
`VITE_API_URL`). Pick a ticket and press **Send the team in**, then watch the agents. Sign requests on the
right; the checking balance drops after each signed payment.

## 6. A full three-ticket run

1. **Reset the DB first:** `python reset_db.py` (or "Reset the books").
2. Run tickets **101 → 102 → 103**, one at a time, from the board or with
   `curl -X POST localhost:9000/api/tickets/101/run`.
3. After each ticket, sign or turn down its requests on the board before starting the next one.

You can also run it from the command line with no dashboard: `python -m backend.run --all --reset`. This leaves
every request pending.

## Shop rules the code enforces

- "Today" is `desk.date_today`.
- A vendor won't ship while it has an open, unpaid invoice that no one has requested payment for.
- Agents only *request*. Every payment needs a named human's approval, and the approve and pay tools are never
  given to agents.
- No negative balances. Cash only goes out.
- Nothing is ever sent: customer, landlord and vendor messages stay as drafts.
- Every agent step is appended to `output/audit_trail.json`.

Details are in `output/harness.md`. Our graded run is documented in `output/desk_tickets.html` (expected vs.
actual, cash, reflection), `output/resolved_tickets.json` and `output/resolved_board.html`.
