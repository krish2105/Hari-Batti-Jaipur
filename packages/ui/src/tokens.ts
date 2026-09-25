// Shared design tokens. Starting values only; the website (P4) will refine the look.
import type { DataSource, SignalColour } from "@haribatti/core";

/** Colours for the signal lights themselves. */
export const signalColours: Record<SignalColour, string> = {
  RED: "#E5383B",
  AMBER: "#F4A259",
  GREEN: "#2BA84A",
  FLASHING_AMBER: "#F4A259",
};

/** Badge colour for each data source, so users can always see where a number came from. */
export const sourceBadgeColours: Record<DataSource, string> = {
  SIM: "#7B61FF",
  FIELD: "#0081A7",
  SURVEY: "#6A994E",
  CROWD: "#F77F00",
  ITMS: "#1D3557",
};

/** Font families (free Google Fonts, with Hindi support via Noto Sans Devanagari). */
export const fonts = {
  sans: "'Inter', 'Noto Sans Devanagari', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
};
