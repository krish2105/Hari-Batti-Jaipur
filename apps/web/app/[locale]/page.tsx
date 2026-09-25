// /en and /hi: the scroll story, statically generated for both languages.
import { notFound } from "next/navigation";
import { Home } from "@/components/Home";
import { getMessages, isLocale } from "@/lib/i18n";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <Home locale={locale} t={getMessages(locale)} />;
}
