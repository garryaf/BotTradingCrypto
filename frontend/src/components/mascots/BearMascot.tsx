export function BearMascot({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 240" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* legs planted, standing tall */}
      <ellipse cx="78" cy="214" rx="20" ry="14" fill="currentColor" opacity={0.85} />
      <ellipse cx="142" cy="214" rx="20" ry="14" fill="currentColor" opacity={0.85} />

      {/* body, standing on hind legs */}
      <path
        d="M58 150 C50 110 72 78 110 78 C148 78 170 110 162 150 C158 176 146 196 110 198 C74 196 62 176 58 150 Z"
        fill="currentColor"
      />

      {/* raised arm — left, claws out */}
      <path
        d="M62 132 C38 118 24 90 30 60 C40 82 54 100 72 114 Z"
        fill="currentColor"
      />
      <path d="M28 58 L20 44 M31 56 L26 40 M36 58 L34 42" stroke="currentColor" strokeWidth={5} strokeLinecap="round" />

      {/* raised arm — right, claws out */}
      <path
        d="M158 132 C182 118 196 90 190 60 C180 82 166 100 148 114 Z"
        fill="currentColor"
      />
      <path d="M192 58 L200 44 M189 56 L194 40 M184 58 L186 42" stroke="currentColor" strokeWidth={5} strokeLinecap="round" />

      {/* ears */}
      <circle cx="78" cy="58" r="16" fill="currentColor" />
      <circle cx="142" cy="58" r="16" fill="currentColor" />
      <circle cx="78" cy="58" r="7" fill="currentColor" opacity={0.5} />
      <circle cx="142" cy="58" r="7" fill="currentColor" opacity={0.5} />

      {/* head */}
      <ellipse cx="110" cy="92" rx="46" ry="42" fill="currentColor" />

      {/* angry brow */}
      <path d="M78 76 L96 82 M142 76 L124 82" stroke="black" strokeWidth={4} strokeLinecap="round" opacity={0.55} />

      {/* glowing angry eyes */}
      <ellipse cx="90" cy="88" rx="5" ry="4" fill="white" />
      <ellipse cx="130" cy="88" rx="5" ry="4" fill="white" />
      <ellipse cx="91" cy="89" rx="2.4" ry="3" fill="black" />
      <ellipse cx="129" cy="89" rx="2.4" ry="3" fill="black" />

      {/* snout */}
      <ellipse cx="110" cy="112" rx="24" ry="18" fill="currentColor" opacity={0.8} />

      {/* roaring mouth */}
      <path d="M90 118 C96 134 124 134 130 118 C120 128 100 128 90 118 Z" fill="black" opacity={0.75} />
      <path d="M96 118 L100 126 L104 118 Z" fill="white" opacity={0.9} />
      <path d="M116 118 L120 126 L124 118 Z" fill="white" opacity={0.9} />
      <ellipse cx="110" cy="108" rx="5" ry="3.5" fill="black" opacity={0.6} />
    </svg>
  );
}
