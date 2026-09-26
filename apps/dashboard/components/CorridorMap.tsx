"use client";
// Map tab: OpenFreeMap vector tiles (no key, needs internet) with the junctions at their
// UNVERIFIED OpenStreetMap candidate positions, coloured by Health. Falls back to a message offline.
import { useEffect, useRef, useState } from "react";
import { Map as MLMap, NavigationControl, setWorkerUrl } from "maplibre-gl";

// MapLibre 6 loads its web worker from this static copy (scripts/copy-maplibre-worker.mjs).
setWorkerUrl("/vendor/maplibre/maplibre-gl-worker.mjs");
import type { FeatureCollection } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
import { useRouter } from "next/navigation";
import { healthColour } from "@/lib/health";
import { useT } from "@/lib/i18n";
import type { JunctionInfo } from "@/lib/types";

export default function CorridorMap({ junctions, health, dark }: { junctions: JunctionInfo[]; health: Record<string, number | null>; dark: boolean }) {
  const { t, href } = useT();
  const router = useRouter();
  const box = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!box.current) return;
    let m: MLMap;
    try {
      m = new MLMap({
        container: box.current,
        style: `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`,
        center: [75.768, 26.848], zoom: 13.2, attributionControl: { compact: true }, cooperativeGestures: true,
      });
    } catch {
      setFailed(true);
      return;
    }
    const timeout = setTimeout(() => !m.loaded() && setFailed(true), 12000);
    m.on("error", () => !m.loaded() && setFailed(true));
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    const points: FeatureCollection = {
      type: "FeatureCollection",
      features: junctions.filter((j) => j.lat !== null && j.lng !== null).map((j) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [j.lng!, j.lat!] },
        properties: { id: j.id, label: `${j.id} ${j.name.replace(/ Junction$/, "")}`, colour: healthColour(health[j.id]) },
      })),
    };
    m.on("load", () => {
      clearTimeout(timeout);
      m.addSource("hb", { type: "geojson", data: points });
      m.addLayer({ id: "hb-halo", type: "circle", source: "hb", paint: { "circle-radius": 14, "circle-color": ["get", "colour"], "circle-opacity": 0.25 } });
      m.addLayer({ id: "hb-dot", type: "circle", source: "hb", paint: { "circle-radius": 7, "circle-color": ["get", "colour"], "circle-stroke-width": 2, "circle-stroke-color": dark ? "#0a1220" : "#fff" } });
      m.addLayer({ id: "hb-label", type: "symbol", source: "hb", layout: { "text-field": ["get", "label"], "text-size": 12, "text-offset": [0, 1.4], "text-anchor": "top", "text-font": ["Noto Sans Bold"] },
        paint: { "text-color": dark ? "#e8edf4" : "#0f1b2d", "text-halo-color": dark ? "#0a1220" : "#fff", "text-halo-width": 1.5 } });
      m.on("click", "hb-dot", (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (id) router.push(href(`/junction/${id}`));
      });
      m.on("mouseenter", "hb-dot", () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", "hb-dot", () => (m.getCanvas().style.cursor = ""));
    });
    return () => {
      clearTimeout(timeout);
      m.remove();
    };
  }, [junctions, health, dark, router, href]);

  return (
    <div>
      <div ref={box} className="h-[340px] w-full overflow-hidden rounded-xl md:h-[420px]" aria-label={t.overview.map} role="region" />
      <p className="faint mt-2 text-xs">{failed ? t.overview.mapOffline : t.overview.mapNote}</p>
    </div>
  );
}
