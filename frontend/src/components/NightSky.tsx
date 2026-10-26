/** Decorative October sky for dark panels: a crescent moon, drifting fog, and a few bats. */
export default function NightSky() {
  return (
    <div className="night-sky" aria-hidden="true">
      <svg className="moon" viewBox="0 0 100 100">
        <defs>
          <mask id="crescent">
            <rect width="100" height="100" fill="white" />
            <circle cx="64" cy="40" r="38" fill="black" />
          </mask>
        </defs>
        <circle cx="50" cy="50" r="40" fill="var(--parchment)" mask="url(#crescent)" />
      </svg>
      {[0, 1, 2].map((i) => (
        <svg key={i} className={`bat bat-${i}`} viewBox="0 0 64 24">
          <path d="M32 8c-2-4-6-4-7 0-5-6-14-7-25-2 8 1 12 5 13 10 4-3 9-3 12 1 2-2 4-3 7-3s5 1 7 3c3-4 8-4 12-1 1-5 5-9 13-10-11-5-20-4-25 2-1-4-5-4-7 0z" />
        </svg>
      ))}
      <div className="fog fog-1" />
      <div className="fog fog-2" />
    </div>
  )
}
