"use client";
// Asphalt, lane dashes, zebra crossings and stop lines — instanced.
import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { CITY_X, CITY_Z, CROSS_HALF, JUNCTION_X, ROAD_HALF, STOP_BACK } from "./layout";

export function Roads({ dark }: { dark: boolean }) {
  const dash = useRef<THREE.InstancedMesh>(null);
  const zebra = useRef<THREE.InstancedMesh>(null);
  const marks = useMemo(() => {
    const d: [number, number, number, number][] = []; // x, z, sx, sz
    for (let x = -CITY_X; x < CITY_X; x += 3) {
      if (Object.values(JUNCTION_X).some((jx) => Math.abs(x - jx) < STOP_BACK + 1)) continue;
      for (const z of [0.88, 1.52, -0.88, -1.52]) d.push([x, z, 1.2, 0.08]);
    }
    const zb: [number, number, number, number][] = [];
    for (const jx of Object.values(JUNCTION_X)) {
      for (let z = -ROAD_HALF + 0.2; z < ROAD_HALF; z += 0.45) for (const s of [-1, 1]) zb.push([jx + s * (STOP_BACK - 0.7), z, 0.9, 0.22]);
      for (let x = -CROSS_HALF + 0.2; x < CROSS_HALF; x += 0.45) for (const s of [-1, 1]) zb.push([jx + x, s * (ROAD_HALF + 0.8), 0.22, 0.9]);
    }
    return { d, zb };
  }, []);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
    marks.d.forEach(([x, z, sx, sz], i) => {
      m.compose(new THREE.Vector3(x, 0.021, z), q, new THREE.Vector3(sx, sz, 1));
      dash.current!.setMatrixAt(i, m);
    });
    marks.zb.forEach(([x, z, sx, sz], i) => {
      m.compose(new THREE.Vector3(x, 0.022, z), q, new THREE.Vector3(sx, sz, 1));
      zebra.current!.setMatrixAt(i, m);
    });
    dash.current!.instanceMatrix.needsUpdate = true;
    zebra.current!.instanceMatrix.needsUpdate = true;
  }, [marks]);
  const asphalt = dark ? "#232833" : "#5b5f66";
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[CITY_X * 2 + 200, CITY_Z * 2 + 200]} />
        <meshStandardMaterial color={dark ? "#2a2427" : "#c9a38f"} roughness={1} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0]} receiveShadow>
        <planeGeometry args={[CITY_X * 2 + 60, ROAD_HALF * 2]} />
        <meshStandardMaterial color={asphalt} roughness={0.9} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.012, 0]}>
        <planeGeometry args={[CITY_X * 2 + 60, 0.35]} />
        <meshStandardMaterial color="#8a7b6c" roughness={1} />
      </mesh>
      {Object.values(JUNCTION_X).map((jx) => (
        <mesh key={jx} rotation-x={-Math.PI / 2} position={[jx, 0.006, 0]} receiveShadow>
          <planeGeometry args={[CROSS_HALF * 2, CITY_Z * 2 + 60]} />
          <meshStandardMaterial color={asphalt} roughness={0.9} />
        </mesh>
      ))}
      <instancedMesh ref={dash} args={[undefined, undefined, marks.d.length]}>
        <planeGeometry />
        <meshBasicMaterial color="#e8e2d6" transparent opacity={0.55} />
      </instancedMesh>
      <instancedMesh ref={zebra} args={[undefined, undefined, marks.zb.length]}>
        <planeGeometry />
        <meshBasicMaterial color="#f2eee6" transparent opacity={0.8} />
      </instancedMesh>
    </group>
  );
}
