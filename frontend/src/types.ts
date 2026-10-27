export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  status: string
  is_open: boolean
  pending_approvals: number
  drafts: number
}

export interface Run {
  run_key: string
  ticket_id: number
  status: 'queued' | 'running' | 'done' | 'error'
  model: string
  started_at: string
  finished_at?: string
  events_from: number
  error?: string
}

export interface AgentEvent {
  index: number
  ts: string
  run_id: string
  ticket_id: number
  agent: AgentName | null
  event: string
  to_agent: AgentName | null
  chain: AgentName[] | null
  message: string | null
  tools_called: { tool: string; args: unknown }[]
  tool_results: { tool: string; content: string }[]
  usage: Record<string, number> | null
}

export interface ApprovalRequest {
  id: number
  ticket_id: number
  kind: 'invoice_payment' | 'rent_payment' | 'purchase_order' | 'price_override'
  ref_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  unit_price: number | null
  amount: number
  payee: string | null
  reason: string | null
  requested_by: AgentName
  status: 'pending' | 'approved' | 'rejected' | 'executed'
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  executed_at: string | null
  result: string | null
}

export interface Draft {
  id: number
  ticket_id: number
  kind: string
  recipient: string
  subject: string | null
  body: string
  created_by: AgentName
  created_at: string
  status: string
}

export interface Board {
  approval_requests: ApprovalRequest[]
  drafts: Draft[]
}

export interface Cash {
  checking_balance: number
  accounts: Record<string, number>
  cash_balance: number
  committed_to_open_requests: number
  available_to_commit: number
  shop_today: string
}

export interface AgentSummary {
  agent: AgentName
  tools: string[]
  asked: AgentName[]
  asked_by: AgentName[]
  summary: string | null
  status: string | null
  runs: number
  tokens: number
}

export interface TicketSummary {
  ticket_id: number
  has_run: boolean
  run_id?: string
  finished_at?: string
  decision?: { decision: string; final_status: string; rationale: string; risks_or_followups: string[] }
  agent_runs?: number
  tokens_used?: number
  agents?: AgentSummary[]
}

export interface RunInfo {
  run_id: string
  started: string | null
  ended: string
  agent_runs: number | null
  tokens_used: number | null
  decision: string | null
}
