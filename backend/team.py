"""The Campus Customs agent team (PydanticAI): boss, inventory, accounting, facilities, customer_service.

- Every agent uses ONLY gpt-6-luna through Portkey (config.MODEL_NAME, PORTKEY_API_KEY).
- Shop facts come only from the MCP server (mcp_server/server.py) over data/campus_customs_new.db. Each agent
  gets a filtered view of that one MCP server (least privilege). The human-only tools (record a decision,
  execute an approved payment) are never given to any agent.
- Full connectivity: every agent has `ask_teammate(teammate, request)` and can ask any other agent.
- Loop guards: no asking yourself or anyone already in the current chain, a maximum chain depth, a cap on
  delegations per agent run, a cap on agent runs per ticket, repeated identical requests answered from cache,
  and per-run request/token limits plus a per-ticket token budget.
- Every agent-loop step is appended to output/audit_trail.json (backend/audit.py).
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.messages import ModelRequest, ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import DB_PATH, MODEL_NAME, PORTKEY_BASE_URL, portkey_api_key  # noqa: E402

from backend import audit  # noqa: E402
from backend.models import AGENT_NAMES, AgentName, AgentReport, Delegation, TicketDecision  # noqa: E402

PROMPTS = Path(__file__).resolve().parent / "prompts"

# ---------------------------------------------------------------------------- limits (token + loop control)
MAX_CHAIN_DEPTH = 3            # boss -> A -> B -> C at most
MAX_DELEGATIONS_PER_RUN = 3    # one agent run may ask teammates at most 3 times
MAX_AGENT_RUNS_PER_TICKET = 10 # all agents together, per ticket
MAX_REQUESTS_PER_RUN = 8       # model round trips per agent run
MAX_TOKENS_PER_RUN = 60_000
MAX_TOKENS_PER_TICKET = 250_000

# ---------------------------------------------------------------------------- least-privilege tool access
READ_TOOLS = {"get_ticket", "list_board"}
TOOLS_BY_AGENT: dict[str, set[str]] = {
    "boss": READ_TOOLS | {"list_open_tickets", "get_cash_position", "update_ticket_status"},
    "inventory": READ_TOOLS | {"check_stock_and_margin", "list_vendors", "check_vendor_can_ship",
                               "request_purchase_order_approval"},
    "accounting": READ_TOOLS | {"get_cash_position", "check_vendor_can_ship", "check_rent_due", "check_stock_and_margin",
                                "list_vendors", "request_payment_approval", "request_purchase_order_approval",
                                "request_price_override_approval"},
    "facilities": READ_TOOLS | {"check_rent_due", "get_cash_position"},
    "customer_service": READ_TOOLS | {"check_stock_and_margin", "save_customer_draft"},
}
HUMAN_ONLY = {"record_human_decision", "execute_approved_request"}
assert not any(HUMAN_ONLY & tools for tools in TOOLS_BY_AGENT.values()), "agents must never get human-only tools"


def build_model() -> OpenAIResponsesModel:
    client = AsyncOpenAI(api_key=portkey_api_key(), base_url=PORTKEY_BASE_URL)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def build_mcp() -> MCPToolset:
    """One connection to the shop's MCP server (stdio), shared by every agent."""
    return MCPToolset(StdioTransport(command=sys.executable, args=[str(ROOT / "mcp_server" / "server.py")],
                                     env={"DB_PATH": str(DB_PATH)}, cwd=str(ROOT)))


# ---------------------------------------------------------------------------- shared run state
@dataclass
class TicketState:
    ticket_id: int
    run_id: str
    agent_runs: int = 0
    tokens_used: int = 0
    cache: dict[tuple[str, str], str] = field(default_factory=dict)
    delegations: list[Delegation] = field(default_factory=list)


@dataclass
class TeamDeps:
    state: TicketState
    agent: str
    chain: tuple[str, ...]
    delegations_this_run: int = 0


class CampusCustomsTeam:
    def __init__(self) -> None:
        self.model = build_model()
        self.mcp = build_mcp()
        self.agents: dict[str, Agent] = {name: self._make_agent(name) for name in AGENT_NAMES}

    def _make_agent(self, name: str) -> Agent:
        allowed = TOOLS_BY_AGENT[name]
        toolset = self.mcp.filtered(lambda ctx, tool_def, allowed=allowed: tool_def.name in allowed)
        return Agent(
            self.model,
            name=name,
            deps_type=TeamDeps,
            output_type=TicketDecision if name == "boss" else AgentReport,
            instructions=(PROMPTS / f"{name}.md").read_text(encoding="utf-8"),
            toolsets=[toolset],
            tools=[self._ask_teammate_tool()],
            retries=2,
        )

    def _ask_teammate_tool(self):
        team = self

        async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, request: str) -> str:
            """Ask another agent on the team for help (full connectivity: any agent may ask any other).

            Args:
                teammate: boss, inventory, accounting, facilities or customer_service (not yourself).
                request: a specific, self-contained request: ticket id, SKU/size/qty, invoice or lease id,
                    and exactly what you need back.
            """
            return await team._delegate(ctx.deps, teammate, request)

        return ask_teammate

    # ------------------------------------------------------------------------ delegation with loop guards
    async def _delegate(self, deps: TeamDeps, teammate: str, request: str) -> str:
        st = deps.state
        chain = list(deps.chain)
        reason = None
        if teammate not in AGENT_NAMES:
            reason = f"'{teammate}' is not on the team."
        elif teammate == deps.agent:
            reason = "You cannot delegate to yourself; do the work with your own tools."
        elif teammate in deps.chain:
            reason = (f"{teammate} is already working on this request chain ({' -> '.join(chain)}). "
                      "Asking them again would create a loop; finish with what you have.")
        elif len(deps.chain) >= MAX_CHAIN_DEPTH:
            reason = f"Delegation depth limit ({MAX_CHAIN_DEPTH}) reached; answer with what you have."
        elif deps.delegations_this_run >= MAX_DELEGATIONS_PER_RUN:
            reason = f"You already asked teammates {MAX_DELEGATIONS_PER_RUN} times in this step; decide with what you have."
        elif st.agent_runs >= MAX_AGENT_RUNS_PER_TICKET:
            reason = f"The team has used its {MAX_AGENT_RUNS_PER_TICKET} agent runs for this ticket; wrap up."
        elif st.tokens_used >= MAX_TOKENS_PER_TICKET:
            reason = f"Token budget for this ticket ({MAX_TOKENS_PER_TICKET:,}) is used up; wrap up."
        if reason:
            st.delegations.append(Delegation(from_agent=deps.agent, to_agent=teammate if teammate in AGENT_NAMES else "boss",
                                             request=request, chain=chain, outcome="blocked_by_guard", reply=reason))
            audit.append({"run_id": st.run_id, "ticket_id": st.ticket_id, "agent": deps.agent, "event": "guard_block",
                          "chain": chain, "to_agent": teammate, "request": request, "reason": reason})
            return f"NOT DELEGATED: {reason}"

        key = (teammate, " ".join(request.lower().split()))
        if key in st.cache:
            audit.append({"run_id": st.run_id, "ticket_id": st.ticket_id, "agent": deps.agent, "event": "delegation_cached",
                          "chain": chain, "to_agent": teammate, "request": request})
            st.delegations.append(Delegation(from_agent=deps.agent, to_agent=teammate, request=request, chain=chain,
                                             outcome="cached", reply=st.cache[key]))
            return "(Same request was already answered.) " + st.cache[key]

        deps.delegations_this_run += 1
        audit.append({"run_id": st.run_id, "ticket_id": st.ticket_id, "agent": deps.agent, "event": "delegation_start",
                      "chain": chain, "to_agent": teammate, "request": request})
        child = TeamDeps(state=st, agent=teammate, chain=tuple(chain + [teammate]))
        try:
            output = await self.run_agent(teammate, request, child)
            reply = output.model_dump_json()
            outcome = "answered"
        except Exception as exc:  # report back instead of crashing the whole ticket
            reply, outcome = f"{teammate} could not finish: {type(exc).__name__}: {exc}", "error"
        st.cache[key] = reply
        st.delegations.append(Delegation(from_agent=deps.agent, to_agent=teammate, request=request, chain=chain,
                                         outcome=outcome, reply=reply))
        audit.append({"run_id": st.run_id, "ticket_id": st.ticket_id, "agent": deps.agent, "event": "delegation_end",
                      "chain": chain, "to_agent": teammate, "outcome": outcome, "reply": reply})
        return reply

    # ------------------------------------------------------------------------ one agent run, step by step
    async def run_agent(self, name: str, prompt: str, deps: TeamDeps):
        st = deps.state
        st.agent_runs += 1
        remaining = max(MAX_TOKENS_PER_TICKET - st.tokens_used, 1)
        limits = UsageLimits(request_limit=MAX_REQUESTS_PER_RUN, total_tokens_limit=min(MAX_TOKENS_PER_RUN, remaining))
        base = {"run_id": st.run_id, "ticket_id": st.ticket_id, "agent": name, "chain": list(deps.chain), "model": MODEL_NAME}
        audit.append({**base, "event": "agent_start", "prompt": prompt, "agent_run_number": st.agent_runs})
        step = 0
        async with self.agents[name].iter(prompt, deps=deps, usage_limits=limits) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    step += 1
                    audit.append({**base, "event": "model_request", "step": step, "parts": _request_parts(node.request)})
                elif Agent.is_call_tools_node(node):
                    audit.append({**base, "event": "model_response", "step": step,
                                  "parts": _response_parts(node.model_response)})
        usage = run.usage() if callable(run.usage) else run.usage
        st.tokens_used += usage.input_tokens + usage.output_tokens
        audit.append({**base, "event": "agent_end", "steps": step, "output": run.result.output.model_dump(),
                      "usage": {"requests": usage.requests, "input_tokens": usage.input_tokens,
                                "cached_tokens": usage.cache_read_tokens, "output_tokens": usage.output_tokens},
                      "ticket_tokens_so_far": st.tokens_used})
        return run.result.output

    async def work_ticket(self, ticket_id: int) -> dict:
        """The boss works one ticket end to end. Returns the decision plus the delegation record."""
        st = TicketState(ticket_id=ticket_id, run_id=uuid.uuid4().hex[:10])
        deps = TeamDeps(state=st, agent="boss", chain=("boss",))
        prompt = (f"Work ticket {ticket_id}. Read it with get_ticket, bring in the teammates it needs, and make the "
                  "final call. Remember: every payment waits for a human, and nothing is ever sent.")
        audit.append({"run_id": st.run_id, "ticket_id": ticket_id, "agent": "boss", "event": "ticket_start",
                      "db": str(DB_PATH.name), "model": MODEL_NAME})
        try:
            async with self.mcp:
                decision = await self.run_agent("boss", prompt, deps)
            result = {"ticket_id": ticket_id, "run_id": st.run_id, "decision": decision.model_dump(),
                      "delegations": [d.model_dump() for d in st.delegations],
                      "agent_runs": st.agent_runs, "tokens_used": st.tokens_used}
            audit.append({"run_id": st.run_id, "ticket_id": ticket_id, "agent": "boss", "event": "ticket_end",
                          "decision": decision.model_dump(), "agent_runs": st.agent_runs, "tokens_used": st.tokens_used})
            return result
        except Exception as exc:
            audit.append({"run_id": st.run_id, "ticket_id": ticket_id, "agent": "boss", "event": "ticket_error",
                          "error": f"{type(exc).__name__}: {exc}", "agent_runs": st.agent_runs, "tokens_used": st.tokens_used})
            raise


def _request_parts(req: ModelRequest) -> list[dict]:
    out = []
    for p in req.parts:
        if p.part_kind == "user-prompt":
            out.append({"kind": "prompt", "text": str(p.content)})
        elif p.part_kind == "tool-return":
            out.append({"kind": "tool_result", "tool": p.tool_name, "content": p.content if isinstance(p.content, str) else __import__("json").dumps(p.content, default=str)})
        elif p.part_kind == "retry-prompt":
            out.append({"kind": "retry", "tool": p.tool_name, "text": p.model_response()})
    return out


def _response_parts(resp: ModelResponse) -> list[dict]:
    out = []
    for p in resp.parts:
        if p.part_kind == "tool-call":
            out.append({"kind": "tool_call", "tool": p.tool_name, "args": p.args_as_dict()})
        elif p.part_kind == "text" and p.content.strip():
            out.append({"kind": "text", "text": p.content})
    return out
