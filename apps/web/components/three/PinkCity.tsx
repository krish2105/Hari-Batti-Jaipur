"use client";
// Procedural low-poly Pink City: instanced blocks (one draw call), chhatri domes on some roofs,
// lit jharokha windows at dusk, a crenellated city wall and neem trees on the median.
// Original geometry — no copied models.
import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { CITY_X, CITY_Z, JUNCTION_X, ROAD_HALF, onRoad, rng } from "./layout";

const PALETTE = ["#e8998d", "#d98476", "#c1666b", "#eab3a4", "#d4907f", "#e3a38f", "#b85c5f", "#f0bfae"];

type Block = { x: number; z: number; w: number; d: number; h: number; c: THREE.Color };

function useCity(quality: "high" | "low", frontage: boolean) {
  return useMemo(() => {
    const r = rng(20260511);
    const step = quality === "high" ? 9 : 12;
    const blocks: Block[] = [];
    for (let x = -CITY_X; x <= CITY_X; x += step) {
      for (let z = -CITY_Z; z <= CITY_Z; z += step) {
        const w = 4 + r() * 3.5, d = 4 + r() * 3.5;
        const cx = x + (r() - 0.5) * 2, cz = z + (r() - 0.5) * 2;
        if (onRoad(cx, cz, Math.max(w, d) / 2 + 1.2)) continue;
        if (frontage && Math.abs(cz) < ROAD_HALF + 4.4 + Math.max(w, d) / 2) continue; // Blender frontage here
        if (r() < 0.08) continue; // parks and plots
        const near = Math.abs(cz) < 30 ? 1.4 : 1; // taller shops along the main road
        const h = (1.2 + r() * r() * 5.5) * near;
        blocks.push({ x: cx, z: cz, w, d, h, c: new THREE.Color(PALETTE[Math.floor(r() * PALETTE.length)]!).multiplyScalar(0.85 + r() * 0.25) });
      }
    }
    // windows on the faces that look at the main road
    const windows: { p: THREE.Vector3; ry: number }[] = [];
    for (const b of blocks) {
      if (Math.abs(b.z) > 45 || r() < 0.25) continue;
      const faceZ = b.z > 0 ? b.z - b.d / 2 - 0.02 : b.z + b.d / 2 + 0.02;
      const floors = Math.max(1, Math.floor(b.h / 1.1));
      const cols = Math.max(1, Math.floor(b.w / 1.4));
      for (let f = 0; f < floors; f++) for (let c = 0; c < cols; c++) {
        if (r() < 0.35) continue;
        windows.push({ p: new THREE.Vector3(b.x - b.w / 2 + 0.7 + c * 1.4, 0.7 + f * 1.1, faceZ), ry: b.z > 0 ? Math.PI : 0 });
      }
    }
    const domes = blocks.filter(() => r() < 0.14);
    return { blocks, windows, domes };
  }, [quality, frontage]);
}

export function PinkCity({ dark, quality, frontage = false }: { dark: boolean; quality: "high" | "low"; frontage?: boolean }) {
  const { blocks, windows, domes } = useCity(quality, frontage);
  const blockRef = useRef<THREE.InstancedMesh>(null);
  const winRef = useRef<THREE.InstancedMesh>(null);
  const domeRef = useRef<THREE.InstancedMesh>(null);
  const parapetRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const s = new THREE.Vector3();
    blocks.forEach((b, i) => {
      m.compose(new THREE.Vector3(b.x, b.h / 2, b.z), q, s.set(b.w, b.h, b.d));
      blockRef.current!.setMatrixAt(i, m);
      blockRef.current!.setColorAt(i, b.c);
      // parapet slab on the roof: the low wall around Jaipur flat roofs
      m.compose(new THREE.Vector3(b.x, b.h + 0.12, b.z), q, s.set(b.w + 0.25, 0.24, b.d + 0.25));
      parapetRef.current!.setMatrixAt(i, m);
      parapetRef.current!.setColorAt(i, b.c.clone().multiplyScalar(0.8));
    });
    blockRef.current!.instanceMatrix.needsUpdate = true;
    parapetRef.current!.instanceMatrix.needsUpdate = true;
    if (blockRef.current!.instanceColor) blockRef.current!.instanceColor.needsUpdate = true;
    if (parapetRef.current!.instanceColor) parapetRef.current!.instanceColor.needsUpdate = true;
    windows.forEach((w, i) => {
      m.compose(w.p, q.setFromEuler(new THREE.Euler(0, w.ry, 0)), s.set(0.55, 0.7, 1));
      winRef.current!.setMatrixAt(i, m);
    });
    winRef.current!.instanceMatrix.needsUpdate = true;
    domes.forEach((b, i) => {
      const rad = Math.min(b.w, b.d) * 0.22;
      m.compose(new THREE.Vector3(b.x + b.w * 0.2, b.h + 0.24, b.z - b.d * 0.2), new THREE.Quaternion(), s.set(rad, rad, rad));
      domeRef.current!.setMatrixAt(i, m);
    });
    domeRef.current!.instanceMatrix.needsUpdate = true;
  }, [blocks, windows, domes]);

  return (
    <group>
      <instancedMesh ref={blockRef} args={[undefined, undefined, blocks.length]} castShadow={quality === "high"} receiveShadow>
        <boxGeometry />
        <meshStandardMaterial roughness={0.92} metalness={0} />
      </instancedMesh>
      <instancedMesh ref={parapetRef} args={[undefined, undefined, blocks.length]}>
        <boxGeometry />
        <meshStandardMaterial roughness={0.95} />
      </instancedMesh>
      <instancedMesh ref={domeRef} args={[undefined, undefined, domes.length]} castShadow={quality === "high"}>
        <sphereGeometry args={[1, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#f3d3c6" roughness={0.8} />
      </instancedMesh>
      <instancedMesh ref={winRef} args={[undefined, undefined, windows.length]}>
        <planeGeometry />
        <meshStandardMaterial color={dark ? "#3a2a24" : "#7b4b44"} emissive={dark ? "#ffb35c" : "#000000"} emissiveIntensity={dark ? 1.6 : 0} toneMapped={!dark} />
      </instancedMesh>
      <CityWall />
      <Trees quality={quality} />
    </group>
  );
}

/** Crenellated wall on the far side, with merlons as one instanced mesh. */
function CityWall() {
  const ref = useRef<THREE.InstancedMesh>(null);
  const merlons = useMemo(() => {
    const out: number[] = [];
    for (let x = -CITY_X; x <= CITY_X; x += 2.4) if (!Object.values(JUNCTION_X).some((jx) => Math.abs(x - jx) < 3)) out.push(x);
    return out;
  }, []);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    merlons.forEach((x, i) => {
      m.makeTranslation(x, 5.1, -CITY_Z - 6);
      ref.current!.setMatrixAt(i, m);
    });
    ref.current!.instanceMatrix.needsUpdate = true;
  }, [merlons]);
  return (
    <group>
      <mesh position={[0, 2.25, -CITY_Z - 6]} receiveShadow>
        <boxGeometry args={[CITY_X * 2 + 10, 4.5, 2.2]} />
        <meshStandardMaterial color="#c9786f" roughness={0.95} />
      </mesh>
      <instancedMesh ref={ref} args={[undefined, undefined, merlons.length]}>
        <boxGeometry args={[1.3, 1.2, 2.2]} />
        <meshStandardMaterial color="#c9786f" roughness={0.95} />
      </instancedMesh>
    </group>
  );
}

/** Neem trees on the median and along the footpaths. */
function Trees({ quality }: { quality: "high" | "low" }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const trunk = useRef<THREE.InstancedMesh>(null);
  const pts = useMemo(() => {
    const r = rng(7);
    const out: [number, number, number][] = [];
    for (let x = -CITY_X; x <= CITY_X; x += quality === "high" ? 7 : 12) {
      if (Object.values(JUNCTION_X).some((jx) => Math.abs(x - jx) < 20)) continue; // keep sight lines to the signals clear
      out.push([x + r() * 2, 0, ROAD_HALF + 0.9], [x + r() * 2, 0, -ROAD_HALF - 0.9]);
    }
    return out;
  }, [quality]);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const r = rng(11);
    pts.forEach(([x, , z], i) => {
      const s = 0.8 + r() * 0.5;
      m.compose(new THREE.Vector3(x, 1.5 * s, z), new THREE.Quaternion(), new THREE.Vector3(s, s * 0.85, s));
      ref.current!.setMatrixAt(i, m);
      m.compose(new THREE.Vector3(x, 0.6, z), new THREE.Quaternion(), new THREE.Vector3(1, 1, 1));
      trunk.current!.setMatrixAt(i, m);
    });
    ref.current!.instanceMatrix.needsUpdate = true;
    trunk.current!.instanceMatrix.needsUpdate = true;
  }, [pts]);
  return (
    <group>
      <instancedMesh ref={ref} args={[undefined, undefined, pts.length]}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color="#5e7d4a" roughness={1} flatShading />
      </instancedMesh>
      <instancedMesh ref={trunk} args={[undefined, undefined, pts.length]}>
        <cylinderGeometry args={[0.08, 0.12, 1.2, 5]} />
        <meshStandardMaterial color="#6b4a3a" />
      </instancedMesh>
    </group>
  );
}
