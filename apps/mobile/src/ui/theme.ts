// Colours and sizes. Signal colours are used only for signal meaning. Dark by default (night rides),
// with large type so a glance is enough.
export const SIGNAL = { RED: "#ff3b30", AMBER: "#ffb020", GREEN: "#22c55e", FLASHING_AMBER: "#ffb020" } as const;

export const DARK = { bg: "#0f1b2d", panel: "#162640", ink: "#f6e7e2", ink2: "#c3b3b6", line: "rgba(232,153,141,0.25)", accent: "#e8998d" };
export const LIGHT = { bg: "#f7e4dd", panel: "#fffaf7", ink: "#0f1b2d", ink2: "#3c4a60", line: "rgba(15,27,45,0.15)", accent: "#a4474d" };
export type Palette = typeof DARK;

export const SOURCE_TONE: Record<string, string> = { SIM: "#7B61FF", CROWD: "#F77F00", ITMS: "#3b82f6", FIELD: "#0081A7", SURVEY: "#3f7d3a" };
