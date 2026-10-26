import { useState } from 'react'
import { api } from '../api'
import { AGENTS, money, REQUEST_KIND } from '../agents'
import type { ApprovalRequest } from '../types'

const MOVES_CASH = new Set(['invoice_payment', 'rent_payment', 'purchase_order'])

/** Requests the agents prepared. Only a named person can sign; signing a payment is what lowers the balance. */
export default function Signatures({
  requests,
  scope,
  onDecided,
}: {
  requests: ApprovalRequest[]
  scope: number | null
  onDecided: () => Promise<void>
}) {
  const [approver, setApprover] = useState(() => localStorage.getItem('approver') ?? '')
  const [busy, setBusy] = useState<number | null>(null)
  const [msg, setMsg] = useState<{ id: number; text: string; ok: boolean } | null>(null)

  const pending = requests.filter((r) => r.status === 'pending')
  const settled = requests.filter((r) => r.status !== 'pending')

  const decide = async (r: ApprovalRequest, approve: boolean) => {
    const who = approver.trim()
    if (!who) {
      setMsg({ id: r.id, text: 'Write your name on the line first.', ok: false })
      return
    }
    localStorage.setItem('approver', who)
    setBusy(r.id)
    setMsg(null)
    try {
      if (approve) {
        const res = await api.approve(r.id, who)
        setMsg({
          id: r.id,
          ok: res.execution.ok,
          text: res.execution.ok
            ? MOVES_CASH.has(r.kind)
              ? `Signed and paid. Checking now ${money(res.cash_balance)}.`
              : 'Signed. The new price is on the books.'
            : `Signed, but not carried out: ${res.execution.error}`,
        })
      } else {
        await api.reject(r.id, who)
        setMsg({ id: r.id, ok: true, text: 'Turned down. Nothing moved.' })
      }
      await onDecided()
    } catch (e) {
      setMsg({ id: r.id, ok: false, text: (e as Error).message })
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="signatures">
      <h3>Awaiting a signature</h3>
      <label className={`sign-line ${approver.trim() ? '' : 'unsigned'}`}>
        <span>Signed by</span>
        <input
          value={approver}
          onChange={(e) => setApprover(e.target.value)}
          placeholder="your name"
          autoComplete="name"
        />
      </label>
      {pending.length === 0 && (
        <p className="muted">{scope == null ? 'Nothing waits on you tonight.' : 'Nothing on this ticket waits on you.'}</p>
      )}
      <ul className="requests">
        {pending.map((r) => (
          <li key={r.id} className={`request kind-${r.kind}`}>
            <div className="request-top">
              <span className="request-kind">{REQUEST_KIND[r.kind] ?? r.kind}</span>
              <span className="request-amount">{money(r.amount)}</span>
            </div>
            <p className="request-payee">
              {r.payee ?? '—'}
              {r.qty ? ` · ${r.qty} × ${r.sku}${r.size ? ` ${r.size}` : ''}` : ''}
              {r.kind === 'price_override' && r.unit_price != null ? ` at ${money(r.unit_price)} each` : ''}
            </p>
            {r.reason && <p className="request-reason">{r.reason}</p>}
            <p className="request-by">
              Prepared by {AGENTS[r.requested_by]?.title ?? r.requested_by} for No. {r.ticket_id}
            </p>
            <div className="request-actions">
              <button className="btn-lantern" disabled={busy === r.id || !approver.trim()} onClick={() => decide(r, true)}>
                {!approver.trim() ? 'Sign your name above' : MOVES_CASH.has(r.kind) ? 'Sign & pay' : 'Sign'}
              </button>
              <button className="btn-ghost" disabled={busy === r.id || !approver.trim()} onClick={() => decide(r, false)}>
                Turn down
              </button>
            </div>
            {msg?.id === r.id && <p className={msg.ok ? 'ok' : 'error'}>{msg.text}</p>}
          </li>
        ))}
      </ul>
      {msg && !pending.some((r) => r.id === msg.id) && <p className={msg.ok ? 'ok' : 'error'}>{msg.text}</p>}
      {settled.length > 0 && (
        <details className="settled-list" open={pending.length === 0}>
          <summary>Already decided ({settled.length})</summary>
          <ul>
            {settled.map((r) => (
              <li key={r.id}>
                <span className={`pill pill-${r.status}`}>{r.status}</span> {REQUEST_KIND[r.kind] ?? r.kind},{' '}
                {money(r.amount)}
                {r.decided_by && <em> · {r.decided_by}</em>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
