import { TICKET_KIND } from '../agents'
import type { Run, Ticket } from '../types'

/** The three tickets, pinned like notices on a courthouse board. Settled ones get a red stamp. */
export default function Docket({
  tickets,
  selected,
  running,
  onPick,
}: {
  tickets: Ticket[]
  selected: number | null
  running: Run | null
  onPick: (id: number) => void
}) {
  const busy = running && (running.status === 'queued' || running.status === 'running') ? running.ticket_id : null
  return (
    <div className="docket">
      <h3>The docket</h3>
      {tickets.length === 0 && <p className="muted">No tickets yet.</p>}
      <ul>
        {tickets.map((t) => (
          <li key={t.id}>
            <button
              className={`notice ${selected === t.id ? 'picked' : ''} ${t.status === 'resolved' ? 'settled' : ''}`}
              onClick={() => onPick(t.id)}
              aria-pressed={selected === t.id}
            >
              <span className="notice-no">No. {t.id}</span>
              <span className="notice-kind">{TICKET_KIND[t.type] ?? t.type}</span>
              <span className="notice-subject">{t.subject}</span>
              <span className="notice-from">{t.requester}</span>
              <span className="notice-foot">
                {busy === t.id ? (
                  <span className="pill pill-live">
                    <span className="dot" /> team at work
                  </span>
                ) : t.status === 'resolved' ? (
                  <span className="pill pill-settled">resolved</span>
                ) : (
                  <span className="pill">{t.status.replace(/_/g, ' ')}</span>
                )}
                {t.pending_approvals > 0 && <span className="pill pill-sign">{t.pending_approvals} to sign</span>}
                {t.drafts > 0 && (
                  <span className="pill">
                    {t.drafts} letter{t.drafts > 1 ? 's' : ''}
                  </span>
                )}
              </span>
              {t.status === 'resolved' && (
                <span className="notice-stamp" aria-hidden="true">
                  Settled
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
