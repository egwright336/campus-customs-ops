import { useEffect, useRef } from 'react'
import { AGENTS, prettyTool } from '../agents'
import type { AgentEvent, AgentName } from '../types'

const LONG = 320

function Said({ text }: { text: string }) {
  if (text.length <= LONG) return <p className="said">{text}</p>
  return (
    <details className="said">
      <summary>{text.slice(0, LONG)}…</summary>
      <p>{text}</p>
    </details>
  )
}

function name(a: AgentName | null) {
  return a ? AGENTS[a]?.title ?? a : 'The desk'
}

/** One entry in the telling, or null for steps that only add noise (bare model requests). */
function Entry({ e }: { e: AgentEvent }) {
  const time = e.ts?.slice(11, 19)
  const voice = e.agent ? AGENTS[e.agent]?.voice : ''
  let head: string
  let body: React.ReactNode = null
  switch (e.event) {
    case 'ticket_start':
      head = 'The ticket is opened'
      break
    case 'agent_start':
      // (the request itself was already shown under the asker's "turns to" entry)
      head = e.chain && e.chain.length > 1 ? `is asked in by ${name(e.chain[e.chain.length - 2])}` : 'takes up the ticket'
      break
    case 'model_response': {
      const tools = e.tools_called.filter((t) => t.tool !== 'ask_teammate')
      if (!tools.length && !e.message) return null
      head = tools.length ? 'goes to the books' : 'says'
      body = (
        <>
          {e.message && <Said text={e.message} />}
          {tools.length > 0 && (
            <ul className="tools">
              {tools.map((t, i) => (
                <li key={i} title={JSON.stringify(t.args)}>
                  {prettyTool(t.tool)}
                </li>
              ))}
            </ul>
          )}
        </>
      )
      break
    }
    case 'model_request':
      if (!e.tool_results.length || e.tool_results.every((r) => r.tool === 'ask_teammate')) return null
      head = 'reads what the books say'
      body = (
        <ul className="slips">
          {e.tool_results
            .filter((r) => r.tool !== 'ask_teammate')
            .map((r, i) => (
              <li key={i}>
                <span className="slip-tool">{prettyTool(r.tool)}</span>
                <code>{r.content.slice(0, 180)}</code>
              </li>
            ))}
        </ul>
      )
      break
    case 'delegation_start':
      head = `turns to ${name(e.to_agent)}`
      body = e.message ? <Said text={e.message} /> : null
      break
    case 'delegation_end':
      return null
    case 'delegation_cached':
      head = `already has ${name(e.to_agent)}’s answer`
      break
    case 'guard_block':
      head = 'is stopped by a house rule'
      body = <p className="said warn">{e.message}</p>
      break
    case 'agent_end':
      head = 'has said its piece'
      body = e.message ? <Said text={e.message} /> : null
      break
    case 'ticket_end':
      head = 'closes the ticket'
      body = e.message ? <Said text={e.message} /> : null
      break
    case 'ticket_error':
      head = 'The run broke off'
      body = <p className="said warn">{e.message}</p>
      break
    default:
      return null
  }
  const desk = e.event === 'ticket_start' || e.event === 'ticket_error'
  return (
    <li className={`entry ${desk ? 'entry-desk' : voice} ev-${e.event}`}>
      <div className="entry-head">
        {!desk && <span className="entry-name">{name(e.agent)}</span>}
        <span className="entry-what">{head}</span>
        <time>{time}</time>
      </div>
      {body}
    </li>
  )
}

/** The running account of the ticket, voice by voice, like chapters headed with the speaker's name. */
export default function Telling({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (running) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [events.length, running])
  return (
    <section className="telling">
      <h3>
        The telling {running && <span className="live-tag">live</span>}
      </h3>
      {events.length === 0 ? (
        <p className="muted">{running ? 'The boss is reading the ticket…' : 'No one has worked this ticket yet.'}</p>
      ) : (
        <ol className="entries">
          {events.map((e) => (
            <Entry key={e.index} e={e} />
          ))}
          {running && (
            <li className="entry entry-desk waiting">
              <span className="quill" /> still talking…
            </li>
          )}
        </ol>
      )}
      <div ref={end} />
    </section>
  )
}
