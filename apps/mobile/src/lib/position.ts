// Position during a ride or walk ONLY: GPS (expo-location, foreground, 1 s) or a clearly labelled
// simulated drive along the corridor for demos and testing. Stops as soon as the screen closes.
import * as Location from "expo-location";
import { useEffect, useState } from "react";
import type { LatLng } from "./geo";
import { CORRIDOR } from "./signals";

export type Fix = { p: LatLng; speedKmh: number; t: number; simulated: boolean };

/** A point `d` metres along the corridor polyline (for the simulated drive). */
function along(d: number): LatLng {
  const pts = CORRIDOR.map((j) => ({ lat: j.lat, lng: j.lng }));
  let left = d;
  for (let i = 0; i + 1 < pts.length; i++) {
    const a = pts[i]!;
    const b = pts[i + 1]!;
    const seg = Math.hypot((b.lat - a.lat) * 111_320, (b.lng - a.lng) * 111_320 * Math.cos((a.lat * Math.PI) / 180));
    if (left <= seg) return { lat: a.lat + ((b.lat - a.lat) * left) / seg, lng: a.lng + ((b.lng - a.lng) * left) / seg };
    left -= seg;
  }
  return pts[pts.length - 1]!;
}

/** Simulated drive (labelled on screen): 32 km/h eastbound from J08, pausing 12 s near each junction so the stopped state (engine-off nudge, trip stops) can be seen. */
function useSimulated(active: boolean): Fix | null {
  const [fix, setFix] = useState<Fix | null>(null);
  useEffect(() => {
    if (!active) return;
    let d = 0;
    let wait = 0;
    const id = setInterval(() => {
      const moving = wait <= 0;
      if (moving) d += 32 / 3.6;
      else wait -= 1;
      if (moving && Math.round(d) % 500 > 440 && Math.round(d) % 500 < 450) wait = 12; // a short stop near each junction
      setFix({ p: along(d), speedKmh: moving ? 32 : 0, t: Date.now() / 1000, simulated: true });
    }, 1000);
    return () => clearInterval(id);
  }, [active]);
  return fix;
}

export function usePosition(active: boolean, simulated: boolean): { fix: Fix | null; denied: boolean } {
  const sim = useSimulated(active && simulated);
  const [fix, setFix] = useState<Fix | null>(null);
  const [denied, setDenied] = useState(false);
  useEffect(() => {
    if (!active || simulated) return;
    let sub: Location.LocationSubscription | null = null;
    let stop = false;
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") return setDenied(true);
      sub = await Location.watchPositionAsync({ accuracy: Location.Accuracy.BestForNavigation, timeInterval: 1000, distanceInterval: 0 }, (l) => {
        if (stop) return;
        const v = l.coords.speed && l.coords.speed > 0 ? l.coords.speed * 3.6 : 0;
        setFix({ p: { lat: l.coords.latitude, lng: l.coords.longitude }, speedKmh: v, t: l.timestamp / 1000, simulated: false });
      });
    })();
    return () => {
      stop = true;
      sub?.remove(); // location stops when the ride / walk ends
    };
  }, [active, simulated]);
  return { fix: simulated ? sim : fix, denied };
}
