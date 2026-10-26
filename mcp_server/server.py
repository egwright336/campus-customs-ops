"""Campus Customs MCP server: the shared toolbox every agent on the team uses.

Reads the WORKING shop database (config.DB_PATH = data/campus_customs_new.db). Every value a tool returns
comes straight from the database or from simple arithmetic on database values; nothing is made up. If a
record does not exist, the tool says so instead of guessing.

Run (stdio):  python mcp_server/server.py
Run (HTTP):   python mcp_server/server.py --http      -> http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DB_PATH  # noqa: E402  (shared setting: the working copy, never the original)

mcp = FastMCP("campus-customs-ops")


def _connect_read_only() -> sqlite3.Connection:
    """Read-only connection: these three tools can look but never change the shop's data."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _shop_today(con: sqlite3.Connection) -> date:
    """The shop's 'today' is desk.date_today (shop rule), not the computer's clock."""
    row = con.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return date.fromisoformat(row["date_today"])


@mcp.tool
def check_stock_and_margin(sku: str, size: str, qty_requested: int) -> dict:
    """Check whether the shop can fill an order for one SKU and size, and what price floor protects margin.

    Reads inventory (units on hand for this exact SKU + size) and pricing (unit cost and list price).
    Returns on-hand units, the shortfall versus the requested quantity, unit cost, list price, margin per
    unit, and the lowest price per unit that still does not sell below cost.

    Args:
        sku: product SKU exactly as stored, e.g. "CC-HOOD-NAVY".
        size: size exactly as stored, e.g. "M" (use "OS" for one-size items).
        qty_requested: how many units the customer wants.
    """
    with _connect_read_only() as con:
        stock = con.execute("SELECT name, qty, location FROM inventory WHERE sku = ? AND size = ?",
                            (sku, size)).fetchone()
        price = con.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        sizes = con.execute("SELECT size, qty FROM inventory WHERE sku = ? ORDER BY size", (sku,)).fetchall()
    if stock is None:
        return {"found": False, "error": f"No inventory row for sku={sku!r}, size={size!r}."}
    on_hand = stock["qty"]
    result = {
        "found": True,
        "sku": sku, "size": size, "name": stock["name"], "location": stock["location"],
        "qty_requested": qty_requested, "qty_on_hand": on_hand,
        "can_fill_from_stock": on_hand >= qty_requested,
        "shortfall": max(qty_requested - on_hand, 0),
        "other_sizes_on_hand": {r["size"]: r["qty"] for r in sizes if r["size"] != size},
    }
    if price is None:
        result["pricing"] = f"No pricing row for sku={sku!r}."
    else:
        cost, list_price = price["unit_cost"], price["list_price"]
        result.update({
            "unit_cost": cost, "list_price": list_price,
            "margin_per_unit_at_list": round(list_price - cost, 2),
            "margin_pct_at_list": round(100 * (list_price - cost) / list_price, 1),
            "lowest_price_without_loss": cost,
            "max_discount_pct_without_loss": round(100 * (list_price - cost) / list_price, 1),
            "order_value_at_list": round(list_price * qty_requested, 2),
            "order_cost": round(cost * qty_requested, 2),
        })
    return result


@mcp.tool
def check_vendor_can_ship(vendor_id: int) -> dict:
    """Check whether a vendor will ship a restock now, and when it would arrive.

    Reads vendors (name, specialty, lead_days), invoices (this vendor's open, unpaid invoices) and desk
    (the shop's today). Shop rule: a vendor will not ship new product while it has an open unpaid invoice.
    Returns the open invoices with days overdue, whether the vendor is blocked, the total that must be paid
    to unblock it, and the earliest arrival date (today + lead_days) once unblocked.

    Args:
        vendor_id: the vendor's id from the vendors table (e.g. the vendor_id on a ticket's invoice).
    """
    with _connect_read_only() as con:
        today = _shop_today(con)
        vendor = con.execute("SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
                             (vendor_id,)).fetchone()
        open_invoices = con.execute(
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date", (vendor_id,)).fetchall()
    if vendor is None:
        return {"found": False, "error": f"No vendor with id={vendor_id}."}
    invoices = []
    for inv in open_invoices:
        due = date.fromisoformat(inv["due_date"])
        invoices.append({
            "invoice_id": inv["id"], "amount": inv["amount"], "due_date": inv["due_date"],
            "status": inv["status"], "description": inv["description"],
            "days_overdue": max((today - due).days, 0), "overdue": due < today,
        })
    blocked = bool(invoices)
    lead = vendor["lead_days"]
    return {
        "found": True,
        "vendor_id": vendor["id"], "vendor_name": vendor["name"], "specialty": vendor["specialty"],
        "shop_today": today.isoformat(), "lead_days": lead,
        "blocked_by_unpaid_invoice": blocked,
        "open_unpaid_invoices": invoices,
        "amount_to_pay_to_unblock": round(sum(i["amount"] for i in invoices), 2),
        "earliest_arrival_if_ordered_today": None if blocked else date.fromordinal(today.toordinal() + lead).isoformat(),
        "earliest_arrival_after_unblocking_today": date.fromordinal(today.toordinal() + lead).isoformat(),
        "note": ("Vendor will not ship until its open invoices are paid; paying requires human approval."
                 if blocked else "No open invoices; vendor can ship."),
    }


@mcp.tool
def check_rent_due(lease_id: int) -> dict:
    """Check a lease's next rent payment against the shop's date and cash.

    Reads leases (space, landlord, monthly_rent, next_due), desk (the shop's today) and cash_accounts
    (balance). Returns days until rent is due (negative if overdue), whether it is overdue, the cash balance,
    and the balance that would remain after paying, so a payment is never proposed that would go negative.

    Args:
        lease_id: the lease id from the leases table (e.g. the lease_id on a rent ticket).
    """
    with _connect_read_only() as con:
        today = _shop_today(con)
        lease = con.execute("SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
                            (lease_id,)).fetchone()
        accounts = con.execute("SELECT name, balance, date FROM cash_accounts").fetchall()
    if lease is None:
        return {"found": False, "error": f"No lease with id={lease_id}."}
    due = date.fromisoformat(lease["next_due"])
    rent = lease["monthly_rent"]
    cash = {a["name"]: a["balance"] for a in accounts}
    total_cash = sum(cash.values())
    return {
        "found": True,
        "lease_id": lease["id"], "space_name": lease["space_name"], "landlord": lease["landlord"],
        "monthly_rent": rent, "next_due": lease["next_due"], "shop_today": today.isoformat(),
        "days_until_due": (due - today).days, "overdue": due < today,
        "cash_balances": cash, "total_cash": total_cash,
        "cash_covers_rent": total_cash >= rent,
        "balance_after_paying_rent": round(total_cash - rent, 2),
        "note": "Paying rent requires human approval; the payment must not take cash below zero.",
    }


# =====================================================================================================
# Problem 5 additions: tickets, cash, vendors, and the approval board.
#
# The "board" lives in two tables the server adds to the WORKING copy if they are missing (a reset restores
# the original without them; the server recreates them on start):
#   approval_requests  money moves and discounts waiting for a human (agents can only create these)
#   drafts             customer/vendor messages that are saved, never sent
# =====================================================================================================

import json  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Literal  # noqa: E402

AGENTS = {"boss", "inventory", "accounting", "facilities", "customer_service"}
BOARD_DDL = """
CREATE TABLE IF NOT EXISTS approval_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER, kind TEXT NOT NULL, ref_id INTEGER, vendor_id INTEGER, sku TEXT, size TEXT, qty INTEGER,
  unit_price REAL, amount REAL NOT NULL, payee TEXT, reason TEXT, requested_by TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
  decided_by TEXT, decided_at TEXT, decision_note TEXT, executed_at TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER, kind TEXT NOT NULL, recipient TEXT NOT NULL, subject TEXT, body TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft');
"""
OPEN_REQUEST = ("pending", "approved")


def _connect_rw() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(BOARD_DDL)
    return con


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _committed(con: sqlite3.Connection) -> float:
    """Money already promised to requests that are pending or approved but not yet paid."""
    row = con.execute("SELECT COALESCE(SUM(amount), 0) FROM approval_requests WHERE status IN ('pending','approved') "
                      "AND kind IN ('invoice_payment','rent_payment','purchase_order')").fetchone()
    return float(row[0])


def _cash(con: sqlite3.Connection) -> float:
    return float(con.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_accounts").fetchone()[0])


def _row(r) -> dict:
    return dict(r) if r is not None else None


def _check_agent(name: str) -> str | None:
    return None if name in AGENTS else f"requested_by must be one of {sorted(AGENTS)}."


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket on the board that is not resolved yet (reads tickets). Start here to see the work queue."""
    with _connect_rw() as con:
        rows = con.execute("SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Full details for one ticket plus the records it links to.

    Reads tickets, and the linked invoices row (with vendor) and/or leases row, plus any approval requests and
    drafts already on the board for this ticket, so an agent never repeats work that is already waiting.

    Args:
        ticket_id: the ticket id, e.g. 101.
    """
    with _connect_rw() as con:
        t = con.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"found": False, "error": f"No ticket with id={ticket_id}."}
        out = {"found": True, "ticket": dict(t), "shop_today": _shop_today(con).isoformat()}
        if t["invoice_id"] is not None:
            inv = con.execute("SELECT i.*, v.name AS vendor_name, v.lead_days FROM invoices i "
                              "LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?", (t["invoice_id"],)).fetchone()
            out["linked_invoice"] = _row(inv)
        if t["lease_id"] is not None:
            out["linked_lease"] = _row(con.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone())
        out["approval_requests_on_board"] = [dict(r) for r in con.execute(
            "SELECT * FROM approval_requests WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        out["drafts_on_board"] = [dict(r) for r in con.execute(
            "SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
    return out


@mcp.tool
def get_cash_position() -> dict:
    """The shop's cash picture before anyone proposes spending.

    Reads cash_accounts (balance), approval_requests (money already committed to pending/approved requests),
    invoices (open bills, with days overdue against desk.date_today) and leases (rent coming due). Returns the
    balance, the committed total, and what is still available to commit without ever going negative.
    """
    with _connect_rw() as con:
        today = _shop_today(con)
        cash, committed = _cash(con), _committed(con)
        balances = {r["name"]: r["balance"] for r in con.execute("SELECT name, balance FROM cash_accounts")}
        invoices = [{**dict(r), "days_overdue": max((today - date.fromisoformat(r["due_date"])).days, 0)}
                    for r in con.execute("SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.description "
                                         "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open'")]
        leases = [{**dict(r), "days_until_due": (date.fromisoformat(r["next_due"]) - today).days}
                  for r in con.execute("SELECT id, space_name, landlord, monthly_rent, next_due FROM leases")]
        pending = [dict(r) for r in con.execute(
            "SELECT id, kind, ref_id, amount, payee, status, requested_by FROM approval_requests "
            "WHERE status IN ('pending','approved') ORDER BY id")]
    return {"shop_today": today.isoformat(), "cash_balance": cash, "cash_balances": balances,
            "committed_to_open_requests": committed,
            "available_to_commit": round(cash - committed, 2), "open_invoices": invoices, "leases": leases,
            "open_requests": pending,
            "note": "Cash only goes out (no revenue is modeled). No request may push available cash below zero."}


@mcp.tool
def list_vendors() -> list[dict]:
    """Every vendor with specialty, lead time, and whether an open unpaid invoice blocks shipping.

    Reads vendors and invoices. Use it to choose who can restock which product (match the specialty to the
    product) before calling check_vendor_can_ship for the details.
    """
    with _connect_rw() as con:
        rows = con.execute(
            "SELECT v.id, v.name, v.specialty, v.lead_days, "
            "(SELECT COUNT(*) FROM invoices i WHERE i.vendor_id = v.id AND i.status = 'open') AS open_invoices, "
            "(SELECT COALESCE(SUM(amount),0) FROM invoices i WHERE i.vendor_id = v.id AND i.status = 'open') AS open_amount "
            "FROM vendors v ORDER BY v.id").fetchall()
    return [{**dict(r), "blocked_by_unpaid_invoice": r["open_invoices"] > 0} for r in rows]


@mcp.tool
def request_payment_approval(kind: Literal["invoice", "rent"], ref_id: int, ticket_id: int,
                             requested_by: str, reason: str) -> dict:
    """Put a payment on the board for a HUMAN to approve. This never moves money.

    Reads invoices or leases (the amount always comes from the database, never from the agent), cash_accounts
    and approval_requests; writes one row to approval_requests with status 'pending'. Refuses if the bill does
    not exist or is already paid, if the same payment is already waiting, or if cash available after other
    open requests would not cover it (no negative balances).

    Args:
        kind: "invoice" (pay a vendor invoice) or "rent" (pay a lease's next rent).
        ref_id: invoices.id for kind="invoice", leases.id for kind="rent".
        ticket_id: the ticket this payment helps resolve.
        requested_by: the agent asking (boss, inventory, accounting, facilities, customer_service).
        reason: one or two sentences a human approver can act on.
    """
    if err := _check_agent(requested_by):
        return {"created": False, "error": err}
    with _connect_rw() as con:
        if kind == "invoice":
            inv = con.execute("SELECT i.*, v.name AS vendor_name FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id "
                              "WHERE i.id = ?", (ref_id,)).fetchone()
            if inv is None:
                return {"created": False, "error": f"No invoice with id={ref_id}."}
            if inv["status"] != "open":
                return {"created": False, "error": f"Invoice {ref_id} is '{inv['status']}', not open."}
            req_kind, amount, payee, vendor_id = "invoice_payment", inv["amount"], inv["vendor_name"], inv["vendor_id"]
        else:
            lease = con.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"created": False, "error": f"No lease with id={ref_id}."}
            req_kind, amount, payee, vendor_id = "rent_payment", lease["monthly_rent"], lease["landlord"], None
        dup = con.execute("SELECT * FROM approval_requests WHERE kind = ? AND ref_id = ? AND status IN ('pending','approved')",
                          (req_kind, ref_id)).fetchone()
        if dup:
            return {"created": False, "already_on_board": dict(dup),
                    "note": "This payment is already waiting for a human; do not request it again."}
        cash, committed = _cash(con), _committed(con)
        if amount > cash - committed:
            return {"created": False, "error": "Not enough uncommitted cash for this payment.",
                    "amount": amount, "cash_balance": cash, "committed_to_open_requests": committed,
                    "available_to_commit": round(cash - committed, 2)}
        cur = con.execute("INSERT INTO approval_requests (ticket_id, kind, ref_id, vendor_id, amount, payee, reason, "
                          "requested_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                          (ticket_id, req_kind, ref_id, vendor_id, amount, payee, reason, requested_by, _now()))
        req = dict(con.execute("SELECT * FROM approval_requests WHERE id = ?", (cur.lastrowid,)).fetchone())
    return {"created": True, "request": req, "available_after_this_request": round(cash - committed - amount, 2),
            "note": "Waiting for human approval on the dashboard. No money has moved."}


@mcp.tool
def request_purchase_order_approval(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                                    requested_by: str, reason: str) -> dict:
    """Put a restock purchase order on the board for a HUMAN to approve. This never moves money.

    Reads vendors, invoices (a vendor with an open unpaid invoice will not ship), pricing (cost = qty x
    unit_cost), cash_accounts and approval_requests; writes one 'pending' row to approval_requests. Refuses if
    the vendor is blocked by an open invoice that has no payment request on the board yet, or if available cash
    would go negative.

    Args:
        vendor_id: who will make the product (match vendors.specialty to the product).
        sku: product SKU, e.g. "CC-HOOD-NAVY".
        size: size to restock, e.g. "M".
        qty: units to order (usually the shortfall from check_stock_and_margin).
        ticket_id: the ticket this restock serves.
        requested_by: the agent asking.
        reason: one or two sentences a human approver can act on.
    """
    if err := _check_agent(requested_by):
        return {"created": False, "error": err}
    if qty <= 0:
        return {"created": False, "error": "qty must be positive."}
    with _connect_rw() as con:
        today = _shop_today(con)
        v = con.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        pr = con.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if v is None or pr is None:
            return {"created": False, "error": f"Unknown vendor_id={vendor_id} or sku={sku!r}."}
        if con.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"created": False, "error": f"No inventory row for {sku} size {size}."}
        open_inv = con.execute("SELECT id, amount FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)).fetchall()
        waiting = {r["ref_id"] for r in con.execute("SELECT ref_id FROM approval_requests WHERE kind = 'invoice_payment' "
                                                     "AND status IN ('pending','approved')")}
        unpaid_unrequested = [r["id"] for r in open_inv if r["id"] not in waiting]
        if unpaid_unrequested:
            return {"created": False, "error": f"{v['name']} will not ship while invoice(s) {unpaid_unrequested} are unpaid. "
                    "Request payment approval for them first (kind='invoice')."}
        amount = round(qty * pr["unit_cost"], 2)
        cash, committed = _cash(con), _committed(con)
        if amount > cash - committed:
            return {"created": False, "error": "Not enough uncommitted cash for this purchase order.",
                    "amount": amount, "cash_balance": cash, "committed_to_open_requests": committed,
                    "available_to_commit": round(cash - committed, 2),
                    "max_units_affordable": int((cash - committed) // pr["unit_cost"]) if cash > committed else 0}
        cur = con.execute("INSERT INTO approval_requests (ticket_id, kind, vendor_id, sku, size, qty, unit_price, amount, payee, "
                          "reason, requested_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (ticket_id, "purchase_order", vendor_id, sku, size, qty, pr["unit_cost"], amount, v["name"],
                           reason, requested_by, _now()))
        req = dict(con.execute("SELECT * FROM approval_requests WHERE id = ?", (cur.lastrowid,)).fetchone())
    blocked_note = (" Ships only after the vendor's open invoice is paid." if open_inv else "")
    return {"created": True, "request": req,
            "expected_arrival_if_approved_today": date.fromordinal(today.toordinal() + v["lead_days"]).isoformat(),
            "note": "Waiting for human approval on the dashboard. No money has moved." + blocked_note}


@mcp.tool
def request_price_override_approval(ticket_id: int, sku: str, qty: int, unit_price: float,
                                    requested_by: str, reason: str) -> dict:
    """Put a discount (price override) on the board for a HUMAN to approve.

    Reads pricing (refuses any price below unit_cost or at/above list_price) and writes one 'pending' row to
    approval_requests. Returns the discount percent and margin at the proposed price.

    Args:
        ticket_id: the ticket asking for the discount.
        sku: product SKU.
        qty: units at the special price.
        unit_price: proposed price per unit.
        requested_by: the agent asking.
        reason: why this price is fair to the customer and safe for the shop.
    """
    if err := _check_agent(requested_by):
        return {"created": False, "error": err}
    with _connect_rw() as con:
        pr = con.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if pr is None:
            return {"created": False, "error": f"No pricing for sku={sku!r}."}
        if unit_price < pr["unit_cost"]:
            return {"created": False, "error": f"${unit_price} is below unit cost ${pr['unit_cost']}; the shop never sells at a loss."}
        if unit_price >= pr["list_price"]:
            return {"created": False, "error": f"${unit_price} is not a discount (list price ${pr['list_price']})."}
        dup = con.execute("SELECT * FROM approval_requests WHERE kind = 'price_override' AND ticket_id = ? "
                          "AND status IN ('pending','approved')", (ticket_id,)).fetchone()
        if dup:
            return {"created": False, "already_on_board": dict(dup), "note": "A discount for this ticket is already waiting."}
        amount = round(qty * unit_price, 2)
        cur = con.execute("INSERT INTO approval_requests (ticket_id, kind, sku, qty, unit_price, amount, reason, requested_by, "
                          "created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                          (ticket_id, "price_override", sku, qty, unit_price, amount, reason, requested_by, _now()))
        req = dict(con.execute("SELECT * FROM approval_requests WHERE id = ?", (cur.lastrowid,)).fetchone())
    return {"created": True, "request": req,
            "discount_pct_off_list": round(100 * (1 - unit_price / pr["list_price"]), 1),
            "margin_per_unit": round(unit_price - pr["unit_cost"], 2),
            "margin_pct": round(100 * (unit_price - pr["unit_cost"]) / unit_price, 1),
            "note": "Waiting for human approval. This is order revenue at the special price; no cash moves."}


@mcp.tool
def save_customer_draft(ticket_id: int, recipient: str, subject: str, body: str, created_by: str,
                        kind: Literal["customer_message", "vendor_message", "landlord_message"] = "customer_message") -> dict:
    """Save a message as a DRAFT on the board. Nothing is ever emailed or sent (shop rule).

    Writes one row to drafts with status 'draft'.

    Args:
        ticket_id: the ticket the message is about.
        recipient: who it is for, exactly as named on the ticket (e.g. the ticket's requester).
        subject: short subject line.
        body: the full message text.
        created_by: the agent writing it.
        kind: customer_message, vendor_message or landlord_message.
    """
    if err := _check_agent(created_by):
        return {"saved": False, "error": err}
    with _connect_rw() as con:
        cur = con.execute("INSERT INTO drafts (ticket_id, kind, recipient, subject, body, created_by, created_at) "
                          "VALUES (?,?,?,?,?,?,?)", (ticket_id, kind, recipient, subject, body, created_by, _now()))
        d = dict(con.execute("SELECT * FROM drafts WHERE id = ?", (cur.lastrowid,)).fetchone())
    return {"saved": True, "draft": d, "note": "Saved as a draft on the board. Not sent."}


@mcp.tool
def update_ticket_status(ticket_id: int, status: Literal["in_progress", "waiting_on_human", "resolved"],
                         note: str, updated_by: str) -> dict:
    """Move a ticket along the board and leave a short note (writes tickets.status and appends to tickets.notes).

    Only the boss may mark a ticket 'resolved' (the boss makes final calls).

    Args:
        ticket_id: the ticket.
        status: in_progress, waiting_on_human (e.g. approvals pending) or resolved.
        note: one line explaining the change.
        updated_by: the agent making the change.
    """
    if err := _check_agent(updated_by):
        return {"updated": False, "error": err}
    if status == "resolved" and updated_by != "boss":
        return {"updated": False, "error": "Only the boss can mark a ticket resolved."}
    with _connect_rw() as con:
        t = con.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"updated": False, "error": f"No ticket with id={ticket_id}."}
        notes = (t["notes"] or "") + f" | [{updated_by} -> {status}] {note}"
        con.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
        return {"updated": True, "ticket": dict(con.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())}


@mcp.tool
def list_board(ticket_id: int | None = None) -> dict:
    """Everything waiting on the board: approval requests (any status) and saved drafts (reads approval_requests, drafts).

    Args:
        ticket_id: optional; only show items for this ticket.
    """
    with _connect_rw() as con:
        where, args = ("WHERE ticket_id = ?", (ticket_id,)) if ticket_id is not None else ("", ())
        reqs = [dict(r) for r in con.execute(f"SELECT * FROM approval_requests {where} ORDER BY id", args)]
        drafts = [dict(r) for r in con.execute(f"SELECT * FROM drafts {where} ORDER BY id", args)]
    return {"approval_requests": reqs, "drafts": drafts}


# ----------------------------------------------------------------------------- human-only tools
# These two are NEVER given to agents (the backend filters them out). The dashboard calls them after a person
# clicks Approve/Reject. They also defend themselves: agent names cannot approve, and payment refuses if cash
# would go negative.

@mcp.tool
def record_human_decision(request_id: int, decision: Literal["approved", "rejected"], approver: str, note: str = "") -> dict:
    """HUMAN ONLY. Record a person's approve/reject decision on a pending request (writes approval_requests)."""
    approver = (approver or "").strip()
    if not approver or approver.lower() in AGENTS:
        return {"ok": False, "error": "Decisions must come from a named human, not an agent."}
    with _connect_rw() as con:
        r = con.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None or r["status"] != "pending":
            return {"ok": False, "error": f"Request {request_id} is not pending."}
        con.execute("UPDATE approval_requests SET status = ?, decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
                    (decision, approver, _now(), note, request_id))
        return {"ok": True, "request": dict(con.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone())}


@mcp.tool
def execute_approved_request(request_id: int) -> dict:
    """HUMAN ONLY. Carry out a request a human approved.

    Payments (invoice, rent, purchase order): refuses if cash would go negative; otherwise writes payments,
    lowers cash_accounts.balance, marks the invoice paid or moves the lease's next_due forward one month, and
    marks the request executed. Price overrides: records the approved price (no cash moves).
    """
    with _connect_rw() as con:
        today = _shop_today(con)
        r = con.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None or r["status"] != "approved":
            return {"ok": False, "error": f"Request {request_id} is not approved by a human."}
        if (r["decided_by"] or "").lower() in AGENTS:
            return {"ok": False, "error": "Approval did not come from a human."}
        if r["kind"] == "price_override":
            con.execute("UPDATE approval_requests SET status='executed', executed_at=?, result=? WHERE id=?",
                        (_now(), f"Approved price ${r['unit_price']} for {r['qty']} x {r['sku']}", request_id))
            return {"ok": True, "result": "Price override recorded; no cash moved."}
        acct = con.execute("SELECT name, balance FROM cash_accounts ORDER BY balance DESC LIMIT 1").fetchone()
        if acct is None or acct["balance"] < r["amount"]:
            return {"ok": False, "error": "Refused: not enough cash; balances can never go negative.",
                    "amount": r["amount"], "cash_balance": acct["balance"] if acct else 0}
        kind = {"invoice_payment": "invoice", "rent_payment": "rent", "purchase_order": "purchase_order"}[r["kind"]]
        ref = r["ref_id"] if r["ref_id"] is not None else request_id
        con.execute("INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?,?,?,?)",
                    (kind, ref, r["amount"], acct["name"], today.isoformat(), r["decided_by"]))
        con.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
                    (r["amount"], today.isoformat(), acct["name"]))
        if r["kind"] == "invoice_payment":
            con.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (r["ref_id"],))
        elif r["kind"] == "rent_payment":
            nd = date.fromisoformat(con.execute("SELECT next_due FROM leases WHERE id = ?", (r["ref_id"],)).fetchone()[0])
            nxt = date(nd.year + (nd.month // 12), nd.month % 12 + 1, min(nd.day, 28))
            con.execute("UPDATE leases SET next_due = ? WHERE id = ?", (nxt.isoformat(), r["ref_id"]))
        result = f"Paid ${r['amount']:.2f} to {r['payee']} from {acct['name']} on {today.isoformat()}"
        con.execute("UPDATE approval_requests SET status='executed', executed_at=?, result=? WHERE id=?",
                    (_now(), result, request_id))
        bal = con.execute("SELECT balance FROM cash_accounts WHERE name = ?", (acct["name"],)).fetchone()[0]
    return {"ok": True, "result": result, "new_balance": bal}


HUMAN_ONLY_TOOLS = {"record_human_decision", "execute_approved_request"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve over HTTP instead of stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001)
    else:
        mcp.run()
