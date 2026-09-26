"use client";
// Live PhaseState stream from the API WebSocket (/ws/signals), with automatic reconnect.
// Keeps the newest state per approach plus a tracker for alerts (lib/alerts.ts).
import { useEffect, useRef, useState } from "react";
import { API_URL } from "./api";
import { alertsFor, track, type Alert, type Track } from "./alerts";
import { usePlanClock } from "./planClock";
import type { Phase } from "./types";

const PILOT_JUNCTIONS = "J01,J02,J03,J04,J05,J06,J07,J08";

export type Feed = "connecting" | "live" | "waiting" | "down" | "planClock";

export function useLive(junction?: string) {
  const tracks = useRef(new Map<string, Track>());
  const [states, setStates] = useState<Phase[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [feed, setFeed] = useState<Feed>("connecting");

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let closed = false;
    let lastMsg = 0;
    // only the pilot junctions (or one): the API sends each subscription just its own states (P8 W10)
    const url = `${API_URL.replace(/^http/, "ws")}/ws/signals?junctions=${junction ?? PILOT_JUNCTIONS}`;

    const connect = () => {
      ws = new WebSocket(url);
      ws.onopen = () => setFeed("waiting");
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data as string) as { states?: Phase[] };
        const now = Date.now();
        for (const s of msg.states ?? []) tracks.current.set(s.approachId, track(tracks.current.get(s.approachId), s, now));
        if (msg.states?.length) {
          lastMsg = now;
          setFeed("live");
        }
      };
      ws.onclose = () => {
        setFeed("down");
        if (!closed) retry = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws?.close();
    };
    connect();

    // repaint once a second (countdowns tick even between messages) and recompute alerts
    const tick = setInterval(() => {
      const now = Date.now();
      setStates([...tracks.current.values()].map((t) => t.state).sort((a, b) => a.approachId.localeCompare(b.approachId)));
      setAlerts(alertsFor(tracks.current.values(), now));
      if (lastMsg && now - lastMsg > 5000) setFeed((f) => (f === "live" ? "waiting" : f));
    }, 1000);

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      clearInterval(tick);
      ws?.close();
    };
  }, [junction]);

  // no live phases for a while: fall back to the assumed plans on the clock (labelled SIM)
  const [fallback, setFallback] = useState(false);
  useEffect(() => {
    if (feed === "live") return setFallback(false);
    const id = setTimeout(() => setFallback(true), 4000);
    return () => clearTimeout(id);
  }, [feed]);
  const clock = usePlanClock(fallback && feed !== "live", junction);
  if (feed !== "live" && fallback && clock.length) return { states: clock, alerts: [], feed: "planClock" as Feed };
  return { states, alerts, feed };
}
