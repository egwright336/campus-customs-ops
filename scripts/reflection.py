"""Problem 10: the Reflection tab of output/desk_tickets.html (rendered by scripts/build_desk_tickets.py).

Every claim points at evidence on the same page (ticket tabs, Cash tab) or in output/run9/runs.json,
output/resolved_tickets.json and output/audit_trail.json.
"""

REFLECTION_HTML = r"""
<section id="reflection" class="tab"><h2>Reflection: the night shift, reviewed</h2>
<p class="lede">Five agents, three tickets, one checking account. The team started with <b>$3,400</b> and ended at
<b>$20</b>, and every dollar of that drop was signed for by a human (Cash tab). The interesting part isn't that
the agents worked. It's <i>where</i> they were sharp, where they were wasteful, and the one place they talked
themselves into something. Evidence is in the ticket tabs (Actual sections and ✓/✗ checklists) and the Cash tab.</p>

<h3>1. How the agents performed on each ticket</h3>
<table class="grades">
<tr><th>Ticket</th><th>Grade</th><th>Cost</th><th>Why</th></tr>
<tr><td><b>101</b><br>Bulldog tee for Tauhid</td><td class="g">B</td><td>5 agent runs<br>63,794 tokens<br>16 tool calls</td>
<td><b>Good:</b>
<ul>
<li>Inventory nailed the facts: size S at 0, shortfall 1, M/L/XL at 5/3/2.</li>
<li>It found the real blocker: invoice 501, $840, 3 days overdue against <code>desk.date_today</code> (2026-08-31). It routed that to accounting instead of trying to pay it itself.</li>
<li>Accounting's second pass looked ahead to the <b>$2,400 rent due 9/2</b> and warned that everything together would leave <b>$152</b>. That was exactly the balance after ticket 102 (Cash tab).</li>
<li>Customer service's draft was honest: no date promised, alternatives offered.</li>
</ul>
<b>Not good:</b>
<ul>
<li>Inventory asked for an <b>$8 PO for a tee the shop had already paid to reprint</b>. <code>invoices.description</code> literally says "Rush reprint CC-TEE-WHITE S".</li>
<li>It took 16 tool calls, with <code>get_cash_position</code> 3 times and <code>get_ticket</code>, <code>check_stock_and_margin</code> and <code>check_vendor_can_ship</code> twice each, for a one-shirt order.</li>
</ul>
Correct and safe, but it missed one clue and spent a lot of tokens.</td></tr>
<tr><td><b>102</b><br>Rent due</td><td class="g">A</td><td>3 agent runs<br>28,865 tokens<br>10 tool calls</td>
<td><b>The cleanest ticket of the night.</b>
<ul>
<li>The boss called exactly the two specialists rent needs: facilities to confirm lease 1, then accounting for the cash and the request.</li>
<li>Inventory and customer service stayed dark on the porch.</li>
<li>No letter to the landlord, no contact. The rent request had the right amount ($2,400, from <code>leases</code>, not from the model's text) and was correctly marked not overdue (2 days out).</li>
</ul>
<b>The accidental re-run (18:11) is the best evidence of good behavior.</b> The boss checked <code>list_board</code>, saw request #3 already pending, and created <i>nothing</i>. That cost 2 runs and 14.6k tokens, with no harm done.<br>
The only nit: <code>get_ticket</code> was called 3 times by three different agents.</td></tr>
<tr><td><b>103</b><br>Yale AI Club, 20 hoodies</td><td class="g">A− / C</td><td>main: 4 runs, 41,652 tokens<br>re-run: 4 runs, 87,348 tokens</td>
<td><b>Main run: A−.</b>
<ul>
<li>A tidy division of labor: inventory counted (8 of 20), accounting priced, customer service wrote.</li>
<li>The override was sensible: 15% off, $49.30, $27.30 over the $22 cost, and <i>only</i> on the 8 hoodies that exist.</li>
<li>With $152 in the bank, nobody forced a 12-hoodie restock.</li>
</ul>
<b>Accidental re-run: C.</b> By 18:50, invoice 501 was paid, so Bulldog could ship.
<ul>
<li>Inventory asked for 12 hoodies ($264), and the MCP tool <b>refused</b> it ("max_units_affordable: 6").</li>
<li>Instead of accepting "blocked", the team <b>split the order until it fit</b>: accounting misread the stock ("8 on hand against the 12-unit ticket, so only 4 are needed") and requested 4 for $88. Then the boss asked for "a separate additional PO" of 2 for $44.</li>
<li>The draft to the club was never updated.</li>
</ul>
Money was never at risk, because committed cash is counted. But judgment was, and a human signed it, taking checking to <b>$20</b> with October rent ($2,400 on 10/02) next in line.</td></tr>
</table>
<p><b>Overall:</b> the team was always <i>safe</i>. No payment without a signature, no negative balance, nothing sent,
and "today" always came from <code>desk.date_today</code>. It was mostly <i>accurate</i>: of 30 predictions, 18 were ✓, 7 were
partial and 5 were ✗. It was rarely <i>efficient</i>. The main runs cost 134k tokens; the two accidental re-runs cost
another 102k.</p>

<h3>2. Actual vs. the plan we wrote first</h3>
<table>
<tr><th>Ticket</th><th>Where the plan was right</th><th>Where reality differed, and what it taught us</th></tr>
<tr><td>101</td><td>
<ul>
<li>Boss → inventory first.</li>
<li>Inventory → accounting for invoice 501.</li>
<li>One $840 payment request.</li>
<li>Facilities never called.</li>
<li>An unsent draft with no promised date.</li>
</ul></td>
<td>
<ul>
<li>We predicted "no new PO because invoice 501 <i>is</i> the reprint", and we were right about the data. The agents weren't: they added the $8 PO.</li>
<li>We predicted ~4 agent runs; there were 5, because accounting was asked twice.</li>
<li>Lesson: <b>showing an agent a fact is not the same as enforcing it.</b> <code>check_vendor_can_ship</code> returned the invoice's description, "Rush reprint CC-TEE-WHITE S", straight to inventory, and inventory still ordered the tee. The rule belongs in the PO tool, not in the hope that the model connects the dots.</li>
</ul></td></tr>
<tr><td>102</td><td>
<ul>
<li>Facilities first.</li>
<li>$2,400 due 9/2, not overdue.</li>
<li>One rent request, no drafts.</li>
<li>Inventory and customer service never called.</li>
<li>~3 agent runs (exactly 3).</li>
</ul></td>
<td>
<ul>
<li>We drew a chain (facilities → accounting); the boss ran it hub-and-spoke instead.</li>
<li>Our cash chain assumed 101 was only <i>committed</i> ($2,560 available). In reality a human had already paid it, so accounting saw $2,552 and $0 committed.</li>
<li>Lesson: <b>the plan modeled the agents but not the human between tickets</b>. Signing order changes what the next ticket sees.</li>
</ul></td></tr>
<tr><td>103</td><td>
<ul>
<li>8 of 20 on hand, $22 vs $58.</li>
<li>A modest (15%) override on the 8 only.</li>
<li>No PO in the main run.</li>
<li>A cautious draft.</li>
<li>Facilities never called.</li>
<li>~4 agent runs (exactly 4).</li>
</ul></td>
<td>
<ul>
<li>We predicted accounting first; the boss went to inventory first.</li>
<li>Our "no PO" prediction rested on <i>two</i> blockers: Bulldog unpaid, and cash short. The re-run removed one of them (501 was paid), and the remaining one, cash, was negotiated around 6 units at a time.</li>
<li>The plan's cash chain ended at $160 uncommitted; reality ended at <b>$20 in the bank</b> (Cash tab, "Expected vs actual cash").</li>
</ul></td></tr>
</table>

<h3>3. What would have been simpler as one agent with tools</h3>
<p><b>Ticket 102, without question.</b> One agent with <code>check_rent_due</code>, <code>get_cash_position</code>,
<code>request_payment_approval</code> and <code>update_ticket_status</code> needs about 5 tool calls. The team used 10,
including <code>get_ticket</code> 3×, <code>check_rent_due</code> 2× and <code>get_cash_position</code> 2×, plus three model
contexts at 28.9k tokens. Rent is one lease, one amount, one date. There is nothing to delegate.</p>
<p><b>Ticket 101, mostly.</b> One agent holding inventory, accounting and draft tools would need about 7 calls instead of 16. It
would <i>not</i> necessarily have avoided the $8 duplicate PO, though. Inventory had the invoice description ("Rush
reprint CC-TEE-WHITE S") in its own tool result and ordered anyway. That was a reasoning miss, not a hand-off
problem, so a single agent could make it too.</p>
<p><b>The 103 re-run is the clearest case for one context.</b> The refusal ("max 6 units") landed in inventory's
context. Inventory handed accounting a summary, accounting misread the stock, and the boss then asked for "another" PO without
the full history. That's three partial views of one decision. A single agent that just got refused is far more likely to
stop, or to ask the human, than to split the order.</p>
<p><b>Why we'd still keep a team for some work:</b> least privilege is real. Customer service <i>cannot</i> request money,
facilities <i>cannot</i> buy stock. And 103's main run showed a genuinely useful split: count, price, write. But
notice where the safety actually came from: the MCP tools (refusals, duplicates, cost floor, no negative balance) and
the human signature, <b>not</b> the number of agents. A single agent behind the same 15 tools would be just as safe.
Our honest recommendation: a <b>router + one generalist</b> for routine tickets like rent, and specialists only when
a ticket crosses domains (stock + price + a customer letter).</p>

<h3>4. Three new problems this team <i>could</i> solve with the tools we built</h3>
<ol class="cases">
<li><b>"Can I get 4 Crest Mugs for my dorm?"</b> <code>CC-MUG-CREST</code> is at <b>0</b> in Aisle D.
 <ul>
 <li>Inventory: <code>check_stock_and_margin</code> (0 on hand, $3.50 cost, $14 list), then <code>check_vendor_can_ship(2)</code>. Elm City Gifts has no open invoice and a 3-day lead.</li>
 <li><code>request_purchase_order_approval</code>: 4 × $3.50 = <b>$14</b>, which even fits today's $20.</li>
 <li>Customer service drafts a "mugs in about 3 days, pending approval" note.</li>
 </ul>
 It's ticket 101's pattern on a vendor that isn't blocked, so no new tools are needed.</li>
<li><b>October rent, with $20 in the bank.</b> Lease 1's <code>next_due</code> moved to <b>2026-10-02</b> when we paid September's (Cash tab).
 <ul>
 <li>A rent ticket would send facilities to <code>check_rent_due(1)</code> and accounting to <code>get_cash_position</code>.</li>
 <li><code>request_payment_approval</code> would <b>refuse</b> ($2,400 vs $20).</li>
 <li>The boss would set the ticket to <code>waiting_on_human</code> with a clear shortfall, and customer service could save (not send) a draft to Elm City Properties asking about timing.</li>
 </ul>
 It can't make money appear, but it can raise the alarm 30+ days early and refuse to overdraw, which is the job.</li>
<li><b>Yale AI Club adds 20 caps at a club price.</b> <code>CC-HAT-BLUE</code> has <b>40</b> on hand (cost $6, list $22).
 <ul>
 <li>Accounting: <code>check_stock_and_margin</code>, then <code>request_price_override_approval</code> at, say, $18. That's above cost, and the tool refuses anything below $6.</li>
 <li>Customer service drafts the offer.</li>
 </ul>
 No PO and no cash are needed. It's ticket 103 without the shortfall, so it should be the team's easiest win.</li>
</ol>

<h3>5. Three new problems this team <i>could not</i> solve, and what it would take</h3>
<ol class="cases">
<li><b>Getting paid.</b> The club accepts the $49.30 price and pays <b>$394.40</b> for 8 hoodies.
 <ul>
 <li>Our shop literally can't record it. The rule is "cash only goes out", there is no sales table, and <code>inventory</code> wouldn't drop from 8.</li>
 <li>Meanwhile the Cash tab shows the shop at $20 with $2,400 rent due 10/02. Revenue is the only way out.</li>
 </ul>
 <i>Needs:</i>
 <ul>
 <li>A <code>sales</code> table, and a <code>record_sale(ticket, sku, size, qty, unit_price)</code> tool that decrements stock and writes a pending receipt.</li>
 <li>A human-confirmed <code>confirm_payment_received</code> that raises <code>cash_accounts</code>.</li>
 <li>A <code>forecast_cash(days)</code> tool that reads <code>leases.next_due</code> and invoice due dates. It would have warned, before anyone signed the $132 of POs, that October rent was uncovered.</li>
 <li>Agent: a <b>Sales / Treasurer</b> agent (or a widened accounting) that owns money <i>in</i> and the cash forecast.</li>
 </ul></li>
<li><b>Receiving stock and actually fulfilling orders.</b> We paid for 1 tee (#2) and 6 hoodies (#5, #6), and the 501 reprint is coming too.
 <ul>
 <li>Yet <code>inventory</code> still says tee S = 0 and hoodie M = 8. There's no <code>purchase_orders</code> table (POs live only as approval requests), no "arrived" event, and no way to hand Tauhid his shirt or ship the club's box.</li>
 </ul>
 <i>Needs:</i>
 <ul>
 <li>A <code>purchase_orders</code> table (ordered/shipped/received).</li>
 <li><code>receive_shipment(po_id, qty)</code> to update <code>inventory.qty</code>.</li>
 <li><code>reserve_stock(ticket_id)</code> / <code>fulfill_order</code>.</li>
 <li>A human-approved <code>book_courier</code> through <b>QuickShip CT</b> (vendor 3, 1-day lead), which no ticket ever used.</li>
 <li>Agent: a <b>Receiving & Fulfillment</b> agent that reopens 101 and 103 when the boxes land (around 9/5 for Bulldog's 5-day lead).</li>
 </ul></li>
<li><b>Having a conversation with the outside world.</b> Draft 1 asks Tauhid "M, L, XL, or wait?" and draft 2 asks the club "8 now or wait?".
 <ul>
 <li>The answers can never come back: no inbox, no send, no reply threading.</li>
 <li>Draft 2 is already stale. It was written before the 6-hoodie POs, and there's no tool to revise it.</li>
 <li>"Approving a PO" also isn't the same as <i>telling Bulldog</i> to print.</li>
 </ul>
 <i>Needs:</i>
 <ul>
 <li><code>send_draft(draft_id)</code>, human-approved (the shop rule stays: nothing goes out unsigned).</li>
 <li><code>update_draft</code>.</li>
 <li><code>ingest_inbox</code>, which turns emails into new tickets or replies on existing ones.</li>
 <li><code>submit_vendor_order(po_id)</code>.</li>
 <li>Agent: a <b>Correspondence</b> agent that triages incoming mail to the boss, plus a rule that customer service must refresh a draft whenever the board changes under it.</li>
 </ul></li>
</ol>

<h3>What I'd change first</h3>
<ul>
<li><b>Enforce what an open invoice is for.</b> <code>check_vendor_can_ship</code> already returns the description; <code>request_purchase_order_approval</code> should refuse a PO for a SKU and size that an open or just-paid invoice already covers. That fixes 101's $8.</li>
<li><b>Refuse PO-splitting.</b> After a <code>request_purchase_order_approval</code> refusal on a ticket and SKU, refuse further POs for that pair unless a human asks. That fixes 103's re-run.</li>
<li><b>Reserve rent.</b> Make <code>get_cash_position</code>'s "available" subtract rent due within 30 days, so a hoodie order can't eat October's lease.</li>
</ul>
</section>"""
