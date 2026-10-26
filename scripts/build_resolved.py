"""Problem 9 deliverables built from the audit trail, the working database and the dashboard screenshots.

    python scripts/collect_run.py && python scripts/build_resolved.py

-> output/resolved_tickets.json  (per ticket: id, final status, outcome, what each agent contributed, human approvals)
-> output/resolved_board.html    (double-click page: a screenshot of the Night Desk for each resolved ticket)
"""
from __future__ import annotations

import base64
import html
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import DB_PATH  # noqa: E402
import run9_actuals as A  # noqa: E402

RUNS = {r["run_id"]: r for r in json.loads((ROOT / "output" / "run9" / "runs.json").read_text())}
START = json.loads((ROOT / "output" / "run9" / "cash_start.json").read_text())["checking_balance"]
con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
strip = lambda s: html.unescape(s.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))


def contributions(run_ids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for rid in run_ids:
        r = RUNS[rid]
        tools: dict[str, list[str]] = {}
        for t in r["tools"]:
            tools.setdefault(t["agent"], [])
            if t["tool"] not in tools[t["agent"]]:
                tools[t["agent"]].append(t["tool"])
        for a in r["agents"]:
            out.setdefault(a["agent"], []).append(
                f"[run {rid}, called by {a['called_by'] or 'nobody (starts the ticket)'}; tools: "
                f"{', '.join(tools.get(a['agent'], [])) or 'none'}] {a.get('summary') or ''}")
    return out


tickets, bal = [], START
for tid in (101, 102, 103):
    t = con.execute("SELECT * FROM tickets WHERE id = ?", (tid,)).fetchone()
    plan = A.RUNS[tid]
    run_ids = [plan["main"], *plan["extra"]]
    reqs = con.execute("SELECT * FROM approval_requests WHERE ticket_id = ? ORDER BY id", (tid,)).fetchall()
    drafts = con.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (tid,)).fetchall()
    out = sum(r["amount"] for r in reqs if r["status"] == "executed" and r["kind"] != "price_override")
    before, bal = bal, bal - out
    tickets.append({
        "id": tid,
        "subject": t["subject"],
        "requester": t["requester"],
        "final_status": t["status"],
        "short_outcome": strip(A.OUTCOME[tid]),
        "boss_decision": RUNS[plan["main"]]["decision"]["decision"],
        "runs": [{"run_id": rid, "kind": "main" if rid == plan["main"] else "extra (dashboard re-run)",
                  "started": RUNS[rid]["started"], "ended": RUNS[rid]["ended"],
                  "agent_runs": RUNS[rid]["agent_runs"], "tokens_used": RUNS[rid]["tokens_used"],
                  "delegations": [f"{d['from']} -> {d['to']}" for d in RUNS[rid]["delegations"]]} for rid in run_ids],
        "agent_contributions": contributions(run_ids),
        "agents_not_called": [a for a in ("boss", "inventory", "accounting", "facilities", "customer_service")
                              if a not in contributions(run_ids)],
        "human_approvals": [{"request_id": r["id"], "kind": r["kind"], "amount": r["amount"], "payee": r["payee"],
                             "requested_by": r["requested_by"], "status": r["status"], "decided_by": r["decided_by"],
                             "decided_at": r["decided_at"], "result": r["result"],
                             "moved_cash": r["kind"] != "price_override" and r["status"] == "executed"} for r in reqs],
        "drafts_unsent": [{"draft_id": d["id"], "recipient": d["recipient"], "subject": d["subject"],
                           "status": d["status"]} for d in drafts],
        "cash": {"checking_before": before, "cash_out": out, "checking_after": bal},
    })

end = con.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
assert abs(bal - end) < 0.005, (bal, end)
doc = {"run": "Problem 9 full run (reset, then 101 -> 102 -> 103, human signing in the Night Desk after each)",
       "model": "gpt-6-luna via Portkey", "shop_today": con.execute("SELECT date_today FROM desk").fetchone()[0],
       "checking_start": START, "checking_end": end, "checking_end_matches_cash_accounts": True,
       "tickets": tickets}
(ROOT / "output" / "resolved_tickets.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))

# ---- resolved_board.html: screenshots embedded as data URIs, so the file works on its own
shots = ""
for tk in tickets:
    png = ROOT / "output" / "screenshots" / f"board_{tk['id']}.png"
    data = base64.b64encode(png.read_bytes()).decode()
    appr = "".join(f"<li>#{a['request_id']} {html.escape(a['kind'])} ${a['amount']:,.2f}: {html.escape(a['status'])} by "
                   f"{html.escape(a['decided_by'] or '—')}</li>" for a in tk["human_approvals"])
    shots += f"""
<section>
 <h2>Ticket {tk['id']} · {html.escape(tk['subject'])} <span class="stamp">{html.escape(tk['final_status'])}</span></h2>
 <p class="meta">Checking ${tk['cash']['checking_before']:,.2f} → <b>${tk['cash']['checking_after']:,.2f}</b>
  (−${tk['cash']['cash_out']:,.2f}) · screenshot taken right after the human signed this ticket's requests.</p>
 <p>{html.escape(tk['short_outcome'])}</p>
 <ul class="appr">{appr}</ul>
 <img src="data:image/png;base64,{data}" alt="Night Desk board for ticket {tk['id']} after it was resolved">
</section>"""

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Customs · Resolved board</title><style>
body{{margin:0;background:#0e1a2e;color:#efe3c8;font-family:Georgia,'Source Serif 4',serif}}
header{{padding:22px 32px;border-bottom:1px solid #c9a24a66}} h1{{margin:0;font-variant:small-caps;letter-spacing:.02em}}
header p{{margin:6px 0 0;color:#cfc4ab}} main{{max-width:1180px;margin:0 auto;padding:10px 32px 60px}}
section{{margin:34px 0;padding-bottom:20px;border-bottom:1px dashed #c9a24a55}} h2{{font-variant:small-caps}}
.stamp{{font:700 13px/1 'Arial Narrow',sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#d4544b;border:3px double #d4544b;padding:3px 8px;margin-left:10px;display:inline-block;transform:rotate(-6deg)}}
.meta{{color:#c9a24a}} img{{width:100%;border:1px solid #c9a24a88;border-radius:4px;box-shadow:0 10px 30px #0008}}
.appr{{color:#cfc4ab;font-size:15px}} table{{border-collapse:collapse}} td,th{{border:1px solid #c9a24a55;padding:6px 12px;text-align:right}}
</style></head><body>
<header><h1>Campus Customs · The Night Desk, all three tickets resolved</h1>
<p>Problem 9 full run on {doc['shop_today']} (desk.date_today) · gpt-6-luna via Portkey ·
checking ${START:,.2f} after the reset → <b>${end:,.2f}</b> at the end, which matches <code>cash_accounts</code> ·
screenshots captured from the React dashboard at http://localhost:5173/?ticket=N.</p></header>
<main>{shots}</main></body></html>"""
(ROOT / "output" / "resolved_board.html").write_text(page)
print("wrote output/resolved_tickets.json and output/resolved_board.html", f"(end ${end:,.2f})")
