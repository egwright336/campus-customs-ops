import { useEffect, useRef, useState } from 'react'
import { money } from '../agents'
import type { Cash } from '../types'

/** The checking balance, set in brass. When it drops, the number counts down and the loss is inked beside it. */
export default function Ledger({ cash }: { cash: Cash | null }) {
  const target = cash?.checking_balance ?? null
  const [shown, setShown] = useState<number | null>(target)
  const [loss, setLoss] = useState<number | null>(null)
  const prev = useRef<number | null>(target)

  useEffect(() => {
    if (target == null) return
    const from = prev.current
    prev.current = target
    if (from == null || from === target) {
      setShown(target)
      return
    }
    if (target < from) setLoss(from - target)
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      setShown(target)
      return
    }
    const start = performance.now()
    const dur = 1400
    let raf = 0
    const step = (now: number) => {
      const k = Math.min(1, (now - start) / dur)
      const eased = 1 - Math.pow(1 - k, 3)
      setShown(from + (target - from) * eased)
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target])

  useEffect(() => {
    if (loss == null) return
    const id = window.setTimeout(() => setLoss(null), 6000)
    return () => window.clearTimeout(id)
  }, [loss])

  return (
    <div className="ledger" aria-live="polite">
      <span className="ledger-label">Checking</span>
      <span className={`ledger-amount ${loss ? 'dropping' : ''}`}>{money(shown)}</span>
      {loss != null && <span className="ledger-loss">−{money(loss)}</span>}
      {cash && cash.committed_to_open_requests > 0 && (
        <span className="ledger-note">
          {money(cash.committed_to_open_requests)} promised to requests awaiting a signature
        </span>
      )}
    </div>
  )
}
