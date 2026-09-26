// The Blender-made vehicle set (tools/blender) and how often each appears in the 3D traffic.
// Visual shares follow the survey mix (two-wheelers ≈ 49%, cars + autos ≈ 48%, the rest small);
// the split inside a survey class (e.g. hatchback vs sedan) is illustrative, not counted.
import manifest from "@/public/models/manifest.json";

export type ModelName =
  | "scooter" | "motorcycle" | "auto_rickshaw" | "e_rickshaw" | "hatchback" | "sedan" | "suv" | "city_bus"
  | "mini_bus" | "lcv_tempo" | "truck" | "tractor" | "bicycle" | "cycle_rickshaw" | "hand_cart";

type Info = { share: number; speed: number; gap: number; filters: boolean; tint?: string[] };
const U = 5; // metres per scene unit

// speed and gap in scene units (1 unit = 5 m): 2.4 u/s ≈ 43 km/h
const INFO: Record<ModelName, Info> = {
  scooter: { share: 0.29, speed: 2.4, gap: 0.12, filters: true },
  motorcycle: { share: 0.195, speed: 2.5, gap: 0.12, filters: true },
  hatchback: { share: 0.15, speed: 2.3, gap: 0.35, filters: false, tint: ["#ffffff", "#d9d9d9", "#9ec3ff", "#ffd0c8"] },
  sedan: { share: 0.1, speed: 2.3, gap: 0.35, filters: false, tint: ["#ffffff", "#ffffff", "#b8c7d9", "#e8d6b0", "#6d7580"] },
  suv: { share: 0.09, speed: 2.2, gap: 0.38, filters: false, tint: ["#ffffff", "#c9ccd1", "#3a3f47", "#c24a3a", "#2f4f7a"] },
  auto_rickshaw: { share: 0.12, speed: 1.9, gap: 0.25, filters: false },
  e_rickshaw: { share: 0.025, speed: 1.4, gap: 0.25, filters: false },
  lcv_tempo: { share: 0.007, speed: 1.9, gap: 0.4, filters: false },
  mini_bus: { share: 0.003, speed: 1.9, gap: 0.45, filters: false },
  tractor: { share: 0.002, speed: 1.2, gap: 0.45, filters: false },
  city_bus: { share: 0.003, speed: 1.8, gap: 0.5, filters: false },
  truck: { share: 0.007, speed: 1.7, gap: 0.5, filters: false },
  bicycle: { share: 0.004, speed: 0.9, gap: 0.12, filters: true },
  cycle_rickshaw: { share: 0.002, speed: 0.8, gap: 0.2, filters: false },
  hand_cart: { share: 0.002, speed: 0.35, gap: 0.2, filters: false },
};

type Dims = { length_m: number; width_m: number; height_m: number; triangles: number; triangles_lod1: number };
const DIMS = manifest.vehicles as unknown as Record<ModelName, Dims>;

export const MODEL_NAMES = Object.keys(INFO) as ModelName[];

export function modelSpec(name: ModelName) {
  const d = DIMS[name];
  const i = INFO[name];
  return { ...i, len: d.length_m / U, wid: d.width_m / U, height: d.height_m / U, dims: d };
}

/** Pick a model at random according to the visual shares. */
export function pickModel(r: number): ModelName {
  let acc = 0;
  const total = MODEL_NAMES.reduce((s, n) => s + INFO[n].share, 0);
  for (const n of MODEL_NAMES) {
    acc += INFO[n].share / total;
    if (r <= acc) return n;
  }
  return "scooter";
}

export const modelUrl = (name: ModelName, lod: 0 | 1 = 1) => `/models/vehicles/${name}${lod === 1 ? "_lod1" : ""}.glb`;
