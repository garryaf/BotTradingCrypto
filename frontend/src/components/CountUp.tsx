"use client";

import { useEffect, useRef, useState } from "react";
import { animate } from "framer-motion";

/** Smoothly tweens the displayed number toward `value` instead of snapping — an "odometer" feel. */
export function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);

  useEffect(() => {
    const controls = animate(prev.current, value, {
      duration: 0.8,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(v),
    });
    prev.current = value;
    return () => controls.stop();
  }, [value]);

  return <>{format(display)}</>;
}
