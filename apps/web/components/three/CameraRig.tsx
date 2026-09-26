"use client";
// Camera flies over the corridor as the page scrolls: one keyframe per section, eased between.
// With reduced motion it jumps between keyframes (no fly-through).
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { getProgress, subscribe } from "@/lib/scrollStore";
import { JUNCTION_X } from "./layout";

type Key = { pos: [number, number, number]; look: [number, number, number] };
const J05 = JUNCTION_X.J05!;
const KEYS: Key[] = [
  { pos: [J05 - 13, 1.9, -3.35], look: [J05 - 2, 2.4, -3.9] },          // 1 hero: on the footpath; signal right of centre
  { pos: [J05 - 26, 3.4, -1.2], look: [J05 - 4, 0.6, -1.2] },           // 2 the wait: along the eastbound queue
  { pos: [J05 - 8, 22, 12], look: [J05, 0, 0] },                        // 3 the squeeze: over the junction
  { pos: [J05 + 6, 1.6, 3.3], look: [J05 + 16, 0.5, 0.6] },            // 3b the mix: kerb level, traffic passing
  { pos: [0, 120, 90], look: [0, 0, 0] },                               // 4 map: rise high
  { pos: [220, 40, 70], look: [150, 0, 0] },                            // 5 ITMS: towards the east end
  { pos: [J05 + 18, 10, 22], look: [J05, 1, 0] },                       // 6 solution
  { pos: [JUNCTION_X.J03! + 20, 14, -26], look: [JUNCTION_X.J06!, 0, 0] }, // 7 green wave: along the row
  { pos: [JUNCTION_X.J06! - 16, 12, 16], look: [JUNCTION_X.J06!, 1.5, 0] }, // 8 AI: orbit a junction
  { pos: [-60, 55, 95], look: [0, 0, 0] },                              // 9 impact
  { pos: [0, 160, 230], look: [0, 10, -60] },                           // 10 pilot: whole skyline
];

export function CameraRig({ reduced }: { reduced: boolean }) {
  const { camera } = useThree();
  const target = useRef(getProgress());
  const look = useRef(new THREE.Vector3());
  const pos = useRef(new THREE.Vector3());
  useEffect(() => subscribe((p) => { target.current = p; }), []);
  useFrame(({ clock }, dt) => {
    const p = Math.min(KEYS.length - 1, Math.max(0, target.current - 0.5));
    const i = Math.floor(p), f = reduced ? 0 : p - i;
    const e = f * f * (3 - 2 * f); // smoothstep
    const a = KEYS[i]!, b = KEYS[Math.min(KEYS.length - 1, i + 1)]!;
    pos.current.set(...a.pos).lerp(new THREE.Vector3(...b.pos), e);
    const lk = new THREE.Vector3(...a.look).lerp(new THREE.Vector3(...b.look), e);
    if (!reduced) pos.current.y += Math.sin(clock.elapsedTime * 0.3) * 0.15; // gentle breathing
    const k = reduced ? 1 : 1 - Math.pow(0.02, dt);
    camera.position.lerp(pos.current, k);
    look.current.lerp(lk, k);
    camera.lookAt(look.current);
  });
  return null;
}
