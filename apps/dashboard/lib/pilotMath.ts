// Pure pilot helpers (P8 W13), unit-tested in test/logic.test.ts.

/** Share of the pilot that has passed (0..1); 0 until it has dates. */
export function progressShare(day: number | null, days: number | null): number {
  if (!day || !days) return 0;
  return Math.min(1, Math.max(0, day / days));
}

/** Is the change between baseline and current an improvement? null when either is missing. */
export function improved(better: "lower" | "higher", baseline: number | null, current: number | null): boolean | null {
  if (baseline === null || current === null || baseline === current) return null;
  return better === "lower" ? current < baseline : current > baseline;
}

/** Stable key for an insight whose content varies (e.g. a copilot question). */
export function insightKey(prefix: string, text: string): string {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
  return `${prefix}.${(h >>> 0).toString(36)}`;
}
