// Pilot operations end to end (P8 W13), desktop only:
//  1. onboard a new organisation through the wizard and check it takes well under 15 minutes,
//  2. vote "useful" on an insight and see the vote on the pilot page,
//  3. generate the Pilot Evidence Pack as a PDF in English and Hindi (Chromium's print-to-PDF),
//  4. archive the test organisation again (archived tenants are hidden; nothing is deleted).
import { expect, test, type Page } from "@playwright/test";
import en from "../messages/en.json";
import hi from "../messages/hi.json";

const API = process.env.HB_API_URL ?? "http://localhost:8000";
const session = () => JSON.parse(process.env.E2E_SESSION ?? "{}") as { token: string };

test.beforeEach(async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "desktop Chromium only (print-to-PDF, one onboarding per run)");
  await page.addInitScript((v) => localStorage.setItem("hb.dashboard.token", v), process.env.E2E_SESSION ?? "");
});

async function archive(page: Page, id: string) {
  const r = await page.request.patch(`${API}/tenants/${id}`, { headers: { authorization: `Bearer ${session().token}` }, data: { archived: true } });
  expect(r.ok()).toBeTruthy();
}

test("a new organisation is onboarded in under 15 minutes and collects feedback", async ({ page }) => {
  const name = `E2E Campus ${Date.now()}`;
  const t0 = Date.now();
  await page.goto("/en/onboarding");
  const o = en.onboarding;
  await page.getByLabel(o.orgName).fill(name);
  await page.getByLabel(o.kind).selectOption("campus");
  await page.getByRole("button", { name: o.next, exact: true }).click();
  await page.getByLabel(`${o.siteName} 1`).fill("Main Gate");
  await page.getByRole("button", { name: `+ ${o.addSite}` }).click();
  await page.getByLabel(`${o.siteName} 2`).fill("North Gate");
  await page.getByRole("button", { name: o.next, exact: true }).click();
  await expect(page.getByLabel(o.src_SIM)).toBeChecked(); // demo data is labelled SIM
  await page.getByRole("button", { name: o.next, exact: true }).click();
  await page.getByRole("button", { name: `+ ${o.addUser}` }).click();
  await page.getByLabel(o.email).fill("gate.manager@example.test");
  await page.getByRole("button", { name: o.next, exact: true }).click();
  await page.getByLabel(en.pilot.start).fill("2026-10-01");
  await page.getByLabel(en.pilot.end).fill("2026-11-29");
  await page.getByRole("button", { name: o.next, exact: true }).click();
  await expect(page.getByText("Main Gate, North Gate")).toBeVisible();
  await page.getByRole("button", { name: o.create }).click();
  await expect(page.getByRole("status")).toContainText(name);
  const seconds = (Date.now() - t0) / 1000;
  expect(seconds, "onboarding time").toBeLessThan(15 * 60);
  console.log(`[W13] onboarding took ${seconds.toFixed(1)} s in the test (goal < 15 min)`);

  // the new tenant is now the selected one: its pilot page shows the dates and SIM demo tag
  await page.getByRole("link", { name: o.openPilot }).click();
  await expect(page.getByRole("heading", { level: 1, name: en.pilot.title })).toBeVisible();
  await expect(page.getByText(en.pilot.demoTag)).toBeVisible();
  const id = await page.evaluate(() => localStorage.getItem("hb.dashboard.tenant"));
  expect(id).toMatch(/^e2e-campus-/);

  // one-click feedback on an insight, then the pilot page counts it
  await page.goto("/en/audit");
  await page.getByRole("button", { name: en.pilot.useful }).first().click();
  await expect(page.getByRole("button", { name: en.pilot.useful }).first()).toHaveAttribute("aria-pressed", "true");
  await page.goto("/en/pilot");
  await expect(page.getByText("audit.top-fixes")).toBeVisible();

  await archive(page, id!);
});

for (const [locale, m] of [["en", en], ["hi", hi]] as const) {
  test(`evidence pack prints to PDF (${locale})`, async ({ page }) => {
    await page.goto(`/${locale}/pilot/evidence`);
    const pack = page.getByTestId("evidence-pack");
    await expect(pack).toBeVisible({ timeout: 20_000 });
    await expect(pack.getByText(m.evidence.placeholderTag).first()).toBeVisible(); // unmeasured KPIs are marked
    await page.emulateMedia({ media: "print" });
    const pdf = await page.pdf({ format: "A4", printBackground: true });
    expect(pdf.subarray(0, 4).toString()).toBe("%PDF");
    expect(pdf.length).toBeGreaterThan(20_000);
    await test.info().attach(`evidence-${locale}.pdf`, { body: pdf, contentType: "application/pdf" });
  });
}
