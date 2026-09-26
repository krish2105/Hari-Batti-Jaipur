// Live phases from the HariBatti API WebSocket (/ws/signals) with automatic reconnect. When there is
// no feed (offline, API down) the screens fall back to the simulated plan and say so (source SIM).
import { useEffect, useRef, useState } from "react";
import type { PhaseState } from "@haribatti/core";
import { CORRIDOR } from "./signals";

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function useLiveSignals() {
  const states = useRef(new Map<string, PhaseState>());
  const [feed, setFeed] = useState<"live" | "offline">("offline");
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let last = 0;
    const connect = () => {
      // only this corridor's junctions: the API sends each subscription just its own states (P8 W10)
      ws = new WebSocket(`${API_URL.replace(/^http/, "ws")}/ws/signals?junctions=${CORRIDOR.map((j) => j.id).join(",")}`);
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(String(e.data)) as { states?: PhaseState[] };
          for (const s of msg.states ?? []) states.current.set(s.approachId, s);
          if (msg.states?.length) last = Date.now();
        } catch {
          /* ignore a malformed message */
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 4000);
      };
      ws.onerror = () => ws?.close();
    };
    connect();
    const id = setInterval(() => {
      const fresh = Date.now() - last < 8000;
      if (!fresh) states.current.clear(); // stale countdowns are worse than none
      setFeed(fresh ? "live" : "offline");
      setTick((t) => t + 1);
    }, 1000);
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      clearInterval(id);
      ws?.close();
    };
  }, []);
  return { states: states.current, feed, tick };
}
