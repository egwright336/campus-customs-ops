"""Build output/desk_tickets.html: one tab per open ticket (expected plan + room for actual), plus Cash and Reflection.

    python scripts/build_desk_tickets.py

Ticket facts are read from the ORIGINAL database (read-only), so the page always shows the starting state.
Expected plans, predictions and the cash chain are written below; the Actual sections are placeholders with
the same headings. After the Problem 9 full run (scripts/collect_run.py -> output/run9/runs.json, judgement in
scripts/run9_actuals.py) the Actual sections, the ✓/✗ checklist and the Cash tab are filled from the audit trail
and the working database; the Expected sections are never changed.
"""

from __future__ import annotations

import html
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import DB_PATH, ORIGINAL_DB  # noqa: E402

RUNS_JSON = ROOT / "output" / "run9" / "runs.json"
HAVE_ACTUALS = RUNS_JSON.exists()
if HAVE_ACTUALS:
    sys.path.insert(0, str(ROOT / "scripts"))
    import run9_actuals as A  # noqa: E402
    from reflection import REFLECTION_HTML  # noqa: E402
    RUNS = {r["run_id"]: r for r in json.loads(RUNS_JSON.read_text())}

OUT = ROOT / "output" / "desk_tickets.html"
e = html.escape

con = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
TICKETS = {r["id"]: dict(r) for r in con.execute("SELECT * FROM tickets")}
TODAY = con.execute("SELECT date_today FROM desk").fetchone()[0]
CASH = con.execute("SELECT SUM(balance) FROM cash_accounts").fetchone()[0]
INV_501 = con.execute("SELECT amount FROM invoices WHERE id = 501").fetchone()[0]
RENT = con.execute("SELECT monthly_rent FROM leases WHERE id = 1").fetchone()[0]
HOOD_COST = con.execute("SELECT unit_cost FROM pricing WHERE sku = 'CC-HOOD-NAVY'").fetchone()[0]

# Cash chain: tickets run in created_at order (101 -> 102 -> 103) and share one checking account.
AFTER_101 = CASH - INV_501
AFTER_102 = AFTER_101 - RENT
RESTOCK_12 = 12 * HOOD_COST
CHAIN = [
    ("Start", "Checking balance on the shop's today", 0, CASH),
    ("101", f"Request to pay invoice 501 (${INV_501:,.0f}) is committed, not paid", INV_501, AFTER_101),
    ("102", f"Request to pay rent (${RENT:,.0f}) is committed, not paid", RENT, AFTER_102),
    ("103", f"Price override moves no cash; a 12-hoodie restock would need ${RESTOCK_12:,.0f} "
            f"but only ${AFTER_102:,.0f} is uncommitted, so it should be refused", 0, AFTER_102),
]
CASH_NOTES = {
    101: f"Goes first with all ${CASH:,.0f} uncommitted. Committing ${INV_501:,.0f} for invoice 501 leaves ${AFTER_101:,.0f}.",
    102: f"Arrives with ${AFTER_101:,.0f} uncommitted (invoice 501 already waiting). Rent of ${RENT:,.0f} fits and leaves ${AFTER_102:,.0f}.",
    103: (f"Arrives with only ${AFTER_102:,.0f} uncommitted. The discount itself moves no cash, but restocking the 12 missing "
          f"hoodies costs ${RESTOCK_12:,.0f} at ${HOOD_COST:,.0f} each, so the tool should refuse it (at most "
          f"{int(AFTER_102 // HOOD_COST)} units fit) and the team should say so instead of forcing it."),
}

PLANS = {
    101: dict(
        first=("inventory", "This is a customer order for one Bulldog tee in size S, so the first question is whether we "
               "can fill it. Inventory owns stock by exact SKU and size, and it is also the agent that can see why a restock is stuck."),
        why_not="Facilities has nothing to do with an apparel order. The boss does not need to ask accounting directly: "
                "inventory will route the invoice question there.",
        delegations=[
            ("boss → inventory", "Is CC-TEE-WHITE size S in stock for 1 unit, and if not, who restocks it and when?"),
            ("inventory → accounting", "Size S is at 0 and our apparel vendor Bulldog Print Co is blocked by open invoice 501 "
             "($840, overdue). Please put invoice 501 up for payment approval. That invoice is the rush reprint of this "
             "exact tee, so paying it should release the reprint without a new order."),
            ("boss → customer_service", "Draft a kind update to Tauhid Zaman: size S is out of stock and being restocked; no "
             "firm date until the vendor bill is approved (about 5 days after it is paid). Mention the sizes that are in "
             "stock without switching his order."),
        ],
        tools=[
            ("boss", "get_ticket(101)", "the order and its linked invoice 501"),
            ("inventory", "check_stock_and_margin(CC-TEE-WHITE, S, 1)", "0 on hand, shortfall 1; M/L/XL available as alternatives"),
            ("inventory", "check_vendor_can_ship(1)", "Bulldog Print Co blocked by invoice 501, 3 days overdue against desk.date_today; 5-day lead time"),
            ("accounting", "get_cash_position()", f"${CASH:,.0f} available before anything is committed"),
            ("accounting", "request_payment_approval(invoice, 501)", f"${INV_501:,.0f} pending human approval; no money moves"),
            ("customer_service", "save_customer_draft(101, Tauhid Zaman, ...)", "draft on the board, never sent"),
            ("boss", "update_ticket_status(101, waiting_on_human)", "waiting on the payment approval"),
        ],
        outcome=f"Ticket waits on a human: one payment request (${INV_501:,.0f} for invoice 501) and one customer draft. "
                "We do <b>not</b> expect a new purchase order, because invoice 501 is already the reprint of this tee.",
        predictions=[
            "The boss's first delegation is to inventory.",
            "Inventory reports CC-TEE-WHITE size S at 0 on hand (shortfall of 1).",
            "Inventory finds Bulldog Print Co blocked by invoice 501 ($840, 3 days overdue).",
            "Inventory hands the invoice to accounting (inventory → accounting).",
            "Exactly one payment request on the board for this ticket: invoice 501, $840, pending.",
            "No new purchase order (invoice 501 is the reprint of this tee).",
            "Customer service saves one draft to Tauhid Zaman that does not promise a firm date.",
            "Facilities is never called.",
            "0 payments made; cash stays at $3,400.",
            "The ticket ends as waiting_on_human.",
            "About 4 agent runs (boss, inventory, accounting, customer_service).",
        ],
    ),
    102: dict(
        first=("facilities", "This is a rent notice from the landlord. Facilities owns the lease, the landlord relationship "
               "and rent timing, so it should confirm what is owed and when before anyone touches money."),
        why_not="Inventory and customer service have no role: nothing is being sold and the landlord's email does not need a "
                "reply. The boss goes to facilities, not straight to accounting, so the lease owner confirms the amount and date first.",
        delegations=[
            ("boss → facilities", "Lease 1 rent: confirm the amount, the due date against the shop's today, and whether it is overdue."),
            ("facilities → accounting", f"Rent for lease 1 is ${RENT:,.0f}, due 2026-09-02 (2 days away). Please check cash and put it up for payment approval."),
        ],
        tools=[
            ("boss", "get_ticket(102)", "rent notice linked to lease 1"),
            ("facilities", "check_rent_due(1)", f"${RENT:,.0f} due 2026-09-02, 2 days after the shop's today, not overdue"),
            ("accounting", "get_cash_position()", f"${INV_501:,.0f} already committed to invoice 501, ${AFTER_101:,.0f} still available"),
            ("accounting", "request_payment_approval(rent, 1)", f"${RENT:,.0f} pending human approval; no money moves"),
            ("boss", "update_ticket_status(102, waiting_on_human)", "waiting on the rent approval"),
        ],
        outcome=f"Ticket waits on a human: one rent payment request (${RENT:,.0f}). No drafts. With invoice 501 also "
                f"pending, ${AFTER_102:,.0f} of cash stays uncommitted.",
        predictions=[
            "The boss's first delegation is to facilities.",
            "Facilities reports $2,400 due 2026-09-02, 2 days out, not overdue.",
            "Facilities hands the rent to accounting (facilities → accounting).",
            "Exactly one rent payment request: lease 1, $2,400, pending.",
            f"Accounting's cash check counts the ${INV_501:,.0f} already committed (${AFTER_101:,.0f} available before rent, ${AFTER_102:,.0f} after).",
            "No drafts are saved for this ticket.",
            "Inventory and customer service are never called.",
            "0 payments made; cash stays at $3,400.",
            "The ticket ends as waiting_on_human.",
            "About 3 agent runs (boss, facilities, accounting).",
        ],
    ),
    103: dict(
        first=("accounting", "This is a discount request, so the core decision is price. Accounting's check_stock_and_margin "
               "returns both the stock for size M (8 of 20) and the margin (cost $22, list $58) in one call, so accounting "
               "can size a safe discount without a separate inventory trip for the units we have."),
        why_not="Facilities has no role. Inventory is only needed for the restock of the 12 missing hoodies, and we expect "
                "that path to be blocked, so it is one short question, not a full workup.",
        delegations=[
            ("boss → accounting", "Yale AI Club wants 20 CC-HOOD-NAVY size M at a bulk discount. What can we supply now, "
             "what price keeps a healthy margin, and is a restock affordable?"),
            ("accounting → inventory", "Can the 12 missing size-M hoodies be restocked, from whom, and when?"),
            ("boss → customer_service", "Draft a warm reply to Yale AI Club: we have 8 in size M now; a group price is being "
             "reviewed; do not promise a price or the other 12 until a person approves."),
        ],
        tools=[
            ("boss", "get_ticket(103)", "20 × CC-HOOD-NAVY, size M, discount request"),
            ("accounting", "check_stock_and_margin(CC-HOOD-NAVY, M, 20)", "8 on hand, shortfall 12; $22 cost vs $58 list (62% margin at list)"),
            ("inventory", "list_vendors() / check_vendor_can_ship(1)", "apparel vendor Bulldog Print Co is blocked by invoice 501; 5-day lead time"),
            ("accounting", "get_cash_position()", f"only ${AFTER_102:,.0f} uncommitted, less than the ${RESTOCK_12:,.0f} a 12-hoodie restock needs"),
            ("accounting", "request_price_override_approval(103, CC-HOOD-NAVY, 8, ~$49)", "a modest bulk discount (around 15%) on the 8 we can supply, well above cost, pending human approval"),
            ("customer_service", "save_customer_draft(103, Yale AI Club, ...)", "draft on the board, never sent"),
            ("boss", "update_ticket_status(103, waiting_on_human)", "waiting on the price approval"),
        ],
        outcome="Ticket waits on a human: one price-override request for the 8 available hoodies and one customer draft. "
                "We expect <b>no</b> purchase order: the vendor is blocked and cash is short, and the team should say so instead of forcing it.",
        predictions=[
            "The boss's first delegation is to accounting.",
            "The team finds 8 of 20 size-M hoodies on hand (shortfall 12) and cost $22 vs list $58.",
            "One price-override request for the 8 available units at a modest discount (about 10–15% off), above the $22 cost.",
            f"No purchase order for the 12 missing hoodies: Bulldog is blocked and/or only ${AFTER_102:,.0f} is uncommitted vs ${RESTOCK_12:,.0f} needed.",
            "Customer service saves one draft to Yale AI Club that promises neither the discount nor the other 12 hoodies.",
            "Facilities is never called.",
            "0 payments made; cash stays at $3,400.",
            "The ticket ends as waiting_on_human.",
            "About 4 agent runs (boss, accounting, inventory, customer_service).",
        ],
    ),
}


def facts(t: dict) -> str:
    rows = [("Type", t["type"]), ("Requester", t["requester"]), ("Subject", t["subject"]), ("Notes", t["notes"]),
            ("Created", t["created_at"])]
    rows += [(k, t[k]) for k in ("sku", "size", "qty", "lease_id", "invoice_id") if t[k] is not None]
    return "<table class='facts'>" + "".join(f"<tr><th>{e(str(a))}</th><td>{e(str(b))}</td></tr>" for a, b in rows) + "</table>"


def cash_chain(tid: int) -> str:
    rows = ""
    for label, what, committed, left in CHAIN:
        cls = " class='here'" if label == str(tid) else ""
        commit = f"−${committed:,.0f}" if committed else "—"
        rows += f"<tr{cls}><td>{e(label)}</td><td>{e(what)}</td><td class='n'>{commit}</td><td class='n'>${left:,.0f}</td></tr>"
    return (f"<p>{e(CASH_NOTES[tid])}</p><table class='chain'><tr><th>Step</th><th>What happens</th>"
            f"<th>Committed</th><th>Uncommitted after</th></tr>{rows}</table>"
            "<p class='muted'>Committed means waiting on a human; no money moves until a person approves. Cash only goes out.</p>")


def checklist(preds: list[str], results: list[tuple[str, str]] | None = None) -> str:
    results = results or [("", "")] * len(preds)
    cls = {"✓": "yes", "✗": "no", "~": "part"}
    rows = "".join(f"<tr><td class='n'>{i}</td><td>{e(p)}</td><td class='res {cls.get(m, '')}'>{e(m)}</td>"
                   f"<td class='ev'>{e(ev)}</td></tr>" for i, (p, (m, ev)) in enumerate(zip(preds, results), 1))
    return (f"<table class='check'><tr><th>#</th><th>Prediction</th><th>✓ / ✗</th><th>Evidence from the run</th></tr>"
            f"{rows}</table>")


def ticket_tab(tid: int, active: bool) -> str:
    t, p = TICKETS[tid], PLANS[tid]
    dl = "".join(f"<li><b>{e(a)}</b>: {e(b)}</li>" for a, b in p["delegations"])
    tl = "".join(f"<tr><td>{e(a)}</td><td><code>{e(b)}</code></td><td>{e(c)}</td></tr>" for a, b, c in p["tools"])
    return f"""
<section id="t{tid}" class="tab{' active' if active else ''}">
 <h2>Ticket {tid} · {e(t['subject'])}</h2>
 {facts(t)}
 <div class="expected">
  <h3>Expected (written before the run)</h3>
  <h4>Who the boss should call first, and why</h4>
  <p><span class="pill">{e(p['first'][0])}</span> {e(p['first'][1])}</p>
  <p class="muted">Who we expect <i>not</i> to need: {e(p['why_not'])}</p>
  <h4>Delegations we expect</h4>
  <ol>{dl}</ol>
  <h4>MCP tools we expect the run to use</h4>
  <table class="tools"><tr><th>Agent</th><th>Tool</th><th>What it should show</th></tr>{tl}</table>
  <h4>Cash chain (tickets run 101 → 102 → 103 and share one account)</h4>
  {cash_chain(tid)}
  <h4>Expected outcome</h4>
  <p>{p['outcome']}</p>
  <h4>Predictions to check after the run</h4>
  {checklist(p['predictions'], A.PREDICTION_RESULTS[tid] if HAVE_ACTUALS else None)}
 </div>
 {actual(tid) if HAVE_ACTUALS else PLACEHOLDER_ACTUAL}
</section>"""


PLACEHOLDER_ACTUAL = """<div class="actual"><h3>Actual (filled in after the agents run)</h3>
  <p class='muted'>To be filled after the agents run.</p></div>"""


def _db():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def run_block(r: dict, label: str) -> str:
    """Who worked, who delegated to whom, and which MCP tools each agent called, for one run."""
    agents = "".join(f"<tr><td><b>{e(a['agent'])}</b></td><td>{e(a['called_by'] or 'starts the ticket')}</td>"
                     f"<td>{e(a.get('status') or '')}</td><td>{e(a.get('summary') or '')}</td></tr>"
                     for a in r["agents"])
    dels = "".join(f"<li><b>{e(d['from'])} → {e(d['to'])}</b>: {e((d['request'] or '')[:260])}"
                   f"{'…' if len(d['request'] or '') > 260 else ''}</li>" for d in r["delegations"]) or "<li>none</li>"
    tools: dict[str, list[str]] = {}
    for t in r["tools"]:
        args = ", ".join(f"{k}={v}" for k, v in (t["args"] or {}).items()
                         if k not in ("reason", "body", "note", "subject", "requested_by", "updated_by"))
        tools.setdefault(t["agent"], []).append(f"{t['tool']}({args})")
    trows = "".join(f"<tr><td><b>{e(a)}</b></td><td>{'<br>'.join(f'<code>{e(x)}</code>' for x in calls)}</td></tr>"
                    for a, calls in tools.items())
    guards = "".join(f"<li>{e(g['agent'])}: {e(g['reason'])}</li>" for g in r["guard_blocks"])
    return f"""
  <div class="run"><p class="runhead">{e(label)} · run <code>{e(r['run_id'])}</code> · {e(r['started'][11:19])}–{e(r['ended'][11:19])}
   · {r['agent_runs']} agent runs · {r['tokens_used']:,} tokens</p>
  <h4>Agents that worked</h4>
  <table><tr><th>Agent</th><th>Called by</th><th>Status</th><th>What it reported</th></tr>{agents}</table>
  <h4>Delegations that actually happened</h4><ol>{dels}</ol>
  <h4>MCP tools actually used</h4>
  <table class="tools"><tr><th>Agent</th><th>Tool calls (in order)</th></tr>{trows}</table>
  {f"<h4>Guard blocks</h4><ul>{guards}</ul>" if guards else ""}</div>"""


def ticket_money(tid: int) -> tuple[list[sqlite3.Row], float]:
    with _db() as con:
        reqs = con.execute("SELECT * FROM approval_requests WHERE ticket_id = ? ORDER BY id", (tid,)).fetchall()
    out = sum(r["amount"] for r in reqs if r["status"] == "executed" and r["kind"] != "price_override")
    return reqs, out


def actual(tid: int) -> str:
    plan = A.RUNS[tid]
    first, why = A.FIRST_CALLED[tid]
    blocks = run_block(RUNS[plan["main"]], "Main run")
    for rid in plan["extra"]:
        blocks += run_block(RUNS[rid], "Extra run (dashboard \"Send the team in again\")")
    reqs, out = ticket_money(tid)
    rows = "".join(f"<tr><td>#{r['id']}</td><td>{e(r['kind'])}</td><td>{e(r['requested_by'])}</td>"
                   f"<td class='n'>${r['amount']:,.2f}</td><td>{e(r['status'])}, {e(r['decided_by'] or '')} "
                   f"{e((r['decided_at'] or '')[11:16])}</td><td>{e(r['result'] or '')}</td></tr>" for r in reqs)
    diffs = "".join(f"<li>{d}</li>" for d in A.DIFFERENCES[tid])
    return f"""<div class="actual done">
  <h3>Actual (Problem 9 full run, from output/audit_trail.json)</h3>
  <h4>Who the boss actually called first</h4>
  <p><span class="pill">{e(first)}</span> {e(why)}</p>
  {blocks}
  <h4>Requests and human decisions</h4>
  <table><tr><th>Req</th><th>Kind</th><th>By</th><th>Amount</th><th>Decision</th><th>Result</th></tr>{rows}</table>
  <h4>Cash after this ticket</h4>
  <p>Cash out because of this ticket: <b>${out:,.2f}</b>. See the Cash tab for the running balance.</p>
  <h4>Actual outcome</h4><p>{A.OUTCOME[tid]}</p>
  <h4>Prediction results</h4><p class='muted'>Marked ✓ / ✗ / ~ (partly) in the Expected checklist above, with evidence.</p>
  <h4>Differences from the plan, and why</h4><ul>{diffs}</ul>
 </div>"""


def cash_tab() -> str:
    start = json.loads((ROOT / "output" / "run9" / "cash_start.json").read_text())["checking_balance"]
    with _db() as con:
        end = con.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
        paid_total = con.execute("SELECT COALESCE(SUM(amount), 0) FROM payments").fetchone()[0]
    rows, bal = "", start
    rows += f"<tr class='sub'><td>Start</td><td colspan='3'>After the reset (data/campus_customs_new.db restored from the original), 2026-08-31</td><td class='n'>${bal:,.2f}</td></tr>"
    for tid in (101, 102, 103):
        reqs, out = ticket_money(tid)
        for r in reqs:
            if r["status"] != "executed":
                continue
            moves = r["kind"] != "price_override"
            k = r["kind"]
            if k == "invoice_payment":
                what = f"Pay invoice {r['ref_id']} to {r['payee']}"
            elif k == "rent_payment":
                what = f"Pay rent on lease {r['ref_id']} to {r['payee']}"
            elif k == "purchase_order":
                what = f"PO {r['qty']} × {r['sku']} {r['size']} from {r['payee']} at ${r['unit_price']:,.0f} each"
            else:
                what = (f"Price override {r['qty']} × {r['sku']} at ${r['unit_price']:,.2f} "
                        "(records a price; cash only goes out)")
            if moves:
                bal -= r["amount"]
            rows += (f"<tr><td>{tid}</td><td>#{r['id']} {e(what)}</td><td>signed by {e(r['decided_by'])} "
                     f"{e(r['decided_at'][11:16])}</td><td class='n'>{'−$' + format(r['amount'], ',.2f') if moves else '$0.00'}</td>"
                     f"<td class='n'>${bal:,.2f}</td></tr>")
        rows += f"<tr class='sub'><td>{tid}</td><td colspan='2'><b>Ticket {tid} resolved: cash change</b></td><td class='n'><b>−${out:,.2f}</b></td><td class='n'><b>${bal:,.2f}</b></td></tr>"
    assert abs(bal - end) < 0.005, f"cash math {bal} != cash_accounts {end}"
    assert abs((start - end) - paid_total) < 0.005, "payments table does not match the drop in cash"
    return f"""<section id="cash" class="tab"><h2>Cash</h2>
<p>Every dollar from the Problem 9 run. Agents only <i>request</i>; each line below happened when a person
(Eliza Wright) signed in the Night Desk dashboard, and the MCP tool <code>execute_approved_request</code> wrote a
<code>payments</code> row and lowered <code>cash_accounts</code>.</p>
<table class="ledger"><tr><th>Ticket</th><th>What was paid / purchased and why</th><th>Human approval</th><th>Cash change</th><th>Checking after</th></tr>
{rows}
<tr class="end"><td>End</td><td colspan="3"><b>Ending checking balance</b>: ${start:,.2f} − ${start - end:,.2f} paid out</td><td class='n'><b>${end:,.2f}</b></td></tr>
</table>
<h4>Check against the database</h4>
<ul>
 <li><code>SELECT balance FROM cash_accounts WHERE name='checking'</code> → <b>${end:,.2f}</b>, matches the ending balance above ✓</li>
 <li><code>SELECT SUM(amount) FROM payments</code> → <b>${paid_total:,.2f}</b> = ${start:,.2f} − ${end:,.2f} ✓</li>
 <li>No balance ever went below zero. The one order that would have (12 hoodies, $264, against $152) was refused by
  <code>request_purchase_order_approval</code> ("max_units_affordable: 6").</li>
</ul>
<h4>Why each ticket moved cash</h4>
<ul>
 <li><b>101: −$848.</b> $840 cleared overdue invoice 501, which unblocked Bulldog Print Co (the shop rule: a vendor
  will not ship while it has an open unpaid invoice). $8 ordered the 1 missing white tee, size S.</li>
 <li><b>102: −$2,400.</b> One month's rent on lease 1 (due 2026-09-02, 2 days after desk.date_today). lease.next_due
  moved to 2026-10-02.</li>
 <li><b>103: −$132.</b> The price override (#4, 8 hoodies at $49.30) moved $0; it is a price, not a payment, and this
  shop records no money coming in. Two POs from the accidental rerun, 4 + 2 navy hoodies size M at $22, cost
  $88 + $44.</li>
</ul>
<h4>Expected vs actual cash</h4>
<p>The plan's cash chain ($3,400 → $2,560 → $160 uncommitted) assumed nothing would be paid during the run and that
101 and 103 would need no POs. The actual chain is $3,400 → $2,552 → $152 → $20. The differences are the human
signing between tickets, plus $8 (101's tee PO) and $132 (103's hoodie POs) that the plan did not expect.</p>
</section>"""


CSS = """
body{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;margin:0;background:#f5f6f8;color:#1d2433}
header{background:#0f2b5b;color:#fff;padding:18px 28px} header h1{margin:0;font-size:22px} header p{margin:4px 0 0;opacity:.85;font-size:14px}
nav{display:flex;gap:4px;padding:12px 28px 0;background:#e9edf3;border-bottom:1px solid #cfd6e1;flex-wrap:wrap}
nav button{border:1px solid #cfd6e1;border-bottom:none;background:#f6f8fb;padding:9px 16px;font-size:14px;cursor:pointer;border-radius:6px 6px 0 0}
nav button.active{background:#fff;font-weight:700;color:#0f2b5b}
main{max-width:1000px;margin:0 auto;padding:22px 28px 60px}
.tab{display:none} .tab.active{display:block}
h2{margin-top:0;color:#0f2b5b} h3{margin:0 0 6px} h4{margin:18px 0 6px;color:#0f2b5b}
table{border-collapse:collapse;width:100%;background:#fff;font-size:14px;margin-bottom:10px}
th,td{border:1px solid #dde3ec;padding:6px 9px;text-align:left;vertical-align:top} th{background:#f6f8fb}
.facts th{width:120px} td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.chain tr.here td{background:#eef4fb;font-weight:600}
.check td.res{width:60px;text-align:center} .check td.ev{width:32%}
.expected{background:#fff;border:1px solid #cfd6e1;border-left:5px solid #2a6496;border-radius:6px;padding:14px 18px;margin-top:10px}
.actual{background:#fafafa;border:2px dashed #c6ccd6;border-radius:6px;padding:14px 18px;margin-top:16px}
.actual h4{color:#5b6576}
.pill{display:inline-block;background:#2a6496;color:#fff;border-radius:12px;padding:1px 10px;font-weight:700;font-size:13px;margin-right:6px}
.actual.done{background:#fff;border:1px solid #cfd6e1;border-left:5px solid #b5651d;border-style:solid}
.actual.done h4{color:#7a3f0c} .run{border-top:1px dashed #d8cbb0;margin-top:12px;padding-top:6px}
.runhead{font-size:13px;color:#5b6576;margin:4px 0} td.res.yes{color:#1d7a3a;font-weight:700} td.res.no{color:#b3261e;font-weight:700} td.res.part{color:#a66a00;font-weight:700}
.ledger tr.sub td{background:#f6f8fb} .ledger tr.end td{background:#eef4fb;font-size:15px}
.muted{color:#5b6576;font-size:14px}
.lede{font-size:16px;line-height:1.55;background:#fff;border-left:5px solid #0f2b5b;padding:12px 16px}
#reflection h3{margin-top:26px;color:#0f2b5b;border-bottom:2px solid #dde3ec;padding-bottom:4px}
#reflection p,#reflection li{line-height:1.55} .grades td.g{font-size:22px;font-weight:800;color:#0f2b5b;text-align:center;white-space:nowrap}
.cases>li{margin:12px 0} code{font-size:12.5px} li{margin:5px 0}
"""

JS = """
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x===b));
 document.querySelectorAll('.tab').forEach(s=>s.classList.toggle('active',s.id===b.dataset.t));
}));
"""

if __name__ == "__main__":
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs · Desk tickets</title><style>{CSS}</style></head><body>
<header><h1>Campus Customs · Desk tickets</h1>
<p>Shop today (desk.date_today): {e(TODAY)} · starting cash ${CASH:,.0f} · 3 open tickets · expected plans written before wiring the backend; actual results from the Problem 9 full run (start ${CASH:,.0f} after reset → end ${_db().execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]:,.0f}).</p></header>
<nav>
 <button data-t="t101" class="active">Ticket 101</button><button data-t="t102">Ticket 102</button><button data-t="t103">Ticket 103</button>
 <button data-t="cash">Cash</button><button data-t="reflection">Reflection</button>
</nav>
<main>
{ticket_tab(101, True)}
{ticket_tab(102, False)}
{ticket_tab(103, False)}
{cash_tab() if HAVE_ACTUALS else '<section id="cash" class="tab"><h2>Cash</h2><p class="muted">Coming later.</p></section>'}
{REFLECTION_HTML if HAVE_ACTUALS else '<section id="reflection" class="tab"><h2>Reflection</h2><p class="muted">Coming later.</p></section>'}
</main>
<script>{JS}</script></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page):,} bytes)")
