/** Charging bull, bold-outline mascot style (ref: classic blue bull-vs-bear market icon). */
export function BullMascot({ className }: { className?: string }) {
  const outline = { stroke: "black", strokeWidth: 4, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
  return (
    <svg viewBox="0 0 220 220" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* front legs — sturdy columns tapering to split (cloven) hooves */}
      <path d="M58 168 C54 182 54 196 60 208 L92 208 C98 196 98 182 94 168 Z" fill="currentColor" {...outline} />
      <path d="M146 168 C142 182 142 196 148 208 L180 208 C186 196 186 182 182 168 Z" fill="currentColor" {...outline} />
      <path d="M56 202 L96 202 L94 214 C90 218 62 218 58 214 Z" fill="black" opacity={0.75} />
      <path d="M144 202 L184 202 L182 214 C178 218 150 218 146 214 Z" fill="black" opacity={0.75} />
      <path d="M76 203 L76 212 M164 203 L164 212" stroke="#0d1016" strokeWidth={2.5} />

      {/* broad muscular shoulders tapering to chest */}
      <path
        d="M50 150 C44 110 70 78 110 78 C150 78 176 110 170 150 C166 172 148 186 110 188 C72 186 54 172 50 150 Z"
        fill="currentColor"
        {...outline}
      />
      {/* thin comic-shine stroke along the top, instead of a flat highlight blob */}
      <path
        d="M60 112 C70 90 88 78 110 76 C92 84 78 98 72 118"
        fill="none"
        stroke="white"
        strokeWidth={3}
        strokeLinecap="round"
        opacity={0.75}
      />
      {/* chest muscle crease */}
      <path d="M92 150 C100 138 100 124 94 112" stroke="black" strokeWidth={2.5} fill="none" opacity={0.25} />
      <path d="M128 150 C120 138 120 124 126 112" stroke="black" strokeWidth={2.5} fill="none" opacity={0.25} />

      {/* ears */}
      <path d="M62 86 L46 70 L68 78 Z" fill="currentColor" {...outline} />
      <path d="M158 86 L174 70 L152 78 Z" fill="currentColor" {...outline} />

      {/* sharp hooked horns, tapering to a point */}
      <path
        d="M72 78 C52 66 40 44 50 20 C54 34 56 48 62 60 C64 48 70 38 80 32 C96 28 110 36 116 50 C100 50 86 56 76 68 C74 72 73 76 72 86 Z"
        fill="currentColor"
        {...outline}
      />
      <path
        d="M148 78 C168 66 180 44 170 20 C166 34 164 48 158 60 C156 48 150 38 140 32 C124 28 110 36 104 50 C120 50 134 56 144 68 C146 72 147 76 148 86 Z"
        fill="currentColor"
        {...outline}
      />

      {/* head, lowered toward the viewer */}
      <ellipse cx="110" cy="118" rx="42" ry="38" fill="currentColor" {...outline} />

      {/* angry brow */}
      <path d="M82 100 L102 106 M138 100 L118 106" stroke="black" strokeWidth={5} strokeLinecap="round" />
      {/* eyes */}
      <path d="M90 112 L104 114 L94 120 Z" fill="white" />
      <path d="M130 112 L116 114 L126 120 Z" fill="white" />
      <circle cx="97" cy="114.5" r="2.4" fill="black" />
      <circle cx="123" cy="114.5" r="2.4" fill="black" />

      {/* snout */}
      <ellipse cx="110" cy="142" rx="26" ry="18" fill="currentColor" opacity={0.85} {...outline} />
      <ellipse cx="100" cy="144" rx="3" ry="4" fill="black" opacity={0.6} />
      <ellipse cx="120" cy="144" rx="3" ry="4" fill="black" opacity={0.6} />
      <path d="M98 150 C104 154 116 154 122 150" stroke="black" strokeWidth={2.5} fill="none" opacity={0.5} />

      {/* nostril steam */}
      <path d="M76 146 C70 140 70 132 76 124" stroke="currentColor" strokeWidth={3} strokeLinecap="round" opacity={0.35} />
      <path d="M144 146 C150 140 150 132 144 124" stroke="currentColor" strokeWidth={3} strokeLinecap="round" opacity={0.35} />
    </svg>
  );
}
