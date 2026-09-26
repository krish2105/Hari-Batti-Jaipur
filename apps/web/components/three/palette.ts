"use client";
// One shared material for every Blender model (vehicles, buildings): base colour, roughness /
// metalness and a night-glow mask are three tiny palette textures with the same swatch layout.
import { useTexture } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

export function usePaletteMaterial(dark: boolean) {
  const [map, mr, em] = useTexture(["/models/palette.webp", "/models/palette_mr.webp", "/models/palette_em.webp"]) as [
    THREE.Texture, THREE.Texture, THREE.Texture,
  ];
  const mat = useMemo(() => {
    for (const [t, srgb] of [[map, true], [mr, false], [em, true]] as const) {
      t.flipY = false; // glTF UV convention
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.magFilter = THREE.NearestFilter;
      t.needsUpdate = true;
    }
    return new THREE.MeshStandardMaterial({ map, roughnessMap: mr, metalnessMap: mr, emissiveMap: em, emissive: new THREE.Color("#ffffff"), metalness: 1, roughness: 1 });
  }, [map, mr, em]);
  useEffect(() => {
    mat.emissiveIntensity = dark ? 1.25 : 0; // shops, lamps and headlamps glow at dusk
  }, [mat, dark]);
  return mat;
}

/** Merge all meshes of a glTF scene into one geometry, scaled from metres to scene units. */
export function mergeScene(scene: THREE.Object3D, metresPerUnit = 5, keep?: (m: THREE.Mesh) => boolean) {
  scene.updateMatrixWorld(true);
  const parts: THREE.BufferGeometry[] = [];
  const scale = new THREE.Matrix4().makeScale(1 / metresPerUnit, 1 / metresPerUnit, 1 / metresPerUnit);
  scene.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh || (keep && !keep(mesh))) return;
    const g = mesh.geometry.clone();
    g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(scale, mesh.matrixWorld));
    for (const k of Object.keys(g.attributes)) if (!["position", "normal", "uv"].includes(k)) g.deleteAttribute(k);
    parts.push(g);
  });
  return parts;
}
