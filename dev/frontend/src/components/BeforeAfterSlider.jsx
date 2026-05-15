import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Draggable before/after image comparison slider.
 *
 * Layout:
 *   - Base layer:   afterSrc (heatmap) — always fully rendered
 *   - Top layer:    beforeSrc (original) — clipped with clip-path so only
 *                   the left `position%` is visible
 *
 * Result at position=50:  left half = original, right half = heatmap,
 * which matches the "Original" (left) and "Heatmap" (right) labels.
 *
 * Works with pointer, touch, and keyboard (Arrow/Home/End on the knob).
 */
export default function BeforeAfterSlider({
  beforeSrc,
  afterSrc,
  beforeLabel = "Original",
  afterLabel = "Grad-CAM",
  initialPosition = 50
}) {
  const containerRef = useRef(null);
  const [position, setPosition] = useState(initialPosition);
  const draggingRef = useRef(false);

  const setPositionFromClientX = useCallback((clientX) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPosition(Math.max(0, Math.min(100, pct)));
  }, []);

  const handlePointerDown = (event) => {
    draggingRef.current = true;
    try {
      containerRef.current?.setPointerCapture?.(event.pointerId);
    } catch {
      /* ignore — some browsers reject capture for mouse */
    }
    setPositionFromClientX(event.clientX);
  };

  const handlePointerMove = (event) => {
    if (!draggingRef.current) return;
    setPositionFromClientX(event.clientX);
  };

  const stopDrag = (event) => {
    draggingRef.current = false;
    if (event?.pointerId != null) {
      try {
        containerRef.current?.releasePointerCapture?.(event.pointerId);
      } catch {
        /* ignore */
      }
    }
  };

  useEffect(() => {
    const cancel = () => {
      draggingRef.current = false;
    };
    window.addEventListener("pointerup", cancel);
    window.addEventListener("pointercancel", cancel);
    return () => {
      window.removeEventListener("pointerup", cancel);
      window.removeEventListener("pointercancel", cancel);
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setPosition((p) => Math.max(0, p - 4));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setPosition((p) => Math.min(100, p + 4));
    } else if (event.key === "Home") {
      event.preventDefault();
      setPosition(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setPosition(100);
    }
  };

  // clip-path keeps only the left `position%` of the original image visible
  const originalClipPath = `inset(0 ${100 - position}% 0 0)`;

  return (
    <div
      className="compare-slider"
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={stopDrag}
      onPointerCancel={stopDrag}
    >
      {/* Base layer: heatmap, always fully visible */}
      <img src={afterSrc} alt={afterLabel} />
      {/* Top layer: original, clipped to left portion */}
      <img
        src={beforeSrc}
        alt={beforeLabel}
        style={{ clipPath: originalClipPath, WebkitClipPath: originalClipPath }}
      />

      <span className="compare-label compare-label-left">{beforeLabel}</span>
      <span className="compare-label compare-label-right">{afterLabel}</span>

      <div className="compare-handle" style={{ left: `${position}%` }}>
        <button
          type="button"
          className="compare-handle-knob"
          aria-label={`Drag to compare ${beforeLabel} and ${afterLabel}`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(position)}
          role="slider"
          onKeyDown={handleKeyDown}
        >
          ⇆
        </button>
      </div>
    </div>
  );
}
