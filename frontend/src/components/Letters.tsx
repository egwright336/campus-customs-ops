import { AGENTS } from '../agents'
import type { Draft } from '../types'

/** Drafts the team wrote. They stay here, unsent: the shop never emails customers or calls vendors on its own. */
export default function Letters({ drafts }: { drafts: Draft[] }) {
  return (
    <section className="letters">
      <h3>Unsent letters</h3>
      {drafts.length === 0 && <p className="muted">No letters drafted.</p>}
      {drafts.map((d) => (
        <details key={d.id} className="letter">
          <summary>
            <span className="letter-to">To {d.recipient}</span>
            <span className="letter-subject">{d.subject ?? d.kind}</span>
          </summary>
          <p className="letter-body">{d.body}</p>
          <p className="letter-by">
            drafted by {AGENTS[d.created_by]?.title ?? d.created_by} · {d.status}, not sent
          </p>
        </details>
      ))}
    </section>
  )
}
