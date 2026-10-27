"""Offline tests for the shop's safety rules (no API key, no model calls, no tokens).

    .venv/bin/python -m pytest tests/ -q

Each test runs the real MCP tool functions in mcp_server/server.py against a fresh temporary copy of the
ORIGINAL database, so the committed data files are never touched.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcp_server"))

import server  # noqa: E402
from config import MODEL_NAME, ORIGINAL_DB  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A clean copy of the original shop for each test: checking $3,400, today 2026-08-31."""
    path = tmp_path / "shop.db"
    shutil.copyfile(ORIGINAL_DB, path)
    path.chmod(0o644)
    monkeypatch.setattr(server, "DB_PATH", path)
    return path


def checking(path: Path) -> float:
    return sqlite3.connect(path).execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]


def rent_request() -> int:
    r = server.request_payment_approval("rent", 1, 102, "accounting", "rent due 2026-09-02")
    assert r["created"], r
    return r["request"]["id"]


# ---------------------------------------------------------------- money needs a human
def test_requests_never_move_money(db):
    rent_request()
    assert checking(db) == 3400
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0


@pytest.mark.parametrize("approver", ["accounting", "boss", "Boss", "", "   "])
def test_agents_cannot_approve(db, approver):
    rid = rent_request()
    r = server.record_human_decision(rid, "approved", approver)
    assert not r["ok"]
    assert "human" in r["error"].lower()


def test_pay_refuses_unapproved_request(db):
    rid = rent_request()
    r = server.execute_approved_request(rid)
    assert not r["ok"] and checking(db) == 3400


def test_human_approval_pays_and_updates_tables(db):
    rid = rent_request()
    assert server.record_human_decision(rid, "approved", "Eliza Wright")["ok"]
    r = server.execute_approved_request(rid)
    assert r["ok"] and r["new_balance"] == 1000
    con = sqlite3.connect(db)
    assert con.execute("SELECT next_due FROM leases WHERE id=1").fetchone()[0] == "2026-10-02"
    assert con.execute("SELECT amount, approved_by FROM payments").fetchone() == (2400, "Eliza Wright")
    # A second execute of the same request must not pay twice.
    assert not server.execute_approved_request(rid)["ok"] and checking(db) == 1000


# ---------------------------------------------------------------- no negative balances
def test_request_refused_when_cash_is_short(db):
    rent_request()  # commits $2,400 of $3,400, leaving $1,000
    # Elm City Gifts (vendor 2) has no unpaid invoice, so only the cash rule can stop this: 300 mugs x $3.50 = $1,050.
    r = server.request_purchase_order_approval(2, "CC-MUG-CREST", "OS", 300, 101, "inventory", "restock")
    assert not r["created"] and "cash" in r["error"].lower()
    assert r["max_units_affordable"] == 285


def test_pay_refuses_to_go_negative(db):
    rid = rent_request()
    assert server.record_human_decision(rid, "approved", "Eliza Wright")["ok"]
    sqlite3.connect(db).execute("UPDATE cash_accounts SET balance = 100").connection.commit()
    r = server.execute_approved_request(rid)
    assert not r["ok"] and "negative" in r["error"].lower()
    assert checking(db) == 100


# ---------------------------------------------------------------- other shop rules
def test_duplicate_payment_request_refused(db):
    rent_request()
    r = server.request_payment_approval("rent", 1, 102, "facilities", "again")
    assert not r["created"] and r.get("already_on_board")


def test_vendor_blocked_by_unrequested_unpaid_invoice(db):
    # Invoice 501 (Bulldog, overdue) is open and nobody has asked to pay it yet.
    assert server.check_vendor_can_ship(1)["blocked_by_unpaid_invoice"] is True
    r = server.request_purchase_order_approval(1, "CC-TEE-WHITE", "S", 1, 101, "inventory", "restock")
    assert not r["created"]


def test_price_below_cost_refused(db):
    r = server.request_price_override_approval(103, "CC-HOOD-NAVY", 8, 21.0, "accounting", "too cheap")
    assert not r["created"]


def test_only_the_boss_can_resolve(db):
    assert not server.update_ticket_status(101, "resolved", "done", "inventory")["updated"]
    assert server.update_ticket_status(101, "resolved", "done", "boss")["updated"]


def test_today_comes_from_the_desk_table(db):
    rent = server.check_rent_due(1)
    assert rent["shop_today"] == "2026-08-31"


# ---------------------------------------------------------------- agents: least privilege, one model
def test_no_agent_gets_human_only_tools():
    from backend.team import TOOLS_BY_AGENT

    for agent, tools in TOOLS_BY_AGENT.items():
        assert not set(tools) & server.HUMAN_ONLY_TOOLS, agent


def test_only_gpt_6_luna():
    assert MODEL_NAME == "gpt-6-luna"
