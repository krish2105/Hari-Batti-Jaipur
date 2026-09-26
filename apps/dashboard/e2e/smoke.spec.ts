// Smoke test: sign in with the development OTP, then open every screen in English and Hindi and
// check that it renders its heading, throws no browser errors and does not scroll sideways.
// The API must echo OTP codes (AUTH_DEV_ECHO_OTP=1) — that only ever happens on a laptop.
import { expect, test } from "@playwright/test";
import en from "../messages/en.json";
import hi from "../messages/hi.json";

const EMAIL = process.env.E2E_EMAIL ?? "admin@haribatti.local";
const MESSAGES = { en, hi } as const;

// path → heading text (the junction page heading is its id + name)
const SCREENS = (m: typeof en): [string, string][] => [
  ["", m.overview.title],
  ["/live", m.live.title],
  ["/junction/J05", "J05"],
  ["/audit", m.audit.title],
  ["/plans", m.plans.title],
  ["/insights", m.insights.title],
  ["/copilot", m.copilot.title],
  ["/reports", m.reports.title],
  ["/events", m.events.title],
  ["/monthly", m.monthly.title],
  ["/admin", m.admin.title],
];

test("sign in through the login page with the dev code", async ({ page }, info) => {
  // once per run: two projects requesting codes for the same email at once would race
  test.skip(info.project.name !== "desktop", "UI sign-in runs in the desktop project only");
  await page.goto("/en/login");
  await page.getByLabel(en.login.email).fill(EMAIL);
  await page.getByRole("button", { name: en.login.send }).click();
  const hint = page.getByText(/Development mode: the code is (\d{6})/);
  await expect(hint).toBeVisible();
  const code = (await hint.textContent())?.match(/(\d{6})/)?.[1] ?? "";
  await page.getByLabel(en.login.code).fill(code);
  await page.getByRole("button", { name: en.login.verify }).click();
  await expect(page.getByRole("heading", { level: 1, name: en.overview.title })).toBeVisible();
});

for (const locale of ["en", "hi"] as const) {
  test.describe(`every screen in ${locale}`, () => {
    test.beforeEach(async ({ page }) => {
      // the session from e2e/global-setup.ts (one sign-in for the whole run)
      await page.addInitScript((v) => localStorage.setItem("hb.dashboard.token", v), process.env.E2E_SESSION ?? "");
    });

    for (const [path, heading] of SCREENS(MESSAGES[locale] as typeof en)) {
      test(`${locale}${path || "/"}`, async ({ page }) => {
        const errors: string[] = [];
        page.on("pageerror", (e) => errors.push(e.message));
        await page.goto(`/${locale}${path}`);
        await expect(page.getByRole("heading", { level: 1 })).toContainText(heading, { timeout: 20_000 });
        await expect(page.locator("html")).toHaveAttribute("lang", locale);
        await page.waitForTimeout(800); // let the data calls settle
        const [client, scroll] = await page.evaluate(() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]);
        expect(scroll, "page scrolls sideways").toBeLessThanOrEqual(client + 1);
        expect(errors).toEqual([]);
      });
    }
  });
}
