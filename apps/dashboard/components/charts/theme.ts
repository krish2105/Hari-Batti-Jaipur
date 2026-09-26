// Shared Recharts styling that follows the CSS theme tokens.
export const axis = { stroke: "var(--ink-3)", fontSize: 11, tickLine: false, axisLine: { stroke: "var(--line)" } } as const;
export const grid = { stroke: "var(--grid)", strokeDasharray: "3 4", vertical: false } as const;
export const tooltip = {
  contentStyle: { background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, fontSize: 12, color: "var(--ink)" },
  labelStyle: { color: "var(--ink-2)", fontWeight: 600 },
  itemStyle: { color: "var(--ink)" },
  cursor: { fill: "var(--accent-soft)" },
} as const;
export const SERIES = ["#e8998d", "#7aa7ff", "#9fd49a", "#ffb020", "#b3a5ff", "#6fd0ec", "#ff8a80", "#c3b3b6"];
