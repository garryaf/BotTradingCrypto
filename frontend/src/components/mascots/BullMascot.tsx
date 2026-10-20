export function BullMascot({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 280 180" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* back legs */}
      <path d="M92 132 L78 168 L92 170 L106 136 Z" fill="currentColor" opacity={0.8} />
      <path d="M118 134 L110 170 L124 172 L136 138 Z" fill="currentColor" opacity={0.8} />
      {/* hooves */}
      <ellipse cx="83" cy="169" rx="8" ry="4" fill="black" opacity={0.45} />
      <ellipse cx="116" cy="171" rx="8" ry="4" fill="black" opacity={0.45} />

      {/* front legs, reaching forward in a gallop */}
      <path d="M160 136 L178 170 L164 174 L148 140 Z" fill="currentColor" />
      <path d="M180 132 L204 160 L192 168 L172 136 Z" fill="currentColor" />
      <ellipse cx="170" cy="173" rx="8" ry="4" fill="black" opacity={0.45} />
      <ellipse cx="196" cy="166" rx="8" ry="4" fill="black" opacity={0.45} />

      {/* tail */}
      <path d="M82 98 C62 94 50 80 56 62" stroke="currentColor" strokeWidth={7} strokeLinecap="round" fill="none" opacity={0.75} />
      <ellipse cx="55" cy="58" rx="7" ry="9" fill="currentColor" opacity={0.75} />

      {/* muscular barrel body */}
      <path
        d="M58 112 C52 82 78 58 122 56 C150 55 170 64 180 82 C186 93 183 104 172 108 C170 118 164 126 150 128 L84 130 C66 130 60 122 58 112 Z"
        fill="currentColor"
      />

      {/* neck + lowered head */}
      <path
        d="M168 78 C182 68 202 68 214 80 C224 90 224 106 212 116 L196 122 C182 118 172 100 168 78 Z"
        fill="currentColor"
      />

      {/* snout */}
      <path d="M205 104 C216 100 230 103 234 114 C237 123 230 130 218 129 C208 128 202 116 205 104 Z" fill="currentColor" opacity={0.78} />
      <ellipse cx="216" cy="115" rx="2.3" ry="3" fill="black" opacity={0.55} />
      <ellipse cx="226" cy="117" rx="2.3" ry="3" fill="black" opacity={0.55} />

      {/* ear */}
      <path d="M186 76 L176 64 L194 70 Z" fill="currentColor" opacity={0.85} />

      {/* symmetric curved horns */}
      <path d="M190 74 C178 58 176 38 188 22" stroke="currentColor" strokeWidth={10} strokeLinecap="round" fill="none" />
      <path d="M204 70 C212 52 228 40 246 40" stroke="currentColor" strokeWidth={10} strokeLinecap="round" fill="none" />

      {/* angry brow + glowing eye */}
      <path d="M188 86 L204 90" stroke="black" strokeWidth={3.5} strokeLinecap="round" opacity={0.5} />
      <ellipse cx="196" cy="94" rx="4.5" ry="3.2" fill="white" />
      <ellipse cx="197" cy="94" rx="2.3" ry="2.7" fill="black" />

      {/* nostril steam */}
      <path d="M236 110 C242 106 248 106 252 100" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" opacity={0.35} />
      <path d="M238 120 C244 118 250 119 254 114" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" opacity={0.35} />
    </svg>
  );
}
