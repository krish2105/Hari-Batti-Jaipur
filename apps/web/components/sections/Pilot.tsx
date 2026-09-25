// Section 10 + footer: the pilot ask, contact (mailto), attribution and the independence note.
import type { Messages } from "@/lib/i18n";
import { Eyebrow, Reveal, Section } from "./Reveal";

const REPO = "https://github.com/krish2105/Hari-Batti-Jaipur";

export function Pilot({ t }: { t: Messages }) {
  // Contact address is opt-in (set NEXT_PUBLIC_CONTACT_EMAIL); otherwise people reach us via GitHub.
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL;
  const mail = email ? `mailto:${email}?subject=${encodeURIComponent(t.pilot.subject)}` : `${REPO}/issues/new?title=${encodeURIComponent(t.pilot.subject)}`;
  return (
    <>
      <Section id="pilot">
        <Reveal className="surface max-w-3xl rounded-3xl p-6 sm:p-10">
          <Eyebrow>{t.pilot.eyebrow}</Eyebrow>
          <h2 className="display text-4xl font-semibold sm:text-6xl">{t.pilot.title}</h2>
          <p className="mt-6 text-lg text-[var(--ink-2)]">{t.pilot.p1}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href={mail} className="rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-[var(--bg)] hover:opacity-90">{t.pilot.cta}</a>
            <a href={REPO} className="rounded-full border border-[var(--line)] px-6 py-3 font-semibold hover:border-[var(--accent)]">{t.pilot.code}</a>
          </div>
          <p className="mt-8 text-sm text-[var(--ink-2)]">{t.pilot.team}</p>
        </Reveal>
      </Section>
      <footer className="relative border-t border-[var(--line)] bg-[var(--bg)] px-4 py-10 text-sm text-[var(--ink-2)]">
        <div className="mx-auto grid max-w-6xl gap-2">
          <p>{t.footer.affiliation}</p>
          <p>{t.footer.data}</p>
          <p>{t.footer.privacy}</p>
          <p>{t.footer.osm} <a className="underline" href="https://www.openstreetmap.org/copyright">openstreetmap.org/copyright</a></p>
          <p>© 2026 HariBatti</p>
        </div>
      </footer>
    </>
  );
}
