"use client";
// React hook for the signed-in session (updates when another tab or the API signs us out).
import { useEffect, useState } from "react";
import { getSession, type Session } from "./api";

export function useSession(): { session: Session | null; ready: boolean } {
  const [session, setS] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const read = () => {
      setS(getSession());
      setReady(true);
    };
    read();
    window.addEventListener("hb-session", read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener("hb-session", read);
      window.removeEventListener("storage", read);
    };
  }, []);
  return { session, ready };
}
