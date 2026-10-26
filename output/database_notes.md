# Campus Customs database: tables, fields and how the 3 open tickets link

Source: `data/campus_customs.db` (original, read-only). Working copy: `data/campus_customs_new.db`.
Shop "today" (`desk.date_today`): **2026-08-31**. Cash (`cash_accounts.checking`): **$3,400.00**.

## Tables and fields

| Table | Fields (PK in bold) | Rows | Notes |
|---|---|---|---|
| desk | date_today, notes | 1 | "today" for the shop = 2026-08-31 |
| tickets | **id**, type, requester, subject, sku, size, qty, lease_id → leases.id, invoice_id → invoices.id, status, notes, created_at | 3 | all `open` |
| inventory | **sku**, **size**, name, qty, location | 10 | stock by SKU + size |
| pricing | **sku**, unit_cost, list_price | 4 | margin = list_price − unit_cost |
| vendors | **id**, name, specialty, lead_days | 3 | lead times for restock |
| invoices | **id**, vendor_id → vendors.id, amount, due_date, status, description | 1 | 501 open, overdue |
| leases | **id**, space_name, landlord, monthly_rent, next_due, notes | 1 | rent due 2026-09-02 |
| cash_accounts | **name**, balance, date | 1 | checking $3,400 |
| payments | **id**, kind, ref_id, amount, account, paid_at, approved_by | 0 | empty; written when a human-approved payment executes |

## The 3 open tickets

| Ticket | What | Links | What it implies |
|---|---|---|---|
| 101 customer_order | Tauhid Zaman: 1 × CC-TEE-WHITE, size S | inventory (CC-TEE-WHITE, S) = **0**; invoice **501** → vendor 1 Bulldog Print Co ($840, due 2026-08-28, **open, 3 days overdue**); pricing $8 cost / $28 list | Out of stock. Bulldog won't ship until 501 is paid (human approval). Then restock lead time 5 days (≈ 2026-09-05). |
| 102 rent_notice | Elm City Properties: rent due | lease **1** Chapel Street shop, $2,400, next_due **2026-09-02** (in 2 days) | Rent payment needed; human approval required. |
| 103 price_override | Yale AI Club: 20 × CC-HOOD-NAVY, size M, bulk discount | inventory (CC-HOOD-NAVY, M) = **8** → shortfall 12; pricing $22 cost / $58 list (≈62% margin); restock vendor would be Bulldog Print Co (apparel) | Discount must protect margin; restock blocked by unpaid invoice 501; lead 5 days. |

## Constraints the agents will have to balance

- Cash: $3,400 − $840 (invoice 501) − $2,400 (rent) = **$160 left**; restocking 12 hoodies costs 12 × $22 = **$264**, so not everything can be paid and restocked. No revenue comes in.
- Links that are **not** declared in the schema: ticket.sku/size → inventory and pricing (by key match); product → vendor (inferred from `vendors.specialty`: apparel → Bulldog Print Co, mugs → Elm City Gifts; QuickShip CT is a courier).
- Other stockouts: CC-MUG-CREST (OS) = 0 (no ticket yet).
