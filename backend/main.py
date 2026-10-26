"""Campus Customs backend (FastAPI) for the React dashboard.

Start it from the backend/ folder:
    uvicorn main:app --port 9000        ->  http://localhost:9000   (API docs at /docs)

Every shop fact and every change goes through the MCP server (mcp_server/server.py); this backend never edits
the database directly, except to reset the working copy from the read-only original. Agents only *prepare*
payments; the approve route is the only place cash changes, and it needs a named human.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_server"))

from config import DB_PATH, MODEL_NAME, ORIGINAL_DB  # noqa: E402

import server as shop_mcp  # noqa: E402  (the MCP server, called through an in-memory MCP client)
from backend.audit import AUDIT_PATH  # noqa: E402
from backend.team import CampusCustomsTeam  # noqa: E402

app = FastAPI(title="Campus Customs Ops API", version="1.0")
# The Vite dashboard (frontend/) runs on http://localhost:5173, or 5174 if 5173 is already taken.
app.add_middleware(CORSMiddleware, allow_origins=[f"http://{host}:{port}" for host in ("localhost", "127.0.0.1")
                                                  for port in (5173, 5174)],
                   allow_methods=["*"], allow_headers=["*"])

_team: CampusCustomsTeam | None = None
_run_lock = asyncio.Lock()
RUNS: dict[str, dict[str, Any]] = {}


def team() -> CampusCustomsTeam:
    global _team
    if _team is None:
        _team = CampusCustomsTeam()
    return _team


async def mcp_call(tool: str, **args) -> Any:
    """Call one MCP tool (same server and rules the agents use)."""
    async with Client(shop_mcp.mcp) as c:
        result = await c.call_tool(tool, args, raise_on_error=False)
    data = result.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        data = data["result"]
    if result.is_error:
        raise HTTPException(502, f"MCP tool {tool} failed: {data}")
    return data


# ----------------------------------------------------------------------------- tickets
@app.get("/api/tickets")
async def list_tickets():
    """The open tickets on the board and whether each is open or resolved."""
    rows = []
    for tid in (101, 102, 103):
        t = (await mcp_call("get_ticket", ticket_id=tid))
        if not t.get("found"):
            continue
        tk = t["ticket"]
        rows.append({"id": tk["id"], "type": tk["type"], "requester": tk["requester"], "subject": tk["subject"],
                     "sku": tk["sku"], "size": tk["size"], "qty": tk["qty"], "status": tk["status"],
                     "is_open": tk["status"] != "resolved",
                     "pending_approvals": sum(r["status"] == "pending" for r in t["approval_requests_on_board"]),
                     "drafts": len(t["drafts_on_board"])})
    return {"tickets": rows, "shop_today": t.get("shop_today") if rows else None}


# ----------------------------------------------------------------------------- run the agent team
async def _run_ticket(run_key: str, ticket_id: int) -> None:
    RUNS[run_key]["status"] = "running"
    try:
        async with _run_lock:
            result = await team().work_ticket(ticket_id)
        # The run is finished: the boss closes the ticket on the board. Any approvals the team prepared stay on the
        # board, pending, for a human (closing the ticket never moves money).
        waiting = result["decision"].get("approvals_waiting") or []
        note = (f"Team run finished. {len(waiting)} approval(s) left on the board for a human." if waiting
                else "Team run finished.")
        await mcp_call("update_ticket_status", ticket_id=ticket_id, status="resolved", note=note, updated_by="boss")
        RUNS[run_key].update(status="done", result=result, audit_run_id=result["run_id"])
    except Exception as exc:
        RUNS[run_key].update(status="error", error=f"{type(exc).__name__}: {exc}")
    RUNS[run_key]["finished_at"] = datetime.now().isoformat(timespec="seconds")


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int):
    """Start the agent team on one ticket (runs in the background; poll /api/runs/{run_key} and /api/events)."""
    t = await mcp_call("get_ticket", ticket_id=ticket_id)
    if not t.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if any(r["status"] in ("queued", "running") for r in RUNS.values()):
        raise HTTPException(409, "The team is already working a ticket; wait for it to finish.")
    run_key = uuid.uuid4().hex[:10]
    RUNS[run_key] = {"run_key": run_key, "ticket_id": ticket_id, "status": "queued", "model": MODEL_NAME,
                     "started_at": datetime.now().isoformat(timespec="seconds"),
                     "events_from": _audit_len()}
    asyncio.create_task(_run_ticket(run_key, ticket_id))
    return RUNS[run_key]


@app.get("/api/runs/{run_key}")
async def get_run(run_key: str):
    if run_key not in RUNS:
        raise HTTPException(404, "Unknown run.")
    return RUNS[run_key]


# ----------------------------------------------------------------------------- agent events (from the audit trail)
def _audit() -> list[dict]:
    try:
        return json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        return []


def _audit_len() -> int:
    return len(_audit())


def _simplify(i: int, e: dict) -> dict:
    """One audit entry -> what the board shows: who, what they said, which tools they used."""
    said, tools, results = [], [], []
    for p in e.get("parts", []) or []:
        if p.get("kind") == "text":
            said.append(p["text"])
        elif p.get("kind") == "tool_call" and p.get("tool") != "final_result":
            tools.append({"tool": p["tool"], "args": p.get("args")})
        elif p.get("kind") == "tool_result" and p.get("tool") != "final_result":
            results.append({"tool": p["tool"], "content": str(p.get("content", ""))[:400]})
    ev = e.get("event")
    message = None
    if ev == "agent_start":
        message = e.get("prompt")
    elif ev == "agent_end":
        out = e.get("output") or {}
        message = out.get("summary") or out.get("decision")
    elif ev in ("delegation_start", "guard_block", "delegation_cached"):
        message = e.get("request") if ev != "guard_block" else e.get("reason")
    elif ev == "delegation_end":
        message = f"{e.get('to_agent')} answered ({e.get('outcome')})"
    elif ev == "ticket_end":
        message = (e.get("decision") or {}).get("decision")
    elif ev == "ticket_error":
        message = e.get("error")
    elif said:
        message = " ".join(said)
    return {"index": i, "ts": e.get("ts"), "run_id": e.get("run_id"), "ticket_id": e.get("ticket_id"),
            "agent": e.get("agent"), "event": ev, "to_agent": e.get("to_agent"), "chain": e.get("chain"),
            "message": message, "tools_called": tools, "tool_results": results, "usage": e.get("usage")}


@app.get("/api/events")
async def events(since: int = 0, ticket_id: int | None = None, limit: int = 200):
    """Recent agent events: what each agent said and which tools it used. Poll with ?since=<next_since>."""
    data = _audit()
    out = [_simplify(i, e) for i, e in enumerate(data) if i >= since
           and (ticket_id is None or e.get("ticket_id") == ticket_id)]
    return {"events": out[-limit:], "next_since": len(data), "total": len(data)}


@app.get("/api/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int):
    """Short summary of what each agent did on this ticket's most recent run (from the audit trail)."""
    data = _audit()
    ends = [e for e in data if e.get("ticket_id") == ticket_id and e.get("event") == "ticket_end"]
    if not ends:
        return {"ticket_id": ticket_id, "has_run": False}
    run_id = ends[-1]["run_id"]
    entries = [e for e in data if e.get("run_id") == run_id]
    agents: dict[str, dict] = {}
    for e in entries:
        a = e.get("agent")
        if not a:
            continue
        info = agents.setdefault(a, {"agent": a, "tools": [], "asked": [], "asked_by": [], "summary": None,
                                     "status": None, "runs": 0, "tokens": 0})
        if e["event"] == "agent_start":
            info["runs"] += 1
            if len(e.get("chain") or []) > 1:
                info["asked_by"].append(e["chain"][-2])
        elif e["event"] == "model_response":
            for p in e.get("parts", []):
                if p.get("kind") == "tool_call" and p["tool"] not in ("final_result", "ask_teammate") \
                        and p["tool"] not in info["tools"]:
                    info["tools"].append(p["tool"])
        elif e["event"] == "delegation_start":
            info["asked"].append(e.get("to_agent"))
        elif e["event"] == "agent_end":
            out = e.get("output") or {}
            info["summary"] = out.get("summary") or out.get("decision")
            info["status"] = out.get("status") or out.get("final_status")
            u = e.get("usage") or {}
            info["tokens"] += (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
    order = ["boss", "inventory", "accounting", "facilities", "customer_service"]
    return {"ticket_id": ticket_id, "has_run": True, "run_id": run_id, "finished_at": ends[-1].get("ts"),
            "decision": ends[-1].get("decision"), "agent_runs": ends[-1].get("agent_runs"),
            "tokens_used": ends[-1].get("tokens_used"),
            "agents": [agents[a] for a in order if a in agents]}


# ----------------------------------------------------------------------------- the board and human approval
@app.get("/api/board")
async def board(ticket_id: int | None = None):
    """Everything waiting for a human: approval requests and message drafts (drafts are never sent)."""
    return await mcp_call("list_board", **({"ticket_id": ticket_id} if ticket_id is not None else {}))


class Decision(BaseModel):
    approver: str
    note: str = ""


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, body: Decision):
    """A human clicked Approve: record the decision, then carry it out. This is the ONLY route that changes cash."""
    decided = await mcp_call("record_human_decision", request_id=request_id, decision="approved",
                             approver=body.approver, note=body.note)
    if not decided.get("ok"):
        raise HTTPException(400, decided.get("error"))
    executed = await mcp_call("execute_approved_request", request_id=request_id)
    cash = await mcp_call("get_cash_position")
    return {"decision": decided["request"], "execution": executed, "cash_balance": cash["cash_balance"],
            "note": None if executed.get("ok") else "Approved, but not executed (see execution.error)."}


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, body: Decision):
    decided = await mcp_call("record_human_decision", request_id=request_id, decision="rejected",
                             approver=body.approver, note=body.note)
    if not decided.get("ok"):
        raise HTTPException(400, decided.get("error"))
    return {"decision": decided["request"]}


# ----------------------------------------------------------------------------- cash and reset
@app.get("/api/cash")
async def cash():
    """Current checking balance from cash_accounts (plus money committed to open requests)."""
    pos = await mcp_call("get_cash_position")
    return {"checking_balance": pos["cash_balances"].get("checking"), "accounts": pos["cash_balances"],
            "cash_balance": pos["cash_balance"], "committed_to_open_requests": pos["committed_to_open_requests"],
            "available_to_commit": pos["available_to_commit"], "shop_today": pos["shop_today"]}


@app.post("/api/reset")
async def reset():
    """Restore data/campus_customs_new.db from the read-only original (start a fresh run)."""
    if any(r["status"] in ("queued", "running") for r in RUNS.values()):
        raise HTTPException(409, "Cannot reset while the team is working a ticket.")
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    DB_PATH.chmod(0o644)
    return {"reset": True, "database": DB_PATH.name, "from": ORIGINAL_DB.name}


@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL_NAME, "database": DB_PATH.name}
