"use client";
// Interactive viewer for one Blender vehicle model (full-detail LOD0): studio light, soft shadow,
// slow turntable; drag to orbit. Uses the shared palette material.
import { Canvas } from "@react-three/fiber";
import { ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useMemo } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { modelSpec, modelUrl, type ModelName } from "@/lib/vehicleModels";
import { mergeScene, usePaletteMaterial } from "./palette";

function Model({ name, dark }: { name: ModelName; dark: boolean }) {
  const gltf = useGLTF(modelUrl(name, 0), "/draco/");
  const mat = usePaletteMaterial(dark);
  const brakeMat = useMemo(() => new THREE.MeshStandardMaterial({ color: "#8a0a08", emissive: "#ff2a1a", emissiveIntensity: dark ? 1.4 : 0.4 }), [dark]);
  const { body, brake } = useMemo(() => {
    const b = mergeScene(gltf.scene, 1, (m) => (Array.isArray(m.material) ? m.material[0] : m.material)?.name !== "brake");
    const k = mergeScene(gltf.scene, 1, (m) => (Array.isArray(m.material) ? m.material[0] : m.material)?.name === "brake");
    return { body: mergeGeometries(b)!, brake: k.length ? mergeGeometries(k) : null };
  }, [gltf]);
  const s = modelSpec(name);
  const scale = 3.2 / Math.max(s.dims.length_m, s.dims.height_m * 1.4); // fit big and small vehicles alike
  return (
    <group scale={scale}>
      <mesh geometry={body} material={mat} castShadow />
      {brake && <mesh geometry={brake} material={brakeMat} />}
    </group>
  );
}

export default function ModelViewer({ model, dark }: { model: ModelName; dark: boolean }) {
  const s = modelSpec(model);
  const scale = 3.2 / Math.max(s.dims.length_m, s.dims.height_m * 1.4);
  const centreY = (s.dims.height_m * scale) / 2;
  return (
    <Canvas shadows dpr={[1, 1.75]} camera={{ position: [4.8, 2.3, 4.6], fov: 30 }} aria-label={model}>
      <color attach="background" args={[dark ? "#121f33" : "#f4d9cf"]} />
      <ambientLight intensity={dark ? 0.35 : 0.6} />
      <directionalLight position={[4, 6, 3]} intensity={dark ? 1.6 : 2.4} castShadow />
      <Suspense fallback={null}>
        {/* studio reflections built in the browser (no HDR download) */}
        <Environment resolution={128} environmentIntensity={dark ? 0.6 : 0.9}>
          <Lightformer form="rect" intensity={dark ? 1.5 : 3} position={[0, 4, 2]} scale={[8, 2, 1]} />
          <Lightformer form="rect" intensity={dark ? 1 : 2} position={[-5, 1.5, -1]} rotation-y={Math.PI / 2} scale={[6, 2, 1]} />
          <Lightformer form="ring" color={dark ? "#ff9f7a" : "#ffe7d6"} intensity={dark ? 2 : 1.5} position={[5, 2, 0]} rotation-y={-Math.PI / 2} scale={3} />
        </Environment>
        <Model name={model} dark={dark} />
        <ContactShadows position={[0, 0, 0]} opacity={0.45} scale={8} blur={2.4} far={3} />
      </Suspense>
      <OrbitControls key={model} autoRotate autoRotateSpeed={0.9} enablePan={false} minDistance={3} maxDistance={10} maxPolarAngle={Math.PI / 2.1} target={[0, centreY, 0]} />
    </Canvas>
  );
}
