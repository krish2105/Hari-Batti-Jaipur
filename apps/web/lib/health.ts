// Colour for a 0–100 Health Score (green good, amber watch, red act). Used by map dots and cards.
export function healthColour(h: number) {
  return h >= 85 ? "#22c55e" : h >= 70 ? "#ffb020" : "#ff3b30";
}
