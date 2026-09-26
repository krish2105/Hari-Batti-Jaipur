// Field study (P8 W14): invite-only enrolment, server-randomised runs (advice ON or OFF) and trace
// upload. The phone records GPS once a second ONLY while a study run is open; the server removes the
// first and last 200 m before storing anything. The study token lives on this phone only.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { metres, type LatLng } from "./geo";
import { API_URL } from "./live";
import type { CorridorJunction } from "./signals";

export type Arm = "advice" | "control";
export type Point = [number, number, number, number]; // [t_s, lat, lng, speed_kmh]
export type Enrolment = { participantId: string; token: string; runs: number };
const KEY = "hb.mobile.study";
export const END_BEYOND_M = 250; // keep recording past the last signal so the 200 m trim leaves it in

/** Run ends when the rider has reached the last signal of their direction and gone 250 m past it. */
export function shouldEnd(p: LatLng, eastbound: boolean, js: CorridorJunction[], passedLast: boolean): { passed: boolean; end: boolean } {
  const last = eastbound ? js[js.length - 1]! : js[0]!;
  const d = metres(p, { lat: last.lat, lng: last.lng });
  const passed = passedLast || d < 25;
  return { passed, end: passed && d >= END_BEYOND_M };
}

/** A 1 Hz buffer: keeps at most one point per whole second. */
export function addPoint(buf: Point[], t: number, p: LatLng, speedKmh: number): Point[] {
  const last = buf[buf.length - 1];
  if (last && t - last[0] < 0.9) return buf;
  return [...buf, [Math.round(t * 10) / 10, p.lat, p.lng, Math.max(0, Math.round(speedKmh * 10) / 10)]];
}

async function post<T>(path: string, body: unknown, token?: string): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body ?? {}),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : `${r.status}`);
  return j as T;
}

export async function loadEnrolment(): Promise<Enrolment | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Enrolment) : null;
  } catch {
    return null;
  }
}

async function saveEnrolment(e: Enrolment | null) {
  if (e) await AsyncStorage.setItem(KEY, JSON.stringify(e));
  else await AsyncStorage.removeItem(KEY);
}

export async function enrol(code: string, vehicle: string): Promise<Enrolment> {
  const r = await post<{ participantId: string; token: string }>("/study/enrol", { code: code.trim().toUpperCase(), vehicle, consent: true });
  const e = { ...r, runs: 0 };
  await saveEnrolment(e);
  return e;
}

export const startRun = (e: Enrolment) => post<{ runId: number; arm: Arm; runNumber: number }>("/study/runs", {}, e.token);

export async function upload(e: Enrolment, runId: number, points: Point[], direction: "east" | "west") {
  const r = await post<{ pointsKept: number; pointsTrimmed: number }>(`/study/runs/${runId}/trace`, { points, direction }, e.token);
  await saveEnrolment({ ...e, runs: e.runs + 1 });
  return r;
}

export async function withdraw(e: Enrolment) {
  await post("/study/withdraw", {}, e.token);
  await saveEnrolment(null);
}
