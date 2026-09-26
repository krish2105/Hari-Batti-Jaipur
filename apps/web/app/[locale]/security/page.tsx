// /en/security, /hi/security: public summary of security and privacy (P8 W16/W17), no sensitive detail.
import { notFound } from "next/navigation";
import { SubPage } from "@/components/ui/SubPage";
import { getMessages, isLocale, locales } from "@/lib/i18n";

const REPO = "https://github.com/krish2105/Hari-Batti-Jaipur";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function Security({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getMessages(locale);
  const p = t.pages;
  return (
    <SubPage locale={locale} t={t} title={p.securityTitle} lead={p.securityLead}>
      <ul className="grid gap-4 md:grid-cols-2">
        {p.sec.map(([h, body]) => (
          <li key={h} className="surface rounded-3xl p-6"><h2 className="text-lg font-semibold">{h}</h2><p className="mt-2 text-sm text-[var(--ink-2)]">{body}</p></li>
        ))}
      </ul>
      <section className="surface mt-8 rounded-3xl p-6">
        <h2 className="text-lg font-semibold">{p.report}</h2>
        <p className="mt-2 text-sm text-[var(--ink-2)]">{p.reportBody}</p>
        <a className="mt-3 inline-block text-sm font-semibold underline" href={`${REPO}/security/advisories/new`}>{REPO.replace("https://", "")}/security</a>
      </section>
      <p className="mt-8 text-sm text-[var(--ink-2)]">{p.legal} <a className="underline" href={`${REPO}/tree/main/docs/legal`}>docs/legal</a></p>
    </SubPage>
  );
}
