"use client";
// The one 3D canvas behind the scroll story. Loaded client-side only (next/dynamic, no SSR).
// Quality: "low" on weak devices (few cores, low FPS) — no bloom or shadows, fewer vehicles, lower DPR.
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { PerformanceMonitor } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useEffect, useMemo, useState } from "react";
import type { PhaseState } from "@haribatti/core";
import { CameraRig } from "./CameraRig";
import { PinkCity } from "./PinkCity";
import { CityModules } from "./CityModules";
import { Roads } from "./Roads";
import { SignalPoles } from "./SignalPoles";
import { Vehicles } from "./Vehicles";

export type Quality = "high" | "low";

export default function Scene({ states, dark, density, onQuality }: { states: PhaseState[]; dark: boolean; density: number; onQuality?: (q: Quality) => void }) {
  const [quality, setQuality] = useState<Quality>("high");
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const weak = (navigator.hardwareConcurrency ?? 8) < 6 || window.matchMedia("(max-width: 640px)").matches;
    if (weak) setQuality("low");
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);
  useEffect(() => onQuality?.(quality), [quality, onQuality]);
  const sky = dark ? "#0f1b2d" : "#f3cdbf";
  const fog = useMemo(() => (dark ? { color: "#101d31", near: 60, far: 420 } : { color: "#f2d4c8", near: 80, far: 520 }), [dark]);

  return (
    <Canvas
      shadows={quality === "high"}
      dpr={quality === "high" ? [1, 1.75] : [0.75, 1]}
      camera={{ fov: 42, near: 0.1, far: 1200, position: [30, 6, -14] }}
      gl={{ antialias: quality === "high", powerPreference: "high-performance" }}
      aria-hidden
    >
      <PerformanceMonitor onDecline={() => setQuality("low")} flipflops={2} />
      <color attach="background" args={[sky]} />
      <fog attach="fog" args={[fog.color, fog.near, fog.far]} />
      <hemisphereLight args={[dark ? "#4d5f86" : "#ffe7d6", dark ? "#2a1b1f" : "#b98370", dark ? 0.55 : 1.1]} />
      <directionalLight
        position={dark ? [-120, 60, -80] : [80, 140, 60]}
        intensity={dark ? 0.9 : 2.4}
        color={dark ? "#ff9f7a" : "#fff1dc"}
        castShadow={quality === "high"}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-120}
        shadow-camera-right={120}
        shadow-camera-top={120}
        shadow-camera-bottom={-120}
      />
      <PinkCity dark={dark} quality={quality} frontage={quality === "high"} />
      {quality === "high" && (
        <Suspense fallback={null}>
          <CityModules dark={dark} />
        </Suspense>
      )}
      <Roads dark={dark} />
      <SignalPoles states={states} />
      <Vehicles states={states} density={density} quality={quality} dark={dark} />
      <CameraRig reduced={reduced} />
      {quality === "high" && (
        <EffectComposer multisampling={0}>
          <Bloom mipmapBlur luminanceThreshold={1} intensity={dark ? 1.1 : 0.6} radius={0.7} />
        </EffectComposer>
      )}
    </Canvas>
  );
}
