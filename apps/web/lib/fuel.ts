// VT-Micro instantaneous fuel and CO2 model (Ahn, Rakha, Trani & Van Aerde, 2002), light-duty car
// coefficients. Inputs: speed km/h, acceleration km/h/s. Fuel in litres/s, CO2 in mg/s.
// Used for "fuel for a car making the same ride" in the green-wave demo — an estimate.
const FUEL_POS = [[-7.735, 0.2295, -5.61e-3, 9.77e-5], [0.02799, 0.0068, -7.72e-4, 8.38e-6], [-2.23e-4, -4.4e-5, 7.9e-7, 8.17e-7], [1.09e-6, 4.8e-8, 3.27e-8, -7.79e-9]];
const FUEL_NEG = [[-7.735, -0.01799, -4.27e-3, 1.88e-4], [0.02804, 7.72e-3, 8.38e-4, 3.39e-5], [-2.2e-4, -5.22e-5, -7.44e-6, 2.77e-7], [1.08e-6, 2.47e-7, 4.87e-8, 3.79e-10]];
const CO2_POS = [[6.916, 0.217, 2.35e-4, -3.64e-4], [0.02754, 9.68e-3, -1.75e-3, 8.35e-5], [-2.07e-4, -1.01e-4, 1.97e-5, -1.02e-6], [9.8e-7, 3.66e-7, -1.08e-7, 8.5e-9]];
const CO2_NEG = [[6.915, -0.032, -9.17e-3, -2.89e-4], [0.0284, 8.53e-3, 1.15e-3, -3.06e-6], [-2.27e-4, -6.59e-5, -1.29e-5, -2.68e-7], [1.11e-6, 3.2e-7, 7.56e-8, 2.95e-9]];

function moe(k: number[][], vKmh: number, aKmhS: number) {
  let p = 0;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) p += k[i]![j]! * vKmh ** i * aKmhS ** j;
  return Math.exp(p);
}

/** Fuel (litres per second) at speed v (km/h) and acceleration a (km/h per s). */
export const fuelRate = (vKmh: number, aKmhS: number) => moe(aKmhS > 0 ? FUEL_POS : FUEL_NEG, vKmh, aKmhS);
/** CO2 (grams per second). */
export const co2Rate = (vKmh: number, aKmhS: number) => moe(aKmhS > 0 ? CO2_POS : CO2_NEG, vKmh, aKmhS) / 1000;

/** Integrate over a trajectory of {t (s), v (m/s)} points. Returns litres and grams of CO2. */
export function tripFuel(track: { t: number; v: number }[]) {
  let litres = 0, co2g = 0;
  for (let i = 1; i < track.length; i++) {
    const a = track[i - 1]!, b = track[i]!;
    const dt = b.t - a.t;
    if (dt <= 0) continue;
    const v = ((a.v + b.v) / 2) * 3.6, acc = ((b.v - a.v) / dt) * 3.6;
    // VT-Micro is calibrated for about -5..+11 km/h/s; clamp to stay inside it
    const aa = Math.max(-5, Math.min(11, acc));
    litres += fuelRate(v, aa) * dt;
    co2g += co2Rate(v, aa) * dt;
  }
  return { litres, co2g };
}
