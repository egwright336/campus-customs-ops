"""Data types for the Campus Customs agent team (structured outputs, delegation records, audit entries)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[str, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")


class Finding(BaseModel):
    """One fact an agent learned, always tied to the tool that produced it (no invented data)."""

    fact: str = Field(description="The fact in one sentence, with the real numbers from the tool.")
    source_tool: str = Field(description="MCP tool that returned it, e.g. check_stock_and_margin.")


class BoardAction(BaseModel):
    """Something the agent put on the board (an approval request, a draft, a status change)."""

    kind: Literal["payment_request", "purchase_order_request", "price_override_request", "draft", "status_update"]
    reference: str = Field(description="Request id, draft id or ticket id the tool returned.")
    summary: str


class AgentReport(BaseModel):
    """What a specialist (inventory, accounting, facilities, customer_service) hands back."""

    agent: AgentName
    ticket_id: int
    status: Literal["done", "blocked", "needs_human", "needs_info"] = Field(
        description="done = my part is finished; blocked = something outside my control stops it; "
                    "needs_human = waiting on a person's approval; needs_info = I need a fact I could not get.")
    summary: str = Field(description="2-4 sentences, plain language, polite and solutions-oriented.")
    findings: list[Finding] = Field(default_factory=list)
    actions_taken: list[BoardAction] = Field(default_factory=list)
    waiting_on_human: list[str] = Field(default_factory=list, description="Each approval a person still has to give.")
    next_steps: list[str] = Field(default_factory=list)


class TicketDecision(BaseModel):
    """The boss's final call on one ticket."""

    ticket_id: int
    decision: str = Field(description="The final call in 1-3 sentences.")
    assigned_to: list[AgentName] = Field(description="Teammates who worked on it.")
    final_status: Literal["resolved", "waiting_on_human", "in_progress"]
    approvals_waiting: list[str] = Field(default_factory=list, description="Approval requests a human must decide.")
    drafts_waiting: list[str] = Field(default_factory=list, description="Drafts saved on the board (never sent).")
    rationale: str = Field(description="Why, citing the real numbers the team found.")
    risks_or_followups: list[str] = Field(default_factory=list)


class Delegation(BaseModel):
    """A record of one agent asking another for help."""

    from_agent: AgentName
    to_agent: AgentName
    request: str
    chain: list[str]
    outcome: Literal["answered", "blocked_by_guard", "error", "cached"]
    reply: str = ""
