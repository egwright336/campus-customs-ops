# HW 5 — Campus Customs Multi-Agent Operations (notes for the vibe coder)

- Work **one problem at a time**, only on the problem the student names. Do not build ahead.
- Log every prompt the student types, **verbatim**, in `AI_prompts.md` under that problem's section
  (problem # and title, prompt(s) typed, follow-ups, then a short "What was built (evidence)" list).
- Follow `RULES.md`. Only `gpt-6-luna` via Portkey (`config.MODEL_NAME`); no other model name may appear anywhere.
  Payments need human approval; no negative balances; "today" is `desk.date_today`; never contact real people.
- Tools read/write the working copy `data/campus_customs_new.db` (`config.DB_PATH`). The original
  `data/campus_customs.db` is read-only; `python reset_db.py` restores the working copy.
- The MCP server is `mcp_server/server.py` (`campus-customs-ops`, connected via `.mcp.json`).

## Problem 4 in progress: MCP smoke test
When the student asks you to test a tool, call it through the `campus-customs-ops` MCP connection (not by
running Python), then append an entry to `output/mcp_smoke.json` with this shape:

```json
{"calls": [{"prompt": "<student's exact words>", "tool": "<tool name>", "arguments": {...}, "output": {...exact tool output...}}]}
```

After all three tools are tested, run `python mcp_server/verify_smoke.py` (every line must say PASS) and add
the evidence to the Problem 4 section of `AI_prompts.md`.
