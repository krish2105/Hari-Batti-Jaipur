// Shared 3D layout. 1 unit = 5 m. The corridor road runs along x: J08 (Mansarovar Metro end) in the
// west to J03 (Sanganer Stadium end) in the east, 100 units (500 m, assumed) apart.
export const UNIT_M = 5;
export const JUNCTION_X: Record<string, number> = { J08: -250, J07: -150, J06: -50, J05: 50, J04: 150, J03: 250 };
export const ROAD_HALF = 2.4; // main road: 3 lanes each way + median ≈ 24 m
export const CROSS_HALF = 1.5; // cross roads: 2 lanes each way ≈ 15 m
// India drives on the LEFT. Heading east (+x) your left is -z, so eastbound lanes sit at -z and
// westbound at +z. Heading south (+z) your left is +x, so southbound cross lanes sit at x > junction.
export const MAIN_LANES = [0.55, 1.2, 1.85]; // distance from the centre line
export const CROSS_LANES = [0.45, 1.05];
export const STOP_BACK = 3.2; // stop line distance from the junction centre
export const CITY_X = 330;
export const CITY_Z = 130;

// small deterministic random, so the city is the same on every visit
export function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const onRoad = (x: number, z: number, pad = 0) =>
  Math.abs(z) < ROAD_HALF + pad || Object.values(JUNCTION_X).some((jx) => Math.abs(x - jx) < CROSS_HALF + pad);
