// Health score bands (same thresholds as the website): green good, amber watch, red act.
export function healthColour(h: number | null | undefined) {
  if (h === null || h === undefined) return "var(--grid)";
  return h >= 85 ? "#22c55e" : h >= 70 ? "#ffb020" : "#ff3b30";
}

/** A softer fill for heatmap cells: the band colour with opacity scaled by how far into the band. */
export function healthFill(h: number | null | undefined) {
  if (h === null || h === undefined) return "var(--grid)";
  const base = h >= 85 ? [34, 197, 94] : h >= 70 ? [255, 176, 32] : [255, 59, 48];
  const strength = h >= 85 ? 0.35 + (100 - h) / 30 : h >= 70 ? 0.55 + (85 - h) / 40 : 0.75 + Math.min(0.25, (70 - h) / 80);
  return `rgb(${base.join(" ")} / ${Math.min(1, strength).toFixed(2)})`;
}

export const SIGNAL_HEX = { RED: "#ff3b30", AMBER: "#ffb020", GREEN: "#22c55e", FLASHING_AMBER: "#ffb020" } as const;

/** Corridor order west → east (Mansarovar Metro end first), then the separate B2 Bypass pair. */
export const CORRIDOR = ["J08", "J07", "J06", "J05", "J04", "J03"] as const;
export const B2_PAIR = ["J01", "J02"] as const;
export const ALL_JUNCTIONS = [...CORRIDOR, ...B2_PAIR];
