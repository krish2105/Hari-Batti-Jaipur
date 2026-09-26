// /en/pricing, /hi/pricing: the four offers and the free 60-day pilot. Prices are "on request" until
// the owner publishes numbers (P8 W17); no online payments.
import Link from "next/link";
import { notFound } from "next/navigation";
import { SubPage } from "@/components/ui/SubPage";
import { getMessages, isLocale, locales } from "@/lib/i18n";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function Pricing({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getMessages(locale);
  const p = t.pages;
  return (
    <SubPage locale={locale} t={t} title={p.pricingTitle} lead={p.pricingLead}>
      <section className="surface rounded-3xl border-2 border-[#22c55e]/50 p-6 sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-wider text-[#15803d]">₹0</p>
        <h2 className="display mt-1 text-3xl font-semibold">{p.freePilot}</h2>
        <p className="mt-3 max-w-3xl text-[var(--ink-2)]">{p.freePilotBody}</p>
        <Link href={`/${locale}/contact`} className="mt-6 inline-block rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-[var(--bg)] hover:opacity-90">{p.cta}</Link>
      </section>
      <ul className="mt-8 grid gap-4 md:grid-cols-2">
        {p.offers.map((o) => (
          <li key={o.name} className="surface flex flex-col rounded-3xl p-6">
            <h2 className="display text-2xl font-semibold">{o.name}</h2>
            <p className="mt-1 text-sm text-[var(--ink-2)]">{o.who}</p>
            <p className="mt-4"><span className="text-xl font-semibold">{p.onRequest}</span> <span className="text-sm text-[var(--ink-2)]">· {o.unit}</span></p>
            <ul className="mt-4 grid list-disc gap-1.5 pl-5 text-sm">{o.items.map((i) => <li key={i}>{i}</li>)}</ul>
          </li>
        ))}
      </ul>
      <h2 className="display mt-12 text-2xl font-semibold">{p.included}</h2>
      <ul className="mt-3 grid list-disc gap-1.5 pl-6 text-[var(--ink-2)]">{p.includedList.map((i) => <li key={i}>{i}</li>)}</ul>
      <p className="mt-8 text-sm text-[var(--ink-2)]">{p.noPayments}</p>
    </SubPage>
  );
}
