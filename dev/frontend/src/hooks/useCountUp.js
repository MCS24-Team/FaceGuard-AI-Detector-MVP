import { useEffect, useRef, useState } from "react";

/**
 * Smoothly animates a numeric value from 0 (or previous value) to `target`
 * over `duration` ms using an ease-out curve. Respects reduced motion.
 */
export default function useCountUp(target, { duration = 800, decimals = 2 } = {}) {
  const [value, setValue] = useState(0);
  const frameRef = useRef(0);
  const startRef = useRef(0);
  const fromRef = useRef(0);

  useEffect(() => {
    const safeTarget = Number.isFinite(target) ? target : 0;

    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reduce) {
      setValue(safeTarget);
      return undefined;
    }

    cancelAnimationFrame(frameRef.current);
    fromRef.current = value;
    startRef.current = performance.now();

    const step = (now) => {
      const elapsed = now - startRef.current;
      const progress = Math.min(1, elapsed / duration);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = fromRef.current + (safeTarget - fromRef.current) * eased;
      setValue(next);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        setValue(safeTarget);
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}
