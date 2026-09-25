"use client";
// Instanced traffic on the corridor: scooters, autos, cars and buses that stop at red and queue.
// Left-hand traffic. Two-wheelers filter between vehicles like real Jaipur traffic (they only
// follow a leader they would actually hit). Density follows the survey's hourly PCU profile for
// the current hour in India; the vehicle mix is illustrative (about half two-wheelers, as surveyed).
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { PhaseState, SignalColour } from "@haribatti/core";
import { CITY_X, CROSS_LANES, JUNCTION_X, MAIN_LANES, ROAD_HALF, STOP_BACK, rng } from "./layout";

type Kind = "scooter" | "auto" | "car" | "bus";
const SPEC: Record<Kind, { len: number; wid: number; v: number; share: number; gap: number }> = {
  scooter: { len: 0.38, wid: 0.15, v: 2.4, share: 0.48, gap: 0.12 },
  auto: { len: 0.55, wid: 0.28, v: 1.9, share: 0.14, gap: 0.3 },
  car: { len: 0.86, wid: 0.35, v: 2.3, share: 0.35, gap: 0.35 },
  bus: { len: 2.2, wid: 0.5, v: 1.8, share: 0.03, gap: 0.5 },
};
const KINDS = Object.keys(SPEC) as Kind[];
const CAR_COLOURS = ["#e9e6e1", "#b8b9bd", "#2f3440", "#8a1f24", "#1f4e79", "#d9d2c3", "#5b6168"];

type V = { kind: Kind; s: number; v: number; lat: number; colour: THREE.Color };
type Lane = {
  axis: "x" | "z"; dir: 1 | -1; offset: number; fixed: number; start: number; end: number;
  stops: { at: number; key: string }[]; vehicles: V[]; spawnAcc: number; rate: number;
};

function box(w: number, h: number, d: number, y: number, x = 0) {
  const g = new THREE.BoxGeometry(w, h, d);
  g.translate(x, y, 0);
  return g;
}
function geometryFor(kind: Kind) {
  const s = SPEC[kind];
  if (kind === "scooter") return mergeGeometries([box(s.len, 0.1, s.wid * 0.8, 0.09), box(0.1, 0.2, 0.12, 0.26, -0.03)])!;
  if (kind === "auto") return mergeGeometries([box(s.len, 0.22, s.wid, 0.15), box(s.len * 0.8, 0.08, s.wid * 1.02, 0.32, -0.03)])!;
  if (kind === "bus") return box(s.len, 0.55, s.wid, 0.32);
  return mergeGeometries([box(s.len, 0.16, s.wid, 0.12), box(s.len * 0.55, 0.13, s.wid * 0.92, 0.26, -0.04)])!;
}

function makeLanes(): Lane[] {
  const lanes: Lane[] = [];
  const xs = Object.entries(JUNCTION_X);
  for (const [i, off] of MAIN_LANES.entries()) {
    // eastbound (+x) on the -z side: stops before each junction, west of it; approach "Mansarover Metro"
    lanes.push({ axis: "x", dir: 1, offset: off, fixed: -off, start: -CITY_X - 20, end: CITY_X + 20, vehicles: [], spawnAcc: i * 0.3, rate: 0,
      stops: xs.map(([id, x]) => ({ at: x - STOP_BACK, key: `${id}:mansarover-metro` })).sort((a, b) => a.at - b.at) });
    lanes.push({ axis: "x", dir: -1, offset: off, fixed: off, start: CITY_X + 20, end: -CITY_X - 20, vehicles: [], spawnAcc: i * 0.5, rate: 0,
      stops: xs.map(([id, x]) => ({ at: x + STOP_BACK, key: `${id}:sanganer-stadium` })).sort((a, b) => b.at - a.at) });
  }
  for (const [id, x] of xs) {
    for (const off of CROSS_LANES) {
      lanes.push({ axis: "z", dir: 1, offset: off, fixed: x + off, start: -70, end: 70, vehicles: [], spawnAcc: 0, rate: 0,
        stops: [{ at: -ROAD_HALF - 0.7, key: `${id}:cross` }] });
      lanes.push({ axis: "z", dir: -1, offset: off, fixed: x - off, start: 70, end: -70, vehicles: [], spawnAcc: 0, rate: 0,
        stops: [{ at: ROAD_HALF + 0.7, key: `${id}:cross` }] });
    }
  }
  return lanes;
}

export function Vehicles({ states, density, quality, dark }: { states: PhaseState[]; density: number; quality: "high" | "low"; dark: boolean }) {
  const max = quality === "high" ? 520 : 200;
  const lanes = useMemo(makeLanes, []);
  const rand = useMemo(() => rng(42), []);
  const meshes = useRef<Partial<Record<Kind, THREE.InstancedMesh | null>>>({});
  const heads = useRef<THREE.InstancedMesh>(null);
  const tails = useRef<THREE.InstancedMesh>(null);
  const geoms = useMemo(() => Object.fromEntries(KINDS.map((k) => [k, geometryFor(k)])) as Record<Kind, THREE.BufferGeometry>, []);
  const colours = useRef(new Map<string, SignalColour>());

  // latest signal colour per stop key (main approaches, and one cross approach per junction)
  colours.current = useMemo(() => {
    const m = new Map<string, SignalColour>();
    for (const s of states) {
      const tail = s.approachId.slice(4);
      if (tail === "mansarover-metro" || tail === "sanganer-stadium") m.set(`${s.junctionId}:${tail}`, s.colour);
      else if (!m.has(`${s.junctionId}:cross`)) m.set(`${s.junctionId}:cross`, s.colour);
    }
    return m;
  }, [states]);

  // start with traffic already on the road (otherwise the first minute is empty)
  const seeded = useRef(false);
  if (!seeded.current) {
    seeded.current = true;
    for (const lane of lanes) {
      const n = Math.round((lane.axis === "x" ? 34 : 3) * density * (max / 520));
      for (let i = 0; i < n; i++) {
        const r = rand();
        let acc = 0;
        const kind = KINDS.find((k) => (acc += SPEC[k].share) >= r) ?? "car";
        const s = lane.start + (lane.end - lane.start) * (1 - (i + rand() * 0.5) / Math.max(1, n));
        lane.vehicles.push({ kind, s, v: SPEC[kind].v * 0.8, lat: kind === "scooter" ? (rand() - 0.5) * 0.45 : 0,
          colour: new THREE.Color(kind === "auto" ? "#2f8f4e" : kind === "bus" ? "#b8452f" : CAR_COLOURS[Math.floor(rand() * CAR_COLOURS.length)]!) });
      }
      lane.vehicles.sort((a, b) => (b.s - a.s) * lane.dir); // front first
    }
  }

  const tmp = useMemo(() => ({ m: new THREE.Matrix4(), q: new THREE.Quaternion(), p: new THREE.Vector3(), sc: new THREE.Vector3(1, 1, 1), e: new THREE.Euler() }), []);

  useFrame((_, rawDt) => {
    const dt = Math.min(0.05, rawDt);
    const total = lanes.reduce((n, l) => n + l.vehicles.length, 0);
    const counts: Record<Kind, number> = { scooter: 0, auto: 0, car: 0, bus: 0 };
    let lights = 0;
    for (const lane of lanes) {
      // spawning: main lanes carry most traffic (66-90% on the main road in the survey)
      lane.rate = (lane.axis === "x" ? 1.6 : 0.22) * density;
      lane.spawnAcc += lane.rate * dt;
      const last = lane.vehicles[lane.vehicles.length - 1];
      if (lane.spawnAcc >= 1 && total < max && (!last || Math.abs(last.s - lane.start) > 1.4)) {
        lane.spawnAcc = 0;
        const r = rand();
        let acc = 0;
        const kind = KINDS.find((k) => (acc += SPEC[k].share) >= r) ?? "car";
        const colour = new THREE.Color(kind === "auto" ? "#2f8f4e" : kind === "bus" ? "#b8452f" : kind === "scooter" ? ["#1d1f24", "#8a1f24", "#1f4e79", "#c9c3b8"][Math.floor(rand() * 4)]! : CAR_COLOURS[Math.floor(rand() * CAR_COLOURS.length)]!);
        lane.vehicles.push({ kind, s: lane.start, v: SPEC[kind].v * 0.8, lat: kind === "scooter" ? (rand() - 0.5) * 0.45 : (rand() - 0.5) * 0.08, colour });
      }
      // move: front vehicle first
      const vs = lane.vehicles;
      for (let i = 0; i < vs.length; i++) {
        const me = vs[i]!;
        const spec = SPEC[me.kind];
        let gap = Infinity;
        for (let j = i - 1; j >= 0; j--) {
          const o = vs[j]!;
          if (me.kind === "scooter" && Math.abs(o.lat - me.lat) > (SPEC[o.kind].wid + spec.wid) / 2 + 0.02) continue; // filters past
          gap = Math.min(gap, (o.s - me.s) * lane.dir - (SPEC[o.kind].len + spec.len) / 2);
          break;
        }
        const nextStop = lane.stops.find((st) => (st.at - me.s) * lane.dir > spec.len / 2 - 0.05);
        if (nextStop) {
          const c = colours.current.get(nextStop.key) ?? "RED";
          const d = (nextStop.at - me.s) * lane.dir - spec.len / 2;
          const canStop = d > (me.v * me.v) / (2 * 3.5) - 0.05;
          if (c !== "GREEN" && (c === "RED" || canStop)) gap = Math.min(gap, d + spec.gap);
        }
        const target = Math.max(0, Math.min(spec.v, (gap - spec.gap) / 0.9));
        me.v += Math.max(-4 * dt, Math.min(1.6 * dt, target - me.v));
        if (gap - spec.gap < 0.02) me.v = Math.min(me.v, 0);
        me.s += me.v * dt * lane.dir;
      }
      lane.vehicles = vs.filter((v) => (lane.end - v.s) * lane.dir > 0);
      // draw
      for (const v of lane.vehicles) {
        const mesh = meshes.current[v.kind];
        if (!mesh || counts[v.kind] >= mesh.count) continue;
        const along = v.s, across = lane.fixed + (lane.axis === "x" ? v.lat * -lane.dir : v.lat);
        tmp.p.set(lane.axis === "x" ? along : across, 0, lane.axis === "x" ? across : along);
        tmp.e.set(0, lane.axis === "x" ? (lane.dir === 1 ? 0 : Math.PI) : (lane.dir === 1 ? -Math.PI / 2 : Math.PI / 2), 0);
        tmp.m.compose(tmp.p, tmp.q.setFromEuler(tmp.e), tmp.sc);
        mesh.setMatrixAt(counts[v.kind], tmp.m);
        mesh.setColorAt(counts[v.kind], v.colour);
        counts[v.kind]++;
        // head and tail lights: small emissive quads at the front and back
        if (heads.current && tails.current && lights < heads.current.count) {
          const half = SPEC[v.kind].len / 2;
          const fx = lane.axis === "x" ? lane.dir : 0, fz = lane.axis === "z" ? lane.dir : 0;
          tmp.m.compose(tmp.p.clone().add(new THREE.Vector3(fx * half, 0.13, fz * half)), tmp.q, tmp.sc);
          heads.current.setMatrixAt(lights, tmp.m);
          tmp.m.compose(tmp.p.clone().add(new THREE.Vector3(-fx * half, 0.13, -fz * half)), tmp.q, tmp.sc);
          tails.current.setMatrixAt(lights, tmp.m);
          lights++;
        }
      }
    }
    for (const k of KINDS) {
      const mesh = meshes.current[k];
      if (!mesh) continue;
      for (let i = counts[k]; i < mesh.count; i++) {
        tmp.m.makeScale(0, 0, 0);
        mesh.setMatrixAt(i, tmp.m);
      }
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
    for (const lm of [heads.current, tails.current]) {
      if (!lm) continue;
      for (let i = lights; i < lm.count; i++) {
        tmp.m.makeScale(0, 0, 0);
        lm.setMatrixAt(i, tmp.m);
      }
      lm.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group>
      {KINDS.map((k) => (
        <instancedMesh key={k} ref={(m) => { meshes.current[k] = m; }} args={[geoms[k], undefined, Math.ceil(max * (k === "bus" ? 0.08 : SPEC[k].share + 0.15))]} castShadow={quality === "high"}>
          <meshStandardMaterial roughness={0.55} metalness={0.15} />
        </instancedMesh>
      ))}
      <instancedMesh ref={heads} args={[undefined, undefined, max]}>
        <boxGeometry args={[0.04, 0.05, 0.16]} />
        <meshBasicMaterial color={dark ? [4, 3.4, 2.4] : [1.4, 1.3, 1.1]} toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={tails} args={[undefined, undefined, max]}>
        <boxGeometry args={[0.04, 0.05, 0.16]} />
        <meshBasicMaterial color={dark ? [3.2, 0.25, 0.2] : [1.2, 0.15, 0.1]} toneMapped={false} />
      </instancedMesh>
    </group>
  );
}
