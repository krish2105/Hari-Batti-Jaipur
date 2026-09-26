// Geometry for matching a GPS fix to the corridor (J08 in the west to J03 in the east).
// Junction positions are UNVERIFIED OpenStreetMap candidates (J08 is extrapolated, ASSUMED), so
// distances are approximate; the app says so on screen.

export type LatLng = { lat: number; lng: number };

const R = 6_371_000;
const rad = (d: number) => (d * Math.PI) / 180;

/** Great-circle distance in metres. */
export function metres(a: LatLng, b: LatLng): number {
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** Local flat projection (metres east/north of an origin); fine over a few kilometres. */
function xy(p: LatLng, o: LatLng) {
  return { x: rad(p.lng - o.lng) * R * Math.cos(rad(o.lat)), y: rad(p.lat - o.lat) * R };
}

/** Where a point falls on the polyline: distance along it from the first vertex (chainage, metres)
 * and how far it is from the line (offset, metres). */
export function project(p: LatLng, line: LatLng[]): { chainage: number; offset: number } {
  const o = line[0]!;
  const q = xy(p, o);
  let best = { chainage: 0, offset: Infinity };
  let along = 0;
  for (let i = 0; i + 1 < line.length; i++) {
    const a = xy(line[i]!, o);
    const b = xy(line[i + 1]!, o);
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy);
    const t = len ? Math.max(0, Math.min(1, ((q.x - a.x) * dx + (q.y - a.y) * dy) / (len * len))) : 0;
    const off = Math.hypot(a.x + t * dx - q.x, a.y + t * dy - q.y);
    if (off < best.offset) best = { chainage: along + t * len, offset: off };
    along += len;
  }
  return best;
}

/** Chainage of every vertex (cumulative length). */
export function chainages(line: LatLng[]): number[] {
  const out = [0];
  for (let i = 1; i < line.length; i++) out.push(out[i - 1]! + metres(line[i - 1]!, line[i]!));
  return out;
}

/** A position rounded to about 100 m (privacy: reports never carry an exact location). */
export function coarse(p: LatLng): LatLng {
  return { lat: Math.round(p.lat * 1000) / 1000, lng: Math.round(p.lng * 1000) / 1000 };
}
