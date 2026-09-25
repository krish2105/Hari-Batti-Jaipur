"use client";
// Signal poles for the six corridor junctions: 3 emissive lamps + an LED dot-matrix countdown
// board drawn on a canvas, driven by the same PhaseState stream as the rest of the page.
import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PhaseState, SignalColour } from "@haribatti/core";
import { JUNCTION_X, ROAD_HALF, STOP_BACK } from "./layout";

const HEX: Record<SignalColour, string> = { RED: "#ff3b30", AMBER: "#ffb020", GREEN: "#22c55e", FLASHING_AMBER: "#ffb020" };
const LAMP_ORDER: SignalColour[] = ["RED", "AMBER", "GREEN"];

/** Draw 2 digits as a dot matrix (5x7 font) — the look of Jaipur's countdown timers. */
const FONT: Record<string, string[]> = {
  "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"], "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"], "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"], "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
  "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"], "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"], "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
};

function drawBoard(ctx: CanvasRenderingContext2D, text: string, colour: string) {
  const W = ctx.canvas.width, H = ctx.canvas.height;
  ctx.fillStyle = "#07090d";
  ctx.fillRect(0, 0, W, H);
  const cell = W / 13, r = cell * 0.36;
  const digits = text.padStart(2, "0").slice(-2).split("");
  digits.forEach((d, di) => {
    const rows = FONT[d] ?? FONT["8"]!;
    for (let y = 0; y < 7; y++) for (let x = 0; x < 5; x++) {
      const on = rows[y]![x] === "1";
      ctx.beginPath();
      ctx.arc(cell * (1 + di * 6 + x) + cell / 2, (H - cell * 7) / 2 + cell * y + cell / 2, r, 0, Math.PI * 2);
      ctx.fillStyle = on ? colour : "#1a1d24";
      ctx.fill();
    }
  });
}

function Pole({ x, z, facing, state }: { x: number; z: number; facing: number; state?: PhaseState }) {
  const canvas = useMemo(() => {
    if (typeof document === "undefined") return null;
    const c = document.createElement("canvas");
    c.width = 208; c.height = 128;
    return c;
  }, []);
  const tex = useMemo(() => {
    if (!canvas) return null;
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  }, [canvas]);
  const lamps = useRef<(THREE.MeshStandardMaterial | null)[]>([]);
  useEffect(() => {
    if (!canvas || !tex || !state) return;
    drawBoard(canvas.getContext("2d")!, String(Math.min(99, state.secondsRemaining)), HEX[state.colour]);
    tex.needsUpdate = true;
  }, [canvas, tex, state]);
  useFrame(({ clock }) => {
    const c = state?.colour ?? "RED";
    const blink = c === "FLASHING_AMBER" ? (Math.sin(clock.elapsedTime * 6) > 0 ? 1 : 0.1) : 1;
    LAMP_ORDER.forEach((lc, i) => {
      const mat = lamps.current[i];
      if (!mat) return;
      const on = lc === c || (lc === "AMBER" && c === "FLASHING_AMBER");
      mat.emissiveIntensity = on ? 4.5 * blink : 0.04;
    });
  });
  return (
    <group position={[x, 0, z]} rotation-y={facing}>
      <mesh position={[0, 1.7, 0]} castShadow>
        <cylinderGeometry args={[0.07, 0.09, 3.4, 8]} />
        <meshStandardMaterial color="#2c313a" metalness={0.6} roughness={0.4} />
      </mesh>
      <mesh position={[0, 3.3, 0.18]} castShadow>
        <boxGeometry args={[0.46, 1.25, 0.3]} />
        <meshStandardMaterial color="#14171c" roughness={0.6} />
      </mesh>
      {LAMP_ORDER.map((c, i) => (
        <mesh key={c} position={[0, 3.72 - i * 0.4, 0.34]}>
          <sphereGeometry args={[0.14, 16, 12]} />
          <meshStandardMaterial ref={(m) => { lamps.current[i] = m; }} color="#222" emissive={HEX[c]} emissiveIntensity={0.04} toneMapped={false} />
        </mesh>
      ))}
      {tex && (
        <mesh position={[0, 2.45, 0.34]}>
          <planeGeometry args={[0.66, 0.4]} />
          <meshBasicMaterial map={tex} toneMapped={false} />
        </mesh>
      )}
    </group>
  );
}

export function SignalPoles({ states }: { states: PhaseState[] }) {
  const byJunction = useMemo(() => {
    const m = new Map<string, PhaseState[]>();
    for (const s of states) m.set(s.junctionId, [...(m.get(s.junctionId) ?? []), s]);
    return m;
  }, [states]);
  return (
    <group>
      {Object.entries(JUNCTION_X).map(([id, x]) => {
        const s = byJunction.get(id) ?? [];
        const east = s.find((a) => a.approachId.endsWith("mansarover-metro")); // arriving from the west
        const west = s.find((a) => a.approachId.endsWith("sanganer-stadium")); // arriving from the east
        return (
          <group key={id}>
            {/* left-hand traffic: eastbound drives on the -z side, so its signal stands there */}
            <Pole x={x - STOP_BACK} z={-ROAD_HALF - 0.5} facing={-Math.PI / 2} state={east} />
            <Pole x={x + STOP_BACK} z={ROAD_HALF + 0.5} facing={Math.PI / 2} state={west} />
          </group>
        );
      })}
    </group>
  );
}
