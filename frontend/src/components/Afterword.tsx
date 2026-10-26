import { AGENTS, prettyTool } from '../agents'
import type { TicketSummary } from '../types'

/** After the run: one short card per agent that took part, plus the boss's ruling. */
export default function Afterword({ summary }: { summary: TicketSummary }) {
  const d = summary.decision
  return (
    <section className="afterword">
      <h3>What each one did</h3>
      {d && (
        <div className="ruling">
          <span className="ruling-label">The boss’s ruling</span>
          <p>{d.decision}</p>
          <span className="ruling-meta">
            {summary.agent_runs} agent runs · {(summary.tokens_used ?? 0).toLocaleString()} tokens
          </span>
        </div>
      )}
      <div className="afterword-cards">
        {summary.agents?.map((a) => (
          <article key={a.agent} className={`deed ${AGENTS[a.agent].voice}`}>
            <header>
              <span className="seal">{AGENTS[a.agent].seal}</span>
              <h4>{AGENTS[a.agent].title}</h4>
              {a.status && <span className="pill">{a.status.replace(/_/g, ' ')}</span>}
            </header>
            {a.summary && <p>{a.summary}</p>}
            <dl>
              {a.asked_by.length > 0 && (
                <>
                  <dt>Called by</dt>
                  <dd>{[...new Set(a.asked_by)].map((x) => AGENTS[x].title).join(', ')}</dd>
                </>
              )}
              {a.asked.length > 0 && (
                <>
                  <dt>Asked</dt>
                  <dd>{[...new Set(a.asked)].map((x) => AGENTS[x]?.title ?? x).join(', ')}</dd>
                </>
              )}
              <dt>Tools</dt>
              <dd>{a.tools.length ? a.tools.map(prettyTool).join(', ') : 'none'}</dd>
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}
