import { useId, useMemo } from "react";

/**
 * Lightweight SVG radar chart for the detection report breakdown.
 *
 * Improvements over the first pass:
 *   - Generous padding + overflow visible so labels never clip
 *   - Long labels auto-wrap onto two lines at the midpoint
 *   - Ring percentage labels (25/50/75/100) for scale reference
 *   - Score chip near each vertex
 *   - Text uses paint-order stroke fill for crisp contrast over the polygon
 *
 * Props:
 *   items: [{ title: string, score: number (0-100), severity: string }, ...]
 *   baseline: number (0-100) — dashed reference envelope (default 30)
 *   size: svg viewBox edge (default 560)
 */
export default function RadarChart({ items = [], baseline = 30, size = 560 }) {
  const gradientId = useId();
  const glowId = `${gradientId}-glow`;

  const data = useMemo(() => {
    const filtered = items.filter((item) => item && typeof item.score === "number");
    const count = filtered.length;
    if (!count) return [];
    return filtered.map((item, index) => ({
      ...item,
      angle: (Math.PI * 2 * index) / count - Math.PI / 2
    }));
  }, [items]);

  if (!data.length) return null;

  const center = size / 2;
  const padding = 120; // leaves room for two-line labels and score chips
  const radius = center - padding;
  const rings = [
    { ratio: 0.25, label: "25" },
    { ratio: 0.5, label: "50" },
    { ratio: 0.75, label: "75" },
    { ratio: 1.0, label: "100" }
  ];

  const pointFor = (angle, ratio) => {
    const r = radius * ratio;
    return {
      x: center + Math.cos(angle) * r,
      y: center + Math.sin(angle) * r
    };
  };

  const toPolygonPoints = (ratioFor) =>
    data
      .map((point) => {
        const { x, y } = pointFor(point.angle, ratioFor(point));
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

  const clampScore = (score) => Math.max(0, Math.min(1, (score || 0) / 100));
  const polyImage = toPolygonPoints((p) => clampScore(p.score));
  const polyBaseline = toPolygonPoints(() => clampScore(baseline));

  // Split long labels into two balanced lines by word boundaries.
  const splitLabel = (title) => {
    if (!title) return [""];
    if (title.length <= 13) return [title];
    const words = title.split(" ");
    if (words.length === 1) return [title];
    let bestSplit = 1;
    let bestDiff = Infinity;
    for (let index = 1; index < words.length; index += 1) {
      const left = words.slice(0, index).join(" ").length;
      const right = words.slice(index).join(" ").length;
      const diff = Math.abs(left - right);
      if (diff < bestDiff) {
        bestDiff = diff;
        bestSplit = index;
      }
    }
    return [words.slice(0, bestSplit).join(" "), words.slice(bestSplit).join(" ")];
  };

  const severityColor = (severity) => {
    if (severity === "high" || severity === "warning") return "#f87171";
    if (severity === "mild") return "#fbbf24";
    return "#4ade80";
  };

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Detection signal radar chart"
      style={{ overflow: "visible" }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4fd1c5" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.95" />
        </linearGradient>
        <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* concentric rings */}
      {rings.map(({ ratio }) => (
        <circle
          key={ratio}
          cx={center}
          cy={center}
          r={radius * ratio}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1"
        />
      ))}

      {/* ring value labels on the top axis */}
      {rings.map(({ ratio, label }) => (
        <text
          key={`ring-${ratio}`}
          x={center + 6}
          y={center - radius * ratio}
          fill="rgba(180, 192, 222, 0.55)"
          fontSize="10"
          fontFamily="JetBrains Mono, monospace"
          dominantBaseline="middle"
        >
          {label}
        </text>
      ))}

      {/* spokes */}
      {data.map((point) => {
        const { x, y } = pointFor(point.angle, 1);
        return (
          <line
            key={`spoke-${point.title}`}
            x1={center}
            y1={center}
            x2={x}
            y2={y}
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        );
      })}

      {/* baseline envelope */}
      <polygon
        points={polyBaseline}
        fill="rgba(255,255,255,0.05)"
        stroke="rgba(255,255,255,0.22)"
        strokeWidth="1"
        strokeDasharray="3 4"
      />

      {/* image signals polygon */}
      <polygon
        points={polyImage}
        fill={`url(#${gradientId})`}
        fillOpacity="0.3"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.5"
        filter={`url(#${glowId})`}
      />

      {/* vertex dots */}
      {data.map((point) => {
        const ratio = clampScore(point.score);
        const { x, y } = pointFor(point.angle, ratio);
        return (
          <g key={`dot-${point.title}`}>
            <circle cx={x} cy={y} r="6" fill={severityColor(point.severity)} fillOpacity="0.25" />
            <circle
              cx={x}
              cy={y}
              r="3.6"
              fill={severityColor(point.severity)}
              stroke="#03060f"
              strokeWidth="1.5"
            />
          </g>
        );
      })}

      {/* axis labels (two-line for long titles) */}
      {data.map((point) => {
        const labelPos = pointFor(point.angle, 1.14);
        const cos = Math.cos(point.angle);
        const anchor = cos > 0.3 ? "start" : cos < -0.3 ? "end" : "middle";
        const lines = splitLabel(point.title);
        const baseY = labelPos.y - (lines.length - 1) * 7;

        return (
          <g key={`label-${point.title}`}>
            {lines.map((line, index) => (
              <text
                key={line + index}
                x={labelPos.x}
                y={baseY + index * 14}
                textAnchor={anchor}
                dominantBaseline="middle"
                fill="rgba(230, 236, 250, 0.92)"
                fontSize="11.5"
                fontFamily="Inter, sans-serif"
                fontWeight="600"
                style={{
                  paintOrder: "stroke",
                  stroke: "rgba(3, 6, 15, 0.9)",
                  strokeWidth: 3,
                  strokeLinejoin: "round"
                }}
              >
                {line}
              </text>
            ))}
          </g>
        );
      })}

      {/* score chips near each vertex (small) */}
      {data.map((point) => {
        const ratio = clampScore(point.score);
        const chipPos = pointFor(point.angle, ratio);
        const cos = Math.cos(point.angle);
        const sin = Math.sin(point.angle);
        // offset the chip slightly outward from the dot
        const offsetX = chipPos.x + cos * 12;
        const offsetY = chipPos.y + sin * 12;
        return (
          <text
            key={`score-${point.title}`}
            x={offsetX}
            y={offsetY}
            textAnchor={cos > 0.3 ? "start" : cos < -0.3 ? "end" : "middle"}
            dominantBaseline="middle"
            fontFamily="JetBrains Mono, monospace"
            fontSize="10"
            fontWeight="600"
            fill="rgba(255, 255, 255, 0.85)"
            style={{
              paintOrder: "stroke",
              stroke: "rgba(3, 6, 15, 0.9)",
              strokeWidth: 2.5,
              strokeLinejoin: "round"
            }}
          >
            {Math.round(point.score)}
          </text>
        );
      })}
    </svg>
  );
}
