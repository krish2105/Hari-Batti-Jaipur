"use client";
// Client for the HariBatti API (services/api). The API is read-only towards signals: the only
// writes are sign-in, citizen report status, Plan Studio simulations and audit-log events.
import { useCallback, useEffect, useRef, useState } from "react";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "hb.dashboard.token";

export type Role = "Viewer" | "Operator" | "Admin";
export type Session = { token: string; email: string; role: Role };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** The signed-in officer, kept in localStorage (the token expires after 12 h on the API side). */
export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function setSession(s: Session | null) {
  try {
    if (s) localStorage.setItem(TOKEN_KEY, JSON.stringify(s));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode: the session just won't survive a reload */
  }
  window.dispatchEvent(new Event("hb-session"));
}

/** fetch() with the bearer token and readable errors (the API sends {"detail": "..."}). */
export async function api<T>(path: string, init: RequestInit & { json?: unknown; timeoutMs?: number } = {}): Promise<T> {
  const s = getSession();
  const headers = new Headers(init.headers);
  if (s) headers.set("authorization", `Bearer ${s.token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("content-type", "application/json");
    body = JSON.stringify(init.json);
  }
  let res: Response;
  const ctrl = new AbortController();
  const timer = init.timeoutMs ? setTimeout(() => ctrl.abort(), init.timeoutMs) : null;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, body, signal: ctrl.signal });
  } catch {
    if (ctrl.signal.aborted) throw new ApiError(408, "timed out"); // our own time limit, not a dead API
    window.dispatchEvent(new CustomEvent("hb-api", { detail: false }));
    throw new ApiError(0, "API not reachable");
  } finally {
    if (timer) clearTimeout(timer);
  }
  window.dispatchEvent(new CustomEvent("hb-api", { detail: true }));
  if (res.status === 401) setSession(null);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  return (await res.json()) as T;
}

/** Load one GET endpoint; re-runs when the path changes. `refresh` re-fetches on demand. */
export function useApi<T>(path: string | null, opts: { pollMs?: number } = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const current = useRef(path);
  current.current = path;

  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try {
      const d = await api<T>(path);
      if (current.current === path) {
        setData(d);
        setError(null);
      }
    } catch (e) {
      if (current.current === path) setError(e as ApiError);
    } finally {
      if (current.current === path) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    load();
    if (!opts.pollMs) return;
    const id = setInterval(load, opts.pollMs);
    return () => clearInterval(id);
  }, [load, opts.pollMs]);

  // come back automatically when the API returns after being offline
  useEffect(() => {
    const onApi = (e: Event) => {
      if ((e as CustomEvent<boolean>).detail && error?.status === 0) load();
    };
    window.addEventListener("hb-api", onApi);
    return () => window.removeEventListener("hb-api", onApi);
  }, [error, load]);

  return { data, error, loading, refresh: load };
}

/** Record an export (PDF, CSV, printed report) in the API audit log. Never blocks the export. */
export function logExport(action: "export_pdf" | "export_csv" | "print_report", detail: Record<string, unknown> = {}) {
  api("/audit/event", { method: "POST", json: { action, detail } }).catch(() => undefined);
}

/** Turn rows into a CSV download in the browser. */
export function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0] ?? {});
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function roleAtLeast(role: Role | undefined, need: Role) {
  const rank: Record<Role, number> = { Viewer: 0, Operator: 1, Admin: 2 };
  return role !== undefined && rank[role] >= rank[need];
}
