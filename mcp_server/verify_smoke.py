"""Check output/mcp_smoke.json against the database itself.

    python mcp_server/verify_smoke.py

For every saved tool call, re-reads the same rows straight from data/campus_customs_new.db with SQL and
confirms the key values in the saved tool output match. Prints PASS/FAIL per tool.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import DB_PATH  # noqa: E402

con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
today = date.fromisoformat(con.execute("SELECT date_today FROM desk").fetchone()[0])


def expect_stock(a: dict) -> dict:
    inv = con.execute("SELECT qty FROM inventory WHERE sku=? AND size=?", (a["sku"], a["size"])).fetchone()
    pr = con.execute("SELECT unit_cost, list_price FROM pricing WHERE sku=?", (a["sku"],)).fetchone()
    return {"qty_on_hand": inv["qty"], "shortfall": max(a["qty_requested"] - inv["qty"], 0),
            "unit_cost": pr["unit_cost"], "list_price": pr["list_price"]}


def expect_vendor(a: dict) -> dict:
    v = con.execute("SELECT name, lead_days FROM vendors WHERE id=?", (a["vendor_id"],)).fetchone()
    inv = con.execute("SELECT id, amount FROM invoices WHERE vendor_id=? AND status='open'", (a["vendor_id"],)).fetchall()
    return {"vendor_name": v["name"], "lead_days": v["lead_days"], "blocked_by_unpaid_invoice": bool(inv),
            "amount_to_pay_to_unblock": round(sum(i["amount"] for i in inv), 2)}


def expect_rent(a: dict) -> dict:
    lease = con.execute("SELECT monthly_rent, next_due FROM leases WHERE id=?", (a["lease_id"],)).fetchone()
    cash = sum(r["balance"] for r in con.execute("SELECT balance FROM cash_accounts"))
    return {"monthly_rent": lease["monthly_rent"], "next_due": lease["next_due"],
            "days_until_due": (date.fromisoformat(lease["next_due"]) - today).days, "total_cash": cash}


EXPECT = {"check_stock_and_margin": expect_stock, "check_vendor_can_ship": expect_vendor, "check_rent_due": expect_rent}

if __name__ == "__main__":
    calls = json.loads((ROOT / "output" / "mcp_smoke.json").read_text())["calls"]
    ok_all = True
    for c in calls:
        want = EXPECT[c["tool"]](c["arguments"])
        got = {k: c["output"].get(k) for k in want}
        ok = got == want
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {c['tool']}({c['arguments']})  db={want}" + ("" if ok else f"  saved={got}"))
    print("ALL MATCH THE DATABASE" if ok_all else "MISMATCH FOUND")
