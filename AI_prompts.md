# AI_prompts.md — HW 5: Campus Customs Multi-Agent Operations

Log of what I (the student) typed to my vibe coder (Claude Code), kept up to date as I work.
One section per problem: the problem number and title, at least one prompt I typed, and follow-up prompts when needed.

---

## Problem 1 — Vibe coder prompts (this log)

### Prompt I typed

> create ai_prompts.md at the start of the assignment and keep it updated as we work. this is the log of what I am going to type to the vibe coder. put one section for each problem. each section must include: the problem # and title, at least one prompt i typed, one follow-up prompt if necessary

### Follow-up prompts (setting up the scenario, data and rules at the start)

> here's our scenario first: campus customs multi-agent operations is the agentic team that runs the shopp. open tickets land on a baord -- customer orders, rent, unpaid bills, discount requests, whatever the shop has to handle. we're goign to build 3 pieces that talk to each other: an MCP server, a FastAPI backend with a multi-agent team, and a react dashboard so a human can watch the agents work and approve requests. The agent team has full connectivity - any agent may delegate tasks to any other agent for help. In this assignment we're going to build these agents:

> * boss -- reads each tickert, decides who should work on it, and makes final calls
> * inventory -- checks stock by SKU and size, spots shortfalls, and figures out who can restock
> * accounting -- watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval
> * facilities -- handles the shop space side
> * customer service -- drafts messages for customers and is known for kindness

> this is the data/campus_customs.db. this file is the original shop database. tables include desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, an d invoices. our tools are going to update the database as tickets get resolved. Make a copy of the database file called data/campus_customs_new.db and piont the MCP server and backend at that workign copy. Keep campus_customs untouched so we can reset when we want to restart resolving the tickets

> we have some rules
>
> [screenshot of the assignment's "Rules of this shop"]:
> - The field `desk.date_today` is "today" for the shop. Use this date to determine what is overdue.
> - Vendor lead times come from the `vendors` table
> - A vendor will not ship new product while they still have an open unpaid invoice
> - Human approval is required for any payments. Points will be deducted if this is not done. If payment is made, make sure to update the relevant table.
> - If there is not enough cash, the pay tool must refuse — no negative balances
> - Cash only goes out in this homework — we did not model revenue, so no money comes in
> - Before a full run to resolve the tickets, make sure to reset the database to the original values
> - Do **not** email customers or call real vendors. Drafts stay on the board
> - Use your `PORTKEY_API_KEY` for AI calls. For this assignment, use **only** `gpt-6-luna` through Portkey for every agent. Points will be deducted if any other model shows up in your code or runs.

### What was built (evidence)

- `AI_prompts.md` — this log, one section per problem, updated as the work happens.
- `data/campus_customs.db` — original shop database from the course zip; set read-only so it is never modified.
- `data/campus_customs_new.db` — working copy (identical checksum at creation) that tools will update.
- `config.py` — shared `DB_PATH` (points to `data/campus_customs_new.db`) for the MCP server and the backend.
- `reset_db.py` — `python reset_db.py` restores the working copy from the original to restart ticket resolution.
- Check: writing to the original raises `attempt to write a readonly database`; the working copy opens normally.
- `RULES.md` — the shop rules, enforced in code; `config.py` hard-codes `MODEL_NAME = "gpt-6-luna"` via Portkey (`PORTKEY_API_KEY`).

---

## Problem 2 — Explore the shop database

### Prompt I typed

> this is problem 2: open data/campus_customs.db and look through every table and its fields. copy the original file to data/campus_customs_new.db -- later problems update that working copy. study the 3 open tickets so we can see how they link to other tables.

### Follow-up prompt

> start output/harness.md for each table, list the fields and one short line on why that table matters for the agents. we're going to keep growing this harness file in later problems.

### What was built (evidence)

- Re-copied the original to `data/campus_customs_new.db` with `python reset_db.py` (checksums match: `f447ca6a…`).
- `output/database_notes.md` — every table and field, the 3 open tickets, and how they link (invoice 501 overdue and blocking Bulldog Print Co; rent $2,400 due 2026-09-02; hoodie shortfall of 12; only $160 left after both payments).
- `output/harness.md` — started: each table's fields and one line on why it matters to the agents (to be extended in later problems).

---

## Problem 3 — Build the MCP server

### Prompt I typed

> this is problem 3: build the MCP server. write an MCP server in mcp_server/ using FastMCP. it will talk to data/campus_customs_new.db. you do not need to connect or run it in this problem. every agent in this hw uses the tools in thi sMCp server. you will add more tools to it later; for now write three tools you know you will need for the tickets in the database. keep the names clear. NEVER invent any data, only use real information in the database. In output/harness.md, list each of your three MCp tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why that tool is the right one for that ticket. vague lines like "reads inventory" score low -- tie the tool to the ticket with as much sophistication as is necessary. also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has.

### What was built (evidence)

- `mcp_server/server.py` — FastMCP server `campus-customs-ops` reading `config.DB_PATH` (`data/campus_customs_new.db`) through a read-only connection, with three tools: `check_stock_and_margin`, `check_vendor_can_ship`, `check_rent_due`.
- Tested in-process with the FastMCP client: hoodie M shows 8 on hand / shortfall 12 / cost $22 vs list $58; vendor 1 is blocked by invoice 501 ($840, 3 days overdue, arrival 2026-09-05 once paid); lease 1 rent $2,400 due in 2 days with $1,000 left after paying; unknown ids return "not found".
- `output/harness.md` — new section 2: each tool, the tables it reads, the ticket it unlocks and why.
- `mcp_server/README.md` — what the server is for, the database it uses, and the three tools.

---

## Problem 4 — Connect the MCP server to the vibe coder and test each tool

### Prompt I typed

> this is probelm 4: add the MCP server to vibe coder and test each tool. ass your MCP server to this project so the vibe coder can call the tools. save the connection JSON text in .mcp.json at the project root. with the vibe coder connected, test each of our 3 MCP tools. Save the evidence in output/mcp_smoke.json. For every tool include: the prompt I asked the vibe coder, the tool name, the tool output (must match values in data/campus_customs_new.db)

### What was built (evidence)

- `.mcp.json` (project root) — connection JSON for the `campus-customs-ops` server (stdio: the project's Python runs `mcp_server/server.py`).
- Checked that this exact `.mcp.json` launches the server over stdio and lists the 3 tools.
- `mcp_server/verify_smoke.py` — re-reads the database with SQL and checks every saved tool output in `output/mcp_smoke.json` (PASS/FAIL per tool).
- `CLAUDE.md` — HW 5 working rules for the vibe coder session that has the MCP server connected.

---

## Problem 5 — Build the agent team and grow the MCP tools

### Prompt I typed

> this is problem 5: build the agent team and grow the MCP tools. Build the agentic team for campus customs using pydanticAI: boss, inventory, accounting, facilities, and customer service. INclude prompts, models, and agent loops so they can delegate work to each other with full connectivity. Try to prevent any issues where they get stuck on loops within/with each other. Put the agent prompts in backend/prompts/ - one file per agent. Put data types in backend/models.py and the agent files under backend. use your portkey_API_KEy and only gpt-6-luna for every agent. Make sure the agents are polite and solutions-oriented. write the prompt in our own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt. try to be as thorough as you can be without being unnecessarily complicated. add any tools the agents need to our MCP server so they can work on the open tickets. Shop facts comr from the MCp server over data/campus_customs_new.db, do not invent a second shop-tools layer that bypasses MCP. Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. append to this file, don't wipe it each run. in output/harness.md, list each agent and each MCP tool (including ones we add in this problem) along with which table the tool uses. Also add a safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check. update mcp_server/readme so the tool list matches what we have now

> (follow-up, after the MCP server connected to the vibe coder session) this is probelm 4: add the MCP server to vibe coder and test each tool. ... [re-sent the Problem 4 prompt to run the tests]

### Smoke test (evidence)

- The vibe coder called all 3 tools through the `campus-customs-ops` MCP connection (`mcp__campus-customs-ops__*`).
- `output/mcp_smoke.json` — for each tool: my prompt, the tool name, the arguments and the exact tool output.
- `python mcp_server/verify_smoke.py` → PASS for all 3 tools; every value matches `data/campus_customs_new.db`
  (hoodie M: 8 on hand, shortfall 12, $22 cost / $58 list; Bulldog Print Co blocked by $840 invoice 501, 5-day lead;
  lease 1 rent $2,400 due 2026-09-02, 2 days out, $3,400 cash).

### What was built (evidence)

- `backend/prompts/` — one detailed prompt per agent (boss, inventory, accounting, facilities, customer_service): role, scope, tools, the shop rules each needs, when to ask which teammate, tone (polite, solutions-oriented), and the expected output.
- `backend/models.py` — data types: `AgentReport`, `TicketDecision`, `Finding`, `BoardAction`, `Delegation`.
- `backend/team.py` — PydanticAI team on gpt-6-luna via Portkey; each agent gets a filtered view of the one MCP server; `ask_teammate` gives full connectivity; loop guards (no self/chain delegation, depth ≤ 3, ≤ 3 delegations per run, ≤ 10 agent runs and 250k tokens per ticket, cached repeats, ≤ 8 requests / 60k tokens per run).
- `backend/audit.py` — appends every agent-loop step to `output/audit_trail.json` (never wiped).
- `backend/run.py` — `python -m backend.run --ticket 102` or `--all --reset`.
- MCP server grew from 3 to 15 tools (tickets, cash, vendors, board; payment/PO/discount *requests*; drafts; status). Two human-only tools (record decision, execute approved payment) are never given to agents and refuse agent approvers and negative balances. Tested on a scratch copy: restock refused while invoice 501 unpaid, duplicate refused, hoodie PO refused for cash ($160 available), $20 hoodie refused below cost, agent cannot approve or resolve, human-approved $840 payment wrote `payments` and set cash to $2,560.
- Live run, ticket 102: boss → facilities + accounting; rent request #1 ($2,400) left **pending** for a human; 3 agent runs, ~29k tokens; 34 audit entries; only `gpt-6-luna` in the trail. Database reset afterwards.
- `output/harness.md` — sections 3–5: every agent, every MCP tool with its tables, and the safety section (guardrails + token limits).
- `mcp_server/README.md` — tool list updated to all 15 tools.

> (follow-up) you're sure everything is running correctly?

- Full live run from a reset (`python -m backend.run --all --reset`): all 3 tickets ended `waiting_on_human` with 0 payments made and cash still $3,400.
  - 101: requests #1 (pay invoice 501, $840) and #2 (PO 1 × tee S, $8, only after 501); kind draft #1 to Tauhid Zaman (offers in-stock sizes, no promised date). 5 agent runs, ~57k tokens.
  - 102: request #3 (rent $2,400). 3 agent runs, ~29k tokens.
  - 103: request #4 (8 hoodies at $49.30 = 15% off, 55% margin, only the units in stock); draft #2 to Yale AI Club. 4 agent runs, ~40k tokens.
- Loop guards tested directly (no model calls): self-delegation, A→B→A loop, depth limit, per-run cap, unknown agent and per-ticket cap are all blocked and logged as `guard_block` in the audit trail.
- Audit trail: 172 entries after these runs, 0 errors, only `gpt-6-luna`.

---

## Problem 6 — Expected plan per ticket (desk_tickets.html)

### Prompt I typed

> this is problem 6: before we wire the backend, write down what you expect the team to do on each open ticket. build output/desk_tickets.html -- a page I can double click with one tab per ticket (101, 102, and 103). Also add empty cash and relfection tabs for later problems (leave them blank or with a short "coming later" note for now. On each ticket tab, fill an expected section only (leave room for actual secion to be filled after the agents are run). For each ticket's expected section, write in our own words: who the boss should call first and why, all the agent delegations we expect, and and which MCp tools we expect that run to use. plans that send every specialist on every ticket score low. we will compare this plan to what actually happens when the agents resolve the 3 tickets.

### Follow-up prompts

> how can we improve the html you sent?

> add 1, 3, and 6

### What was built (evidence)

- `output/desk_tickets.html` — double-click page with tabs Ticket 101 / 102 / 103 / Cash / Reflection (no external files). Each ticket tab shows the ticket's real fields from the database, an **Expected** section (who the boss calls first and why, who is *not* needed, every expected delegation, each MCP tool with what it should show, expected outcome) and an empty **Actual** box for after the run. Cash and Reflection say "Coming later."
- Plan in brief (lean, not every specialist on every ticket):
  - 101: boss → inventory first (stock question); inventory → accounting (pay invoice 501, which is the reprint of this tee, so no new PO expected); boss → customer_service (draft). No facilities.
  - 102: boss → facilities first (owns the lease); facilities → accounting (rent payment request). No inventory or customer service.
  - 103: boss → accounting first (price decision; one `check_stock_and_margin` gives stock and margin); accounting → inventory (restock of 12, expected blocked/unaffordable); boss → customer_service (draft). No facilities.
- Improvements after my follow-ups (built by `scripts/build_desk_tickets.py`, which reads ticket facts from the original database):
  - **Predictions checklist** per ticket (9–11 concrete, checkable claims each) with blank ✓/✗ and evidence columns.
  - **Cash chain** per ticket: tickets run 101 → 102 → 103 on one account ($3,400 → $2,560 after the invoice-501 request → $160 after the rent request), explaining why the 12-hoodie restock ($264) should be refused on 103.
  - **Actual section** now has the same headings as Expected (first call, delegations, tools, cash after, outcome, prediction results, differences and why), ready to fill after the run.

---

## Problem 7 — Backend routes (FastAPI)

### Prompt I typed

> ok this is problem 7: backend routes. your react frontend dashboard (the next problem) needs a backend it can call. in backend/main.py use fastAPI and add routes that do the following: return 3 tickets and whether each is open or resolved, take a ticket id and run your agent team on that ticket, return recent agent events -- what each agent said and which tools they used so the board can refresh, approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash), return the current checking balance from cash_accounts, and reset the database to the original values when you want to try a fresh run.
>
> from the backend/fodler, start the server with: uvicorn main:app --reload --port 8000
> this turns on the backend at http://localhost:8000 so the frontend dashboard can call those routes. in output/harness.md, list each route in one line (what URL/what it does)

### What was built (evidence)

- `backend/main.py` — FastAPI app with the routes listed in `output/harness.md` section 6 (tickets, run a ticket, run status, events, board, approve/reject, cash, reset, health). Every shop read and change goes through the MCP server (in-memory MCP client); approval is the only route that changes cash.
- Tested (on a spare port because port 8000 was held by an old HW 4 server): health → gpt-6-luna; reset; tickets 101–103 all `open`; cash $3,400; `POST /api/tickets/102/run` ran boss → facilities → accounting (a second run was refused while busy); `/api/events` showed each agent's messages and tools (e.g. facilities: `get_ticket`, `check_rent_due`); approve with approver "accounting" → refused; approve as "Eliza Wright" → rent paid, `payments` row written, lease next_due → 2026-10-02, cash $3,400 → $1,000; approving twice → refused; `/api/reset` restored $3,400.
- `output/harness.md` — section 6, one line per route.

---

## Problem 8 — Agent dashboard (React + Vite + TypeScript)

### Prompt I typed

> this is problem 8: agent dashboard. buidl the frontend dashboard in frontend/ with react + vite + typescript. the page should call the routes you built in problem 7. at minimum the baord should: list all 3 tickets, let you pick one ticket and start the agent on it, show each agent and what they are saying/doing while the ticket runs, mark a ticket resolved when the run finishes, show a short summary of what each agent did on that ticket, let a human approve a pay or purchase when asked, show the checking balance (it should drop after an approved pay). Make the dashboard look good. Use similar aesthetics as what we did with the previous campus customs assignment, the spooky-faulkner aesthetic. this is a real desk people would want to sit at, so put thought into how it looks. Tell the front end to talk to your backend at http://localhost:9000. on the backend, allow the vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. start the board with: xnpm run dev. This opens the react desk in your browser so you can pick tickets and watch agents. Write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why -- including the creative choices that make it feel special and something humans would actually enjoy using.

### Follow-up prompts

> (none yet)

### What was built (evidence)

- `frontend/`: React 19 + Vite 8 + TypeScript. `src/api.ts` calls `http://localhost:9000` (override with `VITE_API_URL`). Components: `Docket` (the 3 tickets), `Porch` (the 5 agents, live state, the speaking agent lit), `Telling` (live feed polling `/api/events?since=`), `Afterword` (per-agent summary), `Signatures` (approve/reject with a named signer), `Letters` (unsent drafts), `Ledger` (checking balance that counts down after a payment), plus `Crest` and `NightSky` from HW4. `npx tsc -b` is clean.
- Backend changes (`backend/main.py`): CORS allows http://localhost:5173 (and 5174 as a fallback); when a run finishes, the boss marks the ticket `resolved` through the MCP `update_ticket_status` tool; new `GET /api/tickets/{id}/summary`; the docstring now says port 9000. Harness section 6 is updated.
- `output/design.md`: layout, the five voices (ink, font and seal per agent), the SETTLED stamp, the cash ledger, and the reasoning behind the creative choices.
- Live test (backend on :9000, board in the preview): picked ticket 102 and sent the team in. The feed streamed Boss → Facilities → Accounting live, with Inventory and Customer Service left dim ("Not called"). The run finished (3 agent runs, 28,436 tokens), the ticket was stamped SETTLED, and the "What each one did" cards appeared. Rent request #1 ($2,400) showed under "Awaiting a signature". Signed as "Eliza Wright" → executed; the ledger dropped from $3,400.00 to $1,000.00 ("Signed and paid. Checking now $1,000.00."). No console errors. Then reset the DB through `/api/reset` (cash back to $3,400).
- Fixed during testing: a delegation request was printed twice in the feed; the sticky left column overlapped the signature panel at mid-width; agent cards were cramped in 5 columns (they now wrap).


## Problem 9 — Full run over the three tickets, resolved board, and cash reconciliation

### Prompt I typed

> this is problem 9: before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db again so you start clean. note the starting checking balance. then run all three tickets (101, 102, 103) until each is resolved. Open output/desk_tickets.html from problem 6. on each ticket tab, fill the actual section from this run: which agents worked, what they delegated, and which tools they used. keep our expected section so we can compare the two. On the cash tab of the same output/desk_tickets.html, itemize the money: start checking balance (after the reset), for each ticket: how cash changed when that ticket resolved, and why (which pay/purchase, dollar amount), ending checking balance -- it must match cash_accounts in the working database. Wrong cash math loses points even if the board shows every ticket resolved. Also save: output/resolved_tickets.json -- for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals. 
> output/resolved_board.html -- a page you can double-click with a screenshot of your reach board for each resolved ticket (101, 102, 103). Append real runs to output/audit_trail.json. finish output/harnes.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

### Follow-up prompts

> reset and redo

> signed both, run 102

> i hit sign & pay

> what now?

> done

(Answer to my question about who signs: "I'll sign in the dashboard".)

### What was built (evidence)

- **Reset:** `POST /api/reset` at 18:05. Starting checking balance was **$3,400.00** (`output/run9/cash_start.json`, `cash_accounts`). An earlier attempt was thrown away and redone, because ticket 103 had been started from the dashboard out of order and 101's signatures hadn't gone through.
- **Runs** (gpt-6-luna via Portkey), each followed by signing in the Night Desk:
  - 101 (run e9ec8ecb1a, 5 agent runs, 63.8k tokens). Signed #1 invoice 501 $840 and #2 tee PO $8 → **$2,552**.
  - 102 (run df4dffb6bd, 3 agent runs, 28.9k tokens). Signed #3 rent $2,400 → **$152**. An accidental dashboard re-run (9f742c95ff) created no duplicate.
  - 103 (run adc640b99c, 4 agent runs, 41.7k tokens) produced #4, a price override of 8 hoodies at $49.30. An accidental re-run (bb01273412) had a 12-hoodie PO **refused** by the cash guard, then requested #5 (4 hoodies, $88) and #6 (2 hoodies, $44). All three were signed → **$20.00**.
  - All 3 tickets are `resolved`.
- **Cash check:** ending checking $20.00 = `cash_accounts.checking`, and `SUM(payments)` = $3,380 = $3,400 − $20. The builder `assert`s both.
- **`output/desk_tickets.html`:**
  - Expected sections unchanged.
  - Actual section per ticket: who was called first, the agents that worked (and who called them), every delegation, every MCP tool call per agent, requests and human decisions, outcome, and differences from the plan.
  - ✓/✗/~ marked on every prediction with evidence.
  - Cash tab itemized per ticket and checked against the DB.
  - Built by `scripts/collect_run.py` → `output/run9/runs.json`, plus `scripts/run9_actuals.py` (written judgement) and `scripts/build_desk_tickets.py`.
- **`output/resolved_tickets.json`:** per ticket: id, final status, short outcome, the boss's decision, runs, each agent's contribution, agents not called, human approvals, unsent drafts, and cash before/after.
- **`output/resolved_board.html`:** opens on double-click, with the three dashboard screenshots embedded (`output/screenshots/board_10{1,2,3}.png`, taken with headless Chrome at `http://localhost:5173/?ticket=N` right after each ticket's signing).
- **`output/audit_trail.json`:** grew from 383 to 602 entries; real runs appended, never truncated.
- **`output/harness.md`:**
  - Added a contents table, run lessons under Safety (re-runs are idempotent; "the cash guard limits money, not judgment"), §7 Dashboard and §8 Full run.
  - Now covers tables, MCP tools, the five agents, API routes, the dashboard and safety rules.
- **Dashboard fixes found during the run:**
  - The sign buttons stay disabled until a name is written.
  - A note says "N requests await your signature".
  - "Send the team in again" is a ghost button and asks for confirmation on settled tickets.
  - "Already decided" opens when nothing is pending.
  - `/?ticket=N` deep link.
- **Model check:** a scan of code and outputs finds only `gpt-6-luna`.

## Problem 10 — Reflection tab

### Prompt I typed

> this is problem 10: open output/desk_tickets.html and fill in the reflection tab. answer in your own vibe, and be detailed and thorough: how would you evaluate the performance of the agents on each ticket and why, for each ticket how did actual compare to expected plan we wrote earlier, what would have been simpler as one agent with tools - and why, describe three new problems campus customs might face that this agent team could solve with the tools you built, describe three new problems campus customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them. tie every answer to this app and the three tickets you ran -- use the ticket tabs and cash tab on the same page as your evidence. generic ai essays without campus customs details will score low.

### Follow-up prompts

> (none yet)

### What was built (evidence)

- The **Reflection tab** of `output/desk_tickets.html` is written. The source is `scripts/reflection.py`, rendered by `scripts/build_desk_tickets.py`. Sections:
  1. **Grades per ticket**, with cost (agent runs, tokens, tool calls) and reasons:
     - 101: **B**. Correct and safe, but it ordered an $8 duplicate tee: `invoices.description` says "Rush reprint CC-TEE-WHITE S". It also used 16 tool calls.
     - 102: **A**. Lean, and the re-run created no duplicate.
     - 103: main run **A−**, accidental re-run **C**. A refused 12-hoodie PO was split into 4 + 2, after a stock misread.
     - Prediction tally: 18 ✓, 7 partial, 5 ✗ out of 30.
  2. **Actual vs. plan** per ticket, with the lesson from each.
  3. **One agent vs. the team:** 102 clearly simpler (≈5 calls vs. 10). 101 and the 103 re-run suffered from split context. Safety came from the MCP tools and the human signature, not from the number of agents. Recommendation: a router plus one generalist, with specialists for cross-domain tickets.
  4. **Three problems the team could solve today:** 4 Crest Mugs via Elm City Gifts ($14 PO); October rent with $20 in the bank (refuse and raise the alarm); 20 caps at a club price (40 on hand).
  5. **Three it could not solve, with the tools and agents needed:**
     - Money in: `sales` table, `record_sale`, `confirm_payment_received`, `forecast_cash`, and a Sales/Treasurer agent.
     - Receiving and fulfillment: `purchase_orders` table, `receive_shipment`, `fulfill_order`, `book_courier` via QuickShip CT, and a Fulfillment agent.
     - Two-way correspondence: `send_draft` (human-approved), `update_draft`, `ingest_inbox`, `submit_vendor_order`, and a Correspondence agent.
  - Plus the three tool changes I'd make first.
- **Correction carried back into the Problem 9 write-up:** the 101 tab now says the $8 PO duplicated the reprint covered by invoice 501.

## Problem 11 — Publish to a public GitHub repository

### Prompt I typed

> ok this is problem 11: push the code to a public github repository so graders can clone it. give me the repo url for me to submit to canvas, and also put it in output/github_url.txt. do not push real .env to the github repo. do include both database files under data/ (the original and working copy) so graders can run the app easily.

### Follow-up prompts

> here is the expected file layout: (screenshot of the hw5/ tree: AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/ with both .db files, mcp_server/ with server.py and README.md, frontend/, backend/ with main.py, models.py and prompts/*.md, and output/ with harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json and github_url.txt) "README should explain: copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run."

### What was built (evidence)

- **Public repo: https://github.com/egwright336/campus-customs-ops** (`gh repo view` reports `PUBLIC`). The URL is also in `output/github_url.txt`.
- New root `README.md`: setup; `python reset_db.py` to copy the original DB to the working copy; starting the MCP server (stdio or `--http`); starting FastAPI with `uvicorn main:app --port 9000`; `npm run dev` for the board; resetting before a full 101 → 102 → 103 run; the shop rules.
- Every file in the expected layout is present, along with the supporting code (`config.py`, `reset_db.py`, `backend/team.py`, `audit.py`, `run.py`, `scripts/`, `output/run9/`, `output/screenshots/`).
- **No secrets:**
  - `.gitignore` excludes `.env` and `.env.*` (but keeps `.env.example`), `.venv`, `node_modules`, `dist` and `*.log`.
  - The real key lives two folders up, outside the repo.
  - A scan of every file for the actual key value found 0 matches.
  - `git ls-files` contains no `.env`, logs or virtualenv.
- **Both databases committed:** `data/campus_customs.db` (original, checking $3,400) and `data/campus_customs_new.db` (working copy, at the end of the graded run: $20).
- `.mcp.json` now uses relative paths (`.venv/bin/python mcp_server/server.py`), so it works in a grader's clone.
- **Verified:** a fresh `git clone` into a scratch folder has 81 tracked files, and the layout and both databases are as expected.
