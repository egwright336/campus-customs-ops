import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, API_URL } from './api'
import { AGENT_ORDER, AGENTS, TICKET_KIND } from './agents'
import type { AgentEvent, Board, Cash, Run, RunInfo, Ticket, TicketSummary } from './types'
import Crest from './components/Crest'
import NightSky from './components/NightSky'
import Ledger from './components/Ledger'
import Docket from './components/Docket'
import Porch from './components/Porch'
import Telling from './components/Telling'
import Afterword from './components/Afterword'
import Signatures from './components/Signatures'
import Letters from './components/Letters'

const POLL_MS = 1200

/** The events of one run (default: the most recent); the audit trail keeps every run, forever. */
function pickRun(events: AgentEvent[], runId?: string | null): AgentEvent[] {
  const id = runId ?? [...events].reverse().find((e) => e.event === 'ticket_start')?.run_id
  return id ? events.filter((e) => e.run_id === id) : events
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [today, setToday] = useState<string>('')
  const [cash, setCash] = useState<Cash | null>(null)
  const [board, setBoard] = useState<Board>({ approval_requests: [], drafts: [] })
  const [selected, setSelected] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const [runs, setRuns] = useState<RunInfo[]>([])
  const [viewRun, setViewRun] = useState<string | null>(null)
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [offline, setOffline] = useState(false)
  const since = useRef(0)

  const running = run != null && (run.status === 'queued' || run.status === 'running')

  const refreshDesk = useCallback(async () => {
    try {
      const [t, b, c] = await Promise.all([api.tickets(), api.board(), api.cash()])
      setTickets(t.tickets)
      setToday(t.shop_today ?? c.shop_today)
      setBoard(b)
      setCash(c)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  useEffect(() => {
    refreshDesk()
  }, [refreshDesk])

  // Picking a ticket shows one of its runs (the most recent unless runId is given) and that run's summary.
  const openTicket = useCallback(async (id: number, runId?: string | null) => {
    setSelected(id)
    setError(null)
    try {
      const [ev, rs] = await Promise.all([api.events(0, id), api.runs(id)])
      const chosen = runId ?? rs.runs.at(-1)?.run_id ?? null
      setRuns(rs.runs)
      setViewRun(chosen)
      setEvents(pickRun(ev.events, chosen))
      setSummary(await api.summary(id, chosen ?? undefined))
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  // Deep link: /?ticket=101 opens that ticket; add &run=<run_id> for an earlier run (used for screenshots).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
    const id = Number(q.get('ticket'))
    if (id) openTicket(id, q.get('run'))
  }, [openTicket])

  const startRun = async () => {
    if (selected == null) return
    if (
      ticket?.status === 'resolved' &&
      !window.confirm(`Ticket ${selected} is already settled. Send the whole team in again? (This is a new run.)`)
    )
      return
    setError(null)
    try {
      const r = await api.run(selected)
      since.current = r.events_from
      setEvents([])
      setSummary(null)
      setViewRun(null)
      setRun(r)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // While the team works: pull new audit events and the run status until the run ends.
  useEffect(() => {
    if (!run || !running) return
    let stop = false
    const tick = async () => {
      try {
        const [ev, st] = await Promise.all([api.events(since.current, run.ticket_id), api.runStatus(run.run_key)])
        if (stop) return
        since.current = ev.next_since
        if (ev.events.length) setEvents((prev) => [...prev, ...ev.events])
        if (st.status !== run.status) setRun(st)
        if (st.status === 'done' || st.status === 'error') {
          if (st.error) setError(st.error)
          const [last, sm] = await Promise.all([api.events(since.current, run.ticket_id), api.summary(run.ticket_id)])
          if (last.events.length) setEvents((prev) => [...prev, ...last.events])
          setSummary(sm)
          api.runs(run.ticket_id).then((rs) => {
            setRuns(rs.runs)
            setViewRun(rs.runs.at(-1)?.run_id ?? null)
          })
          refreshDesk()
        }
      } catch {
        /* the next tick will try again */
      }
    }
    const id = window.setInterval(tick, POLL_MS)
    tick()
    return () => {
      stop = true
      window.clearInterval(id)
    }
  }, [run, running, refreshDesk])

  const reset = async () => {
    if (!window.confirm('Reset the working database from the original? Every payment and request on the board is erased.'))
      return
    try {
      await api.reset()
      setRun(null)
      setEvents([])
      setSummary(null)
      await refreshDesk()
      if (selected != null) openTicket(selected)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const ticket = tickets.find((t) => t.id === selected) ?? null
  const runForThis = run && run.ticket_id === selected ? run : null
  const ticketBoard = useMemo(
    () => ({
      approval_requests: board.approval_requests.filter((r) => selected == null || r.ticket_id === selected),
      drafts: board.drafts.filter((d) => selected == null || d.ticket_id === selected),
    }),
    [board, selected],
  )

  return (
    <div className="desk">
      <header className="masthead">
        <NightSky />
        <div className="masthead-inner">
          <div className="brand">
            <Crest size={46} />
            <div>
              <p className="kicker">Campus Customs · after hours</p>
              <h1>The Night Desk</h1>
              <p className="subtitle">Five voices work each ticket. Nothing leaves the shop without a human hand.</p>
            </div>
          </div>
          <div className="masthead-right">
            <div className="almanac">
              <span className="almanac-label">The shop’s today</span>
              <span className="almanac-date">{today ? formatDay(today) : '—'}</span>
            </div>
            <Ledger cash={cash} />
          </div>
        </div>
      </header>

      {offline && (
        <div className="banner" role="alert">
          The desk can’t reach the backend at <code>{API_URL}</code>. Start it from <code>backend/</code> with{' '}
          <code>uvicorn main:app --port 9000</code>, then refresh.
        </div>
      )}

      <main className="grid">
        <aside className="col col-left">
          <Docket tickets={tickets} selected={selected} running={run} onPick={openTicket} />
          <div className="house-rules">
            <h3>House rules</h3>
            <ul>
              <li>Agents only <em>ask</em>. A person signs every payment.</li>
              <li>Letters are drafted, never sent.</li>
              <li>No account goes below zero.</li>
            </ul>
            <button className="btn-ghost" onClick={reset} disabled={running}>
              Reset the books
            </button>
          </div>
        </aside>

        <section className="col col-center">
          {ticket ? (
            <>
              <div className="case-head">
                <div>
                  <p className="kicker">
                    No. {ticket.id} · {TICKET_KIND[ticket.type] ?? ticket.type}
                  </p>
                  <h2>{ticket.subject}</h2>
                  <p className="case-meta">
                    from <strong>{ticket.requester}</strong>
                    {ticket.sku && (
                      <>
                        {' '}
                        · {ticket.qty} × {ticket.sku}
                        {ticket.size ? ` (${ticket.size})` : ''}
                      </>
                    )}
                  </p>
                </div>
                <div className="case-actions">
                  {ticket.status === 'resolved' && <span className="stamp">Settled</span>}
                  <button
                    className={ticket.status === 'resolved' ? 'btn-ghost' : 'btn-lantern'}
                    onClick={startRun}
                    disabled={running || offline}
                  >
                    {running
                      ? runForThis
                        ? 'The team is at work…'
                        : `Busy with No. ${run?.ticket_id}`
                      : events.length
                        ? 'Send the team in again'
                        : 'Send the team in'}
                  </button>
                </div>
              </div>
              {runs.length > 1 && !(running && runForThis) && (
                <nav className="run-picker" aria-label="Runs of this ticket">
                  <span className="run-picker-label">Runs of this ticket</span>
                  {runs.map((r, i) => (
                    <button
                      key={r.run_id}
                      className={r.run_id === viewRun ? 'on' : ''}
                      aria-pressed={r.run_id === viewRun}
                      onClick={() => openTicket(ticket.id, r.run_id)}
                      title={r.decision ?? ''}
                    >
                      Run {i + 1} · {r.started?.slice(11, 16)} · {r.agent_runs} agents ·{' '}
                      {Math.round((r.tokens_used ?? 0) / 1000)}k tokens{i === runs.length - 1 ? ' · latest' : ''}
                    </button>
                  ))}
                </nav>
              )}
              {ticket.pending_approvals > 0 && !running && (
                <p className="await-note">
                  {ticket.pending_approvals} request{ticket.pending_approvals > 1 ? 's' : ''} on this ticket await your
                  signature — see the right-hand column.
                </p>
              )}
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <Porch events={events} running={running && runForThis != null} />
              <Telling events={events} running={running && runForThis != null} />
              {summary?.has_run && !(running && runForThis) && <Afterword summary={summary} />}
            </>
          ) : (
            <div className="empty-case">
              <h2>Pick a ticket from the docket.</h2>
              <p>
                The boss reads it first and calls in only the specialists it needs. You’ll hear each voice as it works,
                in its own hand.
              </p>
              <div className="cast">
                {AGENT_ORDER.map((a) => (
                  <div key={a} className={`cast-member ${AGENTS[a].voice}`}>
                    <span className="seal">{AGENTS[a].seal}</span>
                    <span className="cast-name">{AGENTS[a].title}</span>
                    <span className="cast-epithet">{AGENTS[a].epithet}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className="col col-right">
          <Signatures
            requests={ticketBoard.approval_requests}
            scope={selected}
            onDecided={async () => {
              await refreshDesk()
            }}
          />
          <Letters drafts={ticketBoard.drafts} />
        </aside>
      </main>

      <footer className="foot">
        Every agent runs on <code>gpt-6-luna</code> through Portkey · backend <code>{API_URL}</code> · every step is
        written to <code>output/audit_trail.json</code>
      </footer>
    </div>
  )
}

function formatDay(iso: string) {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}
