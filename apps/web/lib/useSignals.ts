"use client";
// Live PhaseState[]: WebSocket to the API when NEXT_PUBLIC_SIGNALS_WS is set, otherwise (and on any
// failure) the offline mock generator — so the site never breaks in a demo.
import { useEffect, useState } from "react";
import type { PhaseState } from "@haribatti/core";
import { mockSignals } from "./mockSignals";

export function useSignals(): { states: PhaseState[]; live: boolean } {
  // First render uses a fixed time so server HTML and the first client render match (no hydration
  // mismatch); the real clock takes over right after mount.
  const [states, setStates] = useState<PhaseState[]>(() => mockSignals(0));
  const [live, setLive] = useState(false);

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_SIGNALS_WS;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;
    const startMock = () => {
      setLive(false);
      setStates(mockSignals());
      if (!timer) timer = setInterval(() => setStates(mockSignals()), 1000);
    };
    if (url) {
      try {
        const latest = new Map<string, PhaseState>();
        ws = new WebSocket(url);
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data as string) as { states: PhaseState[] };
          for (const s of msg.states) latest.set(s.approachId, s);
          setStates([...latest.values()]);
          setLive(true);
        };
        ws.onerror = startMock;
        ws.onclose = startMock;
      } catch {
        startMock();
      }
    } else {
      startMock();
    }
    return () => {
      if (timer) clearInterval(timer);
      ws?.close();
    };
  }, []);

  return { states, live };
}
