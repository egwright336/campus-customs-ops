/** An engraved-style shield with a serif Y, in the spirit of old Yale seals. */
export default function Crest({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size * 1.15} viewBox="0 0 52 60" aria-hidden="true" className="crest">
      <path d="M4 3h44v30c0 11-10 19-22 23C14 52 4 44 4 33z" fill="var(--midnight)" stroke="var(--brass)" strokeWidth="2" />
      <path d="M8 7h36v26c0 9-8 15.5-18 19C16 48.5 8 42 8 33z" fill="none" stroke="var(--brass)" strokeWidth="0.75" opacity="0.7" />
      <text x="26" y="37" textAnchor="middle" fontFamily="'IM Fell English SC', Georgia, serif" fontSize="26" fill="var(--parchment)">
        Y
      </text>
    </svg>
  )
}
