import { AGENT_ORDER, AGENTS, prettyTool } from '../agents'
import type { AgentEvent, AgentName } from '../types'

type State = 'idle' | 'thinking' | 'tool' | 'asking' | 'done' | 'blocked'
interface Live {
  state: State
  line: string
  status?: string
}

/** Walk the run's events and work out what each agent is doing right now. */
export function liveStates(events: AgentEvent[]): Record<AgentName, Live> {
  const live = Object.fromEntries(AGENT_ORDER.map((a) => [a, { state: 'idle', line: 'Not called.' }])) as Record<
    AgentName,
    Live
  >
  for (const e of events) {
    const a = e.agent
    if (!a || !(a in live)) continue
    switch (e.event) {
      case 'agent_start':
        live[a] = {
          state: 'thinking',
          line: e.chain && e.chain.length > 1 ? `Asked by ${AGENTS[e.chain[e.chain.length - 2]].title}.` : 'Reading the ticket.',
        }
        break
      case 'model_response': {
        const tools = e.tools_called.filter((t) => t.tool !== 'ask_teammate').map((t) => prettyTool(t.tool))
        if (tools.length) live[a] = { state: 'tool', line: `Checking: ${tools.join(', ')}` }
        else if (e.message) live[a] = { state: 'thinking', line: e.message }
        break
      }
      case 'delegation_start':
        live[a] = { state: 'asking', line: `Asking ${AGENTS[e.to_agent as AgentName]?.title ?? e.to_agent}…` }
        break
      case 'delegation_end':
      case 'delegation_cached':
        live[a] = { state: 'thinking', line: `Heard back from ${AGENTS[e.to_agent as AgentName]?.title ?? e.to_agent}.` }
        break
      case 'guard_block':
        live[a] = { state: 'blocked', line: `A guard stopped it: ${e.message ?? ''}` }
        break
      case 'agent_end':
        live[a] = { state: 'done', line: e.message ?? 'Finished.' }
        break
    }
  }
  return live
}

const STATE_WORD: Record<State, string> = {
  idle: 'quiet',
  thinking: 'thinking',
  tool: 'in the books',
  asking: 'asking a teammate',
  done: 'said its piece',
  blocked: 'stopped by a guard',
}

/** Five chairs on the porch: one card per agent, lit while it speaks. */
export default function Porch({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const live = liveStates(events)
  const speaker = running ? [...events].reverse().find((e) => e.agent && e.event !== 'ticket_start')?.agent : null
  return (
    <div className="porch" aria-label="The agents">
      {AGENT_ORDER.map((a) => {
        const s = live[a]
        const lit = running && speaker === a && s.state !== 'done'
        return (
          <article key={a} className={`chair ${AGENTS[a].voice} state-${s.state} ${lit ? 'lit' : ''}`}>
            <header>
              <span className="seal">{AGENTS[a].seal}</span>
              <div>
                <h4>{AGENTS[a].title}</h4>
                <span className="chair-state">
                  {lit && <span className="dot" />}
                  {STATE_WORD[s.state]}
                </span>
              </div>
            </header>
            <p className="chair-line">{s.line}</p>
          </article>
        )
      })}
    </div>
  )
}
