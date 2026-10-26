# Campus Customs MCP server

**What it is for.** The shared toolbox for the Campus Customs agent team (Boss, Inventory, Accounting,
Facilities, Customer Service). Every agent gets its tools from this one server, so they all see the same shop
data. Tools return only real values from the database (or arithmetic on them) and say "not found" instead of
guessing.

**Database.** `data/campus_customs_new.db`, the working copy (`config.DB_PATH`). The original
`data/campus_customs.db` is read-only; `python reset_db.py` restores the working copy. The shop's "today" is
`desk.date_today`. The server adds two board tables to the working copy if missing: `approval_requests`
(requests waiting for a human) and `drafts` (messages that are never sent).

**Tools**

| Tool | Tables | What it does |
|---|---|---|
| `check_stock_and_margin(sku, size, qty_requested)` | inventory, pricing | On hand vs requested for an exact SKU + size, shortfall, other sizes, cost, list price, price floor. |
| `check_vendor_can_ship(vendor_id)` | vendors, invoices, desk | Open unpaid invoices (days overdue), blocked or not, lead time, earliest arrival. |
| `check_rent_due(lease_id)` | leases, desk, cash_accounts | Rent, days until due, overdue or not, cash after paying. |
| `list_open_tickets()` | tickets | The work queue (everything not resolved). |
| `get_ticket(ticket_id)` | tickets, invoices, vendors, leases, approval_requests, drafts | One ticket with its linked invoice/lease and what is already on the board. |
| `get_cash_position()` | cash_accounts, approval_requests, invoices, leases | Balance, money committed to open requests, available cash, open invoices, rent due. |
| `list_vendors()` | vendors, invoices | Vendors with specialty, lead time and whether an unpaid invoice blocks them. |
| `list_board(ticket_id?)` | approval_requests, drafts | Everything waiting on the board. |
| `request_payment_approval(kind, ref_id, ticket_id, requested_by, reason)` | invoices/leases, cash_accounts, approval_requests | Puts an invoice or rent payment up for human approval (amount from the database; refuses duplicates and anything cash cannot cover). |
| `request_purchase_order_approval(vendor_id, sku, size, qty, ticket_id, requested_by, reason)` | vendors, invoices, pricing, inventory, cash_accounts, approval_requests | Puts a restock up for approval (refused while the vendor has an unpaid, unrequested invoice or if cash is short). |
| `request_price_override_approval(ticket_id, sku, qty, unit_price, requested_by, reason)` | pricing, approval_requests | Puts a discount up for approval (refused below cost). |
| `save_customer_draft(ticket_id, recipient, subject, body, created_by, kind)` | drafts | Saves a message as a draft. Never sent. |
| `update_ticket_status(ticket_id, status, note, updated_by)` | tickets | Moves a ticket along; only the boss may resolve. |
| `record_human_decision(request_id, decision, approver, note)` | approval_requests | **Human only** (dashboard): approve or reject. Rejects agent names. |
| `execute_approved_request(request_id)` | approval_requests, payments, cash_accounts, invoices, leases | **Human only**: pays an approved request, refuses if cash would go negative, updates the relevant tables. |

The backend gives each agent only the tools its job needs and never gives any agent the two human-only tools.

**Run:** `python mcp_server/server.py` (stdio) or `python mcp_server/server.py --http` (http://127.0.0.1:8001/mcp).
