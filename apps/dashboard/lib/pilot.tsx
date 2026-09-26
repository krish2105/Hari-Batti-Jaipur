"use client";
// Pilot context (P8 W13): which tenant the officer is working in (remembered in localStorage) and
// their own "useful / not useful" votes, loaded once for every <Useful> button on the page.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, useApi } from "./api";
import { useSession } from "./session";
import type { FeedbackSummary, Tenant, TenantList } from "./types";

const KEY = "hb.dashboard.tenant";
export const DEFAULT_TENANT = "jaipur-police";

type Ctx = {
  tenants: TenantList | null;
  tenant: Tenant | null;
  tenantId: string;
  setTenantId: (id: string) => void;
  refreshTenants: () => void;
  mine: Record<string, boolean>;
  vote: (insight: string, useful: boolean, page?: string) => Promise<void>;
};

const PilotCtx = createContext<Ctx | null>(null);

export function PilotProvider({ children }: { children: ReactNode }) {
  const { session } = useSession();
  const list = useApi<TenantList>(session ? "/tenants" : null);
  const [tenantId, setId] = useState(DEFAULT_TENANT);
  const [mine, setMine] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved) setId(saved);
    } catch {
      /* private mode */
    }
  }, []);

  // fall back to the first visible tenant when the remembered one is not visible to this user
  const visible = list.data?.tenants ?? [];
  const tenant = visible.find((t) => t.id === tenantId) ?? visible[0] ?? null;
  const effective = tenant?.id ?? tenantId;

  const setTenantId = useCallback((id: string) => {
    setId(id);
    try {
      localStorage.setItem(KEY, id);
    } catch {
      /* private mode */
    }
  }, []);

  useEffect(() => {
    if (!session || !tenant) return;
    let alive = true;
    api<FeedbackSummary>(`/tenants/${tenant.id}/feedback`)
      .then((f) => alive && setMine(f.mine))
      .catch(() => alive && setMine({}));
    return () => {
      alive = false;
    };
  }, [session, tenant]);

  const vote = useCallback(
    async (insight: string, useful: boolean, page?: string) => {
      setMine((m) => ({ ...m, [insight]: useful })); // show it at once; the API call confirms
      await api(`/tenants/${effective}/feedback`, { method: "POST", json: { insight, useful, page } });
    },
    [effective],
  );

  const value = useMemo<Ctx>(
    () => ({ tenants: list.data, tenant, tenantId: effective, setTenantId, refreshTenants: list.refresh, mine, vote }),
    [list.data, list.refresh, tenant, effective, setTenantId, mine, vote],
  );
  return <PilotCtx.Provider value={value}>{children}</PilotCtx.Provider>;
}

export function usePilot(): Ctx {
  const c = useContext(PilotCtx);
  if (!c) throw new Error("usePilot outside PilotProvider");
  return c;
}

// pure helpers live in pilotMath.ts so they can be unit-tested without JSX
export { improved, insightKey, progressShare } from "./pilotMath";
