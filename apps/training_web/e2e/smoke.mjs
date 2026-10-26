import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { registerAndEnter } from "./auth-flow.mjs";
import { verifyTutorDeliveryScenarios } from "./tutor-scenarios.mjs";
import { verifyLearningFlow } from "./learning-flow.mjs";
import { verifyDiagnosisReportFlow } from "./diagnosis-report-flow.mjs";

const browser = await chromium.launch({
  ...(process.env.SIMTROUBLE_BROWSER_CHANNEL ? { channel: process.env.SIMTROUBLE_BROWSER_CHANNEL } : {}),
  headless: true,
});
const baseUrl = process.env.SIMTROUBLE_URL ?? "http://127.0.0.1:5174";

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await registerAndEnter(page, baseUrl, "smoke");
  await page.locator("#tutor-status").filter({ hasText: "可用" }).waitFor({ state: "attached" });
  assert.equal(await page.locator("#case-state").textContent(), "准备就绪");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);

  await page.locator("#play-button").click();
  await page.locator("#case-state").filter({ hasText: "发现异常" }).waitFor({ state: "attached", timeout: 10_000 });
  assert.equal(await page.locator("#fault-callout").isVisible(), true);
  assert.equal(await page.locator("#observations li").count(), 3);

  await page.locator("#reset-button").click();
  assert.equal(await page.locator("#case-state").textContent(), "准备就绪");
  assert.equal(await page.locator("#fault-callout").isHidden(), true);
  await verifyLearningFlow(page);
  await verifyDiagnosisReportFlow(page);
  assert.deepEqual(errors, []);
  await verifyTutorDeliveryScenarios(browser, baseUrl);

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await registerAndEnter(mobile, baseUrl, "mobile");
  assert.equal(await mobile.locator("#play-button").isVisible(), true);
  assert.equal(await mobile.locator("#cad-viewport canvas").isVisible(), true);
  const mobileWidth = await mobile.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert.equal(mobileWidth.scroll, mobileWidth.client);
  await mobile.close();
  console.log("E2E OK: READY -> FAILURE_OBSERVED -> RESET");
  console.log("E2E OK: Session, Evidence, Hypothesis flow and recoverable error");
  console.log("E2E OK: Diagnosis submit, report retry, five dimensions, and create-once guard");
  console.log("E2E OK: Tutor LLM success and timeout/malformed/leakage fallback delivery");
  console.log("E2E OK: 390px responsive viewport");
} finally {
  await browser.close();
}
