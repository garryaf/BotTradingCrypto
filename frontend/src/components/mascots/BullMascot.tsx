/** Charging bull, bold-outline mascot style (ref: classic blue bull-vs-bear market icon). */
export function BullMascot({ className }: { className?: string }) {
  const outline = { stroke: "black", strokeWidth: 4, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
  return (
    <svg viewBox="0 0 220 220" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* front legs, planted wide and ready to charge */}
      <path d="M66 176 C60 190 62 202 76 206 C88 210 96 200 92 186 Z" fill="currentColor" {...outline} />
      <path d="M154 176 C160 190 158 202 144 206 C132 210 124 200 128 186 Z" fill="currentColor" {...outline} />

      {/* broad muscular shoulders tapering to chest */}
      <path
        d="M50 150 C44 110 70 78 110 78 C150 78 176 110 170 150 C166 172 148 186 110 188 C72 186 54 172 50 150 Z"
        fill="currentColor"
        {...outline}
      />
      <path
        d="M68 104 C80 90 96 82 112 82 C96 90 84 102 78 118 C74 128 74 138 78 146 C64 136 58 118 68 104 Z"
        fill="white"
        opacity={0.22}
      />

      {/* ears */}
      <path d="M62 86 L46 70 L68 78 Z" fill="currentColor" {...outline} />
      <path d="M158 86 L174 70 L152 78 Z" fill="currentColor" {...outline} />

      {/* symmetric dramatic "C" horns, tips hooking in toward the brow */}
      <path
        d="M72 78 C54 68 44 48 52 26 C64 36 68 54 66 70 C76 58 90 52 104 54 C88 62 76 70 72 86 Z"
        fill="currentColor"
        {...outline}
      />
      <path
        d="M148 78 C166 68 176 48 168 26 C156 36 152 54 154 70 C144 58 130 52 116 54 C132 62 144 70 148 86 Z"
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
