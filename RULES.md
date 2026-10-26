# Rules of this shop (enforced in code, not just in prompts)

1. **"Today" = `desk.date_today`.** Overdue means due date < `desk.date_today`. Never use the computer's clock.
2. **Vendor lead times come from `vendors.lead_days`.**
3. **No shipment while unpaid.** A vendor with an open unpaid invoice will not ship new product; restock plans must check this first.
4. **Human approval for every payment.** Agents may only *prepare* a payment; it executes only after a human approves it on the dashboard. When paid, update the relevant tables (`payments`, the invoice/lease status, `cash_accounts`).
5. **No negative balances.** The pay tool refuses if cash is insufficient.
6. **Cash only goes out.** No revenue is modeled; nothing adds money.
7. **Reset before a full run:** `python reset_db.py` restores `data/campus_customs_new.db` from the read-only original.
8. **No real contact.** No emails to customers, no calls to vendors. Drafts stay on the board.
9. **Model:** every agent uses only `gpt-6-luna` through Portkey with `PORTKEY_API_KEY`. No other model name appears in code or runs.
