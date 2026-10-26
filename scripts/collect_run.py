"""Collect what actually happened in the Problem 9 full run from output/audit_trail.json.

    python scripts/collect_run.py            -> output/run9/runs.json

Every ticket_start..ticket_end block since the Problem 9 reset (audit index FROM) becomes one run: which agents
worked (and who called them), every delegation, every MCP tool each agent called, guard blocks, and tokens.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "output" / "audit_trail.json"
OUT = ROOT / "output" / "run9" / "runs.json"
FROM = 383  # first audit entry after the Problem 9 reset (earlier entries are older test runs)

audit = json.loads(AUDIT.read_text())
runs: dict[str, dict] = {}
for i, e in enumerate(audit[FROM:], FROM):
    rid = e.get("run_id")
    if not rid:
        continue
    r = runs.setdefault(rid, {"run_id": rid, "ticket_id": e.get("ticket_id"), "first_index": i, "agents": [],
                              "delegations": [], "tools": [], "guard_blocks": [], "decision": None,
                              "agent_runs": None, "tokens_used": None})
    ev, agent = e["event"], e.get("agent")
    if ev == "ticket_start":
        r["started"] = e["ts"]
    elif ev == "agent_start":
        chain = e.get("chain") or [agent]
        r["agents"].append({"agent": agent, "called_by": chain[-2] if len(chain) > 1 else None})
    elif ev == "delegation_start":
        r["delegations"].append({"from": agent, "to": e.get("to_agent"), "request": e.get("request")})
    elif ev == "guard_block":
        r["guard_blocks"].append({"agent": agent, "to": e.get("to_agent"), "reason": e.get("reason")})
    elif ev == "model_response":
        for p in e.get("parts") or []:
            if p.get("kind") == "tool_call" and p.get("tool") not in ("final_result", "ask_teammate"):
                r["tools"].append({"agent": agent, "tool": p["tool"], "args": p.get("args")})
    elif ev == "agent_end":
        out = e.get("output") or {}
        for a in reversed(r["agents"]):
            if a["agent"] == agent and "summary" not in a:
                a["summary"] = out.get("summary") or out.get("decision")
                a["status"] = out.get("status") or out.get("final_status")
                break
    elif ev == "ticket_end":
        r.update(ended=e["ts"], decision=e.get("decision"), agent_runs=e.get("agent_runs"),
                 tokens_used=e.get("tokens_used"))

OUT.write_text(json.dumps(list(runs.values()), indent=1))
print(f"wrote {OUT.relative_to(ROOT)}: {len(runs)} runs")
