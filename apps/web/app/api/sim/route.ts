// GET /api/sim — latest PhaseState[]: proxies the HariBatti API when SIM_API_URL is set,
// otherwise returns the built-in simulated signals (so the site works with no backend).
import { NextResponse } from "next/server";
import { mockSignals } from "@/lib/mockSignals";

export const dynamic = "force-dynamic";

export async function GET() {
  const api = process.env.SIM_API_URL;
  if (api) {
    try {
      const r = await fetch(`${api}/signals/latest`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
      if (r.ok) return NextResponse.json({ source: "api", ...(await r.json()) });
    } catch {
      /* fall through to the mock */
    }
  }
  return NextResponse.json({ source: "mock", states: mockSignals() });
}
