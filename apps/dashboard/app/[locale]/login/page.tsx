"use client";
// Email + one-time code sign-in. In development the API echoes the code (AUTH_DEV_ECHO_OTP=1),
// because no email service is configured; in production the code goes by email only.
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { api, setSession, type Session } from "@/lib/api";
import { fmt, useT } from "@/lib/i18n";

function LoginForm() {
  const { t, href } = useT();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ sent: boolean; devCode?: string }>("/auth/otp/request", { method: "POST", json: { email } });
      setDevCode(r.devCode ?? null);
      setStep("code");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await api<Session>("/auth/otp/verify", { method: "POST", json: { email, code } });
      setSession(s);
      // only same-app paths are accepted as a return address
      router.replace(next && /^\/(en|hi)(\/|$)/.test(next) ? next : href("/"));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel w-full max-w-md p-6 md:p-8">
      <div className="mb-6 flex items-center gap-3">
        <span aria-hidden className="flex h-12 w-6 flex-col items-center justify-between rounded-md bg-[var(--panel-2)] py-1.5 ring-1 ring-[var(--line)]">
          <span className="size-2 rounded-full bg-[#ff3b30]/25" />
          <span className="size-2 rounded-full bg-[#ffb020]/25" />
          <span className="size-2 rounded-full bg-[#22c55e] shadow-[0_0_8px_#22c55e]" />
        </span>
        <div>
          <p className="eyebrow">{t.app.name}</p>
          <h1 className="mt-1 text-xl font-semibold">{t.login.title}</h1>
        </div>
      </div>
      <p className="muted mb-5 text-sm">{t.login.lead}</p>

      {step === "email" ? (
        <form onSubmit={send} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            {t.login.email}
            <input className="field" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <button className="btn btn-primary" disabled={busy}>{t.login.send}</button>
        </form>
      ) : (
        <form onSubmit={verify} className="flex flex-col gap-3">
          <p className="text-sm">{fmt(t.login.sent, { email })}</p>
          {devCode && <p className="panel-2 p-2.5 text-xs">{fmt(t.login.devCode, { code: devCode })}</p>}
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            {t.login.code}
            <input className="field num tracking-[0.4em]" inputMode="numeric" pattern="\d{6}" maxLength={6} required autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
          </label>
          <button className="btn btn-primary" disabled={busy || code.length !== 6}>{t.login.verify}</button>
          <button type="button" className="btn" onClick={() => { setStep("email"); setCode(""); }}>{t.login.change}</button>
        </form>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-[#ff3b30]">{fmt(t.login.error, { msg: error })}</p>}
      <p className="faint mt-6 text-xs leading-relaxed">{t.login.roles}</p>
      <p className="faint mt-2 text-xs leading-relaxed">{t.app.readOnly}</p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="grid min-h-dvh place-items-center p-4">
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}
