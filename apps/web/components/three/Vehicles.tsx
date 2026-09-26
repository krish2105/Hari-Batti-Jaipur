"use client";
// Instanced traffic on the corridor using the Blender-made vehicle set (tools/blender): scooters,
// motorcycles, autos, e-rickshaws, cars, buses, trucks, tractors, bicycles, cycle rickshaws and
// hand carts. One instanced mesh per model (plus one for its brake lamps), so the whole city is a
// few dozen draw calls. Left-hand traffic; two-wheelers filter between vehicles (they only follow
// a leader they would actually hit); vehicles stop at red and queue; brake lamps light when slowing.
// Density follows the survey's hourly PCU profile for the current hour in India. Low-power mode
// keeps simple boxes (no model download).
import { Suspense, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { PhaseState, SignalColour } from "@haribatti/core";
import { MODEL_NAMES, modelSpec, modelUrl, pickModel, type ModelName } from "@/lib/vehicleModels";
import { CITY_X, CROSS_LANES, JUNCTION_X, MAIN_LANES, ROAD_HALF, STOP_BACK, rng } from "./layout";
import { usePaletteMaterial } from "./palette";

const DRACO = "/draco/";
const M_PER_UNIT = 5;

type Geo = { body: THREE.BufferGeometry; brake: THREE.BufferGeometry | null; material: THREE.Material | null };
type V = { model: ModelName; s: number; v: number; lat: number; colour: THREE.Color; braking: number };
type Lane = { axis: "x" | "z"; dir: 1 | -1; fixed: number; start: number; end: number; stops: { at: number; key: string }[]; vehicles: V[]; spawnAcc: number };

function makeLanes(): Lane[] {
  const lanes: Lane[] = [];
  const xs = Object.entries(JUNCTION_X);
  for (const [i, off] of MAIN_LANES.entries()) {
    lanes.push({ axis: "x", dir: 1, fixed: -off, start: -CITY_X - 20, end: CITY_X + 20, vehicles: [], spawnAcc: i * 0.3,
      stops: xs.map(([id, x]) => ({ at: x - STOP_BACK, key: `${id}:mansarover-metro` })).sort((a, b) => a.at - b.at) });
    lanes.push({ axis: "x", dir: -1, fixed: off, start: CITY_X + 20, end: -CITY_X - 20, vehicles: [], spawnAcc: i * 0.5,
      stops: xs.map(([id, x]) => ({ at: x + STOP_BACK, key: `${id}:sanganer-stadium` })).sort((a, b) => b.at - a.at) });
  }
  for (const [id, x] of xs) {
    for (const off of CROSS_LANES) {
      lanes.push({ axis: "z", dir: 1, fixed: x + off, start: -70, end: 70, vehicles: [], spawnAcc: 0, stops: [{ at: -ROAD_HALF - 0.7, key: `${id}:cross` }] });
      lanes.push({ axis: "z", dir: -1, fixed: x - off, start: 70, end: -70, vehicles: [], spawnAcc: 0, stops: [{ at: ROAD_HALF + 0.7, key: `${id}:cross` }] });
    }
  }
  return lanes;
}

/** Box stand-ins sized from the real model dimensions (low-power mode and while models load). */
function boxGeometries(): Record<ModelName, Geo> {
  return Object.fromEntries(MODEL_NAMES.map((n) => {
    const s = modelSpec(n);
    const g = new THREE.BoxGeometry(s.len, s.height * 0.8, s.wid * 0.85);
    g.translate(0, s.height * 0.4, 0);
    return [n, { body: g, brake: null, material: null }];
  })) as unknown as Record<ModelName, Geo>;
}

/** Merge every mesh of a GLB into one body geometry + one brake-lamp geometry (scene units). */
function mergeGltf(scene: THREE.Object3D): Geo {
  scene.updateMatrixWorld(true);
  const body: THREE.BufferGeometry[] = [];
  const brake: THREE.BufferGeometry[] = [];
  let material: THREE.Material | null = null;
  const scale = new THREE.Matrix4().makeScale(1 / M_PER_UNIT, 1 / M_PER_UNIT, 1 / M_PER_UNIT);
  scene.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mat = Array.isArray(mesh.material) ? mesh.material[0]! : mesh.material;
    const g = mesh.geometry.clone();
    g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(scale, mesh.matrixWorld));
    for (const k of Object.keys(g.attributes)) if (!["position", "normal", "uv"].includes(k)) g.deleteAttribute(k);
    if (mat.name === "brake") brake.push(g);
    else {
      body.push(g);
      material ??= mat;
    }
  });
  return { body: mergeGeometries(body)!, brake: brake.length ? mergeGeometries(brake) : null, material };
}

function useModelGeometries(): Record<ModelName, Geo> {
  const gltfs = useGLTF(MODEL_NAMES.map((n) => modelUrl(n, 1)), DRACO);
  return useMemo(() => {
    const out = {} as Record<ModelName, Geo>;
    MODEL_NAMES.forEach((n, i) => { out[n] = mergeGltf(gltfs[i]!.scene); });
    // every model shares the first model's palette material (one texture upload for all)
    const shared = out[MODEL_NAMES[0]!].material;
    for (const n of MODEL_NAMES) out[n].material = shared;
    return out;
  }, [gltfs]);
}

export function Vehicles(props: { states: PhaseState[]; density: number; quality: "high" | "low"; dark: boolean }) {
  const boxes = useMemo(boxGeometries, []);
  if (props.quality === "low") return <Traffic {...props} geos={boxes} />;
  return (
    <Suspense fallback={<Traffic {...props} geos={boxes} />}>
      <ModelTraffic {...props} />
    </Suspense>
  );
}

function ModelTraffic(props: { states: PhaseState[]; density: number; quality: "high" | "low"; dark: boolean }) {
  const loaded = useModelGeometries();
  const mat = usePaletteMaterial(props.dark);
  const geos = useMemo(() => Object.fromEntries(Object.entries(loaded).map(([k, g]) => [k, { ...g, material: mat }])) as unknown as Record<ModelName, Geo>, [loaded, mat]);
  return <Traffic {...props} geos={geos} />;
}

function Traffic({ states, density, quality, dark, geos }: { states: PhaseState[]; density: number; quality: "high" | "low"; dark: boolean; geos: Record<ModelName, Geo> }) {
  const max = quality === "high" ? 560 : 220;
  const lanes = useMemo(makeLanes, []);
  const rand = useMemo(() => rng(42), []);
  const bodies = useRef<Partial<Record<ModelName, THREE.InstancedMesh | null>>>({});
  const brakes = useRef<Partial<Record<ModelName, THREE.InstancedMesh | null>>>({});
  const heads = useRef<THREE.InstancedMesh>(null);
  const colours = useRef(new Map<string, SignalColour>());
  const fallbackMat = useMemo(() => new THREE.MeshStandardMaterial({ color: "#c9c3b8", roughness: 0.55 }), []);
  const brakeMat = useMemo(() => new THREE.MeshBasicMaterial({ color: "#ffffff", toneMapped: false }), []);

  colours.current = useMemo(() => {
    const m = new Map<string, SignalColour>();
    for (const s of states) {
      const tail = s.approachId.slice(4);
      if (tail === "mansarover-metro" || tail === "sanganer-stadium") m.set(`${s.junctionId}:${tail}`, s.colour);
      else if (!m.has(`${s.junctionId}:cross`)) m.set(`${s.junctionId}:cross`, s.colour);
    }
    return m;
  }, [states]);

  const newVehicle = (lane: Lane, s: number): V => {
    const model = pickModel(rand());
    const sp = modelSpec(model);
    const tint = sp.tint ? sp.tint[Math.floor(rand() * sp.tint.length)]! : "#ffffff";
    return { model, s, v: sp.speed * 0.8, lat: sp.filters ? (rand() - 0.5) * 0.45 : (rand() - 0.5) * 0.06, colour: new THREE.Color(tint), braking: 0 };
  };

  // start with traffic already on the road
  const seeded = useRef(false);
  if (!seeded.current) {
    seeded.current = true;
    for (const lane of lanes) {
      const n = Math.round((lane.axis === "x" ? 32 : 3) * density * (max / 560));
      for (let i = 0; i < n; i++) lane.vehicles.push(newVehicle(lane, lane.start + (lane.end - lane.start) * (1 - (i + rand() * 0.5) / Math.max(1, n))));
      lane.vehicles.sort((a, b) => (b.s - a.s) * lane.dir);
    }
  }

  const tmp = useMemo(() => ({ m: new THREE.Matrix4(), q: new THREE.Quaternion(), p: new THREE.Vector3(), sc: new THREE.Vector3(1, 1, 1), e: new THREE.Euler(), c: new THREE.Color() }), []);

  useFrame((_, rawDt) => {
    const dt = Math.min(0.05, rawDt);
    const total = lanes.reduce((n, l) => n + l.vehicles.length, 0);
    const counts = Object.fromEntries(MODEL_NAMES.map((n) => [n, 0])) as Record<ModelName, number>;
    let lights = 0;
    for (const lane of lanes) {
      lane.spawnAcc += (lane.axis === "x" ? 1.6 : 0.22) * density * dt;
      const last = lane.vehicles[lane.vehicles.length - 1];
      if (lane.spawnAcc >= 1 && total < max && (!last || Math.abs(last.s - lane.start) > 1.6)) {
        lane.spawnAcc = 0;
        lane.vehicles.push(newVehicle(lane, lane.start));
      }
      const vs = lane.vehicles;
      for (let i = 0; i < vs.length; i++) {
        const me = vs[i]!;
        const spec = modelSpec(me.model);
        let gap = Infinity;
        for (let j = i - 1; j >= 0; j--) {
          const o = vs[j]!;
          const os = modelSpec(o.model);
          if (spec.filters && Math.abs(o.lat - me.lat) > (os.wid + spec.wid) / 2 + 0.02) continue; // filters past
          gap = Math.min(gap, (o.s - me.s) * lane.dir - (os.len + spec.len) / 2);
          break;
        }
        const nextStop = lane.stops.find((st) => (st.at - me.s) * lane.dir > spec.len / 2 - 0.05);
        if (nextStop) {
          const c = colours.current.get(nextStop.key) ?? "RED";
          const d = (nextStop.at - me.s) * lane.dir - spec.len / 2;
          const canStop = d > (me.v * me.v) / (2 * 3.5) - 0.05;
          if (c !== "GREEN" && (c === "RED" || canStop)) gap = Math.min(gap, d + spec.gap);
        }
        const target = Math.max(0, Math.min(spec.speed, (gap - spec.gap) / 0.9));
        const dv = Math.max(-4 * dt, Math.min(1.6 * dt, target - me.v));
        me.braking = dv < -0.02 || me.v < 0.05 ? 1 : Math.max(0, me.braking - dt * 3);
        me.v += dv;
        if (gap - spec.gap < 0.02) me.v = Math.min(me.v, 0);
        me.s += me.v * dt * lane.dir;
      }
      lane.vehicles = vs.filter((v) => (lane.end - v.s) * lane.dir > 0);
      for (const v of lane.vehicles) {
        const mesh = bodies.current[v.model];
        if (!mesh || counts[v.model] >= mesh.count) continue;
        const spec = modelSpec(v.model);
        const across = lane.fixed + (lane.axis === "x" ? v.lat * -lane.dir : v.lat);
        tmp.p.set(lane.axis === "x" ? v.s : across, 0, lane.axis === "x" ? across : v.s);
        tmp.e.set(0, lane.axis === "x" ? (lane.dir === 1 ? 0 : Math.PI) : lane.dir === 1 ? -Math.PI / 2 : Math.PI / 2, 0);
        tmp.m.compose(tmp.p, tmp.q.setFromEuler(tmp.e), tmp.sc);
        const k = counts[v.model]++;
        mesh.setMatrixAt(k, tmp.m);
        mesh.setColorAt(k, v.colour);
        const bm = brakes.current[v.model];
        if (bm) {
          bm.setMatrixAt(k, tmp.m);
          const glow = dark ? 0.9 + v.braking * 3.2 : 0.7 + v.braking * 1.6;
          bm.setColorAt(k, tmp.c.setRGB(glow, glow * 0.06, glow * 0.04));
        }
        if (heads.current && dark && lights < heads.current.count && spec.len > 0.3) {
          const half = spec.len / 2;
          const fx = lane.axis === "x" ? lane.dir : 0, fz = lane.axis === "z" ? lane.dir : 0;
          tmp.m.compose(tmp.p.clone().add(new THREE.Vector3(fx * half, 0.13, fz * half)), tmp.q, tmp.sc);
          heads.current.setMatrixAt(lights++, tmp.m);
        }
      }
    }
    for (const n of MODEL_NAMES) {
      for (const mesh of [bodies.current[n], brakes.current[n]]) {
        if (!mesh) continue;
        for (let i = counts[n]; i < mesh.count; i++) {
          tmp.m.makeScale(0, 0, 0);
          mesh.setMatrixAt(i, tmp.m);
        }
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      }
    }
    if (heads.current) {
      for (let i = lights; i < heads.current.count; i++) {
        tmp.m.makeScale(0, 0, 0);
        heads.current.setMatrixAt(i, tmp.m);
      }
      heads.current.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group>
      {MODEL_NAMES.map((n) => {
        const g = geos[n];
        const cap = Math.max(4, Math.ceil(max * Math.min(0.4, modelSpec(n).share + 0.04)));
        return (
          <group key={n}>
            <instancedMesh ref={(m) => { bodies.current[n] = m; }} args={[g.body, g.material ?? fallbackMat, cap]} castShadow={quality === "high"} frustumCulled={false} />
            {g.brake && <instancedMesh ref={(m) => { brakes.current[n] = m; }} args={[g.brake, brakeMat, cap]} frustumCulled={false} />}
          </group>
        );
      })}
      <instancedMesh ref={heads} args={[undefined, undefined, max]} frustumCulled={false}>
        <boxGeometry args={[0.03, 0.04, 0.12]} />
        <meshBasicMaterial color={[4, 3.4, 2.4]} toneMapped={false} />
      </instancedMesh>
    </group>
  );
}
