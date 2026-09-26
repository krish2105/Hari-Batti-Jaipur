"use client";
// 3D Jaipur map: OpenFreeMap vector tiles (no key), extruded buildings, 45° pitch, the surveyed
// junctions coloured by Health Score. Positions are unverified OpenStreetMap matches (labelled);
// junctions with no position yet are not drawn — they stay in the list next to the map.
import { useEffect, useRef, useState } from "react";
import { Map as MLMap, NavigationControl, setWorkerUrl } from "maplibre-gl";

// MapLibre 6 loads its web worker from this static copy (scripts/copy-maplibre-worker.mjs).
setWorkerUrl("/vendor/maplibre/maplibre-gl-worker.mjs");
import type { Feature, FeatureCollection } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
import { site } from "@/lib/site";
import { healthColour } from "@/lib/health";

export default function JaipurMap({ dark, selected, onSelect, ariaLabel, sharedLabel }: { dark: boolean; selected: string; onSelect: (id: string) => void; ariaLabel: string; sharedLabel: string }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!box.current) return;
    let m: MLMap;
    try {
      m = new MLMap({
        container: box.current,
        style: `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`,
        center: [75.7665, 26.853], zoom: 13.7, pitch: 52, bearing: -28,
        attributionControl: { compact: true }, cooperativeGestures: true,
      });
    } catch {
      setFailed(true);
      return;
    }
    map.current = m;
    let alive = true; // false once this map is removed (theme change / unmount)
    m.addControl(new NavigationControl({ visualizePitch: true }), "top-right");
    // junctions whose candidate points coincide (J02/J03 today) become one dot with a joint label
    const groups = new Map<string, typeof site.junctions>();
    for (const j of site.junctions.filter((x) => x.position.lat != null)) {
      const key = `${j.position.lat!.toFixed(4)},${j.position.lng!.toFixed(4)}`;
      groups.set(key, [...(groups.get(key) ?? []), j]);
    }
    const points: FeatureCollection = {
      type: "FeatureCollection",
      features: [...groups.values()].map((js) => {
        const j = js[0]!;
        const label = js.length > 1 ? `${js.map((x) => x.id).join(" / ")} · ${sharedLabel}` : `${j.id} ${j.name}`;
        return {
          type: "Feature", id: Number(j.id.slice(1)),
          geometry: { type: "Point", coordinates: [j.position.lng!, j.position.lat!] },
          properties: { id: j.id, name: j.name, colour: healthColour(Math.min(...js.map((x) => x.health.avg))), label },
        };
      }),
    };
    const corridor = ["J03", "J04", "J05", "J06", "J07"].map((id) => site.junctions.find((j) => j.id === id)!).filter((j) => j.position.lat != null);
    const line: Feature = { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: corridor.map((j) => [j.position.lng!, j.position.lat!]) } };

    m.on("load", () => {
      const src = Object.keys(m.getStyle().sources).find((s) => s.includes("openmaptiles")) ?? "openmaptiles";
      if (!m.getLayer("hb-buildings")) {
        m.addLayer({
          id: "hb-buildings", type: "fill-extrusion", source: src, "source-layer": "building", minzoom: 13,
          paint: {
            "fill-extrusion-color": dark ? "#3b2a33" : "#e8b4a6",
            "fill-extrusion-height": ["coalesce", ["get", "render_height"], 6],
            "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
            "fill-extrusion-opacity": 0.85,
          },
        });
      }
      m.addSource("hb-corridor", { type: "geojson", data: line });
      m.addLayer({ id: "hb-corridor-glow", type: "line", source: "hb-corridor", paint: { "line-color": "#e8998d", "line-width": 10, "line-opacity": 0.25, "line-blur": 4 } });
      m.addLayer({ id: "hb-corridor", type: "line", source: "hb-corridor", paint: { "line-color": "#e8998d", "line-width": 3, "line-dasharray": [0, 2, 2] } });
      m.addSource("hb-junctions", { type: "geojson", data: points });
      m.addLayer({ id: "hb-halo", type: "circle", source: "hb-junctions", paint: {
        "circle-radius": ["case", ["boolean", ["feature-state", "selected"], false], 22, 14],
        "circle-color": ["get", "colour"], "circle-opacity": 0.22, "circle-blur": 0.4 } });
      m.addLayer({ id: "hb-dot", type: "circle", source: "hb-junctions", paint: {
        "circle-radius": 7, "circle-color": ["get", "colour"], "circle-stroke-width": 2, "circle-stroke-color": dark ? "#0f1b2d" : "#ffffff" } });
      m.addLayer({ id: "hb-label", type: "symbol", source: "hb-junctions", layout: {
        "text-field": ["get", "label"], "text-size": 12, "text-offset": [0, 1.5], "text-anchor": "top", "text-font": ["Noto Sans Bold"] },
        paint: { "text-color": dark ? "#f6e7e2" : "#0f1b2d", "text-halo-color": dark ? "#0f1b2d" : "#ffffff", "text-halo-width": 1.5 } });
      m.on("click", "hb-dot", (e) => { const id = e.features?.[0]?.properties?.id; if (id) onSelect(String(id)); });
      m.on("mouseenter", "hb-dot", () => { m.getCanvas().style.cursor = "pointer"; });
      m.on("mouseleave", "hb-dot", () => { m.getCanvas().style.cursor = ""; });
      // flowing dashes along the corridor (illustrative motion, not vehicle tracks)
      const seq = [[0, 4, 3], [0.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1], [2.5, 4, 0.5], [3, 4, 0], [0, 0.5, 3, 3.5], [0, 1, 3, 3], [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1], [0, 3.5, 3, 0.5]];
      let step = 0;
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const tick = () => {
        if (!alive || reduced) return;
        step = (step + 1) % seq.length;
        if (m.getLayer("hb-corridor")) m.setPaintProperty("hb-corridor", "line-dasharray", seq[step]);
        setTimeout(() => requestAnimationFrame(tick), 70);
      };
      tick();
    });
    m.on("error", () => undefined);
    return () => { alive = false; map.current = null; m.remove(); };
  }, [dark, onSelect, sharedLabel]);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded() || !m.getSource("hb-junctions")) return;
    site.junctions.forEach((j) => m.setFeatureState({ source: "hb-junctions", id: Number(j.id.slice(1)) }, { selected: j.id === selected }));
    const j = site.junctions.find((x) => x.id === selected);
    if (j?.position.lat != null) m.easeTo({ center: [j.position.lng!, j.position.lat!], duration: 900, zoom: 15 });
  }, [selected]);

  if (failed) return null;
  return <div ref={box} className="h-full w-full" role="region" aria-label={ariaLabel} />;
}
