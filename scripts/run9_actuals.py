"""What actually happened in the Problem 9 full run, written up after reading output/run9/runs.json
(collected from output/audit_trail.json by scripts/collect_run.py) and the working database.

Facts that can be computed (who ran, delegations, tools, cash) are rendered from those files by
build_desk_tickets.py; this file holds only the human-written judgement: which run is the main one, the
outcome, the differences from the plan, and the ✓/✗ against each prediction.
"""

# Main run per ticket, plus any extra runs (accidental "Send the team in again" clicks on the dashboard).
RUNS = {
    101: {"main": "e9ec8ecb1a", "extra": []},
    102: {"main": "df4dffb6bd", "extra": ["9f742c95ff"]},
    103: {"main": "adc640b99c", "extra": ["bb01273412"]},
}

FIRST_CALLED = {
    101: ("inventory", "Matches the plan. The boss read the ticket (get_ticket) and sent inventory the exact SKU, size, "
                       "qty and the open $840 invoice 501, asking for stock, shortfall and the restock path."),
    102: ("facilities", "Matches the plan. The boss asked facilities to confirm lease 1's amount and due date and said "
                        "\"Return facts only; do not contact anyone.\""),
    103: ("inventory", "Differs from the plan (we predicted accounting). The boss wanted the exact-size stock count "
                       "first, then took \"8 on hand, 12 short\" to accounting for the price decision."),
}

OUTCOME = {
    101: ("Resolved. Two requests on the board: <b>#1 pay invoice 501, $840</b> (accounting) and <b>#2 purchase "
          "order 1 × CC-TEE-WHITE S, $8</b> (inventory). One unsent draft to Tauhid Zaman says size S is out, the "
          "restock is awaiting approval with no date, and M/L/XL are in stock. Eliza Wright signed both at "
          "18:08: checking went from $3,400 to $2,552, and invoice 501 is now <i>paid</i>, so Bulldog Print Co "
          "can ship again. Note that the $8 tee PO duplicates the reprint invoice 501 already covers."),
    102: ("Resolved. One request, <b>#3 pay rent on lease 1, $2,400</b> (accounting). No drafts, and the landlord "
          "was never contacted. Eliza Wright signed at 18:13: checking went from $2,552 to $152, and lease 1's "
          "next_due moved from 2026-09-02 to 2026-10-02."),
    103: ("Resolved. The main run produced <b>#4 price override: 8 × CC-HOOD-NAVY M at $49.30</b> (15% off $58, "
          "$27.30 above the $22 cost) and an unsent draft to Yale AI Club. No purchase order was made: cash was "
          "only $152 and the team said so. An accidental second run (18:50) then added <b>#5 PO 4 hoodies, "
          "$88</b> and <b>#6 PO 2 hoodies, $44</b>. Eliza Wright signed #4, #5 and #6 at 19:19. The price "
          "override moved no cash, and the two POs took checking from $152 to $20. Result: 8 hoodies at the group "
          "price now, 6 more on order from Bulldog (5-day lead), and 6 of the 20 still without a plan."),
}

DIFFERENCES = {
    101: [
        "<b>An $8 purchase order we did not predict, and it was a mistake.</b> Our plan said invoice 501 <i>is</i> the "
        "tee reprint, and the data agrees: <code>invoices.description</code> reads \"Rush reprint CC-TEE-WHITE S\". "
        "Inventory treated the invoice only as an old debt blocking Bulldog, never connected the description to the "
        "missing shirt, and ordered 1 more tee on top of the reprint already paid for. Cheap ($8), but a duplicate "
        "order. The PO tool allowed it because invoice 501 was already requested (the shop rule only blocks POs while "
        "an unpaid invoice is <i>un</i>requested), and no tool checks whether an open invoice already covers the SKU.",
        "<b>5 agent runs, not 4: accounting was asked twice.</b> First by inventory (put invoice 501 up), then by "
        "the boss (\"do not create duplicates… check cash/competing commitments\"). The second call earned its "
        "keep: accounting called check_rent_due and warned that the invoice, the PO and the $2,400 rent "
        "together would leave $152. That is exactly where the shop ended up after ticket 102.",
        "Customer service re-ran get_ticket and check_stock_and_margin before drafting. It was redundant but "
        "safe, and it is why the draft lists M, L and XL correctly.",
    ],
    102: [
        "<b>Hub-and-spoke, not a chain.</b> We expected facilities → accounting. Instead the boss asked facilities, "
        "then asked accounting itself. The result was the same, with one more hop through the boss.",
        "<b>The cash premise changed.</b> The plan assumed invoice 501 was still only <i>committed</i> ($2,560 "
        "available). Because a human signed ticket 101's requests first, accounting saw $2,552 in the bank with "
        "$0 committed, and correctly reported that rent would leave $152.",
        "<b>An extra run (18:11, the dashboard's \"Send the team in again\").</b> The boss called list_board, saw "
        "rent request #3 already pending, asked only facilities to re-confirm, and created nothing new: 2 agent "
        "runs and 14,584 tokens for no change. Duplicate protection worked, but the click was wasted. That is "
        "why the dashboard now asks for confirmation before re-running a settled ticket.",
    ],
    103: [
        "<b>Inventory first, not accounting.</b> The boss split the job cleanly: inventory counted (8 of 20), "
        "accounting priced, and customer service wrote. It cost one more hop than our plan, but each agent stayed "
        "in its lane.",
        "<b>The main run matched the plan almost exactly:</b> a 15% override on the 8 available hoodies only, no "
        "PO, and a draft that promises neither the price nor the other 12.",
        "<b>The accidental second run (18:50) is the most interesting failure.</b> By then invoice 501 was paid, "
        "so Bulldog was unblocked. Inventory asked for a 12-hoodie PO ($264). The server <b>refused</b> it "
        "(\"Not enough uncommitted cash… max_units_affordable: 6\"). Inventory passed the problem to "
        "accounting, which misread the stock (\"8 units on hand against the 12-unit ticket, so only 4 are "
        "needed\"; the 12 was already the shortfall <i>after</i> the 8) and requested 4 ($88). The boss then "
        "asked for \"a separate additional PO\", and accounting added 2 more ($44). Every request passed the "
        "cash guard, which counts committed money, so the balance was never at risk. But the team chopped a "
        "refused order into pieces until it fit, on top of a reasoning error. The guard limits money, not "
        "judgment.",
        "The draft to Yale AI Club was written in the first run and was <b>not updated</b> after the POs. It still "
        "says \"the remaining 12 are not confirmed\", which is now only half true.",
    ],
}

# ✓ / ✗ / ~ for each prediction in build_desk_tickets.PLANS, in the same order, with evidence.
PREDICTION_RESULTS = {
    101: [
        ("✓", "First delegation_start: boss → inventory (18:06:03)."),
        ("✓", "check_stock_and_margin(CC-TEE-WHITE, S, 1): 0 on hand, shortfall 1; M 5 / L 3 / XL 2."),
        ("✓", "check_vendor_can_ship(1): blocked by invoice 501, $840, 3 days overdue as of 2026-08-31."),
        ("✓", "delegation inventory → accounting: \"please put invoice 501 up for payment approval\"."),
        ("✓", "Request #1 invoice_payment 501, $840, pending (one payment request; the PO is separate)."),
        ("✗", "Request #2: PO 1 × CC-TEE-WHITE S, $8, requested by inventory, even though invoice 501 is described as \"Rush reprint CC-TEE-WHITE S\"."),
        ("✓", "Draft 1 says \"we can't confirm when it will be available yet\"; no date promised."),
        ("✓", "No facilities agent_start in run e9ec8ecb1a."),
        ("~", "Agents made 0 payments. Cash dropped to $2,552 only when Eliza Wright signed #1 and #2."),
        ("~", "The boss set waiting_on_human; the backend then marked it resolved when the run ended (Problem 8 design)."),
        ("✗", "5 agent runs (accounting twice: asked by inventory and by the boss), 63,794 tokens."),
    ],
    102: [
        ("✓", "First delegation_start: boss → facilities (18:09)."),
        ("✓", "check_rent_due(1): $2,400 due 2026-09-02, 2 days out, not overdue."),
        ("✗", "Hub-and-spoke: boss → facilities, then boss → accounting; facilities did not hand off."),
        ("✓", "Request #3 rent_payment, lease 1, $2,400, pending (and no duplicate on the 18:11 rerun)."),
        ("✗", "Premise changed: 101's requests were already signed, so accounting saw $2,552 with $0 committed; rent leaves $152."),
        ("✓", "list_board(102): drafts = []."),
        ("✓", "Only boss, facilities and accounting have agent_start in run df4dffb6bd."),
        ("~", "Agents made 0 payments. Cash dropped $2,552 → $152 when Eliza Wright signed #3."),
        ("~", "waiting_on_human from the boss, then resolved by the backend at the end of the run."),
        ("✓", "3 agent runs, 28,865 tokens (plus a 2-run, 14,584-token accidental rerun)."),
    ],
    103: [
        ("✗", "First delegation_start: boss → inventory, then boss → accounting."),
        ("✓", "check_stock_and_margin(CC-HOOD-NAVY, M, 20): 8 on hand, shortfall 12; cost $22, list $58."),
        ("✓", "Request #4 price_override: 8 × $49.30 (15% off), $27.30 above cost."),
        ("~", "✓ in the main run (no PO). ✗ in the accidental rerun: a 12-unit PO was refused, then #5 (4, $88) and #6 (2, $44)."),
        ("✓", "Draft 2: \"pending review, so it has not been approved… the remaining 12 are not confirmed\"."),
        ("✓", "No facilities agent_start in either 103 run."),
        ("~", "Main run: 0 payments. Signing #5 and #6 took cash $152 → $20; #4 moved no cash."),
        ("~", "waiting_on_human from the boss, then resolved by the backend at the end of the run."),
        ("✓", "4 agent runs, 41,652 tokens in the main run (rerun: 4 runs, 87,348 tokens)."),
    ],
}
