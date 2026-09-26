// Scroll position as "section index + fraction", shared by the DOM and the 3D camera rig.
export const SECTIONS = ["hero", "wait", "squeeze", "mix", "map", "itms", "solution", "wave", "ai", "impact", "pilot"] as const;
export type SectionId = (typeof SECTIONS)[number];

let progress = 0;
const listeners = new Set<(p: number) => void>();

export function getProgress() {
  return progress;
}

export function subscribe(fn: (p: number) => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Recompute from the DOM: which section holds the viewport centre, and how far through it. */
export function measure() {
  const mid = window.innerHeight * 0.5;
  let p = 0;
  for (let i = 0; i < SECTIONS.length; i++) {
    const el = document.getElementById(SECTIONS[i]!);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.top <= mid) p = i + Math.min(1, Math.max(0, (mid - r.top) / Math.max(1, r.height)));
  }
  progress = p;
  listeners.forEach((fn) => fn(p));
}
