// /en/status and /hi/status: public service status. Honest about what is not public yet: the
// pilot server's own per-minute uptime ledger lives in the dashboard until hosting in India (W18).
import { notFound } from "next/navigation";
import { SubPage } from "@/components/ui/SubPage";
import { getMessages, isLocale, locales } from "@/lib/i18n";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function Status({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getMessages(locale);
  const p = t.pages;
  const rows: [string, string, "ok" | "pending"][] = [
    [p.website, p.websiteOk, "ok"],
    [p.pilotServer, p.pilotServerNote, "pending"],
    [p.app, p.appNote, "pending"],
  ];
  return (
    <SubPage locale={locale} t={t} title={p.statusTitle} lead={p.statusLead}>
      <ul className="grid gap-4">
        {rows.map(([name, note, state]) => (
          <li key={name} className="surface flex flex-col gap-2 rounded-2xl p-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="max-w-2xl"><p className="font-semibold">{name}</p><p className="mt-1 text-sm text-[var(--ink-2)]">{note}</p></div>
            <span className={`inline-flex shrink-0 items-center gap-2 self-start rounded-full px-3 py-1 text-sm font-semibold ${state === "ok" ? "bg-[#22c55e]/15 text-[#15803d]" : "bg-[#ffb020]/15 text-[#b7791f]"}`}>
              <span aria-hidden className="size-2 rounded-full" style={{ background: state === "ok" ? "#22c55e" : "#ffb020" }} />
              {state === "ok" ? p.operational : p.notPublic}
            </span>
          </li>
        ))}
      </ul>
      <h2 className="display mt-12 text-2xl font-semibold">{p.checks}</h2>
      <ul className="mt-4 grid list-disc gap-2 pl-6 text-[var(--ink-2)]">{p.checksList.map((c) => <li key={c}>{c}</li>)}</ul>
      <p className="mt-8 text-sm text-[var(--ink-2)]">{p.updated}</p>
    </SubPage>
  );
}
