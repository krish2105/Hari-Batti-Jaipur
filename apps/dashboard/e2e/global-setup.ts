// Signs in ONCE before all tests (dev OTP) and hands the session to every worker through an
// environment variable. Requesting a code per test would race: a new code replaces the old one.
const API = process.env.HB_API_URL ?? "http://localhost:8000";
const EMAIL = process.env.E2E_EMAIL ?? "admin@haribatti.local";

export default async function globalSetup() {
  const post = (path: string, body: unknown) =>
    fetch(`${API}${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  const req = await post("/auth/otp/request", { email: EMAIL }).catch(() => null);
  if (!req?.ok) throw new Error(`The API at ${API} is not running (start it with AUTH_DEV_ECHO_OTP=1)`);
  const { devCode } = (await req.json()) as { devCode?: string };
  if (!devCode) throw new Error("The API did not echo a dev code: set AUTH_DEV_ECHO_OTP=1");
  const res = await post("/auth/otp/verify", { email: EMAIL, code: devCode });
  if (!res.ok) throw new Error(`Sign-in failed: ${res.status}`);
  process.env.E2E_SESSION = JSON.stringify(await res.json());
}
