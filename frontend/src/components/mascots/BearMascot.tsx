/** Roaring bear, bold-outline mascot style (ref: classic red bull-vs-bear market icon). */
export function BearMascot({ className }: { className?: string }) {
  const outline = { stroke: "black", strokeWidth: 4, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };
  return (
    <svg viewBox="0 0 220 240" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* planted legs */}
      <path d="M62 198 C58 212 62 222 78 224 C92 226 98 216 94 202 Z" fill="currentColor" {...outline} />
      <path d="M126 202 C124 216 130 226 144 226 C158 226 162 214 156 200 Z" fill="currentColor" {...outline} />

      {/* body */}
      <path
        d="M54 150 C44 112 68 76 110 76 C152 76 176 112 166 150 C162 176 148 198 110 200 C72 198 58 176 54 150 Z"
        fill="currentColor"
        {...outline}
      />
      {/* thin comic-shine stroke along the back, instead of a flat highlight blob */}
      <path
        d="M66 160 C50 144 46 120 54 100 C62 82 78 70 98 66"
        fill="none"
        stroke="white"
        strokeWidth={3}
        strokeLinecap="round"
        opacity={0.75}
      />

      {/* left arm, swiping, jagged fur edge */}
      <path
        d="M58 136 C34 124 18 98 22 68 C30 84 40 98 54 110 C50 96 52 82 60 70 C64 88 66 104 74 118 L70 128 Z"
        fill="currentColor"
        {...outline}
      />
      <path
        d="M22 70 L12 58 L24 62 L18 48 L30 56 L26 42"
        stroke="currentColor"
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M26 66 L14 54 M32 70 L22 56 M38 76 L30 60" stroke="black" strokeWidth={4} strokeLinecap="round" />

      {/* right arm, swiping, jagged fur edge */}
      <path
        d="M162 136 C186 124 202 98 198 68 C190 84 180 98 166 110 C170 96 168 82 160 70 C156 88 154 104 146 118 L150 128 Z"
        fill="currentColor"
        {...outline}
      />
      <path
        d="M198 70 L208 58 L196 62 L202 48 L190 56 L194 42"
        stroke="currentColor"
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M194 66 L206 54 M188 70 L198 56 M182 76 L190 60" stroke="black" strokeWidth={4} strokeLinecap="round" />

      {/* ears, furred */}
      <path d="M68 62 C60 50 62 36 74 32 C78 44 78 54 76 64 Z" fill="currentColor" {...outline} />
      <path d="M152 62 C160 50 158 36 146 32 C142 44 142 54 144 64 Z" fill="currentColor" {...outline} />

      {/* head */}
      <path
        d="M62 94 C56 64 80 44 110 44 C140 44 164 64 158 94 C154 116 134 130 110 130 C86 130 66 116 62 94 Z"
        fill="currentColor"
        {...outline}
      />

      {/* fur-spike crown along the top of the head */}
      <path
        d="M80 48 L86 36 L92 50 L100 34 L108 50 L116 34 L122 50 L130 36 L136 48"
        fill="none"
        stroke="currentColor"
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* angry brow */}
      <path d="M78 80 L98 86 M142 80 L122 86" stroke="black" strokeWidth={4} strokeLinecap="round" />
      {/* eyes */}
      <ellipse cx="92" cy="92" rx="5" ry="4" fill="white" />
      <ellipse cx="128" cy="92" rx="5" ry="4" fill="white" />
      <ellipse cx="93" cy="93" rx="2.4" ry="3" fill="black" />
      <ellipse cx="127" cy="93" rx="2.4" ry="3" fill="black" />

      {/* snout */}
      <path
        d="M86 108 C94 100 126 100 134 108 C138 118 130 128 110 128 C90 128 82 118 86 108 Z"
        fill="currentColor"
        opacity={0.85}
        {...outline}
      />

      {/* roaring open mouth, teeth + tongue */}
      <path d="M92 114 C98 132 122 132 128 114 C120 124 100 124 92 114 Z" fill="black" />
      <path d="M100 120 C108 128 112 128 120 120 C116 132 104 132 100 120 Z" fill="#c0392b" />
      <path d="M97 115 L101 122 L105 115 Z" fill="white" />
      <path d="M115 115 L119 122 L123 115 Z" fill="white" />
      <ellipse cx="110" cy="104" rx="5" ry="3.6" fill="black" opacity={0.6} />
    </svg>
  );
}
