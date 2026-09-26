// Types for public/data/site.json (aggregates exported by scripts/export_web_data.py).
import raw from "@/public/data/site.json";

export type SitePosition = { lat: number | null; lng: number | null; status: "REGISTRY" | "CANDIDATE" | "PENDING"; confidence?: string; alsoMatches?: string | null };
export type SiteJunction = {
  id: string;
  name: string;
  position: SitePosition;
  approaches: { name: string; main: boolean; pmPeakPcu: number | null }[];
  survey: Record<string, { totalVeh: number; totalPcu: number; twoWheelerPct: number; amPeak: string; amPeakPcu: number; pmPeak: string; pmPeakPcu: number }>;
  hourlyPcu: number[];
  plan: { cycleS: number; mainGreenS: number; crossGreenS: number; label: string; source: string; oversaturated: boolean };
  health: { avg: number; worst: number; worstHour: string; avgRedWaitS: number };
  vcOver09: number;
};
export type VehicleClass = { key: string; label: string; pcu: number; vehicles: number; share: number; models: string[] };
export type Site = {
  generated: string;
  vehicleClasses: { pcuFitR2: number; classes: VehicleClass[]; note: string };
  labels: Record<string, string>;
  corridor: { totalVeh: number; junctions: number; junctionDays: number; twoWheelerPctRange: [number, number]; vcOver09: number; vcRows: number; busiestPmPeak: string };
  junctions: SiteJunction[];
};

export const site = raw as unknown as Site;
export const DAY = "2026-05-11";
export const junctionById = (id: string) => site.junctions.find((j) => j.id === id)!;
/** Six signals in a row on the corridor road, Sanganer Stadium end first. */
export const CORRIDOR = ["J03", "J04", "J05", "J06", "J07", "J08"] as const;
