# The Night Desk: dashboard design (Problem 8)

`frontend/` is a React + Vite + TypeScript board that talks to the FastAPI backend at **http://localhost:9000**
(`src/api.ts`, override with `VITE_API_URL`). The backend's CORS list allows the Vite page at
`http://localhost:5173`, plus 5174 in case 5173 is already taken by the HW4 dashboard.

```bash
cd backend && uvicorn main:app --port 9000      # the API
cd frontend && npm install && npm run dev        # the board -> http://localhost:5173
```

## The look in one line

It's Campus Customs after closing: the HW4 "Old Campus after dark" palette and type, recast as a Southern Gothic
night desk. Five narrators tell the same ticket in turn, each in their own voice. The structure nods to Faulkner's
multi-voice novels, where each chapter is headed by the speaker's name. No text is quoted from them; all the copy
is original.

## Layout

| Zone | What's there | Why |
|---|---|---|
| **Masthead** (midnight, crescent moon, bats, drifting fog) | Crest, "The Night Desk", the shop's *today* (`desk.date_today`, which is Monday, August 31, 2026), and **the Ledger**, the checking balance set in brass | The two facts every decision hangs on (what day the shop thinks it is, and how much cash there is) are always visible and never scroll away |
| **Run picker** (under the ticket header) | One pill per run of the ticket (time, agents, tokens, "latest") | A re-run never hides the main run; the audit trail keeps them all, so the board shows them all |
| **Left: the docket** | The 3 tickets as parchment notices pinned with a brass tack, slightly askew. Pills show status, how many requests wait for a signature, and how many letters were drafted. *House rules* and **Reset the books** sit below | It reads like a courthouse notice board. Picking a notice outlines it in lantern orange |
| **Center: the case** | Ticket header with **Send the team in** → **the porch** (five agent "chairs") → **the telling** (live feed) → **What each one did** (after the run) | One ticket at a time, read top to bottom: who is here, what they are saying, what they did |
| **Right: awaiting a signature** | A *Signed by ___* line, request slips with the amount stamped in Oswald, **Sign & pay** / **Turn down** buttons, and already-decided requests folded away. Below that, **Unsent letters** (drafts) | The human's job sits on its own side of the desk, separate from the agents' talk |

At ≤1180px the right column drops below. At ≤760px everything stacks into one column.

## How the agents read differently

Each agent gets **its own ink, its own typeface, and its own wax-seal letter**, so you can tell who is talking
without reading the name:

| Agent | Ink | Hand (font) | Epithet |
|---|---|---|---|
| The Boss | brass `#c9a24a` | IM Fell English SC headings, IM Fell text: the old seal voice | *who makes the final call* |
| Inventory | kudzu green `#8fb48a` | Oswald: stock counts, stamped and plain | *keeper of the stockroom* |
| Accounting | ledger blue `#86aed6` | Special Elite: the typewriter in the back office | *keeper of the ledger* |
| Facilities | wisteria `#b9a3d9` | Source Serif 4: a lease, plainly read | *keeper of the lease* |
| Customer Service | magnolia `#e3a19a` | IM Fell English italic: letter-writing | *who writes the letters* |

- **The porch:** each chair shows the agent's live state (*quiet, thinking, in the books, asking a teammate,
  said its piece, stopped by a guard*) and its latest line. The agent speaking right now is **lit**: a glow in
  its own ink and a flickering lantern dot. Agents the boss never called stay dim and grey ("Not called."). That
  makes it easy to see when a plan *didn't* send every specialist.
- **The telling:** one entry per meaningful audit event. Each is headed with the speaker's name in their hand
  and color, followed by an italic stage direction: *takes up the ticket, goes to the books, reads what the books
  say, turns to Facilities, has said its piece, closes the ticket*. Tool calls appear as small typewriter chips;
  tool results appear as "ledger slips". Long messages fold behind *read on*. Bare model requests are skipped as
  noise. A guard block shows in warning red. The feed polls `/api/events?since=` every 1.2s and scrolls as it grows.

## Resolved tickets

When a run finishes, the backend has the boss mark the ticket `resolved` (through the same MCP
`update_ticket_status` tool, which only the boss may use). It leaves a note on the ticket saying how many
approvals are still waiting for a human. On the board, a resolved notice turns a shade darker and gets a red
double-ruled **SETTLED** rubber stamp that thumps down at an angle. The case header gets the same stamp.
**What each one did** then appears with:

- the boss's ruling on parchment, with agent-run and token counts;
- one card per agent that took part, showing its summary, its final status, who called it in, whom it asked,
  and which MCP tools it used.

These come from `GET /api/tickets/{id}/summary`, built from that run's audit trail.

Resolved does **not** mean paid. Payments stay pending on the right until a person signs, which is the shop rule.

## Cash

The **Ledger** in the masthead reads `GET /api/cash` (`cash_accounts` → checking). When a payment is signed, the
board refetches and the brass figure **counts down** over 1.4s with an ease-out. It flickers once, and the loss
(for example **−$2,400.00**) is inked in red beside it and then fades. Underneath, a quiet line shows how much is
*promised* to requests still waiting for a signature, so the human can see what's coming before signing.
Signing needs a name on the *Signed by* line. The backend refuses agent names and refuses anything that would
take an account below zero; the slip shows the refusal if that happens.

## Creative choices and why

- **Same house as HW4.** Yale blue and midnight, parchment and brass, with lantern orange used **only for things
  you can click** (Send the team in, Sign & pay). The fonts are the same family, so the shop and its back office
  feel like one brand.
- **Southern Gothic.** The palette got a few overgrown Southern inks (kudzu, wisteria, magnolia). The copy talks
  about the docket, the porch, the telling, the books, unsent letters and settling, and there is a red
  courthouse stamp. The point is that a multi-agent run *is* a story told by several narrators, and the design
  leans into that instead of hiding it behind a log table.
- **Paper for human things, night for agent things.** Tickets, the ruling and the request slips are on paper
  (human documents). The agents' talk is on the dark desk. You can see at a glance where your signature goes.
- **Honest by default.** The footer shows the model (`gpt-6-luna` through Portkey) and that every step is written
  to `output/audit_trail.json`. Letters say "draft, not sent", because the shop never emails customers.
- **Motion with restraint.** The moon rises once, three bats cross slowly, fog drifts, the speaking agent's
  lantern flickers, the stamp drops, and the balance counts down. All of it switches off under
  `prefers-reduced-motion`.
