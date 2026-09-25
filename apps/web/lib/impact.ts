// Impact calculator formulas (shown on the page). Results are estimates, not measurements.
export const CO2_KG_PER_LITRE = 2.31; // kg CO2 per litre of petrol
export const DEFAULT_IDLE_L_PER_H = 0.6; // car idling, editable assumption
export const DEFAULT_PETROL_INR = 104.7; // ₹ per litre, Jaipur, editable assumption

export type ImpactInput = { junctions: number; vehiclesPerJunction: number; secondsSaved: number; idleLitresPerHour?: number; petrolInr?: number };

export function impact({ junctions, vehiclesPerJunction, secondsSaved, idleLitresPerHour = DEFAULT_IDLE_L_PER_H, petrolInr = DEFAULT_PETROL_INR }: ImpactInput) {
  const hoursPerDay = (junctions * vehiclesPerJunction * secondsSaved) / 3600;
  const fuelLitres = hoursPerDay * idleLitresPerHour;
  const co2Kg = fuelLitres * CO2_KG_PER_LITRE;
  return { hoursPerDay, fuelLitres, co2Kg, rupees: fuelLitres * petrolInr };
}
