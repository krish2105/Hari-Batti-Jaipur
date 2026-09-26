// /en/contact, /hi/contact: pilot request form (P8 W17).
import { notFound } from "next/navigation";
import { ContactForm } from "@/components/pages/ContactForm";
import { SubPage } from "@/components/ui/SubPage";
import { getMessages, isLocale, locales } from "@/lib/i18n";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function Contact({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getMessages(locale);
  return (
    <SubPage locale={locale} t={t} title={t.pages.contactTitle} lead={t.pages.contactLead}>
      <ContactForm t={t.pages} />
    </SubPage>
  );
}
