import type { AgentEvent, Board, Cash, Run, Ticket, TicketSummary } from './types'

/** The FastAPI backend (backend/main.py). Override with VITE_API_URL if it moves. */
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  tickets: () => call<{ tickets: Ticket[]; shop_today: string }>('/api/tickets'),
  run: (ticketId: number) => call<Run>(`/api/tickets/${ticketId}/run`, { method: 'POST' }),
  runStatus: (runKey: string) => call<Run>(`/api/runs/${runKey}`),
  events: (since: number, ticketId: number) =>
    call<{ events: AgentEvent[]; next_since: number }>(`/api/events?since=${since}&ticket_id=${ticketId}&limit=500`),
  summary: (ticketId: number) => call<TicketSummary>(`/api/tickets/${ticketId}/summary`),
  board: () => call<Board>('/api/board'),
  cash: () => call<Cash>('/api/cash'),
  approve: (id: number, approver: string, note = '') =>
    call<{ cash_balance: number; execution: { ok: boolean; error?: string } }>(`/api/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approver, note }),
    }),
  reject: (id: number, approver: string, note = '') =>
    call(`/api/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify({ approver, note }) }),
  reset: () => call<{ reset: boolean }>('/api/reset', { method: 'POST' }),
  health: () => call<{ ok: boolean; model: string; database: string }>('/api/health'),
}
