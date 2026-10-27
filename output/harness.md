# Campus Customs Multi-Agent Operations — Harness

The harness is everything around the model that lets the agent team do real work safely: the data it can see,
the tools it can call, the rules it must follow, and the human checkpoints.

| Section | Covers |
|---|---|
| 1. Data | every table in the shop database and why it matters |
| 2 + 4. MCP tools | the 15 tools on `campus-customs-ops` and the tables each reads or writes |
| 3. Agents | the five agents, their jobs, their tools and what they return |
| 5. Safety | guardrails for money, customers, accountability and token limits |
| 6. API routes | the FastAPI backend the dashboard calls |
| 7. Dashboard | the Night Desk (React + Vite + TypeScript) |
| 8. Full run | the Problem 9 run that exercised all of it, with evidence |

## 1. Data: the shop database

Agents work on the working copy `data/campus_customs_new.db`; the original `data/campus_customs.db` is read-only
and restores the shop with `python reset_db.py`. Shop "today" is `desk.date_today` (2026-08-31).

| Table | Fields | Why it matters for the agents |
|---|---|---|
| `desk` | date_today, notes | The shop's "today": every overdue / due-soon decision uses this date, never the computer clock. |
| `tickets` | id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at | The work queue on the board: Boss reads each open ticket and routes it; status shows what is resolved. |
| `inventory` | sku, size, name, qty, location | Inventory checks stock by SKU and size to spot shortfalls before anyone promises an order. |
| `pricing` | sku, unit_cost, list_price | Accounting checks margins here before approving a discount or a purchase order. |
| `vendors` | id, name, specialty, lead_days | Inventory picks who can restock (by specialty) and how long it takes (lead_days). |
| `invoices` | id, vendor_id, amount, due_date, status, description | Unpaid vendor bills: a vendor with an open invoice will not ship, so these can block restocks. |
| `leases` | id, space_name, landlord, monthly_rent, next_due, notes | Facilities tracks the shop space and when rent is due. |
| `cash_accounts` | name, balance, date | The cash Accounting can spend; payments must never take it below zero (cash only goes out). |
| `payments` | id, kind, ref_id, amount, account, paid_at, approved_by | The record of executed, human-approved payments; written only after a person approves on the dashboard. |

## 2. Tools: the MCP server (`mcp_server/server.py`)

Every agent gets its tools from one FastMCP server that reads `data/campus_customs_new.db`. These first three
tools only read (read-only connection); tools that change data, like paying a bill, come later and will sit
behind human approval. Each tool returns only database values or arithmetic on them, and says "not found"
instead of guessing.

| Tool | Tables it reads | Ticket it unlocks | Why it is the right tool for that ticket |
|---|---|---|---|
| `check_stock_and_margin(sku, size, qty_requested)` | `inventory`, `pricing` | **103** (Yale AI Club: 20 × CC-HOOD-NAVY, size M, bulk discount) | It answers both halves of the discount request at once: stock for the exact SKU and size (8 on hand, so a shortfall of 12, with other sizes listed so nobody substitutes without asking) and the margin math (cost $22 vs list $58, so any discount up to 62% stays above cost), which lets Accounting set a discount that never sells below cost and Inventory size the restock. |
| `check_vendor_can_ship(vendor_id)` | `vendors`, `invoices`, `desk` | **101** (Tauhid Zaman: 1 × CC-TEE-WHITE, size S, linked to invoice 501) | The size-S tee is out of stock and the ticket's invoice 501 ($840 to Bulldog Print Co, "Rush reprint CC-TEE-WHITE S", due 2026-08-28) is 3 days overdue against `desk.date_today`, so this tool shows the real blocker: Bulldog will not ship the reprint until 501 is paid, and once it is, the 5-day lead time means about 2026-09-05, which is what Customer Service can honestly promise. |
| `check_rent_due(lease_id)` | `leases`, `desk`, `cash_accounts` | **102** (Elm City Properties: rent notice, lease 1) | It turns "rent due in 2 days" into a decision Accounting can bring to a human: $2,400 for the Chapel Street shop due 2026-09-02 (2 days after the shop's today, not yet overdue), $3,400 in checking, and $1,000 left after paying, so the payment can be proposed for approval without ever risking a negative balance. |

How the tools combine across tickets: paying invoice 501 ($840) and rent ($2,400) together leaves $160, while
restocking the 12 missing hoodies for ticket 103 would cost $264 at unit cost, so the agents must prioritize.

## 3. The agent team (`backend/`, PydanticAI)

Every agent runs on **gpt-6-luna through Portkey** (`config.MODEL_NAME`, `PORTKEY_API_KEY`; no other model name
appears in the code or the runs). Prompts are in `backend/prompts/<agent>.md`, data types in `backend/models.py`,
the team and its loops in `backend/team.py`. Shop facts come only from the MCP server; each agent gets a filtered
view of it (least privilege). Every agent has `ask_teammate(teammate, request)`, so any agent can ask any other
(full connectivity).

| Agent | Job | MCP tools it can use (plus `ask_teammate`) | Returns |
|---|---|---|---|
| **boss** | Reads each ticket, decides who works on it, checks the whole cash picture, makes the final call and sets the ticket's status. | `get_ticket`, `list_open_tickets`, `get_cash_position`, `list_board`, `update_ticket_status` | `TicketDecision` |
| **inventory** | Stock by SKU and size, shortfalls, which vendor can restock and when, restock purchase-order requests. | `check_stock_and_margin`, `list_vendors`, `check_vendor_can_ship`, `request_purchase_order_approval`, `get_ticket`, `list_board` | `AgentReport` |
| **accounting** | Cash, invoices, margins; prepares payments, purchase orders and discounts for human approval. | `get_cash_position`, `check_vendor_can_ship`, `check_rent_due`, `check_stock_and_margin`, `list_vendors`, `request_payment_approval`, `request_purchase_order_approval`, `request_price_override_approval`, `get_ticket`, `list_board` | `AgentReport` |
| **facilities** | The shop space: lease, landlord, rent timing. | `check_rent_due`, `get_cash_position`, `get_ticket`, `list_board` | `AgentReport` |
| **customer_service** | Kind, honest message drafts (never sent). | `check_stock_and_margin`, `save_customer_draft`, `get_ticket`, `list_board` | `AgentReport` |

## 4. All MCP tools and the tables they use

| Tool | Tables | Reads / writes | Who can call it |
|---|---|---|---|
| `check_stock_and_margin` | inventory, pricing | read | inventory, accounting, customer_service |
| `check_vendor_can_ship` | vendors, invoices, desk | read | inventory, accounting |
| `check_rent_due` | leases, desk, cash_accounts | read | accounting, facilities |
| `list_open_tickets` | tickets | read | boss |
| `get_ticket` | tickets, invoices, vendors, leases, approval_requests, drafts, desk | read | all agents |
| `get_cash_position` | cash_accounts, approval_requests, invoices, vendors, leases, desk | read | boss, accounting, facilities |
| `list_vendors` | vendors, invoices | read | inventory, accounting |
| `list_board` | approval_requests, drafts | read | all agents |
| `request_payment_approval` | invoices or leases, vendors, cash_accounts, approval_requests | writes a **pending** request (no money moves) | accounting |
| `request_purchase_order_approval` | vendors, invoices, pricing, inventory, cash_accounts, approval_requests, desk | writes a **pending** request | inventory, accounting |
| `request_price_override_approval` | pricing, approval_requests | writes a **pending** request | accounting |
| `save_customer_draft` | drafts | writes a draft (never sent) | customer_service |
| `update_ticket_status` | tickets | writes status + note (only boss may resolve) | boss |
| `record_human_decision` | approval_requests | writes approve/reject | **humans only** (dashboard) |
| `execute_approved_request` | approval_requests, payments, cash_accounts, invoices, leases, desk | moves money after approval | **humans only** (dashboard) |

`approval_requests` and `drafts` are the board: the MCP server adds these two tables to the working copy if they
are missing (a reset restores the original database; the server recreates them).

## 5. Safety: guardrails for real customers and real money

**Money**
- Agents can only *request* money moves. Payments, purchase orders and discounts sit on the board as `pending`
  until a named person approves them; the two tools that approve and pay are never given to any agent.
- The approve tool rejects agent names as approvers; the pay tool runs only on human-approved requests.
- Amounts come from the database (invoice amount, rent, qty × unit cost), never from the agent's text.
- No negative balances: requests are refused if they exceed cash minus money already committed to other open
  requests, and the pay tool re-checks the balance at payment time.
- Duplicate requests for the same bill are refused; restocks are refused while the vendor has an unpaid invoice
  that has no payment requested; discounts below unit cost are refused.
- Every executed payment writes a `payments` row with who approved it, and updates the invoice, lease and cash.
- These rules are covered by 17 offline tests in `tests/test_safety.py` (`python -m pytest tests/`; no API key or tokens needed).

**Customers and the outside world**
- Nothing is ever sent: customer, landlord and vendor messages are drafts on the board for a person to review.
- Customer service may not promise discounts, refunds or dates that a human has not approved.
- Agents use only tool facts; "not found" is returned instead of guessing.

**Accountability**
- `output/audit_trail.json` (append-only) records every agent-loop step: the prompt, each model response, every
  tool call with its arguments and result, each delegation (and each one a guard blocked), the final output and
  token usage per run.
- Least privilege: each agent sees only the tools its job needs.
- Only the boss can mark a ticket resolved.
- "Today" always comes from `desk.date_today`, so overdue logic is reproducible.

**Limits that keep token use (and loops) in check**
- No delegating to yourself or to anyone already in the current request chain (blocks A→B→A loops).
- Chain depth ≤ 3, at most 3 delegations per agent run, at most 10 agent runs per ticket.
- Identical repeated requests are answered from a cache instead of re-running an agent.
- Per agent run: ≤ 8 model requests and ≤ 60k tokens; per ticket: ≤ 250k tokens total.
- Specialists get short, specific requests (ticket id, SKU, size, ids), and prompts tell agents to accept a
  "blocked" answer instead of re-asking.
- Measured in the Problem 9 full run: 101 took 5 agent runs and 63.8k tokens, 102 took 3 runs and 28.9k, 103 took 4 runs and 41.7k.

**Lessons from the full run (Problem 9)**
- A finished run marks its ticket `resolved`, but that never moves money. Requests stay `pending` until a person signs.
- Re-running a ticket is idempotent for bills: the 102 re-run found rent request #3 on the board and created nothing.
  The dashboard now asks for confirmation before re-running a settled ticket, because a re-run still costs tokens
  (14.6k for nothing on 102, 87.3k on 103).
- **The cash guard limits money, not judgment.** On the 103 re-run, a 12-hoodie PO ($264) was refused against $152.
  The team then requested 4 + 2 hoodies ($88 + $44), each of which fit. Cash was never at risk, because committed
  money is counted, but a refused order was split until it passed, and one step was based on a misread of the
  stock. The human signature is the real check. A stricter rule would refuse a second PO for the same ticket and
  SKU after a refusal unless a person asks for it.

## 6. Backend routes (`backend/main.py`, FastAPI)

Start from the `backend/` folder: `uvicorn main:app --port 9000` → http://localhost:9000 (interactive docs at `/docs`). Port 9000 is the one the Problem 8 dashboard calls; CORS allows the Vite page at http://localhost:5173 (and 5174). Under the iCloud Desktop, `--reload` restarts spuriously and kills runs, so run without it.
All shop reads and writes go through the MCP server; the backend never edits shop tables directly (only `/api/reset` copies the original file).

- `GET  /api/tickets` — the 3 tickets with status and whether each is open or resolved (plus pending approvals and drafts per ticket).
- `POST /api/tickets/{ticket_id}/run` — starts the agent team on that ticket in the background; returns a `run_key` (refuses a second run while one is in progress). When the run finishes, the boss marks the ticket `resolved` via `update_ticket_status`, noting how many approvals still wait for a human; resolving never moves money.
- `GET  /api/runs/{run_key}` — status of that run (queued / running / done / error) and the boss's final decision.
- `GET  /api/events?since=N&ticket_id=` — recent agent events from `output/audit_trail.json`: who acted, what they said, which tools they called; poll with `since=next_since` so the board refreshes.
- `GET  /api/tickets/{ticket_id}/runs` — every finished run of the ticket in the audit trail (the board's run picker).
- `GET  /api/tickets/{ticket_id}/summary?run_id=` — what each agent did on one run (default: the latest) (summary, status, who called it, whom it asked, MCP tools used) plus the boss's ruling, built from the audit trail.
- `GET  /api/board` — everything waiting for a human: approval requests and message drafts (drafts are never sent).
- `POST /api/approvals/{request_id}/approve` — a named human approves; records the decision and executes it (the only route that changes cash; agent names are refused; refuses if cash would go negative).
- `POST /api/approvals/{request_id}/reject` — a named human rejects a pending request.
- `GET  /api/cash` — current checking balance from `cash_accounts`, plus money committed to open requests.
- `POST /api/reset` — restores `data/campus_customs_new.db` from the read-only original for a fresh run (refused while a run is in progress).
- `GET  /api/health` — server up, model (gpt-6-luna) and database file.

## 7. The dashboard: the Night Desk (`frontend/`, React + Vite + TypeScript)

Start the backend from `backend/` with `uvicorn main:app --port 9000`. Then from `frontend/`, run `npm install` once and
`npm run dev` → **http://localhost:5173**. `src/api.ts` points at `http://localhost:9000` (override with
`VITE_API_URL`), and the backend's CORS list allows the Vite origin (5173, or 5174 if 5173 is taken). The full
design write-up is in `output/design.md`.

| Part of the page | What it does | Route(s) |
|---|---|---|
| Masthead **Ledger** | Checking balance from `cash_accounts`. It counts down and shows the red loss after a signed payment, and shows money promised to pending requests | `GET /api/cash` |
| **The docket** (left) | The 3 tickets as pinned notices with status, "N to sign" and letters. A resolved ticket gets a red SETTLED stamp | `GET /api/tickets` |
| **Send the team in** | Starts the agent team on the picked ticket. It asks for confirmation if the ticket is already settled | `POST /api/tickets/{id}/run`, `GET /api/runs/{key}` |
| **The porch** | One card per agent with its live state (quiet, thinking, in the books, asking a teammate, said its piece, stopped by a guard). The speaking agent is lit, and agents never called stay dim | `GET /api/events?since=` (polled every 1.2s) |
| **The telling** | The live feed, headed by each speaker's name in its own ink and font. Shows tool chips, tool-result slips and delegations | `GET /api/events` |
| **What each one did** | After the run: the boss's ruling, plus a card per agent (summary, status, called by, asked, tools) | `GET /api/tickets/{id}/summary` |
| **Awaiting a signature** (right) | A "Signed by" line, then Sign & pay / Turn down on each pending request. The buttons stay off until a name is written | `GET /api/board`, `POST /api/approvals/{id}/approve` or `/reject` |
| **Unsent letters** | Drafts the team wrote. They are never sent | `GET /api/board` |
| **Reset the books** | Restores the working DB from the original (with a confirm step) | `POST /api/reset` |

A **run picker** under the ticket header switches between every run of that ticket (`GET /api/tickets/{id}/runs`), so a re-run never hides the main run. `/?ticket=101` opens a ticket directly, and `&run=<run_id>` opens a specific run. The screenshots in `output/resolved_board.html` were taken that way.

## 8. The full run (Problem 9): what exercised the whole harness

1. `POST /api/reset` restored the working DB; checking was **$3,400.00**.
2. Tickets were run one at a time from the API: 101 → 102 → 103. After each, a person (Eliza Wright) signed the
   requests in the dashboard before the next ticket ran.
3. Cash: $3,400 → −$840 (invoice 501) −$8 (tee PO) = $2,552 → −$2,400 (rent) = $152 → −$88 −$44 (hoodie POs) =
   **$20.00**, which equals `cash_accounts`. The $49.30 price override moved $0.
4. Evidence:
   - `output/audit_trail.json` (5 runs appended, including 2 accidental dashboard re-runs);
   - `output/run9/runs.json` (collected by `scripts/collect_run.py`);
   - `output/desk_tickets.html` (Actual sections, ✓/✗ checklist and Cash tab, built by
     `scripts/build_desk_tickets.py`);
   - `output/resolved_tickets.json` and `output/resolved_board.html` (built by `scripts/build_resolved.py`).
