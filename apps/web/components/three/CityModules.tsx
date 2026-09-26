"use client";
// Pink City street frontage from the Blender modules (tools/blender/hb_city.py): arcaded
// shopfronts and jharokha blocks line both sides of the corridor, chhatris on some roofs.
// Instanced (one draw call per module type). High-quality mode only.
import { useGLTF } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { CITY_X, CROSS_HALF, JUNCTION_X, ROAD_HALF, rng } from "./layout";
import { mergeScene, usePaletteMaterial } from "./palette";

const NAMES = ["bldg_arcade", "bldg_jharokha", "bldg_chhatri"] as const;
// footprint along the street (x) and depth (z), scene units (metres / 5)
const WIDTH = { bldg_arcade: 12 / 5, bldg_jharokha: 7 / 5 };
const DEPTH = { bldg_arcade: 9 / 5, bldg_jharokha: 8 / 5 };
export const FRONTAGE_DEPTH = 2.2; // scene units kept free of procedural blocks behind the footpath

type Placement = { x: number; z: number; ry: number };

function layoutFrontage() {
  const r = rng(90210);
  const out: Record<(typeof NAMES)[number], Placement[]> = { bldg_arcade: [], bldg_jharokha: [], bldg_chhatri: [] };
  for (const side of [-1, 1]) {
    let x = -CITY_X + 10;
    while (x < CITY_X - 10) {
      const kind = r() < 0.55 ? "bldg_arcade" : "bldg_jharokha";
      const w = WIDTH[kind];
      if (Object.values(JUNCTION_X).some((jx) => Math.abs(x + w / 2 - jx) < CROSS_HALF + w / 2 + 1.4)) {
        x += 1;
        continue;
      }
      const z = side * (ROAD_HALF + 1.9 + DEPTH[kind] / 2);
      // Blender's street side (-Y) is +Z in glTF: face the road
      out[kind].push({ x: x + w / 2, z, ry: side < 0 ? 0 : Math.PI });
      if (kind === "bldg_jharokha" && r() < 0.3) out.bldg_chhatri.push({ x: x + w / 2 + 0.2, z: z + side * 0.3, ry: 0 });
      x += w + (r() < 0.25 ? 0.6 + r() : 0.05);
    }
  }
  // the jharokha roof is 9.85 m high: chhatris stand on it
  return out;
}

export function CityModules({ dark }: { dark: boolean }) {
  const gltfs = useGLTF(NAMES.map((n) => `/models/city/${n}.glb`), "/draco/");
  const mat = usePaletteMaterial(dark);
  const geos = useMemo(() => NAMES.map((_, i) => mergeGeometries(mergeScene(gltfs[i]!.scene))!), [gltfs]);
  const places = useMemo(layoutFrontage, []);
  const refs = useRef<(THREE.InstancedMesh | null)[]>([]);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const s = new THREE.Vector3(1, 1, 1);
    NAMES.forEach((n, i) => {
      const mesh = refs.current[i];
      if (!mesh) return;
      places[n].forEach((p, k) => {
        const y = n === "bldg_chhatri" ? 9.85 / 5 : 0;
        m.compose(new THREE.Vector3(p.x, y, p.z), q.setFromEuler(new THREE.Euler(0, p.ry, 0)), s);
        mesh.setMatrixAt(k, m);
      });
      mesh.instanceMatrix.needsUpdate = true;
    });
  }, [places]);
  return (
    <group>
      {NAMES.map((n, i) => (
        <instancedMesh key={n} ref={(el) => { refs.current[i] = el; }} args={[geos[i], mat, Math.max(1, places[n].length)]} castShadow receiveShadow />
      ))}
    </group>
  );
}
