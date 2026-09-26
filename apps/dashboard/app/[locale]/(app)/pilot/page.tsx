"use client";
// Pilot mode (P8 W13): pilot dates and progress, the success-measure tracker (baseline vs now, each
// value source-labelled or "not measured yet"), officer notes and pins, the weekly 5-question
// review, the log of timing changes officers made, and the useful/not-useful summary.
import Link from "next/link";
import { ChangeLog, FeedbackPanel, KpiTracker, NotesPanel, PilotDates, TenantPicker, WeeklyReview } from "@/components/pilot";
import { ErrorNote, Loading, PageHead } from "@/components/ui";
import { roleAtLeast, useApi } from "@/lib/api";
import { usePilot } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { useT } from "@/lib/i18n";
import type { Pilot, Tenant } from "@/lib/types";

export default function PilotPage() {
  const { t, href } = useT();
  const { session } = useSession();
  const { tenant } = usePilot();
  const detail = useApi<Tenant>(tenant ? `/tenants/${tenant.id}` : null);
  const pilotId = tenant?.pilots[0]?.id;
  const pilot = useApi<Pilot>(pilotId ? `/pilots/${pilotId}` : null);
  const sites = detail.data?.sites ?? [];

  return (
    <>
      <PageHead title={t.pilot.title} lead={t.pilot.lead}>
        <TenantPicker />
        {tenant?.demo && <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">{t.pilot.demoTag}</span>}
        {pilotId && <Link className="btn btn-primary" href={href(`/pilot/evidence?pilot=${pilotId}`)}>{t.pilot.evidence}</Link>}
        {roleAtLeast(session?.role, "Admin") && <Link className="btn" href={href("/onboarding")}>{t.pilot.onboard}</Link>}
      </PageHead>
      <ErrorNote error={pilot.error ?? detail.error} />
      {!pilot.data || !detail.data ? <Loading /> : (
        <div key={tenant?.id} className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="flex min-w-0 flex-col gap-4">
            <PilotDates pilot={pilot.data} onSaved={pilot.refresh} />
            <KpiTracker pilot={pilot.data} onSaved={pilot.refresh} />
            <ChangeLog tenantId={detail.data.id} sites={sites} />
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            <WeeklyReview pilotId={pilot.data.id} />
            <NotesPanel tenantId={detail.data.id} sites={sites} />
            <FeedbackPanel tenantId={detail.data.id} />
          </div>
        </div>
      )}
    </>
  );
}
